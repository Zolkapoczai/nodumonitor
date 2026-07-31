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

CONVERSATION INTENT LAYER (2026-07-29, v2)
A v1 minden strategiat EGYENLOEN mert, fuggetlenul attol, MILYEN beszelgetesbe
szall be a komment. 30+ kezzel ertekelt poszt merese: velemeny-/dilemma-/
debate-posztokon 91-95/100, DE mesterseg-, tutorial-, portfolio- es
technika-megosztas posztokon a motor uzleti strategiava, ROI-va, szervezeti
hatassa emelte a temat, holott a szerzo szandekosan technikai szinten tartotta.
A komment technikailag helyes volt, de MAS KERDESRE valaszolt, mint amit a
szerzo feltett.

Ez nem reasoning-hiba volt, hanem hianyzo dontesi szint. Ezert a strategia-
valasztas ELE bekerult ket uj, a REASON-hivasban felvett mezo:

  conversation_intent — MILYEN szakmai beszelgetes ez? (nem: mi a temaja)
  discourse_level     — MELYIK sikon beszel a szerzo: technical | management |
                        business

es a kettobol a KOD ket kulon mechanizmussal dolgozik:

  1. INTENT-BIAS (lagy)  — minden intent el- vagy lehuzza az egyes strategiakat
     (`CONVERSATION_INTENTS[...]["bias"]`). A pontozas marad a modelle, a
     sulyozas a kode. A strategia-ter nem szukul, csak atrendezodik.
  2. LEVEL-VETO (kemeny) — ha a szerzo TECHNIKAI sikon beszel, a
     `business_impact` egyaltalan nem jelolhet (`_LEVEL_VETO`). Ez a munkaparancs
     "Critical Principle"-je: a beszelgetes absztrakcios szintjet nem a motor
     valasztja meg. Lagy levonas itt nem elegendo volt: ha a modell 10-re
     pontozza a business_impactet es 4-re a tobbit, egy -2-es bias meg mindig
     atengedi — a merheto kovetkezmeny pedig pont ez a hiba volt.

MIERT NEM UJ LLM-HIVAS A LAYER
Az intent egy OSZTALYOZAS ugyanarrol a szovegrol, amit a REASON-hivas mar
elemez — kulon hivasban ugyanazt a posztot olvasnank ujra, +1 korral es
+latenciaval, szinkron UI-muveletben. Ket uj sema-mezo ugyanazt a hatart huzza
meg, koltseg nelkul (a projekt elve: "Egy hivas, egy sema" —
01-architektura-audit §6/§7). A hivas-szam VALTOZATLAN: 2, legfeljebb 3.

AMI SZANDEKOSAN NEM VALTOZOTT
A `professional_opinion` es az `industry_debate` intent bias-a URES — ezek a
merésben 91-95/100-at kaptak, tehat a mai viselkedes a helyes viselkedes.
Az elfogadasi kriterium ("Opinion posts remain as strong as today") csak igy
garantalhato: a nem-torott esetben a dontes bitre azonos a v1-essel.

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

ENGINE_VERSION = "linkedin-tle-v3"

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

