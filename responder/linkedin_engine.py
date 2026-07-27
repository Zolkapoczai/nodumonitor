"""
LinkedIn Thought Leadership Engine — a kommentgeneralas dontes-vezerelt magja.

Ez valtja le a korabbi egy-hivasos "generalj valaszt" megoldast
(`draft_generator._LINKEDIN_REPLY_SYSTEM_PROMPT`), ami a tipikus LLM-viselkedest
produkalta: osszefoglalta a posztot, egyetertett a szerzovel, dicserte, es
altalanossagokat irt. A cel a szakmai tekintely, nem az udvariassag.

FELELOSSEG-SZETVALASZTAS
A gondolatmenet (mit erdemes mondani) es a szovegezes (hogyan mondjuk) KULON
lepes. A korabbi prompt a kettot egyben kerte, ezert a modell a legkonnyebb utat
valasztotta: parafrazalt.

  Stage 1-5  REASON   — egy strukturalt hivas: intent, core thesis, missing
                        perspective, strategia-valasztas, EGY original insight.
                        Prozat NEM ir.
  Stage 6-7  COMPOSE  — egy hivas: a reasoning-objektumbol megirja a kommentet
                        (experience layer + 20/80 szerkezet).
  Stage 8-9  GATE     — DETERMINISZTIKUS ellenorzes kod ban (nem LLM), es csak
                        sertes eseten egy celzott ujrairas.

MIERT 2 HIVAS ES NEM 9 (a brief 9 stage-et ir le)
1. A projekt sajat, rogzitett elve (01-architektura-audit §6/§7): "Egy hivas, egy
   sema — nem 6 kulon agent-hivas", koltseg es latencia miatt.
2. A brief maga is token-hatekonysagot ir elo design-constraintként.
3. Ez SZINKRON UI-muvelet (`POST /linkedin/compose`) — 9 sorosan futo hivas
   15-25 s varakozas lenne a felhasznalonak.
A 9 felelosseg NEM tunt el: stage-hataronkent kulon semamező es kulon
prompt-szakasz felel meg nekik. A hatarok a semaban es a kodban vannak, nem a
hivasok szamaban.

MIERT DETERMINISZTIKUS A QUALITY GATE (stage 9)
A brief "deterministic behaviour"-t kert. Egy LLM-nek feltett "original ez?"
kerdesre a valasz gyakorlatilag mindig igen. A tiltott fordulat, a hossz, a
bekezdesszam, a markaemlites es az "osszefoglalta a posztot" hiba viszont
MERHETO — regexszel es n-gram-atfedessel, ingyen, 100%-ban reprodukalhatoan es
teszthetoen. Ezert a kapu kodban van; az LLM csak akkor kap munkat (egyetlen
celzott ujrairas), ha a kapu konkret sertest talalt.

TOKEN-HATEKONYSAG
A legnagyobb nyeresег nem a promptok rovidítése volt: a korabbi implementacio a
teljes NODU tudasbazist (`storage/nodu_knowledge_base.md`, ~274 KB ≈ 70k token)
beforditotta MINDEN LinkedIn-hivas system-promptjaba. Egy olyan motornak, ami
alapbol nem is emliti a NODU-t, ez tiszta veszteseg — es aktivan rontja a
kimenetet, mert termek-dokumentacio fele huzza a modellt. Kivezetve.
"""
import json
import re

from google import genai
from google.genai import types

from env_secrets import get_secret

ENGINE_VERSION = "linkedin-tle-v1"

