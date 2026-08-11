# -*- coding: utf-8 -*-
"""
Telemetria-osszefoglalo a LinkedIn-motorhoz (`storage/linkedin_telemetry.jsonl`).

MIERT EZ A HAROM BLOKK: a v8 dontesek harom nyitott kerdest hagytak
(`docs/03-linkedin-composer-spec.md` zaro blokkjai), es a script pontosan azokra
felel:
  1. Strategia-eloszlas — nyer-e valaha a `constructive_challenge`, es a horgonyzas
     utan egyezik-e a nyers maximum a vegso gyoztessel (bias = nudge, nem teherhordo).
  2. Sav-betartas — `target_length` vs `reply_words`. A sav UTASITAS, nem kapu:
     csak a naplobol derul ki, betartja-e a modell.
  3. Konkretsag-komponensek — `anchors_added` / `abstract_count` / `hedges`. Nincs
     osszpontszam es nincs belole kapu, szandekosan. Ha egyik komponens sem korrelal
     semmivel, a blokk torolheto — ez az authenticity-rubrika tanulsaga.

Hasznalat:
    python bench_report.py
    python bench_report.py --path storage/linkedin_telemetry.jsonl
"""
import argparse
import collections
import io
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PATH = os.path.join("storage", "linkedin_telemetry.jsonl")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def row_language(row: dict) -> str:
    """A sor nyelve: a naplozott `reply_language`, vagy VISSZAMENOLEG szamolva.

    A v11 elotti sorokban nincs nyelv-mezo, a `reply_text` viszont benne van — a
    motor sajat `looks_english`-evel utolag is eldontheto. Igy a mar meglevo sorok
    is szegmentalhatok, es nem kell megvarni, hogy osszejojjon egy uj koteg.
    """
    lang = row.get("reply_language")
    if lang:
        return lang
    text = row.get("reply_text") or ""
    if not text.strip():
        return "-"
    try:
        sys.path.insert(0, BASE_DIR)
        from responder.linkedin_engine import looks_english
        return "en" if looks_english(text) else "other"
    except Exception:                                            # noqa: BLE001
        return "en?"