# --- Conversation Intent Layer (uj: stage 3.5, a strategia-valasztas ELOTT) --
# "Milyen szakmai beszelgetes ez?" — NEM "mi a temaja". A `recognise` a REASON-
# prompt osztalyozasi kriteriuma, a `directive` a COMPOSE-hivasba kerul, a `bias`
# pedig a strategia-pontszamokat sulyozza (pick_strategy).
#
# A BIAS-SZAMOK OLVASATA: a modell 0-10-re pontoz, tehat +/-1.5 eszreveheto de
# felulirhato, +/-3 dontő, -5 gyakorlatilag kizar. Ahol a munkaparancs "strong
# preference"/"strong penalty"-t irt, ott a nagyobb ertek all.
CONVERSATION_INTENTS: dict[str, dict] = {
    "professional_opinion": {
        "label": "Professional Opinion",
        "recognise": "the author argues a position or states a view and invites "
                     "agreement or disagreement",
        "directive": "The author is arguing a position. Engage with the argument "
                     "itself — its reasoning, its limits, its consequences.",
        # URES SZANDEKOSAN: a merésben ez az eset 91-95/100. Nincs mit javitani,
        # es a v1-es dontest bitre meg kell orizni (elfogadasi kriterium 1).
        "bias": {},
    },
    "industry_debate": {
        "label": "Industry Debate",
        "recognise": "the post enters an ongoing industry-level disagreement, or "
                     "contrasts conflicting viewpoints or vendor/standard camps",
        "directive": "This is a live industry disagreement. Take a clear, "
                     "defensible position and say what it rests on.",
        "bias": {},                       # ld. professional_opinion — mert eset
    },
    "engineering_problem": {
        "label": "Engineering Problem",
        "recognise": "the author describes an unresolved technical problem, "
                     "failure, blocker or dilemma they are actually facing",
        "directive": "There is an unresolved problem here. Produce new insight "
                     "into the problem — a cause, a constraint, a trade-off the "
                     "author has not named yet.",
        # A munkaparancs: preferalt systems_thinking / field_experience /
        # practical_lesson / missing_perspective; business_impact "only moderate
        # influence". A constructive_challenge NEM kap levonast: egy hibas
        # premisszat kimondani a legertekesebb hozzaszolas lehet.
        "bias": {
            "systems_thinking": 2.0,
            "field_experience": 2.0,
            "practical_lesson": 2.0,
            "missing_perspective": 1.5,   # a -1.5 alapbias-t nullara hozza
            "business_impact": -1.5,
            "future_outlook": -1.0,
        },
    },
    "technical_tutorial": {
        "label": "Technical Tutorial",
        "recognise": "the post teaches a method, workflow or software technique, "
                     "or walks through how to do something",
        "directive": "The author is teaching. EXTEND the lesson: practical "
                     "nuance, an implementation trade-off, a common mistake, or "
                     "a field observation that makes the method more reliable. "
                     "No executive abstraction.",
        "bias": {
            "field_experience": 2.5,
            "practical_lesson": 2.5,
            "missing_perspective": 0.5,
            "future_outlook": -2.0,
            "business_impact": -4.0,
        },
    },
    "craftsmanship": {
        "label": "Craftsmanship",
        "recognise": "the author shares detailed modelling, drafting or "
                     "engineering craft — how a thing was actually made, with "
                     "attention to the making itself",
        "directive": "The author is sharing craft. CONTRIBUTE CRAFT: your own "
                     "observation at the same level of concreteness. Do not "
                     "reframe the work as a business or organisational matter.",
        # A munkaparancs Root Cause-a NEVSZERINT KETTOT nevez meg elkovetokent:
        # "Business Impact OR Systems Thinking may win even when the author is
        # simply sharing craftsmanship" — ezert a systems_thinking is levonast kap.
        "bias": {
            "field_experience": 3.0,
            "practical_lesson": 3.0,
            "constructive_challenge": -1.0,
            "systems_thinking": -2.0,
            "future_outlook": -2.5,
            "business_impact": -5.0,
        },
    },
    "portfolio_showcase": {
        "label": "Portfolio Showcase",
        "recognise": "the author presents finished work, a project or a "
                     "visual/render primarily to show it",
        "directive": "The author is showing work. Acknowledge ONE concrete "
                     "engineering observation about it, then continue the "
                     "technical discussion with one practical insight. No ROI, "
                     "no competitive advantage, no organisational framing.",
        # A publikus kritika bemutatott munkara tarsadalmilag is rossz valasz,
        # ezert a constructive_challenge itt erosebb levonast kap, mint masutt.
        "bias": {
            "field_experience": 2.5,
            "practical_lesson": 2.0,
            "systems_thinking": -1.5,
            "constructive_challenge": -2.0,
            "future_outlook": -2.0,
            "business_impact": -5.0,
        },
    },
    "case_study": {
        "label": "Case Study",
        "recognise": "the post reports a concrete implementation with its "
                     "context, decisions and outcome",
        "directive": "This is a reported implementation. Engage with the "
                     "decisions and their consequences — what generalises from "
                     "this case and what does not.",
        # Hatareset: a case study gyakran MAR tartalmaz uzleti keretezest. Ha
        # igen, azt a discourse_level jelzi es a veto nem lep be; ha nem, ez a
        # moderalt levonas tartja technikai sikon.
        "bias": {
            "field_experience": 1.5,
            "practical_lesson": 1.5,
            "missing_perspective": 1.0,
            "systems_thinking": 0.5,
            "business_impact": -1.0,
        },
    },
    "product_demonstration": {
        "label": "Product Demonstration",
        "recognise": "the author demonstrates a tool, plugin, feature or "
                     "release, their own or someone else's",
        "directive": "A tool is being demonstrated. Engage with what it does and "
                     "does not handle in real workflows. Never position a "
                     "competing product.",
        "bias": {
            "field_experience": 2.0,
            "practical_lesson": 1.5,
            "constructive_challenge": 1.0,
            "business_impact": -2.0,
            "future_outlook": -0.5,
        },
    },
    "reflection": {
        "label": "Reflection",
        "recognise": "the author reflects personally on their career, practice, "
                     "a lesson learned or a change in how they work",
        "directive": "This is personal reflection. Match it with observation "
                     "from practice, not with analysis of the author.",
        "bias": {
            "field_experience": 2.0,
            "practical_lesson": 1.0,
            "missing_perspective": 0.5,
            "systems_thinking": -1.0,
            "constructive_challenge": -2.0,
            "business_impact": -3.0,
        },
    },
    "personal_experience": {
        "label": "Personal Experience",
        "recognise": "the author shares a lived moment, visit, interaction or "
                     "personal observation, where the human experience is the "
                     "point rather than a lesson or a framework",
        "directive": "This is a human experience. Respond as a fellow "
                     "practitioner: stay with the people, observation and immediate "
                     "meaning. Do not convert the story into process, governance or "
                     "organisational language.",
        "bias": {
            "field_experience": 2.5,
            "practical_lesson": 0.5,
            "systems_thinking": -1.5,
            "constructive_challenge": -2.0,
            "business_impact": -3.0,
        },
    },
    "question_to_community": {
        "label": "Question to Community",
        "recognise": "the author asks the reader a real question and wants an "
                     "answer",
        "directive": "ANSWER THE QUESTION THAT WAS ASKED. Do not change the "
                     "subject, and do not answer a more interesting question "
                     "instead. The answer comes first; anything else is a rider.",
        # A `missing_perspective` itt a legrosszabb valasz: "van egy szempont,
        # amit nem vettel figyelembe" pontosan a temavaltas. Az alapbias-szal
        # egyutt -3.5, tehat gyakorlatilag kizart.
        "bias": {
            "field_experience": 3.0,
            "practical_lesson": 3.0,
            "missing_perspective": -2.0,
            "constructive_challenge": -1.5,
            "future_outlook": -2.0,
            "business_impact": -3.0,
            "systems_thinking": -0.5,
        },
    },
    "announcement": {
        "label": "Announcement",
        "recognise": "the author announces their own news — a release, a role, "
                     "a milestone, an event",
        "directive": "This is the author's own news. One clause of "
                     "acknowledgement, then one substantive observation about "
                     "what it changes in practice. Never criticise it.",
        "bias": {
            "field_experience": 1.5,
            "future_outlook": 1.0,
            "practical_lesson": 0.5,
            "systems_thinking": -1.0,
            "business_impact": -2.0,
            "constructive_challenge": -3.0,
        },
    },
    "industry_news": {
        "label": "Industry News",
        "recognise": "the author shares third-party news (a vendor release, an "
                     "acquisition, a standard) without arguing a position on it",
        "directive": "News is being relayed without a position. Supply the "
                     "reading of it that practitioners need — what actually "
                     "changes for the work.",
        "bias": {
            "future_outlook": 1.5,
            "field_experience": 1.0,
            "missing_perspective": 1.0,
            "constructive_challenge": -1.0,
        },
    },
    "general": {
        "label": "General",
        "recognise": "none of the above fits — use this only as a last resort",
        "directive": "Contribute one substantive professional observation at the "
                     "author's own level.",
        "bias": {},                       # ismeretlen eset: v1-es viselkedes
    },
}

