"""
Kulcsszo-elo-szuro.

FONTOS: ez NEM donteshozo, csak olcso elo-szuro — azt donti el, mi kerul a Pain
Classifier (LLM) ele. A "valodi fajdalom vagy csak temaemlites" kerdes a
classifier dolga (ld. docs/01-architektura-audit-2026-07.md §3).

Teljesitmeny-figyelmeztetes (2026-07-24-en javitott hiba):
A tobbszavas kulcsszavak korabban EGY regexbe forditodtak, lancolt lookahead-ekkel:
`(?=.*\\bszo1)(?=.*\\bszo2)` — `re.DOTALL`-lal es horgony NELKUL. Emiatt a
`re.search` MINDEN kezdopozicionál ujraprobalta a `.*`-os lookahead-eket, ami
negyzetes futasi idot adott. Elesben mert ertekek 59 kulcsszoval (ebbol 54
tobbszavas):
    2 KB szoveg  ->  2,5 s
   10 KB szoveg  -> 57,8 s
Egy hosszabb GitHub-issue (30 KB+, log/stacktrace) ~10 perc CPU-t evett meg, es
ket beakadt `main.py --github` processzt hagyott a gepen.
Ld. docs/02-lead-volume-audit-2026-07.md §3.13.

A javitas: a tobbszavas kulcsszo szavankent kulon, egyszeru mintat kap, es MIND
egyeznie kell. Ez pontosan ugyanaz a szemantika ("minden szo szerepel valahol a
szovegben, barmilyen sorrendben"), csak linearis idoben.
"""
import re

# Vegso vedvonal: a `posts.body` amugy is 2000 karakterre csonkolva tarolodik,
# tehat ennel joval hosszabb szovegen szurni sem konzisztens, sem szukseges.
MAX_TEXT_CHARS = 20_000


# Ennel rovidebb tokenre NEM engedunk toldalek-toleranciat: a "to" prefixkent
# a "tool"-ra, az "ac" az "according"-ra illeszkedne (a configban van "archicad
# to revit" es "ac to rvt" kulcsszo is). 3 karaktertol viszont kell a tolerancia,
# mert az "ifc" igy talalja meg az "IFCs"-t is — ami valos posztcimekben szerepel.
_MIN_LEN_FOR_SUFFIX = 3


def _word_pattern(word: str) -> re.Pattern:
    """
    Egy szo mintaja. Ket dolgot valtoztat a 2026-07-24 elotti allapothoz kepest:

    1. **Szohatar eleje** (`\\b`): korabban az egyszavas kulcsszavak sima,
       hataroktol fuggetlen reszszo-egyezest kaptak (`re.escape(kw)`), tehat a
       "nodu" illeszkedett az "anodus"-ra is. Most a szo elejehez van kotve.
    2. **Toldalek-tolerancia** (`\\w*`) 3+ karakteres tokenre: a felhasznalok
       nem szotari alakot irnak ("export" vs "exports"/"exporting",
       "parameter" vs "parameters"). Enelkul a "lost parameters" kulcsszo nem
       egyezett a "lost parameter" szoveggel.

    FIGYELEM, amit ez NEM tud: ez nem szotovezes. A "lost" tovabbra sem egyezik
    a "losing"-gal — az ilyen tunet-szinonimakat a `keywords.pain_points`
    listaban kell felvenni (ld. config, es docs/02-lead-volume-audit-2026-07.md §3.10).
    """
    esc = re.escape(word)
    if len(word) >= _MIN_LEN_FOR_SUFFIX:
        return re.compile(rf"\b{esc}\w*", re.IGNORECASE)
    return re.compile(rf"\b{esc}\b", re.IGNORECASE)


def _compile(keywords: list[str]) -> list[tuple[list[re.Pattern], str]]:
    """Kulcsszavakat mintakra fordit.

    Visszaad: [(mintak, eredeti_kulcsszo)], ahol MINDEN mintanak egyeznie kell.
    A szavak sorrendje nem szamit (a szoveg barmely reszen szerepelhetnek).
    """
    compiled: list[tuple[list[re.Pattern], str]] = []
    for kw in keywords:
        words = kw.strip().split()
        if not words:
            continue
        compiled.append(([_word_pattern(w) for w in words], kw))
    return compiled


class KeywordFilter:
    def __init__(self, config: dict):
        kw = config.get("keywords", {})
        self._primary = _compile(kw.get("primary", []))
        self._pain = _compile(kw.get("pain_points", []))
        self._context = _compile(kw.get("context", []))

    @staticmethod
    def _hits(text: str, group: list[tuple[list[re.Pattern], str]]) -> list[str]:
        return [kw for patterns, kw in group if all(p.search(text) for p in patterns)]

    def match(self, text: str) -> tuple[list[str], int]:
        """
        Returns (matched_keywords, score).
        Primary match: 3 pts each
        Pain point match: 2 pts each
        Context match: 1 pt each
        """
        text = (text or "")[:MAX_TEXT_CHARS]

        matched: list[str] = []
        score = 0

        for group, points in ((self._primary, 3), (self._pain, 2), (self._context, 1)):
            hits = self._hits(text, group)
            matched.extend(hits)
            score += points * len(hits)

        # deduplicate while preserving order
        seen = set()
        deduped = []
        for kw in matched:
            if kw not in seen:
                seen.add(kw)
                deduped.append(kw)

        return deduped, score