def load_rows(path: str) -> list[dict]:
    if not os.path.isabs(path):
        path = os.path.join(BASE_DIR, path)
    if not os.path.exists(path):
        print(f"Nincs telemetria-fajl: {path}")
        return []
    rows = []
    for i, line in enumerate(io.open(path, encoding="utf-8"), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            print(f"  [figyelmeztetes] {i}. sor nem ervenyes JSON, kihagyva")
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="LinkedIn-telemetria osszefoglalo")
    ap.add_argument("--path", default=DEFAULT_PATH)
    args = ap.parse_args()

    rows = load_rows(args.path)
    if not rows:
        return 1
    gen = [r for r in rows if not r.get("skipped") and r.get("reply_words")]

    print(f"osszes sor: {len(rows)} | generalt: {len(gen)} | "
          f"kihagyott/hibas: {len(rows) - len(gen)}")

    print(f"\n## Soronkent")
    print(f"{'#':<3}{'ts':<13}{'eng':>4}{'post_w':>8}{'sav':>9}{'valasz':>8}{'arany':>7}"
          f"{'':>6}  {'strategia':<24}{'abs':>4}{'anch':>5}{'hedg':>5}{'rw':>3}")
    for i, r in enumerate(rows, 1):
        c = r.get("concreteness") or {}
        tl = r.get("target_length")
        band = f"{tl[0]}-{tl[1]}" if isinstance(tl, list) else "-"
        rw, pw = r.get("reply_words") or 0, r.get("post_words") or 0
        ratio = f"{rw / pw:.2f}" if pw and rw else "-"
        inb = "-" if not isinstance(tl, list) or not rw else (
            "BENT" if tl[0] <= rw <= tl[1] else ("ROVID" if rw < tl[0] else "HOSSZU"))
        print(f"{i:<3}{r.get('ts', '')[5:16]:<13}{(r.get('engine') or '')[-2:]:>4}{pw:>8}"
              f"{band:>9}{rw:>8}{ratio:>7}{inb:>6}  "
              f"{(r.get('strategy') or ('SKIP' if r.get('skipped') else '-')):<24}"
              f"{c.get('abstract_count', '-'):>4}{c.get('anchors_added', '-'):>5}"
              f"{c.get('hedges', '-'):>5}{r.get('rewrites', '-'):>3}")

    print("\n## 1. Strategia-eloszlas")
    counts = collections.Counter(r.get("strategy") for r in gen)
    for s, n in counts.most_common():
        print(f"  {s:<24} {n:>3}  ({n / len(gen) * 100:.0f}%)")
    never = [s for s in ("constructive_challenge", "systems_thinking", "field_experience",
                         "business_impact", "future_outlook", "practical_lesson",
                         "missing_perspective") if s not in counts]
    print(f"  SOHA nem nyert: {', '.join(never) if never else '-'}")

    # Motorverziora bontva: a horgonyzas (v8) ELOTTI sorokat egybeszamolni azzal,
    # amit a horgonyzas javitani hivatott, elmosna a hatast. Ugyanez all a
    # strategia-eloszlasra is, de ott a kis n miatt egyelore az egyben-nezet informativ.
    agree = [r for r in gen if r.get("strategy_fit")]
    if agree:
        print("\n  nyers max == vegso gyoztes (a bias nudge, ha ez magas):")
        by_eng = collections.defaultdict(list)
        for r in agree:
            by_eng[r.get("engine") or "?"].append(
                max(r["strategy_fit"], key=r["strategy_fit"].get) == r.get("strategy"))
        for eng in sorted(by_eng):
            v = by_eng[eng]
            print(f"    {eng:<18} {sum(v)}/{len(v)} ({sum(v) / len(v) * 100:.0f}%)")

    print("\n## 2. Sav-betartas (v7+ sorok)")
    # NYELV SZERINT BONTVA (2026-08-11): a sav ANGOL szoszamon all. A magyar
    # agglutinal, tehat ugyanaz a tartalom kevesebb szo — egy magyar sort ugyanabba
    # az aranyba szamolni elmossa, hogy mit mertunk. A `reply_language` hianya
    # 'en'-nek szamit: a v11 elotti sorok mind angolok voltak.
    band_rows = [r for r in gen if isinstance(r.get("target_length"), list)]
    if not band_rows:
        print("  nincs meg ilyen sor")
    tally = collections.Counter()
    for r in band_rows:
        tl, rw = r["target_length"], r["reply_words"]
        lang = row_language(r)
        ok = tl[0] <= rw <= tl[1]
        tally[(lang, ok)] += 1
        print(f"  [{lang:<3}] poszt {r.get('post_words'):>4}sz -> sav {tl[0]}-{tl[1]:<4} "
              f"valasz {rw:>4}sz  {'BENT' if ok else ('ROVID' if rw < tl[0] else 'HOSSZU')}")
    for lang in sorted({l for l, _ in tally}):
        ok, bad = tally[(lang, True)], tally[(lang, False)]
        print(f"  savon belul [{lang}]: {ok}/{ok + bad}")
    if any(l not in ("en", "en?") for l, _ in tally):
        print("    -> a nem-angol sorok kalibracioja MAS; ne szamold egy aranyba oket.")

    print("\n## 3. Konkretsag-komponensek")
    # Csak ANGOL sorok: a horgony- es absztrakcio-lexikon angol es BIM-specifikus,
    # ezert egy magyar/nem-AEC soron az `anchors_added: 0` nem jelez semmit — az
    # atlagba beszamolva viszont lerontja. Ez a merőszam hatara, nem a kimenet hibaja.
    skipped_lang = [r for r in gen if r.get("concreteness")
                    and row_language(r) != "en"]
    if skipped_lang:
        print(f"  ({len(skipped_lang)} nem-angol sor kihagyva: a lexikon angol es "
              f"BIM-specifikus, ott a 0 horgony nem informativ)")
    cr = [r for r in gen if r.get("concreteness") and row_language(r) == "en"]
    if not cr:
        print("  nincs concreteness-adat")
    else:
        print(f"  {'post_w':>7}{'valasz':>8}{'anchors':>9}{'abstract':>10}{'hedges':>8}  strategia")
        for r in cr:
            c = r["concreteness"]
            print(f"  {r.get('post_words'):>7}{c.get('words'):>8}{c.get('anchors_added'):>9}"
                  f"{c.get('abstract_count'):>10}{c.get('hedges'):>8}  {r.get('strategy')}")
        n = len(cr)
        print(f"  atlag: anchors={sum(c['concreteness']['anchors_added'] for c in cr) / n:.1f}  "
              f"abstract={sum(c['concreteness']['abstract_count'] for c in cr) / n:.1f}  "
              f"hedges={sum(c['concreteness']['hedges'] for c in cr) / n:.1f}")

    print("\n## 4. Nyitas-diverzitas (v9+)")
    # A KIJELOLT forma eddig is a naploban volt, a MEGVALOSULT nyitas nem — es a
    # ketto elterese volt a hiba (harom kulonbozo forma, ugyanaz a mondat).
    fp_rows = [r for r in gen if r.get("opening_fingerprint")]
    if not fp_rows:
        print("  nincs meg ujjlenyomat-adat (v9 elotti sorok)")
    else:
        # FUTASONKENT bontva, mert a gyűrű PROCESSZ-eletű: ket kulon futas kozott
        # nem lat at, tehat az ismetles ott nem kapu-kudarc, hanem a mechanizmus
        # ismert hatara. Egybeszamolva a metrika sajat magat cafolna meg.
        # A futas-hatart az `opening_echo_recent` hossza adja: a gyűrű MAR
        # tartalmazza az adott kommentet, tehat az 1-es hossz uj processzt jelent.
        runs, cur = [], []
        for r in fp_rows:
            if len(r.get("opening_echo_recent") or []) <= 1 and cur:
                runs.append(cur)
                cur = []
            cur.append(r)
        if cur:
            runs.append(cur)
        for i, run in enumerate(runs, 1):
            fps = collections.Counter(r["opening_fingerprint"] for r in run)
            dup = {fp: n for fp, n in fps.items() if n > 1}
            print(f"  {i}. futas: {len(fps)}/{len(run)} kulonbozo"
                  f"{'  <-- ISMETLES: ' + str(dup) if dup else ''}")
            for r in run:
                print(f"    {(r.get('opening_shape') or '(szabad)'):<14} -> "
                      f"'{r['opening_fingerprint']}'")
        across = collections.Counter(r["opening_fingerprint"] for r in fp_rows)
        favs = {fp: n for fp, n in across.most_common() if n > 1}
        if favs:
            print(f"  futasokon AT ismetlodo (a modell kedvencei): {favs}")
            print("    -> processz-ujraindulas utan a gyűrű ures; ez a mechanizmus")
            print("       ismert hatara, nem hiba (varianciа-allapot, nem adat).")

    print("\n## 5. Kapuk")
    print(f"  rewrites > 0: {sum(1 for r in gen if r.get('rewrites'))}/{len(gen)}")
    issues = collections.Counter(q for r in gen for q in (r.get("quality_issues_first") or []))
    print(f"  quality_issues_first: {dict(issues) or 'nincs'}")
    print(f"  vendor-skip: {sum(1 for r in rows if r.get('skipped'))} | "
          f"forced: {sum(1 for r in rows if r.get('forced'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
