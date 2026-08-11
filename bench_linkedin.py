# -*- coding: utf-8 -*-
"""
Meresi futtato a LinkedIn-komment motorhoz (`responder/linkedin_engine.py`).

MIERT: a v5-v8 dontesek mind 1-2 meresen alltak, harom kulonbozo poszton. A
kovetkezo lepes GYUJTES: 20-30 valodi poszt, hogy a strategia-eloszlas, a
hossz-sav betartasa es a konkretsag-komponensek korrelalhatoak legyenek
(`docs/03-linkedin-composer-spec.md`, v8 blokk zaro bekezdesei). A dashboard UI-n
at ez posztonkent tobb kattintas; ez a script egy paranccsal viszi vegig a
koteget, es ugyanazt a telemetria-sort irja (`generate_comment` wrapper).

Hasznalat:
    python bench_linkedin.py posts/*.txt
    python bench_linkedin.py posts/            # minden .txt a mappabol
    python bench_linkedin.py posts/ad.txt --force
    python bench_linkedin.py posts/ --quiet    # csak az osszefoglalo tabla

A poszt-fajl elso sora lehet metaadat:  # author=Nev | role=Szerep
"""
import argparse
import glob
import io
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# A konzol cp1250 Windowson: az em dash es a magyar ekezet kulonben UnicodeEncodeError.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_config() -> dict:
    import yaml
    with open(os.path.join(BASE_DIR, "config.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_post(path: str) -> tuple[str, str, str]:
    """A fajl szovege + opcionalis szerzo-metaadat az elso `#` sorbol."""
    text = io.open(path, encoding="utf-8").read().strip()
    author = role = ""
    if text.startswith("#"):
        head, _, rest = text.partition("\n")
        for part in head.lstrip("#").split("|"):
            key, _, val = part.partition("=")
            key, val = key.strip().lower(), val.strip()
            if key == "author":
                author = val
            elif key == "role":
                role = val
        text = rest.strip()
    return text, author, role


def expand(paths: list[str]) -> list[str]:
    out = []
    for p in paths:
        if os.path.isdir(p):
            out.extend(sorted(glob.glob(os.path.join(p, "*.txt"))))
        elif any(ch in p for ch in "*?["):
            out.extend(sorted(glob.glob(p)))
        else:
            out.append(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="LinkedIn-komment meresi futtato")
    ap.add_argument("paths", nargs="+", help=".txt fajl, glob vagy mappa")
    ap.add_argument("--force", action="store_true",
                    help="vendor-hirdetes eseten is generaljon (UI: „Mégis generálj”)")
    ap.add_argument("--quiet", action="store_true", help="csak az osszefoglalo tabla")
    ap.add_argument("--strategy", default="",
                    help="MERESI override: ezt a strategiat kenyszeriti (pl. "
                         "constructive_challenge). A `pick_strategy`-t monkeypatcheli "
                         "CSAK ebben a scriptben — a motor valtozatlan.")
    args = ap.parse_args()

    files = expand(args.paths)
    if not files:
        print("Nincs feldolgozhato fajl.")
        return 1

    config = load_config()
    import responder.linkedin_engine as eng
    from responder.linkedin_engine import generate_comment

    # MERESI OVERRIDE, nem funkcio. A kerdes, amire valaszt ad: ha a
    # `constructive_challenge` sosem NYER, jobb lenne-e a komment, ha megis o irna?
    # Ha nem, a strategia torolheto (a masik hat mar ugyanezt a munkat elvegzi).
    # Miert itt es nem a motorban: a produkcios dontesi utat nem bovitjuk egy
    # kapcsoloval, amit csak a meres hasznal.
    if args.strategy:
        if args.strategy not in eng.STRATEGIES:
            print(f"Ismeretlen strategia: {args.strategy}\n"
                  f"Valaszthato: {', '.join(eng.STRATEGIES)}")
            return 1
        print(f"[bench] STRATEGIA-OVERRIDE: {args.strategy} (a pick_strategy ki van iktatva)")
        eng.pick_strategy = lambda fit, intent="general", level="management": args.strategy

    summary = []
    for i, path in enumerate(files, 1):
        name = os.path.basename(path)
        post, author, role = read_post(path)
        if not post:
            print(f"[{i}/{len(files)}] {name}: URES, kihagyva")
            continue

        print(f"\n{'=' * 78}\n[{i}/{len(files)}] {name}  ({len(post.split())} szo)")
        res = generate_comment(config, post, author, role, force=args.force) or {}

        if res.get("error"):
            print(f"  HIBA: {res['error']}")
            summary.append((name, "HIBA", "", "", "", ""))
            continue

        if res.get("skipped"):
            print(f"  KIHAGYVA: {res.get('skip_reason', '')}")
            print("  (ujra --force kapcsoloval, ha meresre kell)")
            summary.append((name, "SKIP", "", "", "", ""))
            continue

        tl = res.get("target_length") or []
        band = f"{tl[0]}-{tl[1]}" if len(tl) == 2 else "-"
        reply = res.get("reply_text") or res.get("reply") or ""
        words = len(reply.split())
        inband = "-" if not tl else ("BENT" if tl[0] <= words <= tl[1] else
                                     ("ROVID" if words < tl[0] else "HOSSZU"))
        conc = res.get("concreteness") or {}

        if not args.quiet:
            print(f"  strategia : {res.get('strategy')}  (raw max: "
                  f"{max(res.get('strategy_fit') or {'-': 0}, key=(res.get('strategy_fit') or {'-': 0}).get)})")
            print(f"  szandek   : {res.get('conversation_intent')} / "
                  f"{res.get('discourse_level')} / {res.get('human_temperature')}")
            print(f"  hossz     : sav {band}, valasz {words} szo -> {inband}")
            print(f"  konkretsag: anchors={conc.get('anchors_added', '-')} "
                  f"abstract={conc.get('abstract_count', '-')} "
                  f"hedges={conc.get('hedges', '-')}  rewrites={res.get('rewrites', '-')}")
            if res.get("quality_issues_first"):
                print(f"  elso kapu : {res['quality_issues_first']}")
            print(f"\n  --- KOMMENT ---\n{reply}\n")

        summary.append((name, res.get("strategy", "-"), band, str(words), inband,
                        f"a{conc.get('anchors_added', '-')}/x{conc.get('abstract_count', '-')}"))

    print(f"\n{'=' * 78}\nOSSZEFOGLALO")
    print(f"{'fajl':<28}{'strategia':<24}{'sav':>9}{'szo':>6}{'':>7}  konkr")
    for row in summary:
        print(f"{row[0][:27]:<28}{row[1]:<24}{row[2]:>9}{row[3]:>6}{row[4]:>7}  {row[5]}")
    print("\nTelemetria: storage/linkedin_telemetry.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