# --- Stage 4: strategiak -----------------------------------------------------
# Pontosan EGY strategia valasztodik kommentenkent. A `directive` a compose-
# hivasba kerul — ez adja a komment jelleget, ezert rovid es utasito.
STRATEGIES: dict[str, dict[str, str]] = {
    "constructive_challenge": {
        "label": "Constructive Challenge",
        "directive": "Question exactly ONE assumption, respectfully and concretely. "
                     "Name the assumption, then say what it overlooks.",
        "wins_when": "the post rests on a claim that is true only under conditions "
                     "it does not state",
    },
    "systems_thinking": {
        "label": "Systems Thinking",
        "directive": "Connect several causes the post treats separately into one "
                     "higher-level explanation.",
        "wins_when": "the post lists symptoms or causes but does not link them",
    },
    "field_experience": {
        "label": "Field Experience",
        "directive": "Ground the point in what practitioners actually observe. "
                     "Patterns only — no invented anecdotes, names or numbers.",
        "wins_when": "the post is theoretical or aspirational and practice diverges "
                     "from it",
    },
    "business_impact": {
        "label": "Business Impact",
        "directive": "Translate the technical issue into its business consequence "
                     "(cost, risk, timeline, accountability).",
        "wins_when": "the post stays technical and the commercial consequence is "
                     "unstated",
    },
    "future_outlook": {
        "label": "Future Outlook",
        "directive": "Explain where this is heading and what changes as a result. "
                     "Concrete direction, not hype.",
        "wins_when": "the post describes the present state and the trajectory is "
                     "the interesting part",
    },
    "practical_lesson": {
        "label": "Practical Lesson",
        "directive": "Extract one actionable lesson someone can apply this week.",
        "wins_when": "the post diagnoses a problem but offers nothing to do about it",
    },
    "missing_perspective": {
        "label": "Missing Perspective",
        "directive": "Introduce the important angle the author omitted. Do not "
                     "claim the author was wrong — add the dimension they left out.",
        "wins_when": "the omission itself is the most valuable thing you can "
                     "contribute AND no other strategy fits — this is the FALLBACK, "
                     "not the default",
    },
}

# --- Stage 3: hianyzo perspektivak ------------------------------------------
PERSPECTIVES = [
    "interoperability", "lifecycle", "ai", "procurement", "implementation",
    "governance", "operations", "economics", "standards", "scalability",
    "adoption", "incentives", "organisational_behaviour", "automation",
    "business_value", "data_quality", "change_management",
]

# --- Visszafele-kompatibilis lekepezes --------------------------------------
# A dashboard `renderLinkedinResult()`-ja 8 mezot olvas (topic, post_type,
# engagement_intent, reply_style, brand_mode, confidence, reply_text, rationale).
# A refaktor NEM torheti el az API-t es nem valtoztathat UI-viselkedest, ezert az
# uj strategia-fogalmat leképezzuk a regi enumokra, es az uj mezoket ADDITIVAN
# adjuk vissza (a UI ezeket egyszeruen figyelmen kivul hagyja).
_STRATEGY_TO_LEGACY = {
    "missing_perspective":    ("expand", "insight"),
    "constructive_challenge": ("challenge", "analytical"),
    "systems_thinking":       ("educate", "analytical"),
    "field_experience":       ("share_experience", "practical"),
    "business_impact":        ("educate", "expert"),
    "future_outlook":         ("educate", "insight"),
    "practical_lesson":       ("educate", "practical"),
}

_TOPICS = [
    "archicad", "revit", "interoperability", "bim", "ifc", "ai", "automation",
    "digital_construction", "design", "engineering", "project_management",
    "construction", "startup", "business", "leadership", "career", "event",
    "technology", "software", "general",
]
_POST_TYPES = [
    "opinion", "question", "announcement", "case_study", "success_story",
    "technical_problem", "industry_news", "discussion", "experience", "hiring",
    "event", "product", "general",
]