# --- Discourse level: MELYIK sikon beszel a szerzo? --------------------------
# Ez NEM ugyanaz, mint a `technical_depth` (az azt meri, MENNYIRE melyen technikai
# a szoveg). Egy poszt lehet felszines ES uzleti sikon fekvo, vagy expert-szintu
# ES tisztan technikai. A ketto kulon mezo, kulon dontest tamogat.
_DISCOURSE_LEVELS = ["technical", "management", "business"]

# --- Conversation-shaping layer (v3) ----------------------------------------
# Az intent azt mondja meg, MILYEN beszelgetes zajlik; ez a ket mezo azt, milyen
# szerepet var el a szerzo a valaszolotol, illetve MI legyen a komment formaja.
# Mindketto ugyanabban a REASON-hivasban jon vissza: nem indokol uj LLM-kort.
RESPONDER_ROLES: dict[str, str] = {
    "peer_practitioner": "Speak as a peer practitioner sharing directly relevant craft.",
    "technical_advisor": "Give the requested technical advice plainly before adding context.",
    "discussion_partner": "Explore the author's question or position with them, not at them.",
    "product_reviewer": "Offer concrete, user-centred feedback on the demonstrated tool or feature.",
    "research_peer": "Engage as a research peer: be precise about evidence, method and limits.",
    "experience_sharer": "Share a closely related observation while preserving the human tone.",
    "professional_peer": "Respond as an experienced equal at the author's chosen level.",
}

RESPONSE_MODES: dict[str, str] = {
    "direct_answer": "Answer the explicit question directly in the opening sentence.",
    "concrete_suggestion": "Give one concrete feature, example, alternative or practical idea first.",
    "technical_extension": "Extend the technique with one near implementation trade-off or common failure mode.",
    "analytical_response": "Engage the stated argument with one specific implication or limitation.",
    "experience_connection": "Connect through one closely related field observation; preserve the human focus.",
}

HUMAN_TEMPERATURES = [
    "matter_of_fact", "practical", "curious", "reflective", "celebratory",
    "personal", "frustrated", "provocative",
]

_HUMAN_CENTERED_INTENTS = {"reflection", "personal_experience"}

# A "Critical Principle" KODBAN. Lagy levonas helyett VETO — ld. a modul-
# docstring 2. pontjat: a -2-es bias atengedi a 10-re pontozott business_impactet,
# es pont ez volt a jelentett hiba.
_LEVEL_VETO: dict[str, set[str]] = {
    "technical": {"business_impact"},
    "management": set(),
    "business": set(),
}

# Ha a szerzo MAR uzleti sikra tette a beszelgetest, ott folytatni nem elemelés,
# hanem a beszelgetes kovetese — ilyenkor a business_impact felertekelodik.
_LEVEL_STRATEGY_BIAS: dict[str, dict[str, float]] = {
    "technical": {},                      # a vetot nem kell levonassal duplazni
    "management": {},
    "business": {"business_impact": 1.5},
}


def _intent_key(raw) -> str:
    """A modell intent-mezoje -> ervenyes kulcs (ismeretlen esetben 'general')."""
    key = str(raw or "").strip().lower()
    return key if key in CONVERSATION_INTENTS else "general"


def _level_key(raw) -> str:
    """A modell discourse_level-mezoje -> ervenyes kulcs.

    Ismeretlen ertek eseten 'technical' a default, mert az a SZIGORUBB ag (ott
    all a veto). Egy hibas/hianyzo osztalyozas igy nem nyithatja meg az uzleti
    keretezest — a hallgatolagos viselkedes a konzervativ.
    """
    key = str(raw or "").strip().lower()
    return key if key in _DISCOURSE_LEVELS else "technical"


def _responder_role_key(raw) -> str:
    """Modell-mezo -> ervenyes valaszolo-szerep, konzervativ peer defaulttal."""
    key = str(raw or "").strip().lower()
    return key if key in RESPONDER_ROLES else "peer_practitioner"


def _response_mode_key(raw) -> str:
    """Modell-mezo -> ervenyes valaszforma; ismeretlenul kozel marad a munkahoz."""
    key = str(raw or "").strip().lower()
    return key if key in RESPONSE_MODES else "technical_extension"


def _human_temperature_key(raw) -> str:
    """Modell-mezo -> ervenyes emberi hangnem, semleges gyakorlati defaulttal."""
    key = str(raw or "").strip().lower()
    return key if key in HUMAN_TEMPERATURES else "practical"


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
2. conversation_intent — WHAT KIND OF PROFESSIONAL CONVERSATION IS THIS? This is
   not the topic and not the subject matter: it is what the author is DOING.
   Exactly one value:
{chr(10).join(f'   - {k}: {v["recognise"]}' for k, v in CONVERSATION_INTENTS.items())}
3. discourse_level — WHICH PLANE the author chose to speak on. Report what IS
   there, not what could be there:
   - technical — the post stays with the work itself: geometry, families,
     parameters, methods, tools, code, modelling decisions.
   - management — the post is about process, teams, coordination, standards
     adoption, workflows across people.
   - business — the post itself already argues cost, revenue, risk, competitive
     position, client value or organisational strategy.
   Choosing "business" or "management" when the author never went there is an
   ERROR, and it changes how the comment is written. When genuinely unsure,
   answer "technical". This is INDEPENDENT of technical_depth: a shallow post can
   be on the business plane, an expert post can be purely technical.
