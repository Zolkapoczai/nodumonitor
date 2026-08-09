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

NYITAS-ROTACIO (2026-08-09, v5)
A 2026-08-01-i Authenticity Layer hat termeszetes nyito-formát AJANLOTT a
compose-promptban, de a determinisztikus kapu csak a TANACSADOI nyitasokat
tiltja (`_STOCK_OPENING_PATTERNS`). A motor sajat whitelistjenek ismetlodese
ellen semmi nem vedett.

Ez a hiba a kommentek KOZOTT keletkezik: ket komment kulon-kulon hibatlan, a
sorozatuk megis felismerheto. Egy kommenten beluli regex tehat ELVILEG sem
lathatja — ezert nem uj kapu a valasz, hanem kodbeli rotacio a BEMENETEN.
LinkedIn-en ez szamit igazan, mert ugyanaz a kozonseg latja a hozzaszolasaidat
egymas utan; a nyitasok egyformasaga ott AZ AI-ujjlenyomat.

  1. `pick_opening` — a kod valaszt EGY formát a nyolcbol, kizarva a legutobbi
     negyet (`_recent_openings`). A valasztas a poszt-szoveg sha256-hasheból
     jon: determinisztikus (tehat teszthető es utolag megmagyarazhato), es
     posztonkent szór.
  2. A kijelolt forma a FELADAT-uzenetbe kerul (§4/2), nem a system-promptba.
  3. `_OPENING_FREE_MODES` — `answer_the_question` es `concrete_suggestion`
     eseten NINCS kijeloles: ott a nyitast maga a valaszforma dontotte el, es ele
     tenni egy tapasztalat-keretezest a v4 MERT viselkedeset rontana el.

Ugyanaz a minta, mint a `strategy_fit` -> `pick_strategy`: az LLM a szenzor, a
kod a biro (§4/16). A modell nem valaszt nyitast.

Kapcsolat a homersekletttel: alacsonyabb temperature eppen a nyitas-valasztast
lapitja el a leginkabb. A rotacio az, ami a lehuzast biztonsagossa teszi, mert a
varianciat nem a mintavetelre bizza — ld. a kovetkezo szakaszt.

Kill switch: `linkedin.opening_variety: 'on' | 'off'`. Kikapcsolva a
compose-prompt BAJTRA a v4-es (`_V4_OPENING_KEYS` a system-prompt katalogusa; a
ket uj forma csak a per-hivas kijelolesen keresztul jut be), tehat a rotacio
ugyanezen a kodon A/B-zheto, git-revert nelkul.

HIVASONKENTI HOMERSEKLET (2026-08-09, v5)
2026-08-09-ig EGYETLEN `linkedin.temperature` hajtotta mindket hivast, holott a
kovetelmenyuk ellentetes: a REASON osztalyoz (enum + pontszam, ott a
STABILITAS a cel), a COMPOSE nyilvanos prozat ir (ott az alacsony homerseklet a
modalis, legaltalanosabb fogalmazas fele huz — vagyis eppen az "LLM-hang" fele,
ami ellen az egesz motor epult). Ezert `stage_temperature`: ket kulon config-
ertek, a `linkedin.temperature`-bol OROKOLVE, tehat egy regi config viselkedese
bitre valtozatlan. A reszletes indoklas — es hogy miert nem 0.0 a REASON — a
`stage_temperature` docstringjeben van.

TELEMETRIA (2026-08-09, v5)
A motor minden dontest visszaad a valaszban, de a valasz a HTTP-korrel eltunik.
A `generate_comment` ezert vekony wrapper a `_generate_comment` korul, ami minden
kimenetet — a HAT korai hiba-visszaterest is — egy soronkenti JSONL-be ir
(`responder/linkedin_telemetry.py`). Alapbol KIKAPCSOLVA; a `config.yaml`
kapcsolja be. A naplozas hibaja sosem veszi el a mar kifizetett hivas eredmenyet.