# --- Stage 1-5: REASON ------------------------------------------------------
_REASON_PROMPT = f"""
You are a senior AEC/BIM industry analyst preparing a colleague to comment on a
LinkedIn post. You produce REASONING ONLY — never the comment itself.

Fill the JSON fields in this order:

1. topic / post_type — classify semantically, one value each.
2. author_objective — what the author actually wants (attention, validation,
   recruitment, debate, teaching, announcement...). Not a summary.
3. audience — who the post is written for.
4. technical_depth — surface | practitioner | expert.
5. emotional_tone — the author's register (neutral, frustrated, promotional,
   celebratory, reflective, provocative...).
6. core_thesis — the ONE central claim, in one sentence. Ignore supporting
   arguments and examples. If the post has several, pick the load-bearing one.
7. missing_perspective — the STRONGEST dimension the post does not address,
   from the allowed list. Exactly one. Never a list.
8. missing_perspective_reason — one sentence: why this omission matters here.
9. strategy_fit — score EVERY strategy 0-10 on how much professional value it
   would add to THIS post. Do not pick a winner; score them all honestly, and
   let the scores differ. The missing perspective from step 7 is an input to
   this scoring, not the answer to it.
{chr(10).join(f'   - {k}: fits when {v["wins_when"]}' for k, v in STRATEGIES.items())}
10. strategy_reason — one sentence: what the comment has to accomplish for this
    specific audience to be worth reading.
11. explicit_tool_request — true ONLY if the post (or the author in it) directly
    asks the reader to name a tool, product, plugin, service or vendor.
    True examples: "what do you use for this?", "any tool recommendations?",
    "how do you solve this in practice — which software?", "milyen eszkozzel
    oldjatok meg?".
    FALSE for: describing a problem, complaining, asking for opinions or advice
    in general, rhetorical questions, or asking "how" without asking "with what".
    Someone stating a pain is NOT asking for a product. Default to false.
12. tool_request_quote — if explicit_tool_request is true, copy the EXACT words
    from the post that contain the request, verbatim, nothing else. Empty string
    if false. Do not paraphrase — the quote is verified against the post.
11. insight — ONE original, specific claim that is NOT stated in the post and is
    not a restatement of it. This is the substance of the comment. Go deeper,
    not wider. No hedging, no generalities like "communication is important".
12. confidence — 0.0-1.0, your confidence in this reasoning.

Hard rules:
- Do NOT summarise the post anywhere.
- The insight must survive the question "would an experienced professional learn
  something from this?". If not, choose a different one.
- No invented statistics, customer names or personal anecdotes.
""".strip()

_REASON_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "topic": {"type": "STRING", "enum": _TOPICS},
        "post_type": {"type": "STRING", "enum": _POST_TYPES},
        "author_objective": {"type": "STRING"},
        "audience": {"type": "STRING"},
        "technical_depth": {"type": "STRING", "enum": ["surface", "practitioner", "expert"]},
        "emotional_tone": {"type": "STRING"},
        "core_thesis": {"type": "STRING"},
        "missing_perspective": {"type": "STRING", "enum": PERSPECTIVES},
        "missing_perspective_reason": {"type": "STRING"},
        # A modell PONTOZ, nem valaszt — a dontest a kod hozza (pick_strategy).
        "strategy_fit": {
            "type": "OBJECT",
            "properties": {k: {"type": "INTEGER"} for k in STRATEGIES},
            "required": list(STRATEGIES),
        },
        "strategy_reason": {"type": "STRING"},
        "explicit_tool_request": {"type": "BOOLEAN"},
        "tool_request_quote": {"type": "STRING"},
        "insight": {"type": "STRING"},
        "confidence": {"type": "NUMBER"},
    },
    "required": [
        "topic", "post_type", "author_objective", "audience", "technical_depth",
        "emotional_tone", "core_thesis", "missing_perspective",
        "missing_perspective_reason", "strategy_fit", "strategy_reason",
        "explicit_tool_request", "tool_request_quote", "insight", "confidence",
    ],
}

# Azok a temak, ahol a NODU Bridge megnevezese IGAZ es relevans valasz egy
# eszkoz-kerdesre. Egy renderelo-szoftverre vonatkozo kerdes nem meghivo a
# Bridge-re — kulonben ugyanaz a spam lenne, csak kerdesre valaszolva.
_BRAND_RELEVANT_TOPICS = {"archicad", "revit", "interoperability", "ifc"}

# A `missing_perspective` dokumentaltan FALLBACK strategia. Enelkul a bias
# ide (korabban ide, majd a systems_thinking-re) kollapszalt: 5 posztbol 4-5
# ugyanazt kapta, holott pl. a "diagnozis megoldas nelkul" posztra a
# practical_lesson valo. A levonas csak akkor engedi nyerni, ha tenyleg jobb.
_STRATEGY_BIAS = {"missing_perspective": -1.5}


def pick_strategy(fit: dict) -> str:
    """Stage 4 dontes — DETERMINISZTIKUS, a modell pontszamaibol.

    Miert nem a modell valaszt: enum-valasztasnal pozicio- es
    absztrakcio-torzitast mutatott (a listaban elore tett, "okosan hangzo"
    strategiat valasztotta akkor is, ha egy konkretabb jobban illett). A
    pontozas + kodbeli argmax ugyanaz a minta, mint a projekt scoring-elve
    (01-architektura-audit §7: "a Scorer determinisztikus — az LLM mezoket ad,
    a pontszamot sulyprofil szamolja"). Igy a dontes auditalhato es
    reprodukalhato: ugyanaz a pontszam-vektor mindig ugyanazt adja.

    Holtverseny: a STRATEGIES deklaracios sorrendje dont (a fallback all utolso).
    """
    best, best_score = None, None
    for slug in STRATEGIES:                      # stabil, deklaracios sorrend
        raw = fit.get(slug)
        score = (float(raw) if isinstance(raw, (int, float)) else 0.0)
        score += _STRATEGY_BIAS.get(slug, 0.0)
        if best_score is None or score > best_score:
            best, best_score = slug, score
    return best or "missing_perspective"