4. expected_responder_role — WHICH ROLE the author implicitly invites. Exactly
   one value:
{chr(10).join(f'   - {k}: {v}' for k, v in RESPONDER_ROLES.items())}
   A direct question normally needs technical_advisor; a request for feature
   ideas needs product_reviewer; a personal story needs experience_sharer. Do
   not default to an industry analyst when the post assigns a narrower role.
5. response_mode — WHAT SHAPE will serve that role. Exactly one value:
{chr(10).join(f'   - {k}: {v}' for k, v in RESPONSE_MODES.items())}
   When the author explicitly asks for suggestions, select concrete_suggestion.
   When the author asks a question, select direct_answer unless they specifically
   ask for feature ideas or alternatives.
6. human_temperature — the human register to preserve. Exactly one value:
   matter_of_fact | practical | curious | reflective | celebratory | personal |
   frustrated | provocative. Preserve a human story as a human story: do not
   translate a factory visit, career moment or personal observation into a
   process, governance or efficiency discussion.
7. topic_gravity — the post's natural centre of gravity in 2-5 words: the
   concrete subject a knowledgeable reply would stay close to. Examples:
   "Revit family authoring", "Civil 3D surface modelling", "MEP clash
   coordination", "IFC property mapping". Name the subject, not the abstraction.
8. author_objective — what the author actually wants (attention, validation,
   recruitment, debate, teaching, announcement...). Not a summary.
9. audience — who the post is written for.
10. technical_depth — surface | practitioner | expert.
11. emotional_tone — the author's register (neutral, frustrated, promotional,
   celebratory, reflective, provocative...).
12. core_thesis — the ONE central claim, in one sentence. Ignore supporting
   arguments and examples. If the post has several, pick the load-bearing one.
13. missing_perspective — the STRONGEST dimension the post does not address,
    from the allowed list. Exactly one. Never a list.
14. missing_perspective_reason — one sentence: why this omission matters here.
15. strategy_fit — score EVERY strategy 0-10 on how much professional value it
    would add to THIS post. Do not pick a winner; score them all honestly, and
    let the scores differ. The missing perspective from step 10 is an input to
    this scoring, not the answer to it.
{chr(10).join(f'    - {k}: fits when {v["wins_when"]}' for k, v in STRATEGIES.items())}
    Score on professional value ALONE. Do NOT down-score a strategy because it
    seems to clash with the conversation_intent or the discourse_level — those
    are weighted separately, after you answer. Double-counting them here distorts
    the decision.
16. strategy_reason — one sentence: what the comment has to accomplish for this
    specific audience to be worth reading.
17. explicit_tool_request — true ONLY if the post (or the author in it) directly
    asks the reader to name a tool, product, plugin, service or vendor.
    True examples: "what do you use for this?", "any tool recommendations?",
    "how do you solve this in practice — which software?", "milyen eszkozzel
    oldjatok meg?".
    FALSE for: describing a problem, complaining, asking for opinions or advice
    in general, rhetorical questions, or asking "how" without asking "with what".
    Someone stating a pain is NOT asking for a product. Default to false.
18. tool_request_quote — if explicit_tool_request is true, copy the EXACT words
    from the post that contain the request, verbatim, nothing else. Empty string
    if false. Do not paraphrase — the quote is verified against the post.
19. insight — ONE original, specific claim that is NOT stated in the post and is
    not a restatement of it. This is the substance of the comment. Go deeper,
    not wider. No hedging, no generalities like "communication is important".
    The insight must sit at the discourse_level you reported in step 3 — on a
    technical post, a deeper technical claim, NOT a business consequence.
20. confidence — 0.0-1.0, your confidence in this reasoning.

Hard rules:
- Do NOT summarise the post anywhere.
- The insight must survive the question "would an experienced professional learn
  something from this?". If not, choose a different one.
- No invented statistics, customer names or personal anecdotes.
- Depth is not abstraction. Going deeper into the author's own subject is worth
  more than moving up a level away from it.