TOKEN-HATEKONYSAG
A legnagyobb nyeresег nem a promptok rovidítése volt: a korabbi implementacio a
teljes NODU tudasbazist (`storage/nodu_knowledge_base.md`, ~274 KB ≈ 70k token)
beforditotta MINDEN LinkedIn-hivas system-promptjaba. Egy olyan motornak, ami
alapbol nem is emliti a NODU-t, ez tiszta veszteseg — es aktivan rontja a
kimenetet, mert termek-dokumentacio fele huzza a modellt. Kivezetve.
"""
import hashlib
import json
import re
import time
from collections import deque

from google import genai
from google.genai import types

from env_secrets import get_secret

ENGINE_VERSION = "linkedin-tle-v5"

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

# EGYETLEN valaszforma-skala (2026-07-31 osszevonas).
#
# Korabban ketto volt: a `RESPONSE_MODES` (5 ag) es a `CONVERSATION_RESPONSE_
# STRATEGIES` (4 ag) UGYANAZT a dontest kerte a modelltol ket, egymast atfedo
# skalan (direct_answer ~ answer_the_question, experience_connection ~
# share_experience, technical_extension ~ extend_one_insight, analytical_response
# ~ take_a_position; a `concrete_suggestion`-nek nem volt parja). Mindketto
# bekerult a compose-promptba, KODBELI EGYEZTETES NELKUL — tehat ket LLM-valasztas
# mutathatott ellentetes iranyba, es semmi nem oldotta fel. Ez ellentmond a projekt
# sajat elvenek (§4/16: az LLM a szenzor, a kod a biro; a `strategy_fit` ->
# `pick_strategy` minta), ezert egy skala maradt.
#
# MIERT a `response_mode` NEV maradt: a "strategy" szo ebben a modulban MAR jelent
# valamit (a 7 elemu `STRATEGIES`). Egy masodik, mas ertelmu "strategy" pontosan az
# a nevutkozes, ami a v2-ben az `intent` valtozo elarnyekolasat okozta.
#
# MIERT a v4 KULCSNEVEI maradtak: imperativabbak es pontosabbak. A
# `technical_extension` kulonosen felrevezeto volt, mert mesterseg- vagy emberi
# poszton sem "technikai" a kiterjesztes — az `extend_one_insight` altalanosabb es
# egyben az "pontosan EGY lepes" fegyelmet is kimondja.
RESPONSE_MODES: dict[str, str] = {
    "answer_the_question": "Answer the question asked, directly, in the opening "
                           "sentence — before adding any context.",
    "concrete_suggestion": "Give one concrete feature, example or alternative "
                           "first, not a principle.",
    "extend_one_insight": "Extend exactly one insight by its nearest meaningful "
                          "implication, trade-off or common failure mode.",
    "take_a_position": "Take one clear, respectful position on the stated "
                       "argument, and name its limit.",
    "share_experience": "Share one closely related practitioner observation; "
                        "preserve the human focus.",
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
    """Modell-mezo -> ervenyes valaszforma; ismeretlenul kozel marad a munkahoz.

    A default `extend_one_insight`: ez a legkevesbe invaziv valaszforma — egy
    lepes a poszt sajat gondolatan tul, temavaltas es tanacsadoi keretezes nelkul.
    (Az osszevonas elott a ket skala defaultja `technical_extension` es
    `extend_one_insight` volt: ugyanez a dontes, ket neven.)
    """
    key = str(raw or "").strip().lower()
    return key if key in RESPONSE_MODES else "extend_one_insight"


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
5. response_mode — HOW you join this conversation: exactly ONE shape that serves
   that role. This is the only place the response shape is decided.
{chr(10).join(f'   - {k}: {v}' for k, v in RESPONSE_MODES.items())}
   Follow the author's move. When they explicitly ask for suggestions, select
   concrete_suggestion. When they ask a question, select answer_the_question
   unless they specifically ask for feature ideas or alternatives. Do not slip
   into a consultant, architect or solution-designer shape unless the post
   explicitly asks for advice.
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
    let the scores differ. The `missing_perspective` you gave above is an input to
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
    The insight must sit at the `discourse_level` you reported above — on a
    technical post, a deeper technical claim, NOT a business consequence.
20. confidence — 0.0-1.0, your confidence in this reasoning.

Hard rules:
- Do NOT summarise the post anywhere.
- The insight must survive the question "would an experienced professional learn
  something from this?". If not, choose a different one.
- No invented statistics, customer names or personal anecdotes.
- Depth is not abstraction. Going deeper into the author's own subject is worth
  more than moving up a level away from it.
- Stay exactly ONE conceptual step beyond the post: the immediate implication,
  constraint, trade-off or consequence — never a distant framework or a new
  problem the author did not raise.
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

# --- Kep-bemenet (2026-07-31) -----------------------------------------------
# MIERT KELL: a LinkedIn-posztok egy resze tulnyomoreszt KEP (render, fotó,
# diagram, screenshot) — pont az a `portfolio_showcase` / `craftsmanship` /
# `technical_tutorial` halmaz, amelyik a 30+ posztos benchmarkon a legrosszabbul
# teljesitett. A motor eddig csak a szoveget latta, tehat egy render-posztnal
# gyakorlatilag a caption alapjan sorolt be.
#
# A KEP CSAK BESOROLASI KONTEXTUS. Nem azert kapja a modell, hogy a kommentben
# leirja, mit lat — hanem hogy a `conversation_intent`, a `discourse_level` es a
# `topic_gravity` dontes ne a caption talalgatasan alljon. Ket okbol:
#   1. A kep allitasait KODBAN NEM tudjuk ellenorizni (ellentetben a
#      `tool_request_quote`-tal, amit a posztban megkeresunk — §4/18). Egy
#      felrenezett reszlet magabiztosan hamis mondat lenne egy NYILVANOS
#      kommentben.
#   2. A COMPOSE-hivas eleve nem kapja meg a kepet, tehat a "csak kontextus"
#      nagyreszt SZERKEZETILEG all, nem prompt-keresen.
# Egy szivargasi ut marad: a REASON `insight`/`core_thesis` szabad szoveg. Ezt a
# `_VISUAL_REFERENCE_PATTERNS` kapu zarja a kimeneten.
#
# TOKEN: a kliens 384 px-re skaláz, ezert a kep fix 258 token (a Gemini
# kep-tokenizalas szerint mindket oldal <= 384 px eseten 258; efolott 768x768-as
# csempek, csempenkent 258 — egy 1200x900-as screenshot mar ~1032). A
# kep-utasitas es a `image_role` mezo CSAK akkor kerul a hivasba, ha van kep:
# kep nelkul a REASON-hivas bajtra a korabbi.
_IMAGE_ROLES = [
    "primary_content",   # a poszt lenyege maga a kep (render, fotó, portfolio)
    "screenshot",        # kepernyokep: hibauzenet, parameter-tabla, UI
    "diagram",           # abra, folyamat, metszet
    "illustration",      # kapcsolodo, de nem hordozza a tartalmat
    "decorative",        # stock/branding, nincs informacio-tartalma
]

_IMAGE_REASON_BLOCK = f"""

