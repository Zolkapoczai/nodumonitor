"""
A 2026-07-28-i ket P0-s javitas tesztje (docs/04-rendszer-audit-2026-07-28.md).

A) Khoros-dedup (§1.1): a kanonikus kulcs a valtozo `search-action-id`-t es a
   nezet-modositokat kiszuri, tehat ugyanarra a hozzaszolasra MINDIG ugyanaz a
   kulcs — es az `insert_post` masodik beszurasa mar utkozik.
B) Digest-halmaz (§1.2): a statusz-szures az SQL-ben van, tehat a `limit` NEM
   vaghatja le a varakozo jeleket. A regresszio-teszt szandekosan olyan adatot
   allit elo, ahol a regi (Pythonban utoszuro) logika bukott volna.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from connectors.khoros_url import canonical_external_id, canonical_thread_url  # noqa: E402
from storage.db import (  # noqa: E402
    init_db, insert_post, count_opportunities, get_opportunities, get_connection,
)

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


# --- A) kanonizalas ---------------------------------------------------------
U1 = ("https://forums.autodesk.com/t5/revit-forum/archicad-revit-ifc/m-p/13623288/"
      "highlight/true?search-action-id=1351577432174&search-result-uid=13623288#M136")
U2 = ("https://forums.autodesk.com/t5/revit-forum/archicad-revit-ifc/m-p/13623288/"
      "highlight/true?search-action-id=9999999999999&search-result-uid=13623288#M999")
U3 = "https://forums.autodesk.com/t5/revit-forum/archicad-revit-ifc/m-p/13623288"
OTHER = ("https://forums.autodesk.com/t5/revit-forum/other-thread/m-p/10000001/"
         "highlight/true?search-action-id=123#M1")
GRAPHI = ("https://community.graphisoft.com/t5/Modeling/editable-topography/ta-p/304118"
          "?search-action-id=157244860983&search-result-uid=304118")

check("A1 valtozo search-action-id ugyanazt a kulcsot adja",
      canonical_external_id(U1) == canonical_external_id(U2) == "forums.autodesk.com:13623288",
      canonical_external_id(U1))
check("A2 a nezet-modosito nelkuli URL is ugyanaz", canonical_external_id(U3) == canonical_external_id(U1))
check("A3 mas szal mas kulcs", canonical_external_id(OTHER) != canonical_external_id(U1))
check("A4 ta-p (tkb cikk) is felismerve",
      canonical_external_id(GRAPHI) == "community.graphisoft.com:304118", canonical_external_id(GRAPHI))
check("A5 a host resze a kulcsnak (message-id csak forumon belul egyedi)",
      canonical_external_id(U1).startswith("forums.autodesk.com:"))
check("A6 kanonikus URL query/fragment/highlight nelkul",
      canonical_thread_url(U1) ==
      "https://forums.autodesk.com/t5/revit-forum/archicad-revit-ifc/m-p/13623288",
      canonical_thread_url(U1))
check("A7 ures bemenet nem hasal el", canonical_external_id("") == "" and canonical_thread_url("") == "")
check("A8 felismerhetetlen URL-nel a kanonikus URL a fallback",
      canonical_external_id("https://example.invalid/valami?x=1") == "https://example.invalid/valami")

# --- A) dedup a DB-ben ------------------------------------------------------
db = os.path.join(tempfile.mkdtemp(prefix="nodu-dedup-"), "t.db")
init_db(db)


def khoros_post(href, title="Archicad to Revit IFC"):
    return {
        "source": "playwright", "platform": "autodesk",
        "external_id": canonical_external_id(href) or href,
        "url": canonical_thread_url(href) or href,
        "author": "a", "title": title, "body": "b",
        "created_at": "2026-07-20T10:00:00", "fetched_at": "2026-07-20T10:00:00",
        "keywords": "ifc", "score": 5,
    }


check("A9 elso beszuras uj", insert_post(db, khoros_post(U1)) is True)
check("A10 masodik futas UGYANARRA a szalra mar utkozik", insert_post(db, khoros_post(U2)) is False)
check("A11 harmadik forma sem szur be ujat", insert_post(db, khoros_post(U3)) is False)
check("A12 mas szal viszont bejon", insert_post(db, khoros_post(OTHER)) is True)
conn = get_connection(db)
check("A13 a DB-ben 2 poszt van, nem 4",
      conn.execute("SELECT COUNT(*) c FROM posts").fetchone()["c"] == 2)
conn.close()

# --- B) digest-halmaz ------------------------------------------------------
# 130 fajdalom-jel, KEVERT statuszban. A rendezes severity DESC, ezert a regi
# kod (limit=100 + Pythonban utoszures) a magas severity-ju 'alerted' sorokkal
# tolte volna fel a 100-as ablakot, es a 'new' jelek nagy resze STRANDOLT volna.
db2 = os.path.join(tempfile.mkdtemp(prefix="nodu-digest-"), "t.db")
init_db(db2)
conn = get_connection(db2)
NEW_COUNT, ALERTED_COUNT = 30, 100
for i in range(NEW_COUNT + ALERTED_COUNT):
    is_new = i < NEW_COUNT
    # a 'new' jelek sev3-asok, az 'alerted'-ek sev4-esek: pontosan az a minta,
    # ami a rendezes miatt kiszoritja a varakozokat
    conn.execute(
        """INSERT INTO posts (source, platform, external_id, url, author, title, body,
                              created_at, fetched_at, keywords, score, status)
           VALUES ('t','autodesk',?,?,'a',?,'b','2026-07-20T10:00:00','2026-07-20T10:00:00','ifc',5,?)""",
        (f"ext{i}", f"https://example.invalid/{i}", f"Jel {i}", "new" if is_new else "alerted"),
    )
    pid = conn.execute("SELECT last_insert_rowid() r").fetchone()["r"]
    conn.execute(
        """INSERT INTO signals (post_id, is_pain, pain_summary, severity, buying_intent,
                                confidence, classifier_version, classified_at)
           VALUES (?, 1, 'fajdalom', ?, 0, 0.9, 'test', '2026-07-20T11:00:00')""",
        (pid, 3 if is_new else 4),
    )
conn.commit()
conn.close()

pending = count_opportunities(db2, only_pain=True, min_severity=3, post_status="new")
check("B1 count_opportunities a valodi varakozo szamot adja", pending == NEW_COUNT, f"{pending}")
rows = get_opportunities(db2, only_pain=True, min_severity=3, post_status="new", limit=max(pending, 1))
check("B2 MIND a varakozo jel visszajon", len(rows) == NEW_COUNT, f"{len(rows)}")
check("B3 csak 'new' statuszu", all(r["post_status"] == "new" for r in rows))

# a REGI logika szimulacioja ugyanezen az adaton: limit=100, utoszures Pythonban
old = [o for o in get_opportunities(db2, only_pain=True, min_severity=3) if o["post_status"] == "new"]
check("B4 a regi logika ezen az adaton bukott volna", len(old) < NEW_COUNT,
      f"regi={len(old)} uj={len(rows)}")

# a szures ne rontsa el a tobbi hivast
check("B5 post_status nelkul a teljes halmaz jon",
      count_opportunities(db2, only_pain=True, min_severity=3) == NEW_COUNT + ALERTED_COUNT)
check("B6 platform-szures tovabbra is mukodik",
      count_opportunities(db2, only_pain=True, min_severity=3, platform="autodesk")
      == NEW_COUNT + ALERTED_COUNT
      and count_opportunities(db2, only_pain=True, min_severity=3, platform="nincs-ilyen") == 0)
check("B7 platform + statusz egyutt",
      count_opportunities(db2, only_pain=True, min_severity=3,
                          platform="autodesk", post_status="new") == NEW_COUNT)

print()
bad = 0
for name, ok, detail in results:
    if not ok:
        bad += 1
    print(f"  {'OK  ' if ok else 'FAIL'} {name}" + (f"   [{detail}]" if detail else ""))
print(f"\n{len(results) - bad}/{len(results)} teszt zold.")
sys.exit(1 if bad else 0)