""".strip()

_REASON_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "topic": {"type": "STRING", "enum": _TOPICS},
        "post_type": {"type": "STRING", "enum": _POST_TYPES},
        # Conversation Intent Layer — a strategia-valasztas ELOTTI dontes.
        "conversation_intent": {"type": "STRING", "enum": list(CONVERSATION_INTENTS)},
        "discourse_level": {"type": "STRING", "enum": _DISCOURSE_LEVELS},
        "expected_responder_role": {"type": "STRING", "enum": list(RESPONDER_ROLES)},
        "response_mode": {"type": "STRING", "enum": list(RESPONSE_MODES)},
        "human_temperature": {"type": "STRING", "enum": HUMAN_TEMPERATURES},
        "topic_gravity": {"type": "STRING"},
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
        "topic", "post_type", "conversation_intent", "discourse_level",
        "expected_responder_role", "response_mode", "human_temperature",
        "topic_gravity", "author_objective", "audience", "technical_depth",
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


def effective_bias(intent: str = "general",
                   discourse_level: str = "technical") -> dict[str, float]:
    """Strategiankent a HAROM bias-forras osszege.

      alap   — `_STRATEGY_BIAS`: a fallback-levonas, intenttol fuggetlenul.
      intent — `CONVERSATION_INTENTS[intent]["bias"]`: milyen beszelgetes ez.
      szint  — `_LEVEL_STRATEGY_BIAS[level]`: hol all a szerzo absztrakcioban.

    Osszeadodnak, nem felulirjak egymast: igy a `missing_perspective` alap-levonasa
    megmarad ott is, ahol az intent felhozza (pl. engineering_problem +1.5 -> net 0),
    es nem kell minden intentnel ujra leirni.
    """
    intent_bias = CONVERSATION_INTENTS[_intent_key(intent)].get("bias", {})
    level_bias = _LEVEL_STRATEGY_BIAS.get(_level_key(discourse_level), {})
    return {
        slug: (_STRATEGY_BIAS.get(slug, 0.0)
               + intent_bias.get(slug, 0.0)
               + level_bias.get(slug, 0.0))
        for slug in STRATEGIES
    }


def score_strategies(fit: dict, intent: str = "general",
                     discourse_level: str = "technical") -> tuple[dict, set]:
    """(sulyozott pontszamok, vetozott strategiak) — a dontes teljes nyoma.

    Kulon fuggveny, hogy a dontes VISSZAADHATO es teszthető legyen a valasztas
    nelkul is: a `generate_comment` ezt teszi be a valaszba
    (`strategy_scores` / `strategy_vetoed`), igy utolag megmagyarazhato, miert
    az a strategia nyert — ugyanaz az elv, mint a `brand_gate_reason`-nel.
    """
    bias = effective_bias(intent, discourse_level)
    scores = {}
    for slug in STRATEGIES:
        raw = fit.get(slug)
        base = float(raw) if isinstance(raw, (int, float)) else 0.0
        scores[slug] = round(base + bias[slug], 2)
    return scores, set(_LEVEL_VETO.get(_level_key(discourse_level), set()))


def pick_strategy(fit: dict, intent: str = "general",
                  discourse_level: str = "technical") -> str:
    """Stage 4 dontes — DETERMINISZTIKUS, a modell pontszamaibol.

    Miert nem a modell valaszt: enum-valasztasnal pozicio- es
    absztrakcio-torzitast mutatott (a listaban elore tett, "okosan hangzo"
    strategiat valasztotta akkor is, ha egy konkretabb jobban illett). A
    pontozas + kodbeli argmax ugyanaz a minta, mint a projekt scoring-elve
    (01-architektura-audit §7: "a Scorer determinisztikus — az LLM mezoket ad,
    a pontszamot sulyprofil szamolja"). Igy a dontes auditalhato es
    reprodukalhato: ugyanaz a pontszam-vektor mindig ugyanazt adja.

    2026-07-29 (v2): a pontszamra rakerul a Conversation Intent Layer sulyozasa,
    es a VETO. A default `discourse_level="technical"` a SZIGORUBB ag — egy
    hivas, ami nem ad meg szintet, nem nyithatja meg az uzleti keretezest.

    Holtverseny: a STRATEGIES deklaracios sorrendje dont (a fallback all utolso).
    """
    scores, vetoed = score_strategies(fit, intent, discourse_level)
    # A veto sosem urithet ki a jelolt-listat: 7 strategia, legfeljebb 1 vetozott.
    # A `or list(STRATEGIES)` csak vedoszabaly egy jovobeli, szelesebb veto ellen.
    candidates = [s for s in STRATEGIES if s not in vetoed] or list(STRATEGIES)

    best, best_score = None, None
    for slug in candidates:                      # stabil, deklaracios sorrend
        if best_score is None or scores[slug] > best_score:
            best, best_score = slug, scores[slug]
    return best or "missing_perspective"

# --- Stage 6-7: COMPOSE -----------------------------------------------------
_COMPOSE_PROMPT = """
You write LinkedIn comments as an experienced AEC/BIM professional. You are given
finished reasoning; your only job is to turn it into a comment that reads as
written by a practitioner, not by an assistant.

Structure: roughly 20% acknowledgement of the author's point, 80% new thinking.
The acknowledgement is a bridge, not praise — one clause, then move on.

STAY IN THE CONVERSATION THAT IS ALREADY HAPPENING. This is the hardest rule and
the one most often broken:
- Write at the abstraction level the AUTHOR chose. Never climb from technical to
  process, to management, to business, to strategy. If the author is discussing
  how a wall type behaves, the comment discusses how a wall type behaves — not
  what it costs the practice.
- Stay near the post's centre of gravity. A post about Revit families is about
  family authoring, not about digital transformation. A post about Civil 3D
  surfaces is about terrain modelling, not about hardware budgets.
- Depth is not abstraction. Going further INTO the author's own subject is
  thought leadership. Moving UP and away from it is changing the subject.
- Continue the conversation; do not reframe it. If the author asks something,
  answer it. If the author teaches, extend the lesson. If the author shows work,
  discuss the engineering in it. If the author shares craft, contribute craft.
Only follow the discussion to commercial, organisational or strategic ground if
the author has ALREADY taken it there.

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

# A benchmarkban ujra es ujra ezekkel a szerkezetekkel indult a komment. Nem
# tartalmi hibak, de azonos nyitasok sorozata AI-ujjlenyomat. Csak mondat-eleji
# egyezest merunk, igy a kifejezes kesobbi, tartalmilag indokolt hasznalata nem
# serul.
_STOCK_OPENING_PATTERNS: list[tuple[str, str]] = [
    (r"^\s*we often see\b", "ismetlodo nyitas (We often see)"),
    (r"^\s*one consideration(?: is)?\b", "ismetlodo nyitas (One consideration)"),
    (r"^\s*in practice\b", "ismetlodo nyitas (In practice)"),
    (r"^\s*one recurring (?:challenge|pattern)\b", "ismetlodo nyitas (One recurring)"),
]

# Csak a komment VEGEN vizsgaljuk: onmagukban ezek a szavak lehetnek igazak, de
# konkluziokent nem mondanak tobbet, mint az alapertelmezett LLM-payoff. A modell
# az aktualis gyakorlati/emberi kovetkezmennyel zarjon helyette.
_EFFICIENCY_ENDING_PATTERNS: list[tuple[str, str]] = [
    (r"\b(?:improves?|improving|improved|boosts?)\s+(?:overall\s+|operational\s+)?(?:productivity|efficiency)\.?\s*$",
     "sablonos hatekonysag-zaras"),
    (r"\b(?:supports?|improves?)\s+(?:better\s+)?project delivery\.?\s*$",
     "sablonos project-delivery zaras"),
    (r"\b(?:helps?|enables?|allows?)\s+(?:organisations?|organizations?)\s+(?:to\s+)?scale\.?\s*$",
     "sablonos scale-zaras"),
]

# Egyetlen szo nem jelenti, hogy a komment elhagyta a beszelgetest. Ket vagy tobb
# OLYAN kifejezes viszont, amit a szerzo nem hasznalt, mar a megfigyelt
# framework->process->governance reflex merheto jele. Ezert itt nem tiltott szavak,
# hanem kontextushoz kotott lanc.
_AI_FINGERPRINT_PATTERNS: list[tuple[str, str]] = [
    (r"\boperational efficiency\b", "operational efficiency"),
    (r"\bstructured process(?:es)?\b", "structured process"),
    (r"\bgovernance\b", "governance"),
    (r"\bstandardi[sz]ation\b", "standardisation"),
    (r"\bconsistency\b", "consistency"),
    (r"\benterprise adoption\b", "enterprise adoption"),
    (r"\bstakeholder alignment\b", "stakeholder alignment"),
    (r"\bframework\b", "framework"),
]

_BRAND_PATTERN = re.compile(r"\bnodu\b|\bnodu[ .-]?bridge\b", re.IGNORECASE)

# --- Stage 9b: executive-absztrakcio szivargas (2026-07-29) ------------------
# A munkaparancs nevszerint felsorolt "Avoid" listaja: generic ROI, competitive
# advantage, profitability, organisational transformation, executive framing. Ezek
# MERHETOK, tehat a kapuba tartoznak, nem csak a promptba (ugyanaz az elv, mint a
# tiltott dicseret-fordulatoknal): a prompt-utasitast a modell megszegheti, a
# regexet nem.
#
# PRECIZIO > FEDES. Egy hamis pozitiv egy FELESLEGES ujrairo hivast koltene, ezert
# csak olyan kifejezes van a listan, ami technikai kommentben nem fordul elo
# ARTATLANUL. Ezert nincs itt "cost", "value", "efficiency", "time" — ezek egy
# technikai kommentben teljesen legitimek ("the cost of remodelling the family").
_EXEC_ABSTRACTION_PATTERNS: list[tuple[str, str]] = [
    (r"\broi\b", "ROI"),
    (r"\breturn on investment\b", "ROI"),
    (r"\bmegter(?:ules|ülés)\b", "ROI (HU)"),
    (r"\bcompetitive advantage\b", "versenyelony-keretezes"),
    (r"\bversenyelony\b|\bversenyelőny\b", "versenyelony-keretezes (HU)"),
    (r"\bprofitabilit(?:y|ies)\b", "jovedelmezoseg-keretezes"),
    (r"\bjovedelmezoseg\b|\bjövedelmezőség\b", "jovedelmezoseg-keretezes (HU)"),
    (r"\borganisational transformation\b|\borganizational transformation\b",
     "szervezeti transzformacio"),
    (r"\bszervezeti (?:atalakulas|átalakulás|transzformacio|transzformáció)\b",
     "szervezeti transzformacio (HU)"),
    (r"\bdigital transformation\b", "digitalis transzformacio"),
    (r"\bdigit(?:alis|ális) transzform(?:acio|áció)\b", "digitalis transzformacio (HU)"),
    (r"\btotal cost of ownership\b|\btco\b", "TCO"),
    (r"\bbusiness case\b", "business case"),
    (r"\bbottom line\b", "bottom line"),
    (r"\bstakeholder value\b|\bshareholder value\b", "stakeholder value"),
    (r"\bbusiness value\b", "business value"),
    (r"\buzleti ertek\b|\büzleti érték\b", "business value (HU)"),
    (r"\bc-level\b|\bexecutive buy-?in\b", "executive framing"),
    (r"\bbottom-?line impact\b", "bottom line"),
]

# Azok az intentek, ahol a munkaparancs KIFEJEZETTEN tiltja az uzleti keretezest,
# fuggetlenul attol, mit mondott a discourse_level. Ha a szint-osztalyozas
# tevedne, ez a masodik halo.
_NO_EXEC_ABSTRACTION_INTENTS = {
    "craftsmanship", "portfolio_showcase", "technical_tutorial",
}

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


def ai_fingerprint_terms(comment: str, post_text: str) -> list[str]:
    """Nem a posztbol jovo framework-nyelv visszatérő elemei.

    A szerzo sajat "governance"-szavaira valaszolni teljesen jogos. Ezert csak
    olyan mintat adunk vissza, ami a kommentben szerepel, a posztban viszont nem.
    Egyetlen talalat diagnosztikai jel; ketto mar a minosegkapu szamara is eleg.
    """
    low_comment, low_post = (comment or "").lower(), (post_text or "").lower()
    return [label for pattern, label in _AI_FINGERPRINT_PATTERNS
            if re.search(pattern, low_comment, re.IGNORECASE)
            and not re.search(pattern, low_post, re.IGNORECASE)]


def check_quality(comment: str, post_text: str, brand_allowed: bool = False,
                  intent: str = "", discourse_level: str = "",
                  human_temperature: str = "") -> list[str]:
    """Stage 9 — deterministikus kapu. Visszaadja a KONKRET serteseket.

    A lista uressege a "mehet" jel. A hivo ezt a listat adja at az ujrairo
    hivasnak, hogy a modell tudja, mit kell javitani — igy egy korbol javul,
    nem talalgat.

    `intent` / `discourse_level` (2026-07-29): ha a szerzo technikai sikon
    beszelt — vagy az intent kifejezetten tiltja az uzleti keretezest —, akkor az
    executive-absztrakcio szotar is sertes. Ures ertekkel a kapu a v1-es
    viselkedest adja, tehat a regi hivasok valtozatlanul mukodnek.

    v3: aktiv Conversation Intent Layer mellett a sablonos nyitas/záras is
    merheto; a framework-reflex csak technikai vagy emberkozpontu
    beszelgetesben, es csak ket uj (a szerzotol nem atvett) kifejezesnel indit
    ujrairast.
    """
    issues: list[str] = []
    text = (comment or "").strip()
    if not text:
        return ["ures komment"]

    low = text.lower()
    shaping_active = bool(intent or discourse_level or human_temperature)
    for pattern, label in _FORBIDDEN_PATTERNS:
        if re.search(pattern, low, re.IGNORECASE | re.MULTILINE):
            issues.append(f"tiltott fordulat ({label})")

    if shaping_active:
        for pattern, label in _STOCK_OPENING_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
                issues.append(label)

        tail = low[-220:]
        for pattern, label in _EFFICIENCY_ENDING_PATTERNS:
            if re.search(pattern, tail, re.IGNORECASE | re.MULTILINE):
                issues.append(label)

    # Absztrakcio-szivargas: uzleti/vezetoi szotar olyan beszelgetesben, amit a
    # szerzo technikai szinten tartott. Csak akkor mer, ha van mihez mernie —
    # ures intent/level eseten (regi hivas) kihagyjuk.
    if (discourse_level == "technical") or (intent in _NO_EXEC_ABSTRACTION_INTENTS):
        for pattern, label in _EXEC_ABSTRACTION_PATTERNS:
            if re.search(pattern, low, re.IGNORECASE | re.MULTILINE):
                issues.append(
                    f"uzleti absztrakcio technikai beszelgetesben ({label})"
                )

    # Az AI-fingerprint nem egyetlen tiltott szo: csak a nem-indokolt, tobbtagu
    # framework-lanc. `human_temperature` a hivasi szerzodes resze es a jovo
    # finomitast tamogatja; az intent eleg a determinisztikus scope-hoz.
    fingerprint = ai_fingerprint_terms(text, post_text)
    if ((discourse_level == "technical") or
            (intent in _HUMAN_CENTERED_INTENTS)) and len(fingerprint) >= 2:
        issues.append(f"AI-ujjlenyomat / framework-reflex ({', '.join(fingerprint[:3])})")

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


# A layer kikapcsolt allapotanak "egysegeleme": a `general` intent bias-a ures, a
# `management` szint bias-a ES vetoja is ures — ezzel a dontes BITRE a v1-es.
_LAYER_OFF = ("general", "management")


def _intent_layer_enabled(config: dict) -> bool:
    """`linkedin.intent_layer`: on (default) | off.

    Miert van kapcsolo: a Conversation Intent Layer viselkedes-valtozas, amit
    benchmarkon merunk. Ezzel a 30+ posztos meres UGYANAZON a kodon megismetelheto
    ki- es bekapcsolva, git-revert nelkul. Kikapcsolva a dontes bitre a v1-es
    (ld. `_LAYER_OFF`), es a compose-prompt sem kap intent/szint sort.

    A YAML az on/off/yes/no szavakat booleanna alakitja (YAML 1.1) — ezert a bool
    agat is kezeljuk, ugyanaz a csapda, mint a `_brand_policy`-nal (HANDOFF §4/17).
    """
    raw = (config.get("linkedin", {}) or {}).get("intent_layer", "on")
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() not in ("off", "false", "0", "no", "none")


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
                      brand_allowed: bool, issues: list[str] | None = None,
                      intent_layer: bool = True) -> str:
    """A compose-hivas feladat-uzenete.

    A kritikus megkotesek (nyelv, hossz, tilalmak) a system-promptban IS benne
    vannak, de itt megismetelodnek: a HANDOFF §4/2 elesben megtanult lecke
    szerint a modell a csak listaelemkent szereplo szabalyt nem tartja be.

    `intent_layer=False` eseten az intent/szint/gravity/role sorok kimaradnak —
    igy a kikapcsolt layer a v1-es promptot allitja elo.
    """
    strat = STRATEGIES[reasoning["strategy"]]
    intent = CONVERSATION_INTENTS[_intent_key(reasoning.get("conversation_intent"))]
    level = _level_key(reasoning.get("discourse_level"))
    responder_role = _responder_role_key(reasoning.get("expected_responder_role"))
    response_mode = _response_mode_key(reasoning.get("response_mode"))
    human_temperature = _human_temperature_key(reasoning.get("human_temperature"))
    gravity = (reasoning.get("topic_gravity") or "").strip()

    # A beszelgetes-tipus es az absztrakcios szint a HIVAS ELEJERE kerul, nem a
    # vegere: a HANDOFF §4/2 lecke szerint a modell a lista vegen szereplo
    # megkotest gyakran nem tartja be. Ez a ket sor donti el, MELYIK
    # beszelgetesbe szall be — a strategia mar csak azt, hogyan.
    parts = [f"{author_line}POST:\n{post_text[:1800]}\n"]
    if intent_layer:
        parts.append(f"CONVERSATION TYPE: {intent['label']} — {intent['directive']}")
        parts.append(
            f"THE AUTHOR IS SPEAKING ON THE {level.upper()} PLANE. Write on that "
            f"same plane. Do not move the discussion to a higher level of "
            f"abstraction."
        )
        parts.append(
            f"YOUR EXPECTED ROLE: {responder_role}. "
            f"{RESPONDER_ROLES[responder_role]}"
        )
        parts.append(
            f"RESPONSE SHAPE: {response_mode}. {RESPONSE_MODES[response_mode]}"
        )
        parts.append(
            f"HUMAN TEMPERATURE: {human_temperature}. Match that register; do not "
            "cool a human story into a process discussion."
        )
        parts.append(
            "Begin with the contribution itself, not a stock consultant opening "
            "such as 'We often see', 'One consideration', 'In practice' or 'One "
            "recurring challenge'. Vary the rhetorical shape naturally."
        )
        parts.append(
            "Do not end with a generic payoff such as productivity, efficiency, "
            "project delivery or organisational scale. End on the concrete "
            "engineering, human or practical point instead."
        )
        if gravity:
            parts.append(f"CENTRE OF GRAVITY: {gravity}. Stay close to this subject.")
    parts += [
        "",
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
    if intent_layer:
        parts.append("Do not reframe the conversation into a different one.")
        if level == "technical":
            parts.append(
                "The author stayed technical, so you stay technical: no ROI, no "
                "competitive advantage, no profitability, no organisational or "
                "executive framing. Contribute engineering substance instead."
            )
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
            # 900 -> 1100: a semaba harom uj mezo kerult (conversation_intent,
            # discourse_level, topic_gravity). A ket enum nehany token, a
            # topic_gravity 2-5 szo — de a csonka-JSON hiba (§4/1) itt a TELJES
            # valaszt viszi, ezert a keret inkabb bo. A fel nem hasznalt keret nem
            # kerul semmibe: a szamlazas a tenyleges output-tokenre megy.
            _REASON_SCHEMA, max_tokens=1100,
        )
    except Exception as e:
        print(f"[linkedin-tle] reasoning HIBA: {e}")
        return {"error": f"Gemini API hiba (reasoning): {e}"}
    if not reasoning or not isinstance(reasoning.get("strategy_fit"), dict):
        print(f"[linkedin-tle] Ervenytelen reasoning: {reasoning}")
        return {"error": "A reasoning-lépés érvénytelen választ adott."}

    # --- Stage 3.5: Conversation Intent Layer ---
    # A modell OSZTALYOZ (szenzor), a sulyozast es a vetot a kod vegzi (biro) —
    # §4/16. Kikapcsolt layer eseten a `_LAYER_OFF` par az egysegelem, tehat a
    # dontes bitre a v1-es.
    intent_layer = _intent_layer_enabled(config)
    if intent_layer:
        intent = _intent_key(reasoning.get("conversation_intent"))
        level = _level_key(reasoning.get("discourse_level"))
        responder_role = _responder_role_key(reasoning.get("expected_responder_role"))
        response_mode = _response_mode_key(reasoning.get("response_mode"))
        human_temperature = _human_temperature_key(reasoning.get("human_temperature"))
    else:
        intent, level = _LAYER_OFF
        responder_role = "peer_practitioner"
        response_mode = "technical_extension"
        human_temperature = "practical"
    # A normalizalt ertekeket visszairjuk: innentol a compose es a kapu is a
    # KODBAN ervenyesnek elfogadott erteket lassa, nem a modell nyers stringjet.
    reasoning["conversation_intent"] = intent
    reasoning["discourse_level"] = level
    reasoning["expected_responder_role"] = responder_role
    reasoning["response_mode"] = response_mode
    reasoning["human_temperature"] = human_temperature

    # Stage 4: a dontest a kod hozza a modell pontszamaibol (ld. pick_strategy).
    reasoning["strategy"] = pick_strategy(reasoning["strategy_fit"], intent, level)
    strategy_scores, strategy_vetoed = score_strategies(
        reasoning["strategy_fit"], intent, level)
    print(f"[linkedin-tle] intent={intent} | szint={level} | szerep={responder_role} | "
          f"forma={response_mode} | gravity={(reasoning.get('topic_gravity') or '-')!r}"
          + (f" | vetozott={sorted(strategy_vetoed)}" if strategy_vetoed else "")
          + ("" if intent_layer else " | INTENT LAYER KIKAPCSOLVA"))

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
            issues if attempt else None, intent_layer=intent_layer,
        )
        try:
            out = _call_json(client, model, _COMPOSE_PROMPT, user_msg,
                             _COMPOSE_SCHEMA, max_tokens=700)
        except Exception as e:
            print(f"[linkedin-tle] compose HIBA: {e}")
            return {"error": f"Gemini API hiba (compose): {e}"}
        comment = _normalise(((out or {}).get("comment") or ""))
        # A kapu csak akkor meri az absztrakcio-szivargast, ha a layer be van
        # kapcsolva — kikapcsolva a v1-es kapu fut.
        issues = check_quality(
            comment, post_text, brand_allowed,
            intent=intent if intent_layer else "",
            discourse_level=level if intent_layer else "",
            human_temperature=human_temperature if intent_layer else "",
        )
        if not issues:
            break
        rewrites = attempt + 1
        print(f"[linkedin-tle] kapu elutasitotta ({attempt + 1}. kor): {', '.join(issues)}")

    if not comment:
        return {"error": "A kompozíciós lépés üres kommentet adott."}

    # `legacy_intent`, NEM `intent`: a fenti `intent` a Conversation Intent Layer
    # erteke, es ez a sor korabban elarnyekolta (a valasz-osszeallitas ezutan
    # `CONVERSATION_INTENTS['share_experience']`-t keresett -> KeyError MINDEN
    # hivason). A ket fogalom kulon nevet kap, hogy ne csuszhasson ossze ujra.
    legacy_intent, style = _STRATEGY_TO_LEGACY[reasoning["strategy"]]
    strat_label = STRATEGIES[reasoning["strategy"]]["label"]

    return {
        # --- legacy mezok: a dashboard ezeket olvassa, formatum valtozatlan ---
        "topic": reasoning.get("topic", "general"),
        "post_type": reasoning.get("post_type", "general"),
        "engagement_intent": legacy_intent,
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
        # Conversation Intent Layer — a dontes teljes, utolag megmagyarazhato nyoma.
        "conversation_intent": intent,
        "conversation_intent_label": CONVERSATION_INTENTS[intent]["label"],
        "discourse_level": level,
        "expected_responder_role": responder_role,
        "response_mode": response_mode,
        "human_temperature": human_temperature,
        "topic_gravity": reasoning.get("topic_gravity", ""),
        "intent_layer": intent_layer,
        "strategy_scores": strategy_scores,          # sulyozott pontszamok
        "strategy_vetoed": sorted(strategy_vetoed),  # amit a szint kizart
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
        "ai_fingerprint_terms": ai_fingerprint_terms(comment, post_text),
        "rewrites": rewrites,
        "post_overlap": round(overlap_ratio(comment, post_text), 3),
    }