AN IMAGE FROM THE POST IS ATTACHED.
Use it ONLY to classify the post more accurately — above all conversation_intent,
discourse_level and topic_gravity. A post whose substance is a render or a photo
is usually portfolio_showcase or craftsmanship on the technical plane, however
abstract its caption sounds.
Also fill:
- image_role — what the image contributes. Exactly one:
{chr(10).join(f'  - {r}' for r in _IMAGE_ROLES)}
HARD LIMIT: do NOT describe the image, and do NOT put anything you can only see in
the image into core_thesis or insight. Those fields feed the comment, and the
comment must stand on the post's text alone. What you see informs your
CLASSIFICATION, never the wording.""".rstrip()


def reason_prompt_for(image: bool) -> str:
    """A REASON system-prompt; a kep-blokk CSAK kep eseten kerul bele (~60 token)."""
    return _REASON_PROMPT + (_IMAGE_REASON_BLOCK if image else "")


def reason_schema_for(image: bool) -> dict:
    """A REASON sema; az `image_role` CSAK kep eseten kotelezo mezo.

    Miert nem mindig benne: ha kotelezo lenne kep nelkul is, a modellnek olyan
    mezot kellene kitoltenie, amit a prompt nem magyaraz el (ez a
    test_linkedin_intent.py A13.1 invariansa: minden kotelezo mezot ki kell
    mondani a promptban). Igy a kep nelkuli ut valtozatlan.
    """
    if not image:
        return _REASON_SCHEMA
    schema = {
        "type": _REASON_SCHEMA["type"],
        "properties": {**_REASON_SCHEMA["properties"],
                       "image_role": {"type": "STRING", "enum": _IMAGE_ROLES}},
        "required": [*_REASON_SCHEMA["required"], "image_role"],
    }
    return schema

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

# --- Stage 6.5: nyitas-rotacio (2026-08-09, v5) ------------------------------
# A PROBLEMA, amit ez old meg — es amit egyik meglevo kapu sem tud elkapni:
# a 2026-08-01-i whitelist hat nyito-format ajanlott a COMPOSE-promptban, a
# `_STOCK_OPENING_PATTERNS` viszont csak a TANACSADOI nyitasokat tiltja. A motor
# sajat whitelistjenek ismetlodese ellen semmi nem vedett. Ket kommentet kulon
# vizsgalva mindketto atmegy; a hiba a kommentek KOZOTT keletkezik, egy
# kommenten beluli regex tehat elvileg sem lathatja. LinkedIn-en viszont
# ugyanaz a kozonseg latja a hozzaszolasaidat sorozatban — ott az azonos nyitas
# sorozata AZ AI-ujjlenyomat.
#
# MIERT MOST: a `linkedin.temperature` ma 'default' (szerver-oldali ertek), es a
# 2026-08-01-i doksi 0.3-at javasol a hullamzas ellen. Alacsonyabb temperature
# eppen a nyitas-valasztast lapositja el a leginkabb. Ez a rotacio az, ami a
# 0.3-ra allast biztonsagossa teszi: a varianciat nem a mintavetelre bizzuk,
# hanem kodban allitjuk elo.
#
# A MEGOLDAS ILLESZKEDESE: "az LLM a szenzor, a kod a biro" (§4/16) — ugyanaz a
# minta, mint a `strategy_fit` -> `pick_strategy`-nal. A modell nem valaszt
# nyitast; a kod valaszt egyet, es azt adja at.
OPENING_SHAPES: dict[str, dict[str, str]] = {
    "own_practice": {
        "example": '"I\'ve found..."',
        "move": "open with what your own practice taught you",
    },
    "encountered": {
        "example": '"I\'ve run into..."',
        "move": "open with a situation you have met before",
    },
    "stood_out": {
        "example": '"One thing that stood out..."',
        "move": "open with the specific detail in the post that caught you",
    },
    "strikes": {
        "example": '"What strikes me..."',
        "move": "open with what you find notable in the author’s point",
    },
    "learned": {
        "example": '"We\'ve learned..."',
        "move": "open with a lesson shared practice has produced",
    },
    "pattern": {
        "example": '"One pattern I\'ve noticed..."',
        "move": "open with a recurring pattern you have observed",
    },
    # A ket uj forma NEM diszites. Mindketto olyan retorikai mozdulat, ami a hat
    # tapasztalat-keretezesbol hianyzott:
    #   straight  — a `_compose_user_msg` MAR MA is azt kéri, hogy "Begin with the
    #               contribution itself"; a hat keretezes viszont mind elé tesz egy
    #               fel mondatot. Ez a forma feloldja ezt a belso ellentmondast.
    #   condition — a gyakorlo ember jellegzetes nyitasa: nem magaval kezdi, hanem
    #               a feltetellel, ami mellett a dolog szamitani kezd.
    # Egyik sem utkozik a `_STOCK_OPENING_PATTERNS` egyetlen mintajaval sem.
    "straight": {
        "example": "no framing at all — begin with the claim itself",
        "move": "state the substantive claim directly, with no experience framing",
    },
    "condition": {
        "example": '"Once the model leaves the design team..."',
        "move": "open with the condition under which the point starts to matter",
    },
}

# Hany LEGUTOBBI forma van kizarva a valasztasbol. 4 a 8-bol: eleg szeles ahhoz,
# hogy ne legyen eszrevehetó ismetlodés, es marad 4 jelolt, tehat a valasztas nem
# szűkul egyetlen kényszerpályára.
_OPENING_RING_SIZE = 4

# MIERT MEMORIABAN: ez varianciа-allapot, nem adat. Az elvesztese egy
# ujraindulaskor teljesen artalmatlan (legfeljebb egy komment nyitasa ismetlodhet),
# ezert nem indokol sem DB-tablat, sem fajlt — a 03-composer-spec §Hatokor
# "nincs perzisztencia/history-tabla" kikotese igy serthetetlen marad.
# Szalbiztonsag: a `deque.append` maxlen mellett atomi a GIL alatt. Tobb worker-
# processz eseten processzenkent kulon gyűrű van, ami csak a szorast csokkenti
# kisse — helytelen viselkedest nem okoz.
_recent_openings: deque = deque(maxlen=_OPENING_RING_SIZE)

# Az a ket valaszforma, aminel a NYITAST MAR A FORMA eldontotte. A
# `answer_the_question` kifejezetten azt irja elo, hogy a valasz alljon a nyito
# mondatban, a `concrete_suggestion` pedig azt, hogy a konkretum jojjon eloszor —
# ele tenni egy tapasztalat-keretezest pontosan azt a viselkedest rontana el,
# amit a v4 merese jonak talalt. Ilyenkor a kod NEM jelol ki nyitast.
_OPENING_FREE_MODES = {"answer_the_question", "concrete_suggestion"}

# A v4-es prompt HAT formát sorolt fel. A ket uj forma szandekosan NEM kerul be a
# system-prompt katalogusaba: igy `opening_variety: 'off'` mellett a COMPOSE-prompt
# BAJTRA a v4-es marad, tehat a rotacio tiszta A/B-kent merheto. A ket uj forma a
# PER-HIVAS kijelolesen keresztul jut be, a sajat `move` leirasaval egyutt — ahhoz
# a modellnek nem kell katalogus-bejegyzés.
_V4_OPENING_KEYS = ("own_practice", "encountered", "stood_out", "strikes",
                    "learned", "pattern")


def opening_variety_enabled(config: dict) -> bool:
    """`linkedin.opening_variety`: on (default) | off. YAML-boolean kezelve (§4/17).

    Kikapcsolva a compose-prompt BAJTRA a 2026-08-01-i (v4) valtozat, tehat a
    rotacio A/B-zheto git-revert nelkul — ugyanaz az elv, mint az `intent_layer`-nel.
    """
    raw = (config.get("linkedin", {}) or {}).get("opening_variety", "on")
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() not in ("off", "false", "0", "no", "none")


def pick_opening(post_text: str, response_mode: str = "extend_one_insight",
                 recent=None) -> str:
    """Egy nyitó-forma kulcsa, vagy "" ha nem jelolunk ki.

    HAROM KOVETELMENY egyszerre, ezert nem eleg sem a puszta round-robin, sem a
    veletlen:
      1. NE ISMETLODJON — a legutobbi `_OPENING_RING_SIZE` forma ki van zarva.
      2. REPRODUKALHATO — ugyanaz a poszt ugyanazt a formát kapja, kulonben a
         dontes nem teszthetó es nem magyarazhato meg utolag (ugyanaz az elv,
         mint a `pick_strategy` determinisztikus argmaxánál).
      3. SZORODJON — kulonbozo posztok kulonbozo formára essenek.
    A poszt-szoveg hash-e mindharmat teljesiti: determinisztikus es egyenletes.

    MIERT sha256 ES NEM a beepitett `hash()`: a CPython a string-hash-t
    processzenkent randomizalja (PYTHONHASHSEED), tehat a `hash()` ugyanarra a
    posztra ujraindulas utan MAS erteket adna — a 2. kovetelmeny bukna, es a
    teszt hol atmenne, hol nem.
    """
    if _response_mode_key(response_mode) in _OPENING_FREE_MODES:
        return ""
    used = set(_recent_openings if recent is None else recent)
    # A `or sorted(...)` vedoszabaly: ha a gyűrű valaha akkorara nőne, hogy minden
    # formát kizar, a valasztas ne uruljon ki.
    eligible = sorted(k for k in OPENING_SHAPES if k not in used) or sorted(OPENING_SHAPES)
    digest = hashlib.sha256((post_text or "").strip().lower().encode("utf-8")).digest()
    return eligible[int.from_bytes(digest[:8], "big") % len(eligible)]


def remember_opening(key: str) -> None:
    """A kivalasztott formát a gyűrűbe teszi — CSAK sikeres komment utan hivjuk.

    Ha a kapu elutasitotta es a hivas hibaval ér veget, a forma nem ég el: egy
    meg nem jelent komment nem okoz ismetlodest, tehat nem is kell kizarni.
    """
    if key:
        _recent_openings.append(key)


# --- Stage 6-7: COMPOSE -----------------------------------------------------
_COMPOSE_PROMPT = f"""
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