# --- Stage 6-7: COMPOSE -----------------------------------------------------
_COMPOSE_PROMPT = """
You write LinkedIn comments as an experienced AEC/BIM professional. You are given
finished reasoning; your only job is to turn it into a comment that reads as
written by a practitioner, not by an assistant.

Structure: roughly 20% acknowledgement of the author's point, 80% new thinking.
The acknowledgement is a bridge, not praise — one clause, then move on.

Experience layer: make the insight credible with observational framing — the
equivalent of "In enterprise projects...", "One recurring pattern is...",
"We often see...", "In multidisciplinary environments...".
CRITICAL: those are English examples of the PATTERN. Write the framing in the
post's own language, using natural native phrasing. Never drop an English phrase
into a non-English comment — a half-translated sentence is the clearest sign of
machine writing.
Never invent personal stories, numbers, customer names or project details.

Hard limits:
- 80-150 words. Never more than two paragraphs.
- First person, professional, plain. No emoji, no exclamation marks, no hashtags.
- Never open with praise or agreement. Forbidden: "I completely agree",
  "Couldn't agree more", "Great post", "Thanks for sharing", "Well said",
  "Interesting perspective", "Exactly", "Absolutely", "This is so true".
- Never summarise the post back to the author.
- Never re-explain something the author already explained.
- Do not reuse the author's distinctive phrasing; use your own words.
- No marketing language. Nothing that sounds like selling.
- Write in the SAME language as the post.
""".strip()

_COMPOSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {"comment": {"type": "STRING"}},
    "required": ["comment"],
}

# --- Stage 9: deterministikus quality gate ----------------------------------
# Angol ES magyar mintak: a komment a poszt nyelven keszul (a nyelvi sodras
# ellen a HANDOFF §4/2 lecke szerint a user-message-ben is megismeteljuk).
_FORBIDDEN_PATTERNS: list[tuple[str, str]] = [
    (r"\bi (?:completely|totally|fully) agree\b", "egyetertes-nyitas"),
    (r"\bcould ?n['’]?t agree more\b", "egyetertes-nyitas"),
    (r"\b(?:great|excellent|fantastic|brilliant|insightful) (?:post|point|article|read|write-?up)\b", "dicseret"),
    (r"\bthanks? (?:for|you for) sharing\b", "koszonet-frazis"),
    (r"\bwell said\b", "dicseret"),
    (r"\binteresting (?:perspective|point|take|read)\b", "ures elismeres"),
    (r"^\s*(?:exactly|absolutely|indeed|precisely)\b", "ures egyetertes"),
    (r"\bthis is so true\b", "ures egyetertes"),
    (r"\bspot on\b", "ures egyetertes"),
    (r"\bas an ai\b", "AI-onleleples"),
    (r"\bgreat (?:question|thread)\b", "dicseret"),
    (r"\bteljesen egyet ?ert(?:ek|unk)\b", "egyetertes-nyitas (HU)"),
    (r"\bnagyon (?:jo|jó) (?:poszt|iras|írás|cikk)\b", "dicseret (HU)"),
    (r"\bkoszi a megosztast\b|\bköszi a megosztást\b", "koszonet-frazis (HU)"),
    (r"\bkoszonom a megosztast\b|\bköszönöm a megosztást\b", "koszonet-frazis (HU)"),
    (r"\bjol mondod\b|\bjól mondod\b", "dicseret (HU)"),
    (r"\berdekes (?:felvetes|meglatas)\b|\bérdekes (?:felvetés|meglátás)\b", "ures elismeres (HU)"),
    (r"\bpontosan (?:igy|így) van\b", "ures egyetertes (HU)"),
]

_BRAND_PATTERN = re.compile(r"\bnodu\b|\bnodu[ .-]?bridge\b", re.IGNORECASE)

