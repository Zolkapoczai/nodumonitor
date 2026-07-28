"""
Migracio: a Khoros (Autodesk + Graphisoft) posztok deduplikalasa.

MIT JAVIT: a playwright_connector a nyers keresesi URL-t tette az `external_id`-be,
ami tartalmazza a futasonkent valtozo `search-action-id` parametert, ezert a
`UNIQUE(platform, external_id)` sosem fogott. Meres (2026-07-28): 1309 khoros-poszt
= 33 valodi szal (39,7x). Reszletek: docs/04-rendszer-audit-2026-07-28.md §1.1.

MIT TESZ:
  1. Minden khoros-posztra kiszamolja a kanonikus kulcsot (connectors/khoros_url.py —
     UGYANAZ a fuggveny, amit a connector is hasznal).
  2. Csoportonkent kivalaszt egy TULELOT. A sorrend fontos, mert a duplikatumok
     kozott van, amelyikhez mar signal vagy draft tartozik, es azt NEM dobjuk el:
        (a) akinek van draftja  -> a legtobb emberi munka van benne
        (b) akinek van signalja -> a classifier mar fizetett erte
        (c) a legkisebb id      -> a legkorabban latott peldany
     A tulelo statusza a csoport "legelorehaladottabb" statusza lesz (processed >
     alerted > draft_ready > new), hogy egy mar kikuldott jel ne kerulhessen vissza
     'new'-ba es ne menjen ki masodszor.
  3. A tulelo `external_id`-jet a kanonikus kulcsra, az `url`-jet a kanonikus URL-re
     irja — igy a KOVETKEZO connector-futas mar utkozik vele, es nem szur be ujra.
  4. A duplikatumokat torli, es velük a rajuk mutato `signals`/`drafts` sorokat
     (nincs ON DELETE CASCADE, ezert kezzel).

HASZNALAT:
    python migrations/2026_07_28_khoros_dedup.py            # dry-run, semmit nem ir
    python migrations/2026_07_28_khoros_dedup.py --apply    # vegrehajtja

Az --apply ELOTT sajat snapshotot kesyzit a backups/-ba (storage.backup), fuggetlenul
a napi mentestol. Egyetlen tranzakcioban fut: vagy minden, vagy semmi.
"""
import argparse
import os
import sqlite3
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from connectors.khoros_url import canonical_external_id, canonical_thread_url  # noqa: E402

KHOROS_PLATFORMS = ("autodesk", "graphisoft")

# Minel elorehaladottabb, annal nagyobb szam. A tulelo a csoport maximumat kapja.
_STATUS_RANK = {"new": 0, "draft_ready": 1, "alerted": 2, "processed": 3}


def _status_rank(status: str) -> int:
    return _STATUS_RANK.get(status or "new", 0)


def _best_status(statuses: list[str]) -> str:
    return max(statuses, key=_status_rank)


def analyze(db_path: str) -> dict:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    placeholders = ",".join("?" * len(KHOROS_PLATFORMS))
    rows = conn.execute(f"""
        SELECT p.id, p.platform, p.external_id, p.url, p.status, p.fetched_at,
               (SELECT COUNT(*) FROM signals s WHERE s.post_id = p.id) AS n_signals,
               (SELECT COUNT(*) FROM drafts d WHERE d.post_id = p.id)  AS n_drafts
        FROM posts p
        WHERE p.platform IN ({placeholders})
        ORDER BY p.id
    """, KHOROS_PLATFORMS).fetchall()
    conn.close()

    groups: dict[tuple, list[sqlite3.Row]] = defaultdict(list)
    unkeyed = []
    for r in rows:
        key = canonical_external_id(r["url"] or r["external_id"])
        if not key:
            unkeyed.append(r)
            continue
        groups[(r["platform"], key)].append(r)

    plan = []
    for (platform, key), members in groups.items():
        survivor = sorted(
            members,
            key=lambda r: (-(r["n_drafts"] > 0), -(r["n_signals"] > 0), r["id"]),
        )[0]
        dups = [r for r in members if r["id"] != survivor["id"]]
        plan.append({
            "platform": platform,
            "key": key,
            "survivor": survivor,
            "dups": dups,
            "new_status": _best_status([r["status"] for r in members]),
            "canonical_url": canonical_thread_url(survivor["url"] or ""),
        })

    return {
        "posts_total": len(rows),
        "groups": len(groups),
        "unkeyed": unkeyed,
        "plan": plan,
        "dup_posts": sum(len(g["dups"]) for g in plan),
        "dup_signals": sum(r["n_signals"] for g in plan for r in g["dups"]),
        "dup_drafts": sum(r["n_drafts"] for g in plan for r in g["dups"]),
        "status_promotions": [
            g for g in plan if g["new_status"] != g["survivor"]["status"]
        ],
    }