YOU ARE A PEER, NOT A CONSULTANT.
Never write as any of these: a consultant, a standards committee,
a solution architect, a whitepaper, a conference speaker.
Join the discussion; do not try to solve it. Prefer observations over
recommendations, concrete language over abstract nouns, experience over
explanation.

OPENING. The gate rejects stock consultant openings, so open the way a
practitioner actually would. Use one of these shapes, in the post's own language:
{chr(10).join(f'  {OPENING_SHAPES[k]["example"]}' for k in _V4_OPENING_KEYS)}
Never open with: "We often see", "We frequently observe", "One approach",
"Best practice", "Organizations should", "Implementation requires",
"Establishing...", "Ensuring...", "It is critical to".

ENDING. Do not end with advice, a recommendation or a solution. End on a concrete
observation that leaves room for the other person to answer.

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

AFTER writing the comment, score it on five axes, 0-2 each. Score the text you
just wrote, honestly — a low score triggers one targeted rewrite, so an inflated
score only produces a worse comment.
- voice_professional: 2 = reads as a practitioner; 0 = reads as a consultant.
- conversation_fit: 2 = answers the conversation the author started; 0 = answers
  a different one.
- one_step_insight: 2 = exactly one idea beyond the post; 0 = no new idea, or a
  whole theory.
- no_implementation_drift: 2 = NO drift, you stayed at the author's level;
  0 = drifted into implementation, governance, architecture or transformation.
  Higher is always better on every axis, including this one.
- natural_language: 2 = plain professional speech; 0 = enterprise vocabulary the
  author never used.