# Az experience-layer angol pelda-frazisai. Elesben (2026-07-27) a modell ezeket
# SZO SZERINT beemelte egy magyar kommentbe ("Egy recurring pattern, hogy...",
# "Enterprise projektekben azt tapasztaljuk") — ez a legarulkodobb gepi jel, ezert
# a prompt-utasitas mellett a kapu is figyeli.
_FRAMING_PHRASES = [
    "recurring pattern", "in enterprise projects", "enterprise projects",
    "we often see", "in multidisciplinary environments", "one recurring",
]
# Gyakori angol funkcioszavak — a "milyen nyelvu a szoveg" eldontesehez eleg, es
# nem kell hozza kulso nyelvfelismero fuggoseg.
_EN_STOPWORDS = {
    "the", "and", "that", "with", "this", "for", "are", "but", "not", "you",
    "from", "they", "have", "what", "when", "which", "their", "would", "about",
    "your", "than", "then", "there", "been", "more", "most", "into", "will",
}


def looks_english(text: str, threshold: float = 0.06) -> bool:
    """Angolnak tunik-e a szoveg? Egyszeru funkcioszo-arany, kulso lib nelkul."""
    toks = _words(text)
    if len(toks) < 12:
        return True  # tul rovid a dontéshez — ne jelezzunk hamisan
    return sum(1 for t in toks if t in _EN_STOPWORDS) / len(toks) >= threshold

MIN_WORDS = 60
MAX_WORDS = 175
MAX_PARAGRAPHS = 2
# A komment 4-gramjainak legfeljebb ennyi resze szerepelhet a posztban. Efolott
# a komment visszamondja a posztot (a fo hiba, amit a refaktor celoz).
MAX_NGRAM_OVERLAP = 0.22


def _words(text: str) -> list[str]:
    return re.findall(r"[\w'’-]+", (text or "").lower())


def _ngrams(tokens: list[str], n: int = 4) -> set[tuple]:
    return {tuple(tokens[i:i + n]) for i in range(max(0, len(tokens) - n + 1))}


def overlap_ratio(comment: str, post_text: str, n: int = 4) -> float:
    """A komment n-gramjainak hanyada, ami a posztban is szerepel.

    Ez az "osszefoglalta a posztot" / "visszhangozza a szerzo szavait" hiba
    merheto proxyja. 4-gram: ket 4 szavas egyezo szakasz mar atvetel, nem
    veletlen szakszo-egybeeses.
    """
    c = _ngrams(_words(comment), n)
    if not c:
        return 0.0
    p = _ngrams(_words(post_text), n)
    return len(c & p) / len(c)


def _normalise(comment: str) -> str:
    """Tipografiai tisztitas: a modell nehol dupla szokozt es sorvegi szemetet
    hagy, ami vagolapra masolva latszik. Bekezdeshatart (ures sor) megtartjuk."""
    text = (comment or "").replace("\r\n", "\n").strip()
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def check_quality(comment: str, post_text: str, brand_allowed: bool = False) -> list[str]:
    """Stage 9 — deterministikus kapu. Visszaadja a KONKRET serteseket.

    A lista uressege a "mehet" jel. A hivo ezt a listat adja at az ujrairo
    hivasnak, hogy a modell tudja, mit kell javitani — igy egy korbol javul,
    nem talalgat.
    """
    issues: list[str] = []
    text = (comment or "").strip()
    if not text:
        return ["ures komment"]

    low = text.lower()
    for pattern, label in _FORBIDDEN_PATTERNS:
        if re.search(pattern, low, re.IGNORECASE | re.MULTILINE):
            issues.append(f"tiltott fordulat ({label})")

    wc = len(_words(text))
    if wc < MIN_WORDS:
        issues.append(f"tul rovid ({wc} szo, min {MIN_WORDS})")
    elif wc > MAX_WORDS:
        issues.append(f"tul hosszu ({wc} szo, max {MAX_WORDS})")

    paras = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paras) > MAX_PARAGRAPHS:
        issues.append(f"tul sok bekezdes ({len(paras)}, max {MAX_PARAGRAPHS})")

    if not brand_allowed and _BRAND_PATTERN.search(text):
        issues.append("markaemlites, holott nincs engedelyezve")

    ratio = overlap_ratio(text, post_text)
    if ratio > MAX_NGRAM_OVERLAP:
        issues.append(f"a posztot visszhangozza/osszefoglalja (4-gram atfedes {ratio:.0%})")

    # Nyelvi szivargas: angol keret-frazis nem-angol kommentben.
    if not looks_english(post_text):
        leaked = [p for p in _FRAMING_PHRASES if p in low]
        if leaked:
            issues.append(f"angol frazis nem-angol kommentben ({leaked[0]})")

    if "!" in text:
        issues.append("felkialtojel")
    if re.search(r"#\w+", text):
        issues.append("hashtag")
    if re.search(r"[\U0001F300-\U0001FAFF☀-➿]", text):
        issues.append("emoji")

    return issues