def report(res: dict) -> None:
    print(f"Khoros-poszt osszesen        : {res['posts_total']}")
    print(f"Kanonikus csoport (valodi szal): {res['groups']}")
    print(f"Torlendo duplikatum poszt   : {res['dup_posts']}")
    print(f"  velük torlendo signal     : {res['dup_signals']}")
    print(f"  velük torlendo draft      : {res['dup_drafts']}")
    print(f"Kulcs nelkuli poszt (marad) : {len(res['unkeyed'])}")
    print(f"Statusz-oroklés a tulelore  : {len(res['status_promotions'])} csoportban")
    if res["posts_total"]:
        print(f"Duplikacios faktor          : {res['posts_total'] / max(res['groups'], 1):.1f}x")
    print()
    print("Peldak (max 5 csoport):")
    for g in sorted(res["plan"], key=lambda g: -len(g["dups"]))[:5]:
        s = g["survivor"]
        print(f"  [{g['platform']}] {g['key']}: tulelo id={s['id']} "
              f"(signal={s['n_signals']}, draft={s['n_drafts']}, statusz {s['status']} -> {g['new_status']}), "
              f"torlendo {len(g['dups'])} db")


def apply(db_path: str, res: dict) -> None:
    from storage.backup import backup_db
    snap = backup_db(db_path, keep=99)   # keep=99: ezt a snapshotot NE rotalja el
    print(f"[migracio] Snapshot a migracio elott: {snap}")

    dup_ids = [r["id"] for g in res["plan"] for r in g["dups"]]
    conn = sqlite3.connect(db_path, timeout=30)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("BEGIN")

        # 1. tulelok: kanonikus kulcs + URL + oroklott statusz
        for g in res["plan"]:
            conn.execute(
                "UPDATE posts SET external_id = ?, url = ?, status = ? WHERE id = ?",
                (g["key"], g["canonical_url"] or g["survivor"]["url"],
                 g["new_status"], g["survivor"]["id"]),
            )

        # 2. duplikatumok fuggosegei, majd a posztok — 400-as csomagokban, hogy a
        #    SQLite valtozo-limitjebe (999) belefér
        for i in range(0, len(dup_ids), 400):
            chunk = dup_ids[i:i + 400]
            q = ",".join("?" * len(chunk))
            conn.execute(f"DELETE FROM signals WHERE post_id IN ({q})", chunk)
            conn.execute(f"DELETE FROM drafts  WHERE post_id IN ({q})", chunk)
            conn.execute(f"DELETE FROM posts   WHERE id      IN ({q})", chunk)

        conn.commit()
        print(f"[migracio] Kesz: {len(dup_ids)} duplikatum poszt torolve, "
              f"{len(res['plan'])} tulelo kanonizalva.")
    except Exception:
        conn.rollback()
        print("[migracio] HIBA — rollback, a DB valtozatlan.")
        raise
    finally:
        conn.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="Khoros-poszt deduplikacio")
    ap.add_argument("--apply", action="store_true", help="Vegrehajtas (nelkule dry-run)")
    ap.add_argument("--db", default=None, help="DB-utvonal (default: a projekt nodu_monitor.db-je)")
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = args.db or os.path.join(root, "nodu_monitor.db")
    print(f"Adatbazis: {db_path}\n")

    res = analyze(db_path)
    report(res)

    if not args.apply:
        print("\nDRY-RUN — semmi nem valtozott. Vegrehajtas: --apply")
        return
    print()
    apply(db_path, res)

    after = analyze(db_path)
    print()
    print("--- ELLENORZES a migracio utan ---")
    print(f"Khoros-poszt: {after['posts_total']} | csoport: {after['groups']} | "
          f"maradt duplikatum: {after['dup_posts']}")
    if after["dup_posts"]:
        print("FIGYELEM: maradt duplikatum — vizsgald meg.")
        sys.exit(1)


if __name__ == "__main__":
    main()