""".strip()

# --- Authenticity rubrika (2026-08-01) --------------------------------------
# A munkaparancs "Authenticity Score"-ja MEGFORDITVA: a modell nem dont es nem ir
# ujra sajat magatol — csak PONTOZ (szenzor), a kuszobot es az ujrairast a kod
# vegzi (biro). Ez a projekt sajat elve (§4/16), es azert kell igy, mert:
#   1. a COMPOSE strukturalt kimenetet ad `thinking_budget=0`-val, tehat nincs hol
#      egy belso "self-check" kort futtatni — a modell egyszeruen kiirja a JSON-t;
#   2. az LLM-nek feltett "eleg jo ez?" kerdesre a valasz gyakorlatilag mindig igen,
#      ezert az onertekelesre alapozott ujrairas nem megbizhato kapu.
# Amit a rubrika IGY is ad: a modell a vegleges szoveget ot MEGNEVEZETT tengely
# szerint ujraolvassa a lezaras elott, es kapunk egy szamot, ami Zoltan kezi
# benchmark-pontjaival korrelaltathato. A korrelacio maga a proba: ha nincs, a
# rubrika torolheto (10 kimeneti token).
#
# MINDEN tengelyen a NAGYOBB a jobb — a `no_implementation_drift` ezert van
# tagadva megfogalmazva (a munkaparancs "Implementation Drift"-je forditott
# iranyu lett volna, es az osszeg ertelmetlen).
_AUTHENTICITY_DIMENSIONS = [
    "voice_professional", "conversation_fit", "one_step_insight",
    "no_implementation_drift", "natural_language",
]
AUTHENTICITY_MAX = 2 * len(_AUTHENTICITY_DIMENSIONS)      # 10

_COMPOSE_SCHEMA = {
    "type": "OBJECT",
    # A `comment` ELOL all: a modell a mar megirt szoveget pontozza, nem a
    # semmit. A dict-sorrend szandekos.
    "properties": {
        "comment": {"type": "STRING"},
        **{d: {"type": "INTEGER"} for d in _AUTHENTICITY_DIMENSIONS},
    },
    "required": ["comment", *_AUTHENTICITY_DIMENSIONS],
}


def authenticity_score(out: dict) -> tuple[int | None, dict]:
    """(osszeg vagy None, tengelyenkenti pontszamok) a COMPOSE valaszabol.

    KET KULONBOZO HIBA, ket kulonbozo valasz — es ez MERT dontes:

      RESZBEN hianyzo pontszam -> a hianyzo tengely 0. A modell nem tudja
      megkerulni a kaput azzal, hogy a rossz tengelyt kihagyja.

      TELJESEN hianyzo pontszam -> None, es a kapu KIHAGYJA a rubrikat. Ez nem
      minosegi jel, hanem sema-/vezetekezesi hiba: ha 0-nak vennenk, MINDEN hivas
      a kuszob ala esne, tehat mindegyik ujrairast kapna — a masodik hivas
      ugyanugy nem adna pontszamot, tehat a plusz kor semmit nem javitana, csak
      csendben megduplazna a compose-koltseget. Ezt a hibat a v2/v4 tesztek
      stubjai fedtek fel (azok nem pontoznak), es eles uzemben ugyanigy jelentkezne
      egy sema-valtozas utan.
    """
    per = {}
    present = 0
    for d in _AUTHENTICITY_DIMENSIONS:
        raw = (out or {}).get(d)
        if isinstance(raw, (int, float)):
            present += 1
            per[d] = max(0, min(2, int(raw)))
        else:
            per[d] = 0
    if not present:
        return None, per
    return sum(per.values()), per


def authenticity_min_score(config: dict) -> int:
    """`linkedin.authenticity_min_score` — ez alatt egy celzott ujrairas. 0 = ki."""
    raw = (config.get("linkedin", {}) or {}).get("authenticity_min_score", 8)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 8
    return value if 0 <= value <= AUTHENTICITY_MAX else 8

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
    # 2026-08-01: a benchmark tovabbi tanacsadoi nyitasai. Mind mondat-eleji
    # egyezes, tehat a kifejezes kesobbi, tartalmilag indokolt hasznalata nem serul
    # (pl. "...ami best practice lett" a komment kozepen atmegy).
    (r"^\s*we (?:frequently|commonly|typically|usually) (?:see|observe|find)\b",
     "ismetlodo nyitas (We frequently observe)"),
    (r"^\s*one approach\b", "tanacsadoi nyitas (One approach)"),
    (r"^\s*(?:the )?best practice\b", "tanacsadoi nyitas (Best practice)"),
    (r"^\s*organi[sz]ations? (?:should|need|must)\b", "tanacsadoi nyitas (Organizations should)"),
    (r"^\s*implementation requires\b", "tanacsadoi nyitas (Implementation requires)"),
    (r"^\s*establishing\b", "tanacsadoi nyitas (Establishing)"),
    (r"^\s*ensuring\b", "tanacsadoi nyitas (Ensuring)"),
    (r"^\s*it (?:is|'s) critical to\b", "tanacsadoi nyitas (It is critical to)"),
    (r"^\s*a (?:legjobb|bevalt) gyakorlat\b", "tanacsadoi nyitas (HU: best practice)"),
    (r"^\s*a (?:cegeknek|szervezeteknek) (?:erdemes|kell)\b",
     "tanacsadoi nyitas (HU: organizations should)"),
]

# Gondolatjel ANGOL kommentben: a LinkedIn-en ma az egyik legismertebb AI-jel.
# CSAK angolra mer, mert a magyar tipografiaban a gondolatjel legitim irasjel —
# ugyanaz az elv, amiert az "architecture" sem kerult kemeny tiltolistara (egy
# AEC-eszkozben az maga az iparag).
_EM_DASH_PATTERN = re.compile(r"[—]")

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

# --- Stage 9c: kepre hivatkozas (2026-07-31) --------------------------------
# A kep KIZAROLAG besorolasi kontextus (ld. `_IMAGE_REASON_BLOCK`). A COMPOSE nem
# is kapja meg, de a REASON `insight`-jaba beszivaroghat egy csak-kepen-latszo
# reszlet, es onnan a kommentbe. Ezt a kimeneten merjuk: ha a komment a KEPRE
# hivatkozik, az sertes — mert az az allitas ellenorizhetetlen.
# Csak akkor mer, ha tenylegesen volt kep (`image_attached`).
_VISUAL_REFERENCE_PATTERNS: list[tuple[str, str]] = [
    (r"\bin (?:the|your) (?:image|photo|picture|render|screenshot|drawing)\b", "kep-hivatkozas"),
    (r"\b(?:the|your) (?:image|photo|picture|render|screenshot) (?:shows?|suggests?|indicates?)\b", "kep-hivatkozas"),
    (r"\bas (?:seen|shown|visible) in\b", "kep-hivatkozas"),
    (r"\bfrom (?:the|your) (?:image|photo|render|screenshot)\b", "kep-hivatkozas"),
    (r"\bpictured\b|\bin shot\b", "kep-hivatkozas"),
    (r"\ba (?:kepen|képen|fotón|foton|renderen|abran|ábrán|kepernyokepen|képernyőképen)\b", "kep-hivatkozas (HU)"),
    (r"\b(?:latszik|látszik|lathato|látható) a (?:kepen|képen|fotón|foton)\b", "kep-hivatkozas (HU)"),
    (r"\ba (?:megosztott|feltoltott|feltöltött) (?:kep|kép|fotó|foto)\b", "kep-hivatkozas (HU)"),
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
                  human_temperature: str = "",
                  image_attached: bool = False,
                  auth_score: int | None = None,
                  auth_min: int = 0) -> list[str]:
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

    `image_attached` (2026-07-31): ha a REASON kepet is kapott, a kommentben a
    KEPRE hivatkozas sertes — az ilyen allitast kodban nem tudjuk ellenorizni.
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

    # Kep-hivatkozas: csak akkor mer, ha tenylegesen volt kep. A kep besorolasi
    # kontextus — amit csak azon lattunk, az nem allithato egy nyilvanos
    # kommentben, mert ellenorizhetetlen.
    if image_attached:
        for pattern, label in _VISUAL_REFERENCE_PATTERNS:
            if re.search(pattern, low, re.IGNORECASE | re.MULTILINE):
                issues.append(f"a komment a kepre hivatkozik ({label})")
                break

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

    # Authenticity-rubrika: a modell PONTOZ, a kuszob a KODBAN van. auth_min=0
    # kikapcsolja, es a regi (parameter nelkuli) hivasok igy valtozatlanok.
    if auth_min and auth_score is not None and auth_score < auth_min:
        issues.append(f"authenticity-pontszam {auth_score}/{AUTHENTICITY_MAX} "
                      f"(min {auth_min})")

    # Gondolatjel csak ANGOL kommentben (ld. `_EM_DASH_PATTERN`).
    if looks_english(post_text) and _EM_DASH_PATTERN.search(text):
        issues.append("gondolatjel angol kommentben (AI-jel)")

    if "!" in text:
        issues.append("felkialtojel")
    if re.search(r"#\w+", text):
        issues.append("hashtag")
    if re.search(r"[\U0001F300-\U0001FAFF☀-➿]", text):
        issues.append("emoji")

    return issues


# --- Orchesztracio ----------------------------------------------------------

DEFAULT_MODEL = "gemini-2.5-flash"


def linkedin_model(config: dict) -> str:
    """A LinkedIn-komment motor modellje: `linkedin.model`, kulonben orokli
    a `scoring.gemini_model`-t.

    MIERT KELL SZETVALASZTANI: a `scoring.gemini_model` EGYETLEN ertek, amit HAT
    hivasi hely oszt — a Pain Classifier (napi tobb szaz hivas), a negy
    draft_generator-ut es ez a motor. A ket veglet ellentetes koveteleseu:

      classifier      — nagy volumen, strukturalt JSON a kimenet -> a KOLTSEG szamit
      LinkedIn compose — par kezi hivas naponta, nyilvanos szoveg -> a MINOSEG szamit

    Egy modellvalasztas nem szolgalhatja mindkettot: a compose-utat felvinni egy
    dragabb modellre nehany centet jelent, ugyanezt a classifierre ravinni a
    3.6 Flash arazasan (input 5x, output 3x a 2.5 Flash-hez kepest) tobbszorozi a
    havi szamlat egy olyan uton, ahol a kimenet nem is proza.

    Ures/hianyzo ertek eseten a viselkedes VALTOZATLAN — orokli a globalis modellt,
    tehat a szetvalasztas onmagaban nem valtoztat semmit, csak lehetove teszi a
    kulon hangolast.
    """
    raw = (config.get("linkedin", {}) or {}).get("model")
    own = str(raw).strip() if raw is not None else ""
    if own and own.lower() not in ("inherit", "none", "default"):
        return own
    return (config.get("scoring", {}) or {}).get("gemini_model") or DEFAULT_MODEL


def _client(config: dict) -> tuple[genai.Client | None, str, str | None]:
    sc = config.get("scoring", {})
    api_key = get_secret("GEMINI_API_KEY", sc.get("gemini_api_key"))
    if not sc.get("gemini_enabled", False) or not api_key:
        return None, "", "Gemini API nincs beállítva (GEMINI_API_KEY a .env-ben)."
    return genai.Client(api_key=api_key), linkedin_model(config), None


def temperature(config: dict) -> float | None:
    """`linkedin.temperature` — a hullamzas elleni legkozvetlenebb kar.

    2026-08-01-ig ez a kodbazis SOHA nem allitotta a temperature-t, tehat mindket
    hivas az API-defaulton futott (gemini-2.5-flash: 1.0). A benchmark ingadozasa
    reszben egyszeruen ez. 0.3 a default: eleg alacsony a szoveg-varianciahoz, es
    a REASON osztalyozasnak is jot tesz (konzisztensebb intent/szint dontes).

    `null`/'default' -> nem allitjuk be (visszateres az API-defaultra), igy a
    korabbi viselkedes egy config-sorral reprodukalhato.
    """
    raw = (config.get("linkedin", {}) or {}).get("temperature", 0.3)
    if raw is None or str(raw).strip().lower() in ("default", "none", ""):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0.3
    return value if 0.0 <= value <= 2.0 else 0.3


_TEMPERATURE_STAGES = ("reason", "compose")


def stage_temperature(config: dict, stage: str) -> float | None:
    """`linkedin.{stage}_temperature`, oroklodve a `linkedin.temperature`-bol.

    MIERT KELL SZETVALASZTANI — a ket hivas kovetelmenye ELLENTETES, es
    2026-08-09-ig EGYETLEN ertek hajtotta mindkettot:

      REASON  — a kimenet enum + 0-10 pontszam; nincs benne megorzendo
                fogalmazas. Az EGESZ architektura ez alatt van (intent -> bias ->
                veto -> strategia): ha az osztalyozas ingadozik, mas strategia
                nyer, tehat mas komment szuletik. A v2 elfogadasi kriteriuma
                ABSZOLUT ("Craftsmanship posts no longer drift toward business
                value"), nem statisztikai — az stabil besorolast felte­telez.
                -> ALACSONY a helyes.

      COMPOSE — a kimenet NYILVANOS proza. Alacsony homerseklet = modalis
                tokenvalasztas = a leggyakoribb, legaltalanosabb fogalmazas —
                pontosan az az "LLM-hang", ami ellen a v1 ota minden reteg epult.
                Ezt a config sajat kommentje mar 2026-08-01-en kimondta ("lapos,
                altalanos felismeréseket adhat, ami maga is pontlevonas").
                Ráadasul itt van PRECIZEBB kontroll is: a determinisztikus kapu
                fogja a konkret serteseket es egy celzott ujrairast ker — a
                temperature ehhez kepest tompa eszkoz.
                -> NEM kell levinni.

    MIERT NEM 0.0 A REASON: a `strategy_fit` het strategiat pontoz 0-10-en, es a
    `pick_strategy` holtversenyben a DEKLARACIOS SORRENDET koveti — ott pedig a
    `constructive_challenge` all elol. Egy ellaposodo pontszam-eloszlas tehat nem
    "semleges" lenne: csendben a nyilvanos kritikat hozna fel gyakori nyertesse,
    olyan posztokon is (portfolio_showcase, announcement), ahol az intent-bias
    kifejezetten lehuzza, mert az a legrosszabb valasz.

    Hianyzo ertek / 'inherit' -> a `linkedin.temperature`, tehat egy REGI config
    viselkedese bitre valtozatlan. 'default' -> nem allitjuk be (API-default).
    Ertelmezhetetlen ertek -> szinten orokles: egy elgepelt szam nem valtoztathat
    csendben viselkedest.
    """
    if stage not in _TEMPERATURE_STAGES:
        raise ValueError(f"ismeretlen stage: {stage!r} (varhato: {_TEMPERATURE_STAGES})")

    li = config.get("linkedin", {}) or {}
    key = f"{stage}_temperature"
    if key not in li or li[key] is None:
        return temperature(config)

    text = str(li[key]).strip().lower()
    if text in ("inherit", ""):
        return temperature(config)
    if text in ("default", "none"):
        return None
    try:
        value = float(li[key])
    except (TypeError, ValueError):
        return temperature(config)
    return value if 0.0 <= value <= 2.0 else temperature(config)


def _call_json(client, model: str, system: str, user: str, schema: dict,
               max_tokens: int, image: tuple[bytes, str] | None = None,
               temp: float | None = None) -> dict | None:
    """Strukturalt hivas. thinking_budget=0 — a HANDOFF §4/1 lecke: a
    gemini-2.5-flash kulonben a max_output_tokens keretbol "gondolkodik", es
    csonka JSON-t ad.

    `image` = (bytes, mime) vagy None. CSAK a REASON-hivas adja at (a COMPOSE
    nem — ld. `generate_comment`): a kep a besorolast pontositja, a szovegezeshez
    mar a reasoning-objektum kell. Igy a kep tokenjeit egyszer fizetjuk, es az
    ujrairo kor sem fizeti ujra.
    """
    contents = user if image is None else [
        types.Part.from_bytes(data=image[0], mime_type=image[1]),
        user,
    ]
    cfg = dict(
        system_instruction=system,
        response_mime_type="application/json",
        response_schema=schema,
        max_output_tokens=max_tokens,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )
    # Csak akkor adjuk at, ha van ertek: `temperature=None`-t nem kuldunk, hogy a
    # 'default' beallitas tenylegesen az API-defaultot jelentse.
    if temp is not None:
        cfg["temperature"] = temp
    resp = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(**cfg),
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


def image_input_enabled(config: dict) -> bool:
    """`linkedin.image_input`: on (default) | off. YAML-boolean is kezelve (§4/17)."""
    raw = (config.get("linkedin", {}) or {}).get("image_input", "on")
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() not in ("off", "false", "0", "no", "none")


def image_max_px(config: dict) -> int:
    """`linkedin.image_max_px` — a kliens ENNYIRE skaláz le (leghosszabb oldal).

    384 a default, mert a Gemini kep-tokenizalasban mindket oldal <= 384 px
    eseten a kep FIX 258 token; efolott 768x768-as csempek jonnek, csempenkent
    258 (egy 1200x900-as screenshot igy mar ~1032). A 384 eleg ahhoz, hogy a
    modell render / fotó / diagram / screenshot kozott dontsen — screenshotrol
    SZOVEGET olvasni viszont nem eleg. Ha az kell, 768 a kovetkezo ertelmes ertek,
    ~4x tokenert.
    """
    raw = (config.get("linkedin", {}) or {}).get("image_max_px", 384)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 384
    return value if 128 <= value <= 2048 else 384


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
                      intent_layer: bool = True, opening: str = "") -> str:
    """A compose-hivas feladat-uzenete.

    A kritikus megkotesek (nyelv, hossz, tilalmak) a system-promptban IS benne
    vannak, de itt megismetelodnek: a HANDOFF §4/2 elesben megtanult lecke
    szerint a modell a csak listaelemkent szereplo szabalyt nem tartja be.

    `intent_layer=False` eseten az intent/szint/gravity/role sorok kimaradnak —
    igy a kikapcsolt layer a v1-es promptot allitja elo.

    `opening` (v5): a kod altal kijelolt nyito-forma kulcsa, vagy "". Ugyanez a
    §4/2 lecke miatt kerul a FELADAT-uzenetbe es nem a system-promptba: a
    per-hivas valtozo megkotes ott hat, ahol a modell a feladatot olvassa.
    Uresen a mondat BAJTRA a v4-es.
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
        # A tiltas valtozatlan; csak a ZARO tagmondat fugg attol, kijelolt-e a kod
        # formát. Kijeloles nelkul a mondat bajtra a v4-es — ez teszi a rotaciot
        # tiszta A/B-ve (`linkedin.opening_variety`).
        opening_rule = (
            "Begin with the contribution itself, not a stock consultant opening "
            "such as 'We often see', 'One consideration', 'In practice' or 'One "
            "recurring challenge'. "
        )
        if opening in OPENING_SHAPES:
            parts.append(
                opening_rule
                + f"OPENING SHAPE for this comment: {OPENING_SHAPES[opening]['move']}. "
                "Use this shape and no other — it overrides the list of shapes in "
                "your instructions. Render it in the post's own language the way a "
                "practitioner would actually say it, never as a translated formula."
            )
        else:
            parts.append(opening_rule + "Vary the rhetorical shape naturally.")
        parts.append(
            "Do not end with a generic payoff such as productivity, efficiency, "
            "project delivery or organisational scale. End on the concrete "
            "engineering, human or practical point instead."
        )
        parts.append(
            "Stay exactly ONE conceptual step beyond the post: make only the "
            "nearest meaningful implication. Join the conversation; do not switch "
            "into consultant, architect or solution-designer mode unless the post "
            "explicitly asks for advice. Prefer practitioner language over "
            "whitepaper language. End with one memorable insight, not a "
            "recommendation."
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
                     author_role: str = "",
                     image_bytes: bytes | None = None,
                     image_mime: str = "image/jpeg") -> dict:
    """A motor NYILVANOS belepesi pontja: `_generate_comment` + telemetria.

    Miert wrapper es nem a nagy fuggveny vegen egy sor: a `_generate_comment` HAT
    ponton ter vissza korán (ures poszt, nincs API-kulcs, ket API-kivetel,
    ervenytelen reasoning, ures komment). Pont ezek a HIBAS utak azok, amiket
    meg akarunk szamolni — egy zaro sor mindet kihagyna. Igy egyetlen helyen
    fogjuk MINDEN kimenetet, es a `_generate_comment` valtozatlan marad.

    A telemetria alapbol KI van kapcsolva (kod-default); a `config.yaml` kapcsolja
    be. Hibat sosem dob — ld. `linkedin_telemetry.record`.
    """
    from responder.linkedin_telemetry import record

    started = time.monotonic()
    result = _generate_comment(config, post_text, author_name, author_role,
                               image_bytes=image_bytes, image_mime=image_mime)
    record(config, result, post_text,
           elapsed_ms=int((time.monotonic() - started) * 1000))
    return result


def _generate_comment(config: dict, post_text: str, author_name: str = "",
                      author_role: str = "",
                      image_bytes: bytes | None = None,
                      image_mime: str = "image/jpeg") -> dict:
    """
    Thought Leadership Engine — teljes pipeline egy LinkedIn-poszthoz.

    Visszaad: a dashboard altal olvasott 8 legacy mezo + az uj reasoning-mezok.
    Hiba eseten `{"error": "..."}` — a hivo (ui/app.py) ezt mar kezeli.

    Hivas-koltseg: tipikusan 2 LLM-hivas (reason + compose), legfeljebb 3
    (egy celzott ujrairas, ha a deterministikus kapu sertest talalt). A kep NEM
    novel hivas-szamot: a REASON-hivas kapja meg, a COMPOSE es az ujrairas nem.

    `image_bytes`: a poszt kepe (a kliens mar 384 px-re skálázta), vagy None.
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

    # A layer-dontes a REASON-hivas ELE kerul, mert eldonti, kell-e a kep:
    # kikapcsolt layer eseten az intent/szint a `_LAYER_OFF` par, tehat a kep
    # osztalyozasi eredmenye eldobodna — elkuldeni tiszta token-veszteseg lenne.
    intent_layer = _intent_layer_enabled(config)
    # A ket hivas KULON homersekletet kap (2026-08-09): a REASON osztalyoz, a
    # COMPOSE nyilvanos prozat ir — ld. `stage_temperature`. A `temp` a bazis-ertek,
    # ami a valaszban is marad, hogy a korabbi szerzodes ne toljon el.
    temp = temperature(config)
    reason_temp = stage_temperature(config, "reason")
    compose_temp = stage_temperature(config, "compose")
    auth_min = authenticity_min_score(config)
    use_image = bool(image_bytes) and intent_layer and image_input_enabled(config)
    if image_bytes and not use_image:
        why = ("linkedin.image_input=off" if not image_input_enabled(config)
               else "az intent layer ki van kapcsolva, a kep besorolasa elveszne")
        print(f"[linkedin-tle] a kep NEM megy el ({why})")

    # --- Stage 1-5: reasoning (a kep CSAK ide) ---
    try:
        reasoning = _call_json(
            client, model, reason_prompt_for(use_image),
            f"{author_line}POST:\n{post_text[:2000]}",
            # 900 -> 1200: a semaba a Conversation Intent es Conversation Response
            # Layer mezojei kerultek (intent, response strategy, szint, gravity,
            # szerep, valaszforma, human temperature). Az enumok nehany token, a
            # topic_gravity 2-5 szo — de a csonka-JSON hiba (§4/1) itt a TELJES
            # valaszt viszi, ezert a keret inkabb bo. A fel nem hasznalt keret nem
            # kerul semmibe: a szamlazas a tenyleges output-tokenre megy.
            reason_schema_for(use_image), max_tokens=1200,
            image=(image_bytes, image_mime) if use_image else None,
            temp=reason_temp,
        )
    except Exception as e:
        print(f"[linkedin-tle] reasoning HIBA: {e}")
        return {"error": f"Gemini API hiba (reasoning): {e}"}
    if not reasoning or not isinstance(reasoning.get("strategy_fit"), dict):
        print(f"[linkedin-tle] Ervenytelen reasoning: {reasoning}")
        return {"error": "A reasoning-lépés érvénytelen választ adott."}

    image_role = ""
    if use_image:
        raw_role = str(reasoning.get("image_role") or "").strip().lower()
        image_role = raw_role if raw_role in _IMAGE_ROLES else "illustration"

    # --- Stage 3.5: Conversation Intent Layer ---
    # A modell OSZTALYOZ (szenzor), a sulyozast es a vetot a kod vegzi (biro) —
    # §4/16. Kikapcsolt layer eseten a `_LAYER_OFF` par az egysegelem, tehat a
    # dontes bitre a v1-es.
    if intent_layer:
        intent = _intent_key(reasoning.get("conversation_intent"))
        level = _level_key(reasoning.get("discourse_level"))
        responder_role = _responder_role_key(reasoning.get("expected_responder_role"))
        response_mode = _response_mode_key(reasoning.get("response_mode"))
        human_temperature = _human_temperature_key(reasoning.get("human_temperature"))
    else:
        intent, level = _LAYER_OFF
        responder_role = "peer_practitioner"
        response_mode = "extend_one_insight"
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
          + (f" | kep={image_role}" if use_image else "")
          + (f" | vetozott={sorted(strategy_vetoed)}" if strategy_vetoed else "")
          + ("" if intent_layer else " | INTENT LAYER KIKAPCSOLVA"))

    # Markaemlites: a POSZT tulajdonsaga, nem globalis beallitas (ld.
    # brand_mention_allowed). Az idezetet ellenorizzuk a posztban.
    brand_allowed, brand_reason = brand_mention_allowed(config, reasoning, post_text)
    print(f"[linkedin-tle] strategia={reasoning['strategy']} | markaemlites="
          f"{'ENGEDVE' if brand_allowed else 'tiltva'} ({brand_reason})")

    # --- Stage 6.5: nyitas-forma (a kod valaszt, nem a modell) ---
    # A kikapcsolt intent layer itt is v4-es viselkedest ad: a nyitas-sor a
    # layer-blokkban van, tehat kijeloles nelkul a prompt valtozatlan.
    opening = ""
    if intent_layer and opening_variety_enabled(config):
        opening = pick_opening(post_text, response_mode)
        print(f"[linkedin-tle] nyitas={opening or '(a valaszforma dontötte el)'}"
              f" | legutobbiak={list(_recent_openings)}")

    # --- Stage 6-7: compose, + Stage 9: kapu, legfeljebb egy ujrairassal ---
    comment, issues, rewrites = "", ["nem futott le"], 0
    auth_total, auth_per = None, {d: 0 for d in _AUTHENTICITY_DIMENSIONS}
    for attempt in range(2):
        # A nyitas-forma az ujrairo korben is UGYANAZ: az ujrairas a kapu konkret
        # serteseit javitja, nem a retorikai formát valtoztatja. Uj forma itt
        # ujabb valtozot vinne egy amugy is celzott javitasba.
        user_msg = _compose_user_msg(
            post_text, author_line, reasoning, brand_allowed,
            issues if attempt else None, intent_layer=intent_layer,
            opening=opening,
        )
        try:
            out = _call_json(client, model, _COMPOSE_PROMPT, user_msg,
                             _COMPOSE_SCHEMA, max_tokens=700, temp=compose_temp)
        except Exception as e:
            print(f"[linkedin-tle] compose HIBA: {e}")
            return {"error": f"Gemini API hiba (compose): {e}"}
        comment = _normalise(((out or {}).get("comment") or ""))
        auth_total, auth_per = authenticity_score(out or {})
        # A kapu csak akkor meri az absztrakcio-szivargast, ha a layer be van
        # kapcsolva — kikapcsolva a v1-es kapu fut.
        issues = check_quality(
            comment, post_text, brand_allowed,
            intent=intent if intent_layer else "",
            discourse_level=level if intent_layer else "",
            human_temperature=human_temperature if intent_layer else "",
            image_attached=use_image,
            auth_score=auth_total, auth_min=auth_min,
        )
        if not issues:
            break
        rewrites = attempt + 1
        print(f"[linkedin-tle] kapu elutasitotta ({attempt + 1}. kor): {', '.join(issues)}")

    if not comment:
        return {"error": "A kompozíciós lépés üres kommentet adott."}

    # A gyűrű CSAK itt bővul: egy meg nem jelent (hibara futott) komment nyitasa
    # nem okoz ismetlodest, tehat nem is kell kizarni a kovetkezo valasztasbol.
    remember_opening(opening)

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
        # Nyitas-rotacio (v5): a kijelolt forma es a gyűrű pillanatnyi allapota —
        # ugyanaz az auditalhatosagi elv, mint a `strategy_scores`-nal.
        # "" = a valaszforma dontotte el a nyitast (`_OPENING_FREE_MODES`), vagy a
        # rotacio ki van kapcsolva.
        "opening_shape": opening,
        "opening_recent": list(_recent_openings),
        # Kep-bemenet: `image_attached` az ELKULDOTT kepet jelenti, nem a kapottat
        # (kikapcsolt layer / image_input=off eseten false, holott jott kep).
        "image_attached": use_image,
        "image_role": image_role,
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
        # Authenticity-rubrika: a modell pontszamai + a KODBELI kuszob, hogy a
        # dontes utolag megmagyarazhato es a kezi benchmark-pontokkal
        # korrelaltathato legyen.
        "authenticity_score": auth_total,
        "authenticity_max": AUTHENTICITY_MAX,
        "authenticity_min": auth_min,
        "authenticity_detail": auth_per,
        # `temperature` a BAZIS-ertek (visszafele-kompatibilis mezo); a ket hivas
        # tenyleges homerseklete a ket uj, additiv mezoben van — igy utolag
        # megmagyarazhato, melyik lepes min futott.
        "temperature": temp,
        "reason_temperature": reason_temp,
        "compose_temperature": compose_temp,
        "ai_fingerprint_terms": ai_fingerprint_terms(comment, post_text),
        "rewrites": rewrites,
        "post_overlap": round(overlap_ratio(comment, post_text), 3),
    }