# --- Orchesztracio ----------------------------------------------------------

def _client(config: dict) -> tuple[genai.Client | None, str, str | None]:
    sc = config.get("scoring", {})
    api_key = get_secret("GEMINI_API_KEY", sc.get("gemini_api_key"))
    if not sc.get("gemini_enabled", False) or not api_key:
        return None, "", "Gemini API nincs beállítva (GEMINI_API_KEY a .env-ben)."
    model = sc.get("gemini_model", "gemini-2.5-flash")
    return genai.Client(api_key=api_key), model, None


def _call_json(client, model: str, system: str, user: str, schema: dict,
               max_tokens: int) -> dict | None:
    """Strukturalt hivas. thinking_budget=0 — a HANDOFF §4/1 lecke: a
    gemini-2.5-flash kulonben a max_output_tokens keretbol "gondolkodik", es
    csonka JSON-t ad."""
    resp = client.models.generate_content(
        model=model,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=schema,
            max_output_tokens=max_tokens,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    if not resp.text:
        return None
    return json.loads(resp.text)


def _brand_policy(config: dict) -> str:
    """`linkedin.brand_positioning`: "on_request" (default) | "off" | "auto".

    A dontes-logika a `brand_mention_allowed`-ban van; ez csak a beallitas
    normalizalasa.

    A YAML az off/on/yes/no szavakat BOOLEANNA alakitja (YAML 1.1), ezert a
    nyers ertek lehet `False`/`True` is — enelkul a `brand_positioning: on`
    csendben "nem auto"-t jelentene.
    """
    raw = (config.get("linkedin", {}) or {}).get("brand_positioning", "on_request")
    if isinstance(raw, bool):
        return "auto" if raw else "off"
    value = str(raw).strip().lower()
    return value if value in ("off", "on_request", "auto") else "on_request"


def _quote_in_post(quote: str, post_text: str, min_words: int = 3) -> bool:
    """Szerepel-e az idezet TENYLEGESEN a posztban?

    A projekt zero-hallucination elve (01-audit §6, SalesOS 08-spec §2: kotelezo
    forras-URL) itt is all: a modell "igen, kertek eszkozt" allitasat nem
    fogadjuk el szavara. Az idezetet normalizalva (kisbetu, egyszeres szokoz,
    irasjelek nelkul) keressuk a posztban. Tul rovid idezet nem bizonyitek.
    """
    def norm(s: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", (s or "").lower())).strip()

    q, p = norm(quote), norm(post_text)
    if not q or len(q.split()) < min_words:
        return False
    return q in p


def brand_mention_allowed(config: dict, reasoning: dict,
                          post_text: str) -> tuple[bool, str]:
    """Szabad-e megemliteni a NODU-t EBBEN a kommentben? (engedve, indok)

    Harom kapu, `linkedin.brand_positioning` szerint:
      "off"        — soha, meg kifejezett kerdesre sem (szigoru mod).
      "on_request" — csak ha a poszt KIFEJEZETTEN eszkozt ker, az idezet
                     ellenorizhetoen szerepel a posztban, ES a tema olyan, amire
                     a Bridge igaz valasz. Ez az alapertelmezes.
      "auto"       — a korabbi harom-agu markadontes (03-composer-spec §14).

    Igy a markaemlites nem beallitas, hanem a POSZT tulajdonsaga: ha valaki
    megkerdezi, mivel oldjuk meg, a valasz nem spam — ha nem kerdezi, akkor az.
    Az indok-stringet visszaadjuk (`brand_gate_reason`), hogy a dontes
    utolag is megmagyarazhato legyen.
    """
    policy = _brand_policy(config)
    if policy == "auto":
        return True, "brand_positioning=auto (globalis markadontes)"
    if policy == "off":
        return False, "brand_positioning=off (szigoru: kifejezett kerdesre sem)"

    # policy == "on_request" (es minden ismeretlen ertek erre esik vissza)
    if not reasoning.get("explicit_tool_request"):
        return False, "a poszt nem ker eszkozt"

    quote = reasoning.get("tool_request_quote", "")
    if not _quote_in_post(quote, post_text):
        return False, f"az idezett kerdes nem talalhato a posztban ({quote[:60]!r})"

    topic = reasoning.get("topic", "")
    if topic not in _BRAND_RELEVANT_TOPICS:
        return False, f"eszkoz-kerdes, de a tema ({topic}) nem Bridge-relevans"

    return True, f"kifejezett eszkoz-kerdes, igazolt idezet, tema={topic}"


def _compose_user_msg(post_text: str, author_line: str, reasoning: dict,
                      brand_allowed: bool, issues: list[str] | None = None) -> str:
    """A compose-hivas feladat-uzenete.

    A kritikus megkotesek (nyelv, hossz, tilalmak) a system-promptban IS benne
    vannak, de itt megismetelodnek: a HANDOFF §4/2 elesben megtanult lecke
    szerint a modell a csak listaelemkent szereplo szabalyt nem tartja be.
    """
    strat = STRATEGIES[reasoning["strategy"]]
    parts = [
        f"{author_line}POST:\n{post_text[:1800]}\n",
        "REASONING (use it, do not repeat it):",
        f"- core thesis: {reasoning['core_thesis']}",
        f"- missing perspective: {reasoning['missing_perspective']} "
        f"({reasoning['missing_perspective_reason']})",
        f"- strategy: {strat['label']} — {strat['directive']}",
        f"- the insight to deliver: {reasoning['insight']}",
        "",
        "Write ONE comment delivering that insight through that strategy.",
        "80-150 words, max two paragraphs, ~20% acknowledgement / 80% new thinking.",
        "Write it in the SAME language as the POST above. Do not switch language.",
        "Do not praise, do not summarise, do not open with agreement.",
    ]
    if brand_allowed:
        # Csak akkor jutunk ide, ha a poszt tenylegesen eszkozt kert (vagy a
        # globalis 'auto' mod aktiv). A megnevezes ilyenkor a KERDESRE adott
        # valasz, nem hirdetes — ezert szigoru keret: egy tagmondat, tenyszeru.
        parts.append(
            "The post explicitly asks for a tool, so you MAY name NODU Bridge "
            "(Archicad<->Revit parametric data exchange: it converts element "
            "LOGIC via native mapping, not static geometry via IFC) in ONE clause, "
            "factually, as one option among others. No pitch, no link, no claims "
            "beyond that. The insight still carries the comment — the tool is a "
            "footnote to it, not the point."
        )
    else:
        parts.append("Do not mention NODU, NODU Bridge, or any product or vendor.")
    if issues:
        parts += [
            "",
            "The previous attempt was rejected. Fix exactly these problems, "
            "keeping the same insight and strategy:",
            *(f"- {i}" for i in issues),
        ]
    return "\n".join(parts)


def generate_comment(config: dict, post_text: str, author_name: str = "",
                     author_role: str = "") -> dict:
    """
    Thought Leadership Engine — teljes pipeline egy LinkedIn-poszthoz.

    Visszaad: a dashboard altal olvasott 8 legacy mezo + az uj reasoning-mezok.
    Hiba eseten `{"error": "..."}` — a hivo (ui/app.py) ezt mar kezeli.

    Hivas-koltseg: tipikusan 2 LLM-hivas (reason + compose), legfeljebb 3
    (egy celzott ujrairas, ha a deterministikus kapu sertest talalt).
    """
    post_text = (post_text or "").strip()
    if not post_text:
        return {"error": "Üres poszt-szöveg."}

    client, model, err = _client(config)
    if err:
        print(f"[linkedin-tle] {err}")
        return {"error": err}

    author_line = ""
    if author_name or author_role:
        author_line = f"AUTHOR: {author_name or 'unknown'}" \
                      f"{' — ' + author_role if author_role else ''}\n"

    # --- Stage 1-5: reasoning ---
    try:
        reasoning = _call_json(
            client, model, _REASON_PROMPT,
            f"{author_line}POST:\n{post_text[:2000]}",
            _REASON_SCHEMA, max_tokens=900,
        )
    except Exception as e:
        print(f"[linkedin-tle] reasoning HIBA: {e}")
        return {"error": f"Gemini API hiba (reasoning): {e}"}
    if not reasoning or not isinstance(reasoning.get("strategy_fit"), dict):
        print(f"[linkedin-tle] Ervenytelen reasoning: {reasoning}")
        return {"error": "A reasoning-lépés érvénytelen választ adott."}
    # Stage 4: a dontest a kod hozza a modell pontszamaibol (ld. pick_strategy).
    reasoning["strategy"] = pick_strategy(reasoning["strategy_fit"])

    # Markaemlites: a POSZT tulajdonsaga, nem globalis beallitas (ld.
    # brand_mention_allowed). Az idezetet ellenorizzuk a posztban.
    brand_allowed, brand_reason = brand_mention_allowed(config, reasoning, post_text)
    print(f"[linkedin-tle] strategia={reasoning['strategy']} | markaemlites="
          f"{'ENGEDVE' if brand_allowed else 'tiltva'} ({brand_reason})")

    # --- Stage 6-7: compose, + Stage 9: kapu, legfeljebb egy ujrairassal ---
    comment, issues, rewrites = "", ["nem futott le"], 0
    for attempt in range(2):
        user_msg = _compose_user_msg(
            post_text, author_line, reasoning, brand_allowed,
            issues if attempt else None,
        )
        try:
            out = _call_json(client, model, _COMPOSE_PROMPT, user_msg,
                             _COMPOSE_SCHEMA, max_tokens=700)
        except Exception as e:
            print(f"[linkedin-tle] compose HIBA: {e}")
            return {"error": f"Gemini API hiba (compose): {e}"}
        comment = _normalise(((out or {}).get("comment") or ""))
        issues = check_quality(comment, post_text, brand_allowed)
        if not issues:
            break
        rewrites = attempt + 1
        print(f"[linkedin-tle] kapu elutasitotta ({attempt + 1}. kor): {', '.join(issues)}")

    if not comment:
        return {"error": "A kompozíciós lépés üres kommentet adott."}

    intent, style = _STRATEGY_TO_LEGACY[reasoning["strategy"]]
    strat_label = STRATEGIES[reasoning["strategy"]]["label"]

    return {
        # --- legacy mezok: a dashboard ezeket olvassa, formatum valtozatlan ---
        "topic": reasoning.get("topic", "general"),
        "post_type": reasoning.get("post_type", "general"),
        "engagement_intent": intent,
        "reply_style": style,
        # A UI harom erteket ismer (LI_BRAND_LABELS): bridge | nodu | none.
        # "bridge" akkor, ha a megnevezes tenyleg megtortent ES interop-temaban —
        # ez egyezik a 03-composer-spec §14 eredeti jelentesevel.
        "brand_mode": (
            ("bridge" if reasoning.get("topic") in _BRAND_RELEVANT_TOPICS else "nodu")
            if (brand_allowed and _BRAND_PATTERN.search(comment)) else "none"
        ),
        "confidence": reasoning.get("confidence", 0.0),
        "reply_text": comment,
        "rationale": f"{strat_label}: {reasoning.get('strategy_reason', '')} "
                     f"(kihagyott szempont: {reasoning.get('missing_perspective', '')})".strip(),
        # --- uj, additiv mezok (a UI figyelmen kivul hagyja oket) ---
        "engine": ENGINE_VERSION,
        "strategy": reasoning["strategy"],
        "strategy_label": strat_label,
        "core_thesis": reasoning.get("core_thesis", ""),
        "missing_perspective": reasoning.get("missing_perspective", ""),
        "insight": reasoning.get("insight", ""),
        "strategy_fit": reasoning.get("strategy_fit", {}),   # auditalhato dontes
        "explicit_tool_request": bool(reasoning.get("explicit_tool_request")),
        "tool_request_quote": reasoning.get("tool_request_quote", ""),
        "brand_allowed": brand_allowed,
        "brand_gate_reason": brand_reason,
        "author_objective": reasoning.get("author_objective", ""),
        "audience": reasoning.get("audience", ""),
        "technical_depth": reasoning.get("technical_depth", ""),
        "quality_issues": issues,          # ures = a kapu atengedte
        "rewrites": rewrites,
        "post_overlap": round(overlap_ratio(comment, post_text), 3),
    }
