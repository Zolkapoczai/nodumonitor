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
import unicodedata
from collections import defaultdict, deque

from google import genai
from google.genai import types

from env_secrets import get_secret

ENGINE_VERSION = "linkedin-tle-v24"

# --- Stage 4: strategiak -----------------------------------------------------
# Pontosan EGY strategia valasztodik kommentenkent. A `directive` a compose-
# hivasba kerul — ez adja a komment jelleget, ezert rovid es utasito.
STRATEGIES: dict[str, dict[str, str]] = {
    "constructive_challenge": {
        "label": "Constructive Challenge",
        "directive": "Question exactly ONE assumption, respectfully and concretely. "
                     "Name the assumption, then say what it overlooks.",
        # 2026-08-11 (v12) — MERT OK az atirasra. A 33 soros naplo szerint a
        # gyoztes-eloszlas nem a POSZTOKAT kovette, hanem a `wins_when` SZELESSEGET:
        # a harom legkonnyebben teljesitheto feltetel vitte a 33 dontesbol 31-et
        # (field_experience "a poszt elmeleti es a gyakorlat mas" — LinkedIn-en
        # majdnem mindig igaz; practical_lesson "diagnosztizal, de nem ad teendot";
        # business_impact "technikai marad, az uzleti kovetkezmeny kimondatlan").
        # A CC eredeti feltetele volt a legszűkebb: a modellnek egy KIMONDATLAN
        # FELTETELT kellett talalnia, mig a tobbieknek egy allapotot eleg volt
        # felismernie. Az eredmeny: a CC nyers pontja 33 sorban EGYSZER SEM ment 7
        # fole (min 3, max 7, atlag 5.45), a gyoztes viszont 32 sorban 9 volt.
        # Az uj feltetel UGYANAZT a szakmai tartalmat keri (feltetelhez kotott
        # allitas), de FELISMERHETO allapotkent — ugyanazon a szinten, mint a tobbi hat.
        "wins_when": "the post states its central claim generally, and there is a "
                     "common case where it does not hold",
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

# Azok a DISKURZUS-SZINTEK, ahol a framework-reflex kapu mer (2026-08-10, user-dontes).
#
# MIERT KERULT BE A `management`: a 2026-08-10-i eles meres. A ragozas-javitas utan a
# komment `['governance', 'consistency']`-t adott — KETTO uj, a szerzotol nem atvett
# kifejezes, tehat a darabszam-feltetel teljesult —, a kapu megsem lepett be, mert a
# szint `management` volt. A komment eppen az a "foundational governance" + "naming
# conventions" reflex volt, amire ez a mechanizmus keszult, es amit a kulso pontozo
# is kifogasolt ("consultant mode").
#
# MIERT MARAD KI A `business`: ha a szerzo MAR uzleti sikra tette a beszelgetest, ott
# folytatni nem drift, hanem a beszelgetes kovetese — ezt a motor sajat terve mondja
# ki (`_LEVEL_STRATEGY_BIAS['business']` MEG IS EMELI a business_impactet). Ott
# kapuzni szembemenne a sajat dontesunkkel.
#
# MIERT ELEG a `>= 2` kuszob a `management` szinten is: a kapu csak azokat a
# kifejezeseket szamolja, amiket a SZERZO NEM hasznalt (`ai_fingerprint_terms`
# relativizal). Egy management-poszt szerzoje, aki maga beszel governance-rol, igy
# eleve vedett — az o szavai nem szamolodnak. Ami szamol, azt a komment hozta be.
#
# VISSZAFORDITHATO: a hatas a telemetria `rewrites` es `quality_issues_first`
# mezoibol merheto. Ha tul sok hamis pozitivot hoz, ez a halmaz egy sorban szűkul.
_FINGERPRINT_LEVELS = {"technical", "management"}

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
#
# TOROLVE A `strategy_fit`-BOL (2026-08-11, engine v18): a v8-as KALIBRACIOS
# ELLENORZES. Ket szabaly volt benne — "ha negy vagy tobb strategianak adtal 7-est
# vagy tobbet, pontozz ujra" es "a szoras legyen legalabb 5" —, es 50 telemetria-sor
# megmerte, mit ernek:
#
#     verzio | atlag >=7 db | (1) sertes | atlag szoras | (2) sertes
#     v8     |     4.3      |    86%     |     4.7      |    43%
#     v9     |     4.0      |    73%     |     4.9      |    27%
#     v13    |     4.9      |    100%    |     4.9      |    36%
#     v15    |     5.0      |    100%    |     4.8      |    20%
#
# A modell SOHA nem tartotta be, es romlik, nem javul. Ugyanaz a hibaosztaly, mint az
# authenticity-rubrika: a modell onpolicingja nem meroszam — es a projekt sajat
# szabalya erre az volt, hogy kivezetni kell, nem erositeni.
#
# A v16 ota a dontes amugy sem tamaszkodik a RANGSORRA: a nyers pont SZURO
# (`strategy_candidates`, sulyozott padlo 7), a valasztast a kod hozza
# (`decide_strategy`). A ket szabaly tehat halott szoveg volt: minden hivasban kimegy,
# semmit nem kenyszerit ki, es azt a latszatot adja, hogy a szoras garantalt.
#
# AMI SZANDEKOSAN MARADT: a negy horgony (0-2 / 3-5 / 6-8 / 9-10) es a jelentesuk — a
# v16-os jelolt-padlo EPPEN ezekre a savokra epul ("6-8: a good fit" az, amit a modell
# megbizhatoan megmond). Tovabba a "Score on professional value ALONE" mondat, ami most
# fontosabb, mint valaha: a padlo a SULYOZOTT pontra megy, tehat ha a modell a nyers
# pontban is beszamitana az intentet, a bias ketszer szamolna.
# Visszaszivargas ellen teszt orzi: test_linkedin_concreteness.py L3-L5.
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
15. thesis_condition — look again at the core_thesis you just named. If it is
    stated as if it held everywhere, name ONE common case where it does NOT hold,
    in one clause. This is not a rebuttal and not a change of subject: it is the
    boundary the author left unstated. "It depends on the project" is not a
    condition — name the case ("when the model is federated late", "on refurbishment
    work where the as-built is unreliable").
    EMPTY STRING if the claim genuinely carries no such boundary: a definition, an
    arithmetic fact, a report of something that already happened, or a personal
    story about the author's own experience. Do not invent a condition to fill this
    field — an empty answer here is a valid and frequent answer.
    AVOID THE MOST AVAILABLE ANSWER. "When the contracts or the incentives are not
    aligned" is a real condition, but it fits almost every claim in this industry,
    which is exactly what makes it worth little to the author. Prefer the boundary
    that belongs to THIS subject: a technical state (an export path, a schema, a
    version, a coordinate system), a project situation (refurbishment, a discipline
    joining late, a phase boundary, an existing building), or an organisational fact
    (who holds the model, who is on site, who authored the family). Answer with
    commercial or contractual terms only if the post is itself about commercial terms.
16. thesis_quote — if thesis_condition is not empty, copy the EXACT words from the
    post that state that claim, verbatim, nothing else. Empty string otherwise. Do
    not paraphrase and do not stitch fragments together — the quote is looked up in
    the post, and a quote that is not found there voids the condition.
17. strategy_fit — score EVERY strategy 0-10 on how much professional value it
    would add to THIS post. Do not pick a winner; score them all honestly. The
    `missing_perspective` you gave above is an input to this scoring, not the
    answer to it.
{chr(10).join(f'    - {k}: fits when {v["wins_when"]}' for k, v in STRATEGIES.items())}
    WHAT THE NUMBERS MEAN — use the whole scale:
      0-2  applying this strategy here would MISS what the post is about
      3-5  technically applicable, but adds little the author or readers do not
           already have
      6-8  a good fit: the comment would say something worth reading
      9-10 the single best available move for THIS post; any other choice would
           produce a worse comment
    Score on professional value ALONE. Do NOT down-score a strategy because it
    seems to clash with the conversation_intent or the discourse_level — those
    are weighted separately, after you answer. Double-counting them here distorts
    the decision.
    DISAGREEMENT IS NOT A RISK YOU ARE MANAGING. A confident, popular or
    well-written post is not evidence that its central claim is unconditional. If
    that claim is stated generally and you can name one common case where it does
    not hold, then constructive_challenge IS the 9-10 move for this post — naming
    that condition is worth more to the author than a fourth supporting example.
    Scoring it 6-7 to stay safe is the known failure of this step.
18. strategy_reason — one sentence: what the comment has to accomplish for this
    specific audience to be worth reading.
19. explicit_tool_request — true ONLY if the post (or the author in it) directly
    asks the reader to name a tool, product, plugin, service or vendor.
    True examples: "what do you use for this?", "any tool recommendations?",
    "how do you solve this in practice — which software?", "milyen eszkozzel
    oldjatok meg?".
    FALSE for: describing a problem, complaining, asking for opinions or advice
    in general, rhetorical questions, or asking "how" without asking "with what".
    Someone stating a pain is NOT asking for a product. Default to false.
20. tool_request_quote — if explicit_tool_request is true, copy the EXACT words
    from the post that contain the request, verbatim, nothing else. Empty string
    if false. Do not paraphrase — the quote is verified against the post.
21. vendor_promotion — true ONLY if this post is MARKETING MATERIAL published by
    the seller of the product it promotes. The markers are register, not topic:
    the brand written about in the third person, feature or integration counts
    ("30+ integrations"), benefit claims ("nothing falls through the cracks"),
    and a call to action ("stop coordinating around the chaos").
    FALSE for a practitioner showing a tool they use, built or bought — even
    enthusiastically, even naming the vendor. A person sharing their own work is
    NOT vendor marketing. FALSE for a release note or version announcement made
    by a practitioner. When genuinely unsure, answer false.
22. promotion_evidence — if vendor_promotion is true, copy the EXACT words from
    the post that make it marketing (the call to action or the benefit claim),
    verbatim, nothing else. Empty string if false. Do not paraphrase — the quote
    is verified against the post.
23. insight — ONE original, specific claim that is NOT stated in the post and is
    not a restatement of it. This is the substance of the comment. Go deeper,
    not wider. No hedging, no generalities like "communication is important".
    The insight must sit at the `discourse_level` you reported above — on a
    technical post, a deeper technical claim, NOT a business consequence.
    BE CONCRETE. Name the mechanism, the artefact, the phase or the discipline
    where this bites — an IFC property set, a shared parameter GUID, a workset,
    the handover, the MEP model. An insight that names only a CATEGORY ("teams
    classify issues differently") is too vague; name the INSTANCE ("one team
    logs a clash as an issue, the next logs it as an RFI").
    The line: technical concreteness YES, invented project specifics NO. General
    domain facts are fair; numbers, client names and anecdotes from projects you
    cannot have seen are not.
24. confidence — 0.0-1.0, your confidence in this reasoning.

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
        # Kihivas-szenzor (v13). UGYANAZ A MINTA, mint a tool_request/vendor-
        # promotion parosnal: a modell ALLIT (van kimondatlan feltetel), es ad hozza
        # egy SZO SZERINTI idezetet, amit a kod megkeres a posztban. A dontest nem a
        # pontszam hozza — ld. `challenge_override`.
        "thesis_condition": {"type": "STRING"},
        "thesis_quote": {"type": "STRING"},
        # A modell PONTOZ, nem valaszt — a dontest a kod hozza (pick_strategy).
        "strategy_fit": {
            "type": "OBJECT",
            "properties": {k: {"type": "INTEGER"} for k in STRATEGIES},
            "required": list(STRATEGIES),
        },
        "strategy_reason": {"type": "STRING"},
        "explicit_tool_request": {"type": "BOOLEAN"},
        "tool_request_quote": {"type": "STRING"},
        # Ugyanaz a minta, mint a tool_request: a modell ALLIT, a kod pedig az
        # idezetet MEGKERESI a posztban (`_quote_in_post`) — zero-hallucination.
        "vendor_promotion": {"type": "BOOLEAN"},
        "promotion_evidence": {"type": "STRING"},
        "insight": {"type": "STRING"},
        "confidence": {"type": "NUMBER"},
    },
    "required": [
        "topic", "post_type", "conversation_intent", "discourse_level",
        "expected_responder_role", "response_mode", "human_temperature",
        "topic_gravity", "author_objective", "audience", "technical_depth",
        "emotional_tone", "core_thesis", "missing_perspective",
        "missing_perspective_reason", "thesis_condition", "thesis_quote",
        "strategy_fit", "strategy_reason",
        "explicit_tool_request", "tool_request_quote",
        "vendor_promotion", "promotion_evidence", "insight", "confidence",
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


# --- Stage 4b: a fit mint SZURO, nem rangsor (2026-08-11, engine v16) ---------
#
# A MERT DIAGNOZIS (50 sor, motorverziora bontva): a nyers `strategy_fit` NEM rangsor.
#   - a het strategiabol 4-5 MINDIG 7 fole kerul (v15: atlag 5.0 db),
#   - a v8-as prompt ket kimondott szabalya ("legfeljebb harom lehet >= 7", "a szoras
#     legyen legalabb 5") a sorok 73-100%-aban serul, es ROMLIK, nem javul,
#   - a nyers maximum 21 v13+ sorbol 13-ban HOLTVERSENY (2-3 strategia egy erteken),
#   - egy kontrollalt kiserlet (a tezis-mezok a `strategy_fit` UTAN) a CC inflaciojanak
#     felet megszuntette, de a LAPOSSAGON semmit nem valtoztatott -> a hiba szerkezeti,
#     nem egy adott prompt-verzio kovetkezmenye.
#
# Vagyis a modell megbizhatoan megmondja, hogy egy strategia ELFOGADHATO-e ("6-8: a
# good fit" — a sajat prompt-horgonyunk szavaival), de a "9-10: az EGYETLEN legjobb"
# fokozatot rangsor-cimkeként hasznalja. A prompt-oldali onellenorzes HAROMSZOR nem
# vezetett eredmenyre; a projekt sajat szabalya szerint (authenticity-rubrika) az ilyen
# onpolicingot nem erositeni kell, hanem kivezetni.
#
# EZERT: a pontszam SZURO lesz (ki a jelolt), es a jelolt-halmazbol a KOD dont —
# ugyanaz az elv, ami a nyitasnal es a hossznal mar bevalt: a varianciat kodban
# allitjuk elo, nem a mintavetelre bizzuk. A `pick_strategy` VALTOZATLAN marad, es
# ket dolgot szolgal tovabbra is: a kikapcsolt agat (`strategy_candidates: off`) es a
# fallbacket, ha egy poszton egyetlen strategia sem eri el a padlot.
STRATEGY_CANDIDATE_FLOOR = 7

# MIERT SEKELYEBB ez a gyűrű a nyitas-gyűrűnel (4): ott NYOLC formabol valasztunk, itt
# a jelolt-halmaz merve 4-5 elemű. Negy kizarasa a legtobb soron kiuritene a halmazt,
# es a mechanizmus folyamatosan a vedoszabalyra esne vissza — vagyis latszolag mukodne,
# valojaban nem tenne semmit. Kettovel ~3 valodi jelolt marad.
_STRATEGY_RING_SIZE = 2
_recent_strategies: deque = deque(maxlen=_STRATEGY_RING_SIZE)


def strategy_candidates(fit: dict, intent: str = "general",
                        discourse_level: str = "technical") -> list[str]:
    """A jelolt-halmaz: a padlot elero SULYOZOTT pontszam, veto nelkul.

    MIERT A SULYOZOTT ES NEM A NYERS PONT — ezt a J6 teszt talalta meg, es majdnem
    ellenkezojere fordult a mechanizmus. A nyers pontra szűrve a v2 ota dokumentalt
    ALAPHIBAT engedtuk volna vissza: a mesterseg-poszton a modell a
    `business_impact`-nek adott 10-et, a `field_experience`-nek 6-ot. Nyers padlora
    az elobbi vetozott, az utobbi KIESIK — es az egyetlen jelolt a
    `systems_thinking` (7) lett volna, sulyozottan 5.0-tal, holott a bias a
    `field_experience`-t 9.0-ra emeli.
    A bias EPPEN a modell ismert felrepontozasat javitja (`_LEVEL_STRATEGY_BIAS`,
    intent-bias); egy szűro, ami a bias ELOTT vag, kidobja azt a korrekciót, amiert
    az intent layer letezik. A padlo ezert a sulyozott pontszamra megy.
    """
    scores, vetoed = score_strategies(fit, intent, discourse_level)
    return [slug for slug in STRATEGIES          # stabil, deklaracios sorrend
            if scores[slug] >= STRATEGY_CANDIDATE_FLOOR and slug not in vetoed]


def decide_strategy(fit: dict, post_text: str, intent: str = "general",
                    discourse_level: str = "technical",
                    recent=None) -> tuple[str, str]:
    """(strategia, indok) — a jelolt-halmazbol a kod dont.

    HAROM lepes, mindegyik indokkal a naploba:
      1. JELOLTEK: a padlot elero, nem vetozott strategiak. Ha egy sincs, a dontes a
         valtozatlan `pick_strategy` (sulyozott argmax) — a padlo nem urithet ki.
      2. FRISSESSEG: a legutobbi `_STRATEGY_RING_SIZE` strategia kiesik. Vedoszabaly:
         ha ezzel ures lenne a halmaz, a teljes jelolt-lista marad (a rotacio nem
         kenyszerithet ki egy amugy sem illeszkedo strategiat).
      3. VALASZTAS a maradekbol: a sulyozott pontszam (a bias) dont, es CSAK
         holtversenyben a poszt hash-e. Igy a bias ott hat, ahol dolga van —
         kozel-egyenlok kozott valaszt —, es nem egy lapos savon o a teherhordo.

    A hash-es dontobiro ugyanaz a harom kovetelmeny, mint a `pick_opening`-nal: NE
    ismetlodjon, legyen REPRODUKALHATO (ugyanaz a poszt ugyanazt adja), es SZORODJON.
    """
    cands = strategy_candidates(fit, intent, discourse_level)
    if not cands:
        fallback = pick_strategy(fit, intent, discourse_level)
        return fallback, (f"nincs jelolt a {STRATEGY_CANDIDATE_FLOOR}-es padlo felett "
                          f"-> sulyozott argmax ({fallback})")

    # ADAPTIV GYŰRŰ-MELYSEG (2026-08-11, v17). A MERT HIBA: nyolc eles posztbol
    # kettonel mindossze KET jelolt volt, mindketto a ketmelysegű gyűrűben — a
    # vedoszabaly ezert visszaadta a teljes listat, es a rotacio nem tett semmit
    # (ismetles). A melyseg ezert a jelolt-szamhoz igazodik: legfeljebb annyit
    # zarunk ki, hogy MINDIG maradjon legalabb egy valaszthato.
    ring = list(_recent_strategies if recent is None else recent)
    depth = max(0, min(_STRATEGY_RING_SIZE, len(cands) - 1))
    used = set(ring[-depth:]) if depth else set()
    fresh = [s for s in cands if s not in used]
    excluded = [s for s in cands if s in used]
    if not fresh:
        # Elerhetetlen ag a fenti melyseg-szamitas mellett (|used ∩ cands| <= len-1),
        # ezert teszt orzi (L19). Vedoszabalykent marad: ha valaha megis idejutunk, a
        # rotacio ne urithesse ki a dontest.
        fresh = cands
        note = f"mind a {len(cands)} jelolt szerepelt a gyűrűben, ezert nincs kizaras"
    else:
        note = (f"{len(cands)} jelolt (gyűrű-melyseg {depth}), "
                f"kizarva ismetles miatt: {excluded}" if excluded
                else f"{len(cands)} jelolt (gyűrű-melyseg {depth}), nincs ismetles")

    scores, _ = score_strategies(fit, intent, discourse_level)
    top = max(scores[s] for s in fresh)
    tied = [s for s in fresh if scores[s] == top]
    if len(tied) == 1:
        return tied[0], f"{note}; gyoztes: sulyozott max ({top:g})"
    digest = hashlib.sha256((post_text or "").strip().lower().encode("utf-8")).digest()
    chosen = sorted(tied)[int.from_bytes(digest[:8], "big") % len(tied)]
    return chosen, (f"{note}; holtverseny {top:g}-en {sorted(tied)} "
                    f"-> poszt-hash dontott")


def remember_strategy(slug: str) -> None:
    """A strategia a gyűrűbe — CSAK sikeres komment utan, mint a nyitasnal."""
    if slug:
        _recent_strategies.append(slug)


def strategy_candidates_enabled(config: dict) -> bool:
    """`linkedin.strategy_candidates`: on (default) | off. YAML-boolean (§4/17).

    Kikapcsolva a dontes BAJTRA a v15-os: tiszta `pick_strategy` argmax. Igy a
    valtas A/B-zheto ugyanazon a kodon — mint az `intent_layer`-nel es a
    `length_scaling`-nal.
    """
    raw = (config.get("linkedin", {}) or {}).get("strategy_candidates", "on")
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() not in ("off", "false", "0", "no", "none")

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


def length_scaling_enabled(config: dict) -> bool:
    """`linkedin.length_scaling`: on (default) | off. YAML-boolean kezelve (§4/17).

    Kikapcsolva a compose-uzenet hossz-mondata BAJTRA a v6-os fix "80-150 words",
    tehat a skalazas A/B-zheto ugyanezen a kodon — mint az `intent_layer` es az
    `opening_variety`.
    """
    raw = (config.get("linkedin", {}) or {}).get("length_scaling", "on")
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() not in ("off", "false", "0", "no", "none")


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

ENDING (v21). Do not end with advice, a recommendation or a solution. Close in
one of these two ways — pick whichever fits the strategy, do not force both:
  (a) a genuine question that could only be asked by someone who read THIS
      post — it must name the author's specific detail, claim or number, not a
      generic "what do you think?"; or
  (b) an explicit callback to the author's own point — reference what they
      specifically said or claimed, then add your one new thing to it.
A comment that ends on a free-floating observation with no question and no
named callback to the author is the weaker version of this rule — prefer (a)
or (b) whenever the strategy allows it. `constructive_challenge` naturally
wants (a); `field_experience` and `practical_lesson` often read better with
(b). Never use both forms in the same comment — one clean move, not two.

Hard limits:
- 80-150 words, unless the task message gives a different range — that one wins.
  Never more than two paragraphs.
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

# --- COMPOSE sema -----------------------------------------------------------
# TOROLVE (2026-08-10): az Authenticity rubrika (ot 0-2-es onertekelo tengely).
#
# MIERT: harom eles meres, HAROM 10/10. A `no_implementation_drift` mindharom
# esetben 2-t kapott — vagyis "nulla drift" —, kozben a harom komment sorrendben
# ezt irta: "consultant mode"-ot kifogasolt kulso pontozo (88/100), "foundational
# governance"-t es "naming conventions"-t, illetve "cultural willingness to embed
# those capabilities into daily operations"-t. A rubrika tehat NEM gyengen
# korrelalt: egyaltalan nem volt benne VARIANCIA. Egy mérőszám, ami mindig a
# maximumot adja, definicio szerint nem tud rangsorolni.
#
# A 03-composer-spec (2026-08-01, "Nyitott kerdes") sajat feltetelt szabott:
# "Az egyetlen valodi proba, hogy az authenticity_detail korrelal-e a kezi
# benchmark-pontokkal. Ha nem, a rubrika torolheto." Ez a feltetel teljesult.
#
# MIT VESZTUNK: a modell a lezaras elott ot megnevezett tengely szerint
# ujraolvasta a sajat szovegét. Harom meres alapjan ez az ujraolvasas semmit nem
# fogott meg, tehat nem vesztes. Amit NYERUNK: ~10 kimeneti token/hivas, es egy
# hamis biztonsagerzet eltunese — a 10/10 azt sugallta, hogy a komment rendben van.
#
# AMI A HELYERE LEP: a determinisztikus kapu (`check_quality`) es az F2
# konkretsag-diagnosztika (`concreteness`). Mindketto MERT dolgokat mer, nem
# onertekelest kér. A `linkedin.authenticity_min_score` amugy is 0 volt a
# configban, tehat a kuszob mar nem is befolyasolta a kimenetet.
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
    # A fonev-lista 2026-08-11-en bővult (breakdown/summary/reminder/example/
    # framing/insight): ugyanaz a frazis-csalad, csak mas targgyal — a hiany itt
    # ALULSZAMOL, ugyanugy, mint a `_CONTENT_MOVES` szotar-hianyanal.
    (r"\b(?:great|excellent|fantastic|brilliant|insightful) "
     r"(?:post|point|article|read|write-?up|breakdown|summary|reminder|example|"
     r"framing|insight)\b", "dicseret"),
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

# --- DICSERO NYITAS, SZERKEZETI MINTA (2026-08-11, engine v24) ---------------
#
# A MERT ESET: „Your sketch beautifully illustrates how facade alternatives
# balance aesthetics with daylighting…" — `rewrites: 0`, `quality_issues: []`,
# vagyis MINDEN kapun atment. A compose-prompt kimondja: „Never open with praise
# or agreement", a `_FORBIDDEN_PATTERNS` viszont csak NEVESITETT frazisokat ismer
# („Great post", „Thanks for sharing"), es ez az alak egyiket sem tartalmazza.
# Ugyanaz a hibaosztaly, mint a 2026-08-10-i ragozas-hiany: a szotari lista csak
# azt tiltja, amit valaki mar felvett ra.
#
# EZERT SZERKEZETI ES NEM SZOTARI: a mintat nem egy kifejezes adja, hanem egy
# ALAK — [birtokos/hatarozo] + [a szerzo munkaja] + [dicsero hatarozo] +
# [abrazolast jelento ige]. Igy a „Your diagram elegantly captures…" es a „This
# post nicely summarises…" is elesik anelkul, hogy fel kellene sorolni oket.
#
# HAMIS POZITIV, AMIT A MERES MEGFOGOTT: a korpuszban van egy „While Copy/Monitor
# is EXCELLENT for establishing the initial coordination, a common challenge…"
# nyitas. Ez NEM dicseret, hanem szakmai engedmeny egy Revit-funkciorol — egy
# puszta `excellent`-re epulő szo-alapu szabaly ezt elbuktatta volna. Ezert nincs
# benne altalanos dicsero MELLEKNEV, csak a fenti ALAK; es ezert kellenek a
# dicsero HATAROZOK (nem `accurately`/`clearly`, amik tenymegallapitast is
# jelolhetnek).
#
# ES EZERT CSAK A NYITASRA (`_opening_window`, elso ket mondat): a szabaly, amit
# ervenyesit, kifejezetten a NYITASRA szol. Kozepen egy „the drawing nicely shows
# the offset" mar tartalmi allitas lehet, nem hizelges.
# FELTETEL NELKUL mer (nem `shaping_active`-hoz kotve), mert a dicsero nyitas
# tilalma nem az intent-layer fuggvenye — az a motor alapszabalya.
_PRAISE_OPENING_PATTERNS: list[tuple[str, str]] = [
    (r"\b(?:your|this|the)\s+\w+(?:\s+\w+)?\s+"
     r"(?:beautifully|perfectly|elegantly|brilliantly|nicely|wonderfully|"
     r"superbly|masterfully|eloquently|powerfully|neatly)\s+"
     r"(?:illustrat|captur|show|demonstrat|summari[sz]|convey|highlight|"
     r"articulat|encapsulat|frame)\w*",
     "a szerzo munkajanak megdicserese"),
    (r"^\s*(?:i\s+)?(?:really\s+)?love (?:this|that|it)\b", "puszta lelkesedes"),
    (r"^\s*(?:very\s+)?well (?:put|articulated|framed)\b", "ures elismeres"),
]

# SAJAT PREFIX, nem a `tiltott fordulat` — mert a ket halmazba valo tartozas
# kulonbozik, es egy meglevo prefix ujrahasznalata MELLEKHATASKENT szelesitette
# volna ki oket (a `tiltott fordulat` alá az „as an ai" is beesik).
# A `tanacsadoi nyitas` a precedens: az is MINDKET halmazban van — kiadhatatlan,
# de szocserevel javithato, tehat jar ra a harmadik kor.
_PRAISE_ISSUE_PREFIX = "dicsero nyitas"

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
# Hany mondatot tekintunk NYITASNAK (2026-08-10, user-dontes).
#
# A MERT HIBA: a mintak `^`-hoz kotottek `re.MULTILINE`-nal, ami SORkezdet, nem
# MONDATkezdet. Egy eles generalas igy irt: "The challenge of disconnected tools is
# a real one. We often see that even with integrated platforms..." — a sablonos
# fordulat a MASODIK mondat elejen volt, ugyanabban a sorban, tehat a kapu nem
# latta. Ugyanaz a mondat elso helyen viszont sertes volt.
#
# MIERT PONTOSAN KETTO, es miert nem "barmely mondatkezdet": ez a szabaly a
# NYITASROL szol. Egy sablonos fordulat a 8. mondatban nem nyitasi hiba — ott a
# serteés cimkéje ("ismetlodo nyitas") felrevezeto lenne, es atfedesbe kerulne az
# `_AI_FINGERPRINT_PATTERNS`-szel, aminek eppen a regiszter a dolga. A ketto
# megorzi a kodban mar dokumentalt szandekot is: "a kifejezes kesobbi, tartalmilag
# indokolt hasznalata nem serul".
_OPENING_SENTENCES = 2


def _opening_window(text: str) -> list[str]:
    """A komment elso `_OPENING_SENTENCES` mondata, kulon-kulon.

    A nyitas-mintak `^`-hoz kotottek, ezert mondatonkent kell rajuk illeszteni —
    igy a masodik mondat eleje is "kezdet". Mondathatar: irasjel + szokoz, VAGY
    sortores (a bekezdeshatar is uj mondat).

    Ismert korlat: a roviditesek ("e.g.", "vs.") hamis mondathatart adnak. Egy
    ilyen tores legfeljebb egy plusz jelolt-mondatot ereszt be az ablakba, tehat
    a hatas legrosszabb esetben is egy szűkebb/bővebb ablak, nem hibas sertes.
    """
    parts = re.split(r"(?<=[.!?])\s+|\n+", (text or "").strip())
    return [p.strip() for p in parts if p.strip()][:_OPENING_SENTENCES]


# --- Nyitas-visszhang: a MEGVALOSULT nyitas, nem a kijelolt forma (2026-08-11) ---
#
# A MERT HIBA (ot eles generalas, `bench_posts/01..05`): a rotacio HAROM KULONBOZO
# formát osztott ki (`own_practice`, `strikes`, `pattern`), a modell megis
# haromszor ugyanazzal a mondattal indult — "What strikes me ...". A forma-kijeloles
# tehat UTASITAS, nem kikenyszeritett eredmeny, es a megvalosult nyitast eddig
# semmi nem mérte.
#
# MIERT NEM A `_STOCK_OPENING_PATTERNS` BOVITESE: az szotari lista — csak azt
# tiltja, amit valaki mar felvett ra, es a "What strikes me" eppen a sajat
# katalogusunk (`OPENING_SHAPES['strikes']`) ajanlott formája. Tiltolistara tenni
# annyi lenne, mint a sajat whitelistunk ellen kapuzni (ld. G1 teszt). A hiba nem
# a kifejezesben van, hanem az ISMETLESBEN.
#
# A MEGOLDAS: a sajat elozo kimeneteinkhez merunk. Ugyanaz a fajta hiba, mint amire
# a forma-rotacio szuletett — ket komment kulon-kulon hibatlan, sorozatban megis
# felismerheto —, ezert ugyanaz a mintat kap: gyűrű + determinisztikus kapu.
#
# MIERT UGYANOLYAN MELY A KET GYŰRŰ (`_OPENING_RING_SIZE`): kulonben a ket
# mechanizmus egymas ellen dolgozna. A forma-gyűrű 4 hivason at kizarja a mar
# hasznalt formát; ha a visszhang-gyűrű ennel MELYEBB lenne, egy olyan formát is
# megbuntetne, amit a rotacio joggal ad ki ujra. Egyetlen szammal a ket szabaly
# definicio szerint konzisztens.
_OPENING_ECHO_RING_SIZE = _OPENING_RING_SIZE
_recent_opening_texts: deque = deque(maxlen=_OPENING_ECHO_RING_SIZE)

# Hany szo az ujjlenyomat. HAROM, mert a mert eset pontosan ennyiben egyezett
# ("What strikes me ABOUT THIS IS" / "...ABOUT THE DISCUSSION" / "...IS HOW OFTEN"),
# es mert a negyedik szonal mar a tartalom kezdodik: annal hosszabb ujjlenyomat
# ket azonos mozdulatot kulonbozonek latna. Ketto viszont tul rovid — az "I've
# found" (`own_practice`) es az "I've run into" (`encountered`) ket KULONBOZO
# ajanlott forma, amiket nem szabad egybemosni.
_OPENING_FINGERPRINT_WORDS = 3

# Minden nem betu/szam SZOKOZ lesz, tehat az "I've found" -> "i ve found": az
# irasjel-valtozat (`'` vs a modell altal kedvelt `’`) ugyanarra a mozdulatra
# ugyanazt az ujjlenyomatot adja. Az aposztrof igy egy szohatart is bevisz — ez
# nem baj: "i ve found" (`own_practice`) es "i ve run" (`encountered`) a harmadik
# szonal tovabbra is elvalik.
#
# EKEZET-HAJTOGATAS (2026-08-11, MERT HIBA): az elso valtozat `[^a-z0-9]`-t
# hasznalt, ami a MAGYAR ekezetes betut is szohatarnak vette. Egy eles magyar
# kommentnel ("Egy visszatérő mintát látok") az ujjlenyomat 'egy visszat r' lett —
# vagyis harom szo helyett masfel, es a fragmentumok kozott sokkal konnyebb a
# hamis egyezes. Ezert NFKD-vel bontunk es a kombinalo jeleket dobjuk el:
# "visszatérő" -> "visszatero", egyetlen tokenkent. Melekhaszon: az ekezet nelkul
# irt valtozat ("koszonom" vs "köszönöm") ugyanazt az ujjlenyomatot adja.
# ISMERT KORLAT: a feloldott alak MAS ujjlenyomat ("i have found" != "i ve found").
# Fail-open, azaz legfeljebb atengedi az ismetlest — nem hibas sertest ad.
_OPENING_FP_STRIP = re.compile(r"[^a-z0-9]+")


def _fold_accents(text: str) -> str:
    """Ekezet -> alapbetu (NFKD + kombinalo jelek eldobasa)."""
    return "".join(c for c in unicodedata.normalize("NFKD", text)
                   if not unicodedata.combining(c))


# --- Nyito-KERETEK: ugyanaz a mozdulat mas szavakkal (2026-08-11, engine v11) ---
#
# A MERT KIJATSZAS (n=2): a v9-es kapu blokkolta a "What strikes me"-t, a modell
# masodik kore pedig "What's compelling about Frank's approach..."-szal indult.
# Harom szo szerint MAS ujjlenyomat, retorikailag UGYANAZ a mozdulat: „megnevezem,
# mi a feltuno a szerzo pontjaban". A lexikai ujjlenyomat a betűt meri, a mozdulat
# viszont szemantikai — ugyanaz a hibaosztaly, mint a `post_overlap`-nal.
#
# A MEGOLDAS NEM TILTAS, HANEM KANONIZALAS. Ez a kulonbseg dönti el, miert nem esik
# a szotar-csapdaba: a kifejezes tovabbra is HASZNALHATO (a `strikes` a sajat
# katalogusunk formája), csak az ISMETLESE lathato. Egy keret-csaladra eso ket
# egymas utani nyitas ugyanazt az ujjlenyomatot adja, akarhogy is variálja a szavakat.
#
# SZUK: csak MERT alakok es azok kozvetlen szinonimai, es CSAK az elso mondat ELEJEN
# (`^`). A komment kozepen allo ugyanilyen fordulat nem nyitasi hiba — a poszt 13
# kommentje ("I've run into similar challenges..., and what strikes me is...") ezert
# szandekosan a sajat `i ve run` ujjlenyomatat kapja: a NYITASA valoban mas mozdulat.
_OPENING_FRAMES: list[tuple[str, str]] = [
    # A mert par: "What strikes me about this is..." es "What's compelling about..."
    (r"^what(?:'s| is| has)? (?:strikes?|struck|stricken)? ?me\b", "frame:notable"),
    (r"^what(?:'s| is)? (?:so )?(?:compelling|interesting|striking|notable|telling|"
     r"remarkable|fascinating|noteworthy)\b", "frame:notable"),
    (r"^what (?:i find|really) (?:compelling|interesting|striking|notable)\b",
     "frame:notable"),
]


def opening_frame(sentence: str) -> str:
    """A nyito mondat retorikai kerete, vagy "" ha egyik csaladba sem esik."""
    text = (sentence or "").strip().lower()
    for pattern, name in _OPENING_FRAMES:
        if re.search(pattern, text):
            return name
    return ""


def shape_frame(opening_key: str) -> str:
    """A KIOSZTOTT forma sajat kerete (a katalogus peldajabol), vagy "".

    MIERT KELL: a keret-kanonizalas megbontana a ket gyűrű szimmetriajat. A
    forma-gyűrű 4 hivason at kizarja a `strikes` formát, de egy MAS formát kapott
    komment is elhasznalhatja a `frame:notable` keretet (mérve: a 12-es komment
    `stood_out` kiosztassal indult "What strikes me"-vel). Ha ezutan a rotacio
    kiadja a `strikes`-ot, a modell a SAJAT UTASITASA miatt kapna sertest. Ezert a
    hivo a kiosztott forma keretet kiveszi az osszehasonlitasbol: az utasitas
    mindig eros'ebb, mint a visszhang-tilalom.
    """
    shape = OPENING_SHAPES.get(opening_key or "")
    if not shape:
        return ""
    return opening_frame(shape["example"].strip('"'))


def echo_ring_for(opening_key: str, extra: list[str] | None = None) -> list[str]:
    """A KAPUNAK atadott gyűrű: a kiosztott forma sajat kerete kimarad belole.

    Kulon fuggveny es nem egy sor a hivo oldalon, mert ez a szabaly a ket
    mechanizmus kozotti szerzodes (`shape_frame` docstring), es igy tesztelheto
    onmagaban. Ures `own` eseten semmi nem esik ki: ures ujjlenyomat sosem kerul
    a gyűrűbe.

    `extra`: tovabbi bejegyzesek (pl. a szerzonkenti gyűrű) — ld. `move_ring_for`.
    """
    own = shape_frame(opening_key)
    combined = list(_recent_opening_texts) + list(extra or ())
    return [fp for fp in combined if fp != own]


def opening_fingerprint(comment: str) -> str:
    """A komment nyitasanak ujjlenyomata.

    Ket lepes: eloszor a KERET (`_OPENING_FRAMES`) — ha a nyito mondat egy ismert
    retorikai csaladba esik, a csalad neve az ujjlenyomat, tehat a szo-szintű
    varialas nem bujik el. Kulonben az ELSO mondat elso harom szava.

    Miert csak az elso mondat (szemben a kapu ket-mondatos ablakaval): ez a
    szabaly a retorikai MOZDULAT ismetleset meri, es azt az elso mondat hordozza.
    A masodik mondat mar tartalom — ket komment ott joggal indulhat hasonloan.
    """
    window = _opening_window(comment)
    if not window:
        return ""
    frame = opening_frame(window[0])
    if frame:
        return frame
    folded = _fold_accents(window[0].lower())
    words = [w for w in _OPENING_FP_STRIP.sub(" ", folded).split() if w]
    return " ".join(words[:_OPENING_FINGERPRINT_WORDS])


def remember_opening_text(comment: str) -> None:
    """A megvalosult nyitas a gyűrűbe — CSAK sikeres komment utan, mint a formánal.

    Egy hibara futott (soha meg nem jelent) komment nyitasa nem okoz ismetlodest,
    tehat nem is kell kizarni a kovetkezobol.
    """
    fp = opening_fingerprint(comment)
    if fp:
        _recent_opening_texts.append(fp)


def reset_opening_state() -> None:
    """MINDEN varianciа-gyűrűt nullazza (forma, nyitas, mozdulat, feltetel, strategia
    — globalisan ES szerzonkent).

    MIERT KELL: mind a ketto processz-eletű varianciа-allapot, es egy teszt, ami
    hivas-sorozatokra allit (pl. "tiszta elso kor -> nincs ujrairas"), csak akkor
    izolalt, ha MINDKETTO tiszta. Amikor a visszhang-gyűrű bejott, harom meglevo
    teszt azonnal elbukott, mert csak a forma-gyűrűt nullaztak — ezert egy helyen
    van, es nem hivasonkent ket sorban: a kovetkezo gyűrű igy nem ejti ugyanabba a
    csapdaba a kovetkezo tesztet.
    """
    _recent_openings.clear()
    _recent_opening_texts.clear()
    _recent_content_moves.clear()
    _recent_condition_families.clear()
    _recent_insight_families.clear()
    _recent_strategies.clear()
    # Szerzonkenti gyűrűk (v21) — ugyanaz a "mindent nullaz" elv.
    _author_strategies.clear()
    _author_openings.clear()
    _author_opening_texts.clear()
    _author_content_moves.clear()


def opening_echo_gate_enabled(config: dict) -> bool:
    """`linkedin.opening_echo_gate`: on (default) | off. YAML-boolean kezelve (§4/17).

    Kikapcsolva a `check_quality` NEM kap gyűrűt, tehat bajtra a 2026-08-10-i kapu
    fut — ugyanaz az A/B-elv, mint az `opening_variety`-nel es a `length_scaling`-nel.
    """
    raw = (config.get("linkedin", {}) or {}).get("opening_echo_gate", "on")
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() not in ("off", "false", "0", "no", "none")


# --- Tartalmi mozdulat: a GONDOLAT visszhangja (2026-08-11, engine v14) -------
#
# A MERT HIBA: a kihivas-szenzor (v13) utan a `constructive_challenge` vegre nyert —
# es HET CC-kommentbol HAT ugyanoda futott ki: „a valodi kerdes a szerzodes /
# incentiva-struktura". Szo szerinti idezetek: „clear contractual ask" · „shift in
# contractual frameworks" · „the contractual structure itself" · „legal and
# commercial frameworks … liability" · „contractual incentives". A strategia
# diverzifikalodott, a GONDOLAT nem.
#
# Ez ugyanaz a hibaosztaly, mint a nyitas-visszhang: ket komment kulon-kulon
# hibatlan, sorozatban megis egy hangot ad. Ezert ugyanazt a mintat kapja —
# KANONIZALAS es gyűrű, NEM tiltolista. A kereskedelmi keretezes nem hiba: a
# `business_impact` strategia direktivaja EPPEN ezt keri. A hiba az ISMETLESE.
#
# MIERT >= 2 TALALAT: egy futo emlites nem a komment mozdulata. A mert sorokban 2-4
# kulonbozo terminus volt; egyetlen "incentive"-nel (41. sor) meg nem allithato,
# hogy a komment EZ. Ugyanaz a kuszob-logika, mint az `ai_fingerprint_terms`-nel.
_CONTENT_MOVES: list[tuple[str, str]] = [
    # A `procurement`, `compensat*` es a puszta `fees` UTOLAG kerult be, mert a mert
    # adatban ott voltak es a lista kihagyta oket: „when the client's PROCUREMENT
    # process does not explicitly define and COMPENSATE for knowledge transfer"
    # (elfogadott feltetel), illetve „design FEES aren't always structured to fully
    # cover that coordination effort" (a v14-es kapu lexikai kicsuszasa). Ugyanaz a
    # szotar-hianyossag, mint a 2026-08-10-i ragozas-javitasnal: a hiany ALULSZAMOL.
    (r"\b(?:contract|contracts|contractual|contracting)\b|\bincentiv\w+\b|"
     r"\bliabilit\w+\b|\bbillable\b|\bhourly billing\b|\bfee structure\b|"
     r"\bfees?\b|\bprocurement\b|\bcompensat\w+\b|"
     r"\bcommercial model\w*\b|\bpayment milestone\w*\b|\breimburs\w+\b",
     "move:commercial_frame"),
    # A 2026-08-11-i futasban (v15-v19) a "" (nem kategorizalt) `thesis_condition`-ok
    # kozott EGY masik, addig lathatatlan csalad ismetlodott legalabb 5-6x: kozos CDE/
    # BIM execution plan / koordinata-rendszer hianya tobb szoftver/diszciplina eseten.
    # A `condition_family` egy-mintas listaja ezt nem tudta nevesiteni, tehat a gyűrű
    # sem vedhetett ellene — a masik monokultura felugyelet nelkul futott.
    (r"\bCDE\b|\bBIM execution plan\b|\bcoordinate system\w*\b|"
     r"\bauthoring tools?\b|\bmachine-readable\b|"
     r"\bmultiple (?:software )?platforms?\b|\bregional standards?\b",
     "move:tool_interop_frame"),
]
_CONTENT_MOVE_MIN_HITS = 2

# A gyűrű melysege ugyanaz, mint a masik kettonel — ld. `_OPENING_ECHO_RING_SIZE`
# indoklasa: kulonbozo melysegű gyűrűk egymas ellen dolgoznak.
_recent_content_moves: deque = deque(maxlen=_OPENING_RING_SIZE)

# Az a strategia, aminek a kereskedelmi keretezes a SAJAT direktivaja („Translate
# the technical issue into its business consequence"). Ott a mozdulat utasitas, nem
# visszhang — ugyanaz a szerzodes, mint a `shape_frame`-nel: az utasitas erosebb.
_MOVE_EXEMPT_STRATEGY = {"move:commercial_frame": "business_impact"}

# EGYSZERI KEGYELEM, NEM OROK MENTESSEG (2026-08-11, v22).
#
# A MERT HIBA: a kivetel EDDIG a mozdulat MINDEN elofordulasat kivette a gyűrűből,
# tehat a `business_impact` sosem bukhatott kereskedelmi visszhangon — akkor sem,
# ha az azt megelozo NEGY komment mindegyike kereskedelmi keretben zart. Merve: a
# gyűrűben harom `move:commercial_frame` mellett a `business_impact`-nak atadott
# gyűrű URES volt. Vagyis amig ez a strategia nyer, a monokultura korlatlanul
# futhat, es a kapu visszakapcsolasa sem valtoztatna rajta semmit.
#
# A KIVETEL EREDETI INDOKA HELYES, ezert nem toroljuk: a strategia direktivaja
# EPPEN a kereskedelmi keretezest keri, tehat az ELSO ilyen komment nem visszhang,
# hanem utasitas-kovetes. Amit javitunk, az a MERTEK: egy sajat-mozdulat kiesik
# (a kegyelem), a TOBBI szamit. Igy a szerzodes valtozatlan marad — „az utasitas
# erosebb, mint a visszhang-tilalom" —, de csak EGYSZER, nem vegtelenszer.
#
# Kovetkezmeny a gyakorlatban (gyűrű-melyseg 4): a `business_impact` akkor bukik,
# ha a legutobbi kommentek kozott MAR LEGALABB KETTO kereskedelmi volt. Egy
# elozmeny meg valtozatossag, ketto mar sorozat.
_MOVE_EXEMPT_GRACE = 1


def content_move(comment: str) -> str:
    """A komment tartalmi mozdulata, vagy "" ha egyik ismert csaladba sem esik."""
    low = (comment or "").lower()
    for pattern, name in _CONTENT_MOVES:
        if len(set(m.group(0).lower() for m in re.finditer(pattern, low))) \
                >= _CONTENT_MOVE_MIN_HITS:
            return name
    return ""


def remember_content_move(comment: str) -> None:
    """A megvalosult mozdulat a gyűrűbe — CSAK sikeres komment utan."""
    move = content_move(comment)
    if move:
        _recent_content_moves.append(move)


def move_ring_for(strategy: str, extra: list[str] | None = None) -> list[str]:
    """A kapunak atadott mozdulat-gyűrű: a strategia sajat mozdulatabol EGY esik ki.

    A `_MOVE_EXEMPT_GRACE` (1) az egyszeri kegyelem — a strategia sajat direktivaja
    szerinti mozdulat elso elofordulasa nem szamit visszhangnak, a tobbi igen. Ld.
    a konstans melletti indoklast: a kivetel MERTEKE volt hibas, nem a letezese.

    `extra`: tovabbi bejegyzesek (pl. a szerzonkenti gyűrű), amiket a globalis
    gyűrűvel egyutt kell nezni — ld. `_author_content_moves`.
    """
    own = next((m for m, s in _MOVE_EXEMPT_STRATEGY.items() if s == strategy), "")
    combined = list(_recent_content_moves) + list(extra or ())
    if not own:
        return combined
    out, grace = [], _MOVE_EXEMPT_GRACE
    for move in combined:
        if move == own and grace > 0:
            grace -= 1
            continue
        out.append(move)
    return out


# --- Szerzonkenti emlekezet (2026-08-11, engine v21) -------------------------
# A MERT HIANY: a fenti gyűrűk (forma, nyitas-szoveg, mozdulat, strategia)
# GLOBALISAK — minden szerzore egyutt szamolnak. Ha A szerzo posztjara
# `constructive_challenge`-t kap, majd tiz MASIK szerzo kommentje kozbejon, A
# szerzo legkozelebbi posztja ujra kaphat `constructive_challenge`-t, mert a
# globalis gyűrű mar kiuritette A szerzo nyomat — A szerzo szemszogebol ez
# ismetlesnek tunik, akkor is, ha a rendszer egeszben valtozatos volt.
#
# A MEGOLDAS NEM CSERE, HANEM KIEGESZITES: a globalis gyűrűk maradnak (azok
# vedik az OSSZKEP valtozatossagat), es MELLETTUK minden szerzohoz kulon,
# ugyanolyan melysegű gyűrű jar. Egy forma/strategia/mozdulat akkor esik ki,
# ha a globalis VAGY a szerzo-gyűrűben szerepel — a hivo oldalon a ketto
# egyszeruen osszefuzve megy at a mar meglevo `recent`/`extra` parametereken.
# Ismeretlen (nev nelkuli) szerzonel a szerzo-gyűrű ures marad, tehat a
# viselkedes valtozatlan a korabbi (csak globalis) allapothoz.
#
# A melyseg UGYANAZ, mint a megfelelo globalis gyűrűnel — nincs uj magic-
# number, csak egy masik kulcs (szerzo, nem "az egesz folyam") ugyanazon a
# szabalyon.
_author_strategies: defaultdict = defaultdict(lambda: deque(maxlen=_STRATEGY_RING_SIZE))
_author_openings: defaultdict = defaultdict(lambda: deque(maxlen=_OPENING_RING_SIZE))
_author_opening_texts: defaultdict = defaultdict(lambda: deque(maxlen=_OPENING_ECHO_RING_SIZE))
_author_content_moves: defaultdict = defaultdict(lambda: deque(maxlen=_OPENING_RING_SIZE))


def author_key(author_name: str) -> str:
    """A szerzonev kanonikus kulcsa a szerzonkenti gyűrűkhoz.

    Ekezet-fuggetlen, kis- es nagybetűtől fuggetlen, tobbszoros szokoz
    osszevonva — ugyanaz a nev irasvariansai (pl. "Kovács János" vs
    "kovacs janos") ugyanarra a gyűrűre essenek. Ures nev -> ures kulcs, ami
    minden ebbol szarmazo fuggvenyben "nincs szerzonkenti emlekezet"-et jelent.
    """
    folded = _fold_accents((author_name or "").strip().lower())
    return re.sub(r"\s+", " ", folded)


def remember_author_strategy(key: str, slug: str) -> None:
    """A strategia a SZERZO sajat gyűrűjebe — csak sikeres komment utan, mint a globalisnal."""
    if key and slug:
        _author_strategies[key].append(slug)


def remember_author_opening(key: str, shape: str) -> None:
    """A nyitas-forma a SZERZO sajat gyűrűjebe."""
    if key and shape:
        _author_openings[key].append(shape)


def remember_author_opening_text(key: str, comment: str) -> None:
    """A megvalosult nyitas ujjlenyomata a SZERZO sajat gyűrűjebe."""
    if not key:
        return
    fp = opening_fingerprint(comment)
    if fp:
        _author_opening_texts[key].append(fp)


def remember_author_content_move(key: str, comment: str) -> None:
    """A tartalmi mozdulat a SZERZO sajat gyűrűjebe."""
    if not key:
        return
    move = content_move(comment)
    if move:
        _author_content_moves[key].append(move)


# --- A GONDOLAT MONOKULTURAJA A FORRASNAL (2026-08-11, engine v23) -----------
#
# A MERES, ami ezt kikenyszeritette: a naploban 13 kereskedelmi keretű kommentbol
# TIZENKETTONEL mar az `insight` tartalmazta a keret szavait (contracts,
# incentive, liability, compensated) — vagyis a dontes a REASON lepesben mar
# megszuletett, es a COMPOSE csak prozába ontotte. Ez megmagyarazza, miert
# talalta a v14-es meres, hogy a kimeneti kapu „detektal, de nem gyogyit": minden
# ujrairo kor UGYANABBOL a kereskedelmi insightbol vezet le kereskedelmi prozat.
# Egy kimeneti kapu itt elvileg sem tud gyogyitani.
#
# MIERT AZ `insight` ES NEM A `thesis_condition`: a `condition_family` gyűrű mar
# orzi a feltetelt, de ket okbol nem eleg. (a) A mert keret az `insight`-ba szall
# be, amire EDDIG SEMMILYEN vedelem nem volt. (b) A feltetel-gyűrű csak akkor
# bővul, ha a kihivas-szenzor ELSULT — merve: 13 kommentbol HATNAL nem a szenzor,
# hanem a pontszam valasztotta a strategiat, tehat ott a feltetel-ellenorzes le
# sem futott. Az `insight` viszont MINDEN uton keletkezik.
#
# MIERT NEM ONERTEKELES: a modell nem a sajat munkajat osztalyozza (azt a projekt
# joggal vezette ki az Authenticity-rubrikaval). TENYALLAPOTOT kap, amit magatol
# nem tudhat: hogy a legutobbi kommentek melyik keretben zartak. Ugyanaz a
# szerzodes, mint a kiosztott nyitas-formanal es a hossz-savnal — a kod dont, a
# modell azt kapja meg, amit tudnia kell.
#
# MIERT A USER-UZENETBEN es nem a system-promptban: a system-prompt hivasok kozott
# AZONOS (gyorsitotarazhato), a gyűrű-allapot pedig hivasonkent valtozik. Ures
# gyűrű eseten a blokk el sem kerul bele, tehat a REASON-hivas bajtra a v22-es.
#
# SZANDEKOS SZUKITES: itt egyelore CSAK globalis gyűrű van, szerzonkenti par nincs
# (szemben a v21-es strategia/nyitas/mozdulat harmassal). A projekt normaja szerint
# eloszor MERNI kell: ha 10-15 sor utan a globalis steer nem nyitja szet a
# keret-eloszlast, akkor a szerzonkenti par sem fog — ha viszont igen, akkor az a
# kovetkezo lepes, nem elore beepitett komplexitas.
_MOVE_LABELS = {
    "move:commercial_frame": "the commercial/contractual angle (contracts, "
                             "incentives, fees, liability, procurement)",
    "move:tool_interop_frame": "the tool-interoperability angle (a shared CDE, "
                               "BIM execution plan, coordinate systems, "
                               "multiple authoring platforms)",
}

_recent_insight_families: deque = deque(maxlen=_OPENING_RING_SIZE)


def insight_family(insight: str) -> str:
    """Az `insight` keretenek csaladja, vagy "" ha egyik ismert csaladba sem esik.

    A `condition_family`-t hasznalja, mert a BEMENET ALAKJA ugyanaz: egy-ket
    tagmondat, ahol mar az ELSO keret-terminus a lenyeg (ezert 1 talalat a kuszob,
    nem 2, mint a 100+ szavas kommentnel). Egy kulon, azonos torzsű fuggveny csak
    drift-hazard lenne.
    """
    return condition_family(insight)


def remember_insight_family(insight: str) -> None:
    """A MEGVALOSULT insight csaladja a gyűrűbe — csak sikeres komment utan."""
    family = insight_family(insight)
    if family:
        _recent_insight_families.append(family)


def insight_steer_block(recent: list[str] | None) -> str:
    """A REASON user-uzenethez fűzott elterito blokk, vagy "" ha nincs mit kerulni.

    Ures/None gyűrű eseten SZANDEKOSAN ures stringet ad: igy a hivas bajtra a
    korabbi, es a mechanizmus tiszta A/B-kent merheto.
    """
    seen = [f for f in dict.fromkeys(recent or ()) if f in _MOVE_LABELS]
    if not seen:
        return ""
    lines = "\n".join(f"  - {_MOVE_LABELS[f]}" for f in seen)
    return (
        "\n\nFRAMES ALREADY USED BY THE LAST FEW COMMENTS IN THIS STREAM:\n"
        f"{lines}\n"
        "These are not wrong, and this post may genuinely invite one of them — but "
        "they have just been used, and a reader who sees several of your comments "
        "in a row would hear one voice. For `insight` and `thesis_condition`, build "
        "on a DIFFERENT kind of fact this time: the artefact, the model element, the "
        "project phase, the discipline handover, the software behaviour, the person "
        "who ends up doing the work. Only fall back on a frame listed above if the "
        "post leaves you no honest alternative."
    )


def insight_frame_steer_enabled(config: dict) -> bool:
    """`linkedin.insight_frame_steer`: on (kod-default) | off. YAML-boolean (§4/17).

    Kikapcsolva a REASON-hivas BAJTRA a v22-es, tehat a steer A/B-zheto ugyanezen
    a kodon — mint az `intent_layer`-nel es a `length_scaling`-nal.
    """
    raw = (config.get("linkedin", {}) or {}).get("insight_frame_steer", "on")
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() not in ("off", "false", "0", "no", "none")


def content_echo_gate_enabled(config: dict) -> bool:
    """`linkedin.content_echo_gate`: on (kod-default) | off. YAML-boolean (§4/17).

    A MERES VERDIKTJE: a config 'off'-ra allitja, mert ot eles futasban a kapu
    DETEKTALT, de NEM GYOGYITOTT — harom elsules, ketto sertessel kiment, es
    egyetlen komment sem hagyta el a kereskedelmi keretet. A valodi ok feljebb van:
    ot `thesis_condition`-bol ot szerzodesi jellegű volt, tehat a monokultura a
    REASON lepesben keletkezik. A `content_move` MERESE kapcsolo nelkul is fut —
    csak a kapuzas all le. Reszletes indoklas: `config.yaml`, `content_echo_gate`.
    """
    raw = (config.get("linkedin", {}) or {}).get("content_echo_gate", "on")
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() not in ("off", "false", "0", "no", "none")


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
#
# RAGOZAS (2026-08-10): a lista eredetileg csak a SZOTARI ALAKOT kereste, a modell
# viszont ragozva hasznalja ugyanazt a szot. A 2026-08-10-i benchmarkon mérve:
# "standardizing" NEM egyezett a `standardi[sz]ation`-nel, "consistent" NEM
# egyezett a `consistency`-vel, tehat a komment a teljes framework-szokincset
# hasznalta, a kapu meg ures listat adott. A tovek most a kepzett alakokat is
# fedik. A `\b`-hatarok maradnak: a reszszo-egyezes (pl. "inconsistent") nem cel.
_AI_FINGERPRINT_PATTERNS: list[tuple[str, str]] = [
    (r"\boperational(?:ly)? efficien(?:cy|t)\b", "operational efficiency"),
    (r"\bstructured process(?:es)?\b", "structured process"),
    (r"\bgovern(?:ance|ing)\b", "governance"),
    (r"\bstandardi[sz](?:ation|ations|ing|e|es|ed)\b", "standardisation"),
    (r"\bconsisten(?:cy|cies|t|tly)\b", "consistency"),
    (r"\benterprise(?:-wide)? adoption\b", "enterprise adoption"),
    (r"\bstakeholders? align(?:ment|ed)\b", "stakeholder alignment"),
    (r"\bframeworks?\b", "framework"),
    # 2026-08-10, a NEGYEDIK eles futasbol. Mindketto ide kerul es nem a
    # `_MARKETING_CLICHE_PATTERNS`-be, mert LEHET legitim hasznalatuk ("a mapping
    # eleg robusztus, hogy tulelje az ujraepitest"), es a relativizalas + a
    # legalabb-ketto kuszob pont ezt a hataresetet kezeli: ha a SZERZO hasznalta,
    # nem szamol, es egyetlen elofordulas sem indit ujrairast.
    #
    # A "robust" onkritikus tetel: a 2026-08-10-i elso ertekelesemben a kulso spec
    # lexikai tiltolistajat "2019-es AI-jelekkent" intéztem el, es strukturalis
    # tellekre tereltem a figyelmet. A szo ezutan ELES kimenetben jelent meg
    # ("robust BIM tools"), es egyetlen kapu sem fogta. A strukturalis tellek
    # valosak — de a lexikai listat tul konnyen irtam le.
    (r"\brobust(?:ly|ness)?\b", "robust"),
    (r"\bleverag(?:e|es|ed|ing)\b", "leverage"),
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
# RAGOZAS/SZAM (2026-08-10): ugyanaz az audit, mint az `_AI_FINGERPRINT_PATTERNS`-nel
# — a tobbes szam es a kepzett alakok korabban kicsusztak ("competitive advantages",
# "business cases"). A precizio-elv VALTOZATLAN: ide csak olyan kifejezes kerul,
# ami technikai kommentben nem fordul elo artatlanul.
_EXEC_ABSTRACTION_PATTERNS: list[tuple[str, str]] = [
    (r"\broi\b", "ROI"),
    (r"\breturn on investment\b", "ROI"),
    (r"\bmegter(?:ules|ülés)\b", "ROI (HU)"),
    (r"\bcompetitive advantages?\b", "versenyelony-keretezes"),
    (r"\bversenyelony\b|\bversenyelőny\b", "versenyelony-keretezes (HU)"),
    (r"\bprofitabilit(?:y|ies)\b", "jovedelmezoseg-keretezes"),
    (r"\bjovedelmezoseg\b|\bjövedelmezőség\b", "jovedelmezoseg-keretezes (HU)"),
    (r"\borgani[sz]ational transformations?\b", "szervezeti transzformacio"),
    (r"\bszervezeti (?:atalakulas|átalakulás|transzformacio|transzformáció)\b",
     "szervezeti transzformacio (HU)"),
    (r"\bdigital transformations?\b", "digitalis transzformacio"),
    (r"\bdigit(?:alis|ális) transzform(?:acio|áció)\b", "digitalis transzformacio (HU)"),
    (r"\btotal cost of ownership\b|\btco\b", "TCO"),
    (r"\bbusiness cases?\b", "business case"),
    (r"\bbottom line\b", "bottom line"),
    (r"\bstakeholder value\b|\bshareholder value\b", "stakeholder value"),
    (r"\bbusiness value\b", "business value"),
    (r"\buzleti ertek\b|\büzleti érték\b", "business value (HU)"),
    (r"\bc-level\b|\bexecutive buy-?in\b", "executive framing"),
    (r"\bbottom-?line impact\b", "bottom line"),
]

# --- Stage 9d: marketing-klise (2026-08-10) ---------------------------------
# A 2026-08-10-i benchmarkon a komment ATVETTE a hirdetes regiszteret: "can truly
# unlock its full potential". Ez a fordulat egyik meglevo listan sem volt.
#
# MIERT KULON LISTA es miert FELTETEL NELKUL mer: az `_AI_FINGERPRINT_PATTERNS`
# szerzohoz relativizalt es csak technikai/emberkozpontu beszelgetesben, legalabb
# KETTO talalatnal indit — a mert eset viszont `management` sikon volt, tehat ott
# semmi nem fogta volna meg. Egy marketing-klise ellenben SEMMILYEN sikon nem jo
# irás egy gyakorlo szakember kommentjeben, ezert ez a lista a
# `_FORBIDDEN_PATTERNS`-hez hasonloan mindig mer.
#
# SZUK ES VEDHETO: csak olyan fordulat, ami tiszta toltelék. A legitim BIM-zsargon
# (pl. "single source of truth", "pipeline", "architecture") SZANDEKOSAN kimarad —
# ugyanaz az elv, amiert az "architecture" sem kerult kemeny tiltolistara.
_MARKETING_CLICHE_PATTERNS: list[tuple[str, str]] = [
    # 2026-08-10: az eredeti minta `unlock`-ot kovetelt ele, es a mert komment igy
    # atment: "the full potential for risk mitigation can remain untapped". A puszta
    # "full potential" onmagaban is toltelék — nincs olyan gyakorlo-komment, ami
    # nyerne vele —, ezert az `unlock` mar nem feltetel.
    (r"\bfull potential\b", "full potential"),
    (r"\b(?:take|takes|taking) (?:it|this|things) to the next level\b", "next level"),
    (r"\bgame[- ]chang(?:er|ing)\b", "game-changer"),
    (r"\brevolutioni[sz](?:e|es|ing|ed)\b", "revolutionize"),
    (r"\bseamless(?:ly)? integrat(?:e|es|ing|ed|ion)\b", "seamless integration"),
    (r"\bbest[- ]in[- ]class\b", "best-in-class"),
    (r"\bcutting[- ]edge\b", "cutting-edge"),
    (r"\bleverag(?:e|es|ing) the (?:full )?power of\b", "leverage the power of"),
    (r"\bempower(?:s|ing)? (?:teams|organi[sz]ations|users)\b", "empower teams"),
    (r"\bteljes potencial(?:t|ját|jat)\b", "unlock full potential (HU)"),
    (r"\bforradalmasit(?:ja|ani)\b|\bforradalmasít(?:ja|ani)\b", "revolutionize (HU)"),
]

# --- Stage 9e: tanacsadoi hang, EGESZ kommentre (2026-08-11, engine v10) ------
# A MERES, ami ezt kikenyszeritette: a "We (often) see/found" szerkezet a 32 kiadott
# kommentbol TIZBEN benne volt (31%) — messze a leggyakoribb tell a korpuszban:
#   "We've often found" 5x | "We often see" 4x (ebbol 2 a 3. MONDATBAN) | "We often rebuild" 1x
#
# MIERT NEM A NYITAS-ABLAK SZELESITESE: a `_STOCK_OPENING_PATTERNS` ket mondatot
# mer, es ez SZANDEKOS — a 2026-08-10-i dontes kimondta, hogy egy sablonos fordulat
# a 8. mondatban nem NYITASI hiba, ott a cimke felrevezeto lenne. A megfigyelt
# viselkedes viszont pont az volt, hogy a frazis KIHATRALT az ablakbol: a v9 ket
# kommentjeben a 3. mondatban all, ahol semmi nem fogta. A szotar volt hianyos, nem
# az ablak szűk: ez a szerkezet SEM az `_AI_FINGERPRINT_PATTERNS`-ben, SEM a
# `_MARKETING_CLICHE_PATTERNS`-ben nem volt.
#
# MIERT FELTETEL NELKUL MER: ugyanaz az érv, mint a marketing-klisenel. A tanacsadoi
# altalanositas ("mi gyakran azt latjuk...") nem szint-fuggo hiba — egy gyakorlo
# szakember kommentjeben semmilyen sikon nem jo iras, mert megnevezetlen tapasztalatra
# hivatkozik konkretum helyett. A szerzohoz relativizalas (`ai_fingerprint_terms`
# mintaja) itt ezert nem kell: ez retorikai allas, nem szakszo, amit a szerzo
# "engedelyezhetne".
#
# SZUK ES VEDHETO — ami SZANDEKOSAN KIMARAD:
#   - "One pattern I've noticed" (4 talalat): ez a SAJAT katalogusunk `pattern`
#     formája (`OPENING_SHAPES`). Tiltolistara tenni ugyanaz az onellentmondas
#     lenne, amit a G1 teszt orz — az ismetlest a nyitas-visszhang kapu kezeli.
#   - "the real work / challenge / hit / advantage" (8 talalat): NEM kerul be, pedig
#     a szamok alapjan indokolt lehetne. A v7-es A/B-ben eppen egy ilyen mondat volt
#     az elso vagas nelkul kiposztolhato komment magja ("the real hit is often
#     downstream"). Ez TARTALMI szerkezet, nem tic; a lezaras ismetlodese cross-
#     komment jelenseg, tehat ha kell, a visszhang-kapuhoz hasonlo mechanizmus a
#     helyes valasz, nem szotar.
#   - "in practice" / "in our experience": az elso mar a nyitas-listan van, a
#     masodikra NULLA talalat — meres nelkul nem veszunk fel semmit.
_CONSULTANT_VOICE_PATTERNS: list[tuple[str, str]] = [
    # A mert alak es minden ragozott valtozata. A `we've/we have` azert van benne,
    # mert a tiz talalatbol OT eppen ez volt ("We've often found"), negy a
    # "We often see", egy a "We often rebuild" — egyetlen minta fogja mind a harmat.
    (r"\bwe(?:'ve| have)? (?:often|frequently|commonly|typically|usually|routinely|"
     r"generally) (?:see|seen|find|found|observe|observed|notice|noticed|encounter|"
     r"encountered|run into|rebuild)\b", "tanacsadoi hang (We often see/found)"),
    # Az ELSO SZEMELYU valtozat NEM volt a mert adatban. Megis bekerul, mert a
    # pronomen-csere a legkezenfekvobb kijatszas ugyanarra a szerkezetre — ugyanaz
    # a teljesseg-erv, ami a 2026-08-10-i szotar-ragozas javitasa mogott allt
    # (`standardizing` != `standardi[sz]ation`). NEM utkozik az `own_practice`
    # formával ("I've found..."): ott nincs altalanosito hatarozo a ket szo kozott.
    (r"\bi(?:'ve| have)? (?:often|frequently|commonly|typically|usually|routinely|"
     r"generally) (?:see|seen|find|found|observe|observed|notice|noticed|encounter|"
     r"encountered|run into)\b", "tanacsadoi hang (I often find)"),
    # A magyar megfelelo: egyetlen mert eset (a magyar `--force` futas 2. mondata),
    # de szo szerint ugyanaz a mozdulat. A "gyakorlatban" ONMAGABAN legitim
    # ("a gyakorlatban ez 10 mm"), ezert a minta megkoveteli a tapasztalat-igét.
    (r"\ba gyakorlatban azt tapasztal(?:juk|om|tuk|tam)\b",
     "tanacsadoi hang (HU: a gyakorlatban azt tapasztaljuk)"),
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

# --- Hossz: a POSZTHOZ skalazott cel-sav (2026-08-10, v7) --------------------
# A MERT HIBA. Nyolc eles generalas adata:
#
#   poszt szo   komment szo   arany
#      101         82-97      0.81-0.96x
#      254        110-117     0.43-0.46x
#       53        102-116     1.92-2.19x   <- a poszt KETSZERESE
#
# A motor ~100 szot irt, BARMI is volt a bemenet (82-117 mind a nyolc esetben). Egy
# eles, ketmondatos megfigyelesre dupla hosszan valaszolni szerkezetileg is resze
# annak, amiert tomottnek erezzuk: a hossz IS regiszter, es a regisztert illeszteni
# kell — ugyanaz az elv, ami a nyelv es a `human_temperature` mogott all.
#
# MIERT NEM A `MIN_WORDS` VOLT A PROBLEMA (a felulvizsgalat eredmenye): a 60-as
# padlo SOHA nem kotott — nulla "tul rovid" sertes nyolc generalasbol, a legrovidebb
# komment 82 szo. A hosszt a PROMPT szabalyozta ("80-150 words"), nem a kapu. A padlo
# leengedese ezert onmagaban semmit nem valtoztatott volna: a ketto csak EGYUTT hat.
# (A `MAX_WORDS = 175`-nek van dokumentalt csonkolas-tortenete; a `MIN_WORDS = 60`
# viszont kommentar nelkuli, soha nem indokolt szam volt.)
LENGTH_TARGET_FLOOR = 55        # ez ala nem megyunk, barmilyen rovid a poszt
LENGTH_TARGET_CEILING = 120     # egy LinkedIn-komment ne legyen 250 szo
LENGTH_BAND_SPREAD = 0.25       # a cel korul +/- ennyi a sav

# CSILLAPITAS (2026-08-10, masodik iteracio): a padlo FELETTI resz csak feleresben
# szamit, tehat egy hosszabb poszt nem "erdemel ki" aranyosan hosszabb kommentet.
#
# MIERT: a tukrozes elso valtozata csak a ROVID posztok esetet oldotta meg. Mert
# adat harom savszelessegen:
#     poszt  53, sav 40-70  -> komment 51, abstract 0
#     poszt 108, sav 80-135 -> komment 95, abstract 5
#     poszt 254, fix 80-150 -> komment 110-117, abstract 11-13
# Az irany egyertelmu: MINEL TOBB a hely, ANNYIVAL tobb a toltelék. A 108 szavas
# poszton a 95 szavas komment utolso mondata mar homalyos volt ("more rigorous
# visual audits ... adds a layer of complexity"), tehat a sav felso vege toltelekre
# ment el.
#
# EGY parametert valtoztatok, nem harmat: n=1-2 meres savkonfiguraciónkent, es
# vegig azt tanacsoltam, hogy igazolatlan szamokra ne epitsunk. A csillapitas a
# legvedhetobb valtozat, mert a MERT irany (a jo arany a rovid poszton 0.96 volt, a
# gyengebb a hosszabbon 0.86, es ott a plusz szavak toltelekek voltak) pont azt
# mondja, hogy az aranynak CSOKKENNIE kell a poszt hosszaval.
LENGTH_DAMPING = 0.5


def target_length(post_text: str) -> tuple[int, int]:
    """(min, max) cel-szohossz a POSZT hosszabol. A kod dontese, nem a modelle.

    A szabaly: tukrozd a posztot, de a padlo feletti reszt CSILLAPITVA, es vagd le
    mindket vegen. Igy:

        poszt  53 szo -> 40-70    (a padlon)
        poszt 108 szo -> 60-100   (elotte 80-135)
        poszt 254 szo -> 90-150   (a plafonon)

    A plafont igy csak ~185 szavas poszt fole eri el a cel, tehat a valos
    LinkedIn-poszt-hosszak tobbsegen a csillapitas tenylegesen hat.

    A visszaadott sav INVARIANSA (teszt rogziti): a minimuma sosem esik a
    `MIN_WORDS` ala, a maximuma sosem no a `MAX_WORDS` fole — kulonben a prompt es a
    kapu egymassal harcolna, es minden komment ujrairast kapna.
    """
    n = len(_words(post_text))
    damped = LENGTH_TARGET_FLOOR + LENGTH_DAMPING * (n - LENGTH_TARGET_FLOOR)
    target = max(LENGTH_TARGET_FLOOR, min(LENGTH_TARGET_CEILING, damped))
    lo = int(round(target * (1 - LENGTH_BAND_SPREAD) / 5) * 5)
    hi = int(round(target * (1 + LENGTH_BAND_SPREAD) / 5) * 5)
    return lo, hi


# 60 -> 35 (2026-08-10): a padlo mostantol a LEGKISEBB lehetseges cel-sav (40) ALATT
# all, tehat nem harcol a prompttal, de tovabbra is kifogja az elfajzott egysorost
# es a felig ures valaszt. A 60 azert volt karos, mert egy jogosan rovid valaszt
# (az otodik meresnel a jo verzio ~45 szo lett volna) TOMESRE kenyszeritett.
# --- Ujrairo korok (2026-08-11, engine v14) ----------------------------------
# A MERT HIBA: negy komment SERTESSEL ment ki (28., 38., 49., 50. sor). A ciklus
# `range(2)` volt, tehat ket elutasitas utan a motor visszaadta a kommentet — es a
# mert mintazat mindig ugyanaz: az 1. kor "We often see"-re bukott, a 2. kor pedig
# UGYANANNAK a mozdulatnak mas alakjat hozta ("I often find"). A modell valtozatot
# cserelt, nem viselkedest.
#
# MIERT NEM EGYSZERUEN range(3): egy harmadik hivas MINDEN makacs esetben fizetne,
# akkor is, ahol a maradek sertes nem szoválasztas kerdese (pl. "tul rovid", vagy
# uzleti absztrakcio technikai beszelgetesben — ott a modellnek MAS gondolatot kell
# talalnia, nem mas szot). A harmadik kor ezert CSAK az ismetles-osztalyra jar: ott
# a javitas biztosan lehetseges, mert csak a megfogalmazast kell cserelni.
#
# A negy mert eset MINDEGYIKE ebbe az osztalyba esett.
MAX_COMPOSE_ATTEMPTS = 3

# A cimke-prefixek, amiket egy ujrafogalmazas biztosan meg tud oldani: mind a HOGYAN
# fogalmazunk, nem a MIT mondunk. A tobbi sertes (hossz, absztrakcio-szivargas,
# kep-hivatkozas, poszt-atfedes) tartalmi valtozast kiván, arra nem jar plusz kor.
# A `dicsero nyitas` (v24) ITT IS es a `_BLOCKING_PREFIXES`-ben IS szerepel —
# ugyanaz a par, mint a `tanacsadoi nyitas`-nal: kiadhatatlan, DE puszta
# szocserevel javithato, tehat jar ra a harmadik kor. A ketto nelkul a motor egy
# trivialisan javithato nyitason egyetlen ujrairas utan kemeny bukasra futna.
_REPHRASABLE_PREFIXES = ("ismetlodo nyitas", "tanacsadoi nyitas", "tanacsadoi hang",
                         "dicsero nyitas")


def only_rephrasable(issues: list[str]) -> bool:
    """Kizarolag ujrafogalmazassal javithato sertesek? (ures lista: nem)"""
    return bool(issues) and all(
        any(i.startswith(p) for p in _REPHRASABLE_PREFIXES) for i in issues)


# --- KIADHATATLAN sertesek (2026-08-11, engine v22) --------------------------
# A MERT HIBA (naplo, post_id eb39ea74446b980f): a kapu elkapta a „We often see"
# tanacsadoi hangot, a motor HAROMSZOR ujrairta, mind a harom kor ugyanazt adta
# vissza — es a hurok ezutan a MEG MINDIG SERTO szoveget adta ki sikerkent. A
# `quality_issues` ott volt a valaszban, de a hivo (`ui/app.py`) csak az `error`
# kulcsot vizsgalja, tehat a sertes lathatatlanul kiment.
#
# EZ NEM ugyanaz a halmaz, mint a `_REPHRASABLE_PREFIXES`, es a ketto SZANDEKOSAN
# atfed (`tanacsadoi hang` mindkettoben szerepel): a rephrasable azt mondja meg,
# JAR-E ra plusz kor (ujrafogalmazassal javithato-e), ez pedig azt, hogy ha a
# korok elfogytak, KIADHATO-E. Egy sertes lehet egyszerre „erdemes ujra probalni"
# es „de sose menjen ki igy".
#
# A VONAL: ide az kerul, ami a kommentet nyilvanosan vallalhatatlanna vagy
# tenyszeruen hamissa teszi — nem az, ami csak meresi/fokozati kerdes. A hossz, a
# bekezdes-szam es a sorozat-szintű ismetles ezert NEM blokkol: egy 33 szavas vagy
# a legutobbihoz hasonloan kezdodo komment nem szegyen, egy „Great post!" nyitas,
# egy emoji, egy nem letezo kepre hivatkozas vagy egy engedely nelkuli
# markaemlites viszont az.
_BLOCKING_PREFIXES = (
    "tiltott fordulat",          # explicit tiltolista (egyetertes/dicseret)
    "dicsero nyitas",            # v24: a szerkezeti dicseret-alak (`_PRAISE_OPENING_PATTERNS`)
    "tanacsadoi hang",           # a MERT eset: „We often see/found"
    "tanacsadoi nyitas",
    "marketing-klise",
    "AI-ujjlenyomat",
    "gondolatjel angol kommentben",   # a kod maga „AI-jel"-nek nevezi
    "angol frazis nem-angol kommentben",  # fel-forditott mondat = gep-iras
    "a komment a kepre hivatkozik",   # ellenorizhetetlen/hamis allitas
    "markaemlites, holott nincs engedelyezve",
    "emoji",
    "hashtag",
    "felkialtojel",
)


def blocking_issues(issues: list[str]) -> list[str]:
    """Azok a sertesek, amikkel a komment NEM adhato ki (ld. `_BLOCKING_PREFIXES`)."""
    return [i for i in (issues or [])
            if any(i.startswith(p) for p in _BLOCKING_PREFIXES)]


MIN_WORDS = 35
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


# --- F2: konkretsag-diagnosztika (2026-08-10) --------------------------------
# A MERT HIBA: a 2026-08-10-i benchmark kommentje "subtle variations in how they
# classify issues, assign ownership, or define RFI types"-ot irt — ez KATEGORIA,
# nem ESET. Egy gyakorlo szakember azt irja: "az egyik csapat clashkent naplozza,
# a masik ugyanazt RFI-kent". A REASON-prompt kert konkretsagot ("no generalities"),
# de SEMMI nem merte, es az authenticity-rubrika minden tengelyen 2/2-t adott —
# nincs olyan tengelye, ami a homalyossagot latna.
#
# MIERT NINCS BELOLE KAPU, ES MIERT NINCS OSSZPONTSZAM
# Az authenticity-rubrika tanulsaga (03-composer-spec, nyitott kerdes): egy
# igazolatlan mérőszamra kapuzni annyi, mint ugy viselkedni, mintha tudnank valamit.
# Ezert ez a harom szam CSAK a valaszban es a naploban jelenik meg, a dontest nem
# befolyasolja. Osszpontszam SZANDEKOSAN nincs: egy kompozit szam azt sugallna, hogy
# a sulyozas mar validalt. A harom komponenst kulon kell a benchmark-pontokkal
# rangkorrelaltatni — az egyben megmutatja, MELYIK komponens jelez egyaltalan.
#
# Ha egyik sem korrelal, ez a blokk torolheto (nulla LLM-koltseg: tiszta regex).

# Amit egy gyakorlo szakember MEGNEVEZ: formatum, eszkoz, artefaktum, diszciplina,
# fazis. A lista nem teljes es nem is kell annak lennie — a HIANYA a jel.
_CONCRETE_ANCHORS = [
    # formatumok / adatcsere
    "ifc", "ifc2x3", "ifc4", "bcf", "cobie", "gbxml", "dwg", "dxf", "rvt", "pln",
    "nwd", "nwc", "ifczip", "landxml",
    # eszkozok
    "revit", "archicad", "navisworks", "solibri", "speckle", "grasshopper",
    "dynamo", "rhino", "tekla", "bonsai", "ifcopenshell", "bimcollab", "revizto",
    "aconex", "civil 3d", "vectorworks", "allplan",
    # modell-artefaktumok
    "family", "families", "shared parameter", "parameter", "guid", "workset",
    "worksets", "worksharing", "schedule", "view template", "wall type",
    "floor type", "property set", "pset", "ifc class", "classification",
    "mapping table", "central model", "linked model", "type catalog",
    "keynote", "level", "grid", "revision", "sheet",
    # koordinacio-artefaktumok
    "clash", "clashes", "rfi", "rfis", "snag", "snagging", "markup",
    # diszciplinak
    "mep", "structural", "architectural", "facade", "façade", "hvac",
    "electrical", "plumbing", "ductwork", "rebar", "precast", "curtain wall",
    # fazisok
    "handover", "tender", "as-built", "commissioning", "lod", "loi",
    "riba stage", "coordination meeting", "site survey",
    # 2026-08-10: a hianyzo tetelek, amiket az eles posztok sajat szokincse mutatott
    # meg. Mindegyik MEGNEVEZHETO artefaktum, eszkoz vagy metrika — pont az, amit egy
    # gyakorlo ember kimond. A hianyuk ALULSZAMOLT, tehat a kesobbi korrelaciot is
    # rontotta volna.
    # SZANDEKOSAN KIMARAD a "naming convention": az egyik mert komment eppen
    # consultant-nyelvkent hasznalta ("establishing strict naming conventions"),
    # tehat horgonynak venni azt a kommentet JUTALMAZTA volna.
    # Az atfedes elkerulve: "takeoff" (nem "quantity takeoff") es "execution plan"
    # (nem "bim execution plan") — kulonben egy fogalom ket horgonynak szamolna.
    "execution plan", "bep", "4d", "5d", "6d", "takeoff", "qa/qc",
    "scan-to-bim", "lidar", "point cloud", "spi", "cpi", "power bi", "drone",
    # HU
    "atadas", "átadás", "kivitelezes", "kivitelezés", "tenderezes", "tenderezés",
    "szerkezeti", "gepeszet", "gépészet", "homlokzat", "vasalas", "vasalás",
]

# Absztrakt fonevek: nem tiltottak, de a SURUSEGUK a homalyossag proxyja. A poszthoz
# NEM relativizaljuk: ha a poszt absztrakt, a komment dolga akkor is a konkretsag.
_ABSTRACT_TERMS = [
    "coordination", "communication", "collaboration", "alignment", "process",
    "processes", "workflow", "workflows", "efficiency", "quality", "transparency",
    "visibility", "consistency", "standardisation", "standardization", "governance",
    "strategy", "culture", "mindset", "ecosystem", "framework", "synergy",
    "potential", "complexity", "challenge", "challenges", "solution", "solutions",
    "approach", "insight", "insights", "stakeholder", "stakeholders", "adoption",
    "maturity", "transformation", "silo", "silos", "protocol", "protocols",
    "schema", "consensus", "interpretation", "platform", "capability",
    "capabilities", "best practice", "value proposition",
    # HU
    "koordinacio", "koordináció", "kommunikacio", "kommunikáció", "folyamat",
    "hatekonysag", "hatékonyság", "atlathatosag", "átláthatóság", "szemlelet",
    "szemlélet", "megkozelites", "megközelítés", "kihivas", "kihívás",
]

# Bizonytalanito nyelv. A mert kommentben harom "often" volt 97 szoban — aki
# konkret allitast tesz, nem hedge-el haromszor.
_HEDGE_TERMS = [
    "often", "frequently", "sometimes", "usually", "typically", "generally",
    "many", "some", "several", "various", "certain", "subtle", "a bit",
    "somewhat", "tend to", "tends to", "can be", "may be", "might be",
    "in some cases", "more or less", "relatively",
    # HU
    "gyakran", "neha", "néha", "tobbnyire", "többnyire", "altalaban", "általában",
    "nemileg", "némileg", "olykor", "bizonyos",
]


def _term_regex(term: str) -> str:
    """Szo-hataros minta egy (akar tobbszavas) kifejezesre, rugalmas szokozzel.

    Az UTOLSO szo tobbes szama is egyezik. Enelkul a mero rendszeresen ALULSZAMOL:
    a 2026-08-10-i eles futasban a komment "property sets"-et irt, a lista pedig
    "property set"-et keresett — a `set\\b` a "sets"-ben nem hatar, tehat a horgony
    elveszett, es a mero 0 hozott horgonyt jelentett egy olyan kommentre, ami
    tenylegesen megnevezett egyet. Egy alulszamolo diagnosztika a kesobbi
    korrelaciot rontja el, ezert ez itt nem kozmetika.
    """
    parts = term.split()
    head = [re.escape(p) for p in parts[:-1]]
    last = re.escape(parts[-1]) + r"(?:e?s)?"
    return r"\b" + r"\s+".join([*head, last]) + r"\b"


def _found_terms(terms: list[str], text: str) -> list[str]:
    low = (text or "").lower()
    return [t for t in terms if re.search(_term_regex(t), low, re.IGNORECASE)]


def _anchor_key(term: str) -> str:
    """Egyes/tobbes szam osszevonasa a poszthoz valo relativizalashoz.

    Enelkul hamis pozitiv keletkezik: a poszt "RFIs"-t ir, a komment "RFI"-t —
    ket kulon listaelem, tehat az `rfi` "hozott" horgonynak szamitott volna,
    holott a szerzo mar kimondta. A tobbes-s levagasa erre eleg; nem cel altalanos
    stemmelés (a "clashes"/"clash" es a "families"/"family" is a listan van
    kulon-kulon, tehat a kulcsuk igy egybeesik).
    """
    t = term.rstrip()
    if t.endswith("ies") and len(t) > 4:
        return t[:-3] + "y"
    if t.endswith("es") and len(t) > 3:
        return t[:-2]
    if t.endswith("s") and len(t) > 2:
        return t[:-1]
    return t


def concreteness(comment: str, post_text: str) -> dict:
    """Harom fuggetlen homalyossag-proxy. DIAGNOSZTIKA — a kapu nem hasznalja.

    anchors_added  — a komment altal HOZOTT konkret domain-elemek (a posztban nem
                     szereplok). A relativizalas ugyanaz az elv, mint az
                     `ai_fingerprint_terms`-nel: amit a szerzo mar kimondott, az
                     nem a komment erdeme. TOBB = jobb.
    abstract_terms — jelen levo absztrakt fonevek. TOBB = rosszabb.
    hedges         — bizonytalanito fordulatok DARABSZAMA (nem tipusszam): a
                     halmozas a jel, ezert minden elofordulas szamit. TOBB = rosszabb.
    """
    text, post = comment or "", post_text or ""
    # DEDUP fogalmi kulcs szerint: a "clashes" szoveg egyszerre illeszkedik a lista
    # "clash" ES "clashes" elemere, ami ket horgonynak szamitott volna egy fogalomra.
    # A szamnak FOGALMAT kell mernie, nem szoalak-valtozatot.
    seen, in_comment = set(), []
    for t in _found_terms(_CONCRETE_ANCHORS, text):
        key = _anchor_key(t)
        if key not in seen:
            seen.add(key)
            in_comment.append(t)
    # Egyes/tobbes-fuggetlen osszevetes a poszttal — ld. `_anchor_key`.
    in_post_keys = {_anchor_key(t) for t in _found_terms(_CONCRETE_ANCHORS, post)}
    added = [t for t in in_comment if _anchor_key(t) not in in_post_keys]

    hedge_hits, hedge_terms = 0, []
    low = text.lower()
    for t in _HEDGE_TERMS:
        n = len(re.findall(_term_regex(t), low, re.IGNORECASE))
        if n:
            hedge_hits += n
            hedge_terms.append(f"{t}×{n}" if n > 1 else t)

    abstract = _found_terms(_ABSTRACT_TERMS, text)
    return {
        "words": len(_words(text)),
        "anchors_added": len(added),
        "anchor_terms": added,
        "anchors_shared_with_post": [t for t in in_comment
                                     if _anchor_key(t) in in_post_keys],
        "abstract_count": len(abstract),
        "abstract_terms": abstract,
        "hedges": hedge_hits,
        "hedge_terms": hedge_terms,
    }


# A fog-pontszam (absztrakt fonevek + tompitasok) padloja, ami MELLETT a nulla
# hozott horgony mar sertes. A 96 soros naplon mert szakadekba esik: a 0-horgonyu
# tiszta sorok 0-7-ig tomorulnek, 8-on EGYETLEN sor sincs, 9-tol jonnek a kiugrok
# (9, 10, 11, 13, 15). Ld. a reszletes indoklast a `check_quality` homalyossag-
# blokkjaban. Ujrameres eseten ITT kell allitani, es a naplobol ellenorizni, hogy
# a szakadek nem vandorolt-e el.
FOG_SCORE_FLOOR = 8


def concreteness_gate_enabled(config: dict) -> bool:
    """`linkedin.concreteness_gate`: on (kod-default) | off. YAML-boolean (§4/17).

    Kikapcsolva a kapu BAJTRA a v21-es: a `concreteness` tovabbra is MERVE van a
    naploban, csak nem kapuz — ugyanaz az elv, mint a `content_echo_gate`-nel.
    """
    raw = (config.get("linkedin", {}) or {}).get("concreteness_gate", "on")
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() not in ("off", "false", "0", "no", "none")


def check_quality(comment: str, post_text: str, brand_allowed: bool = False,
                  intent: str = "", discourse_level: str = "",
                  human_temperature: str = "",
                  image_attached: bool = False,
                  recent_openings: list[str] | None = None,
                  recent_moves: list[str] | None = None,
                  concreteness_gate: bool = True) -> list[str]:
    """Stage 9 — deterministikus kapu. Visszaadja a KONKRET serteseket.

    A lista uressege a "mehet" jel. A hivo ezt a listat adja at az ujrairo
    hivasnak, hogy a modell tudja, mit kell javitani — igy egy korbol javul,
    nem talalgat.

    `intent` / `discourse_level` (2026-07-29): ha a szerzo technikai sikon
    beszelt — vagy az intent kifejezetten tiltja az uzleti keretezest —, akkor az
    executive-absztrakcio szotar is sertes. Ures ertekkel a kapu a v1-es
    viselkedest adja, tehat a regi hivasok valtozatlanul mukodnek.

    v3: aktiv Conversation Intent Layer mellett a sablonos nyitas/záras is
    merheto; a framework-reflex `_FINGERPRINT_LEVELS`-en (technikai VAGY
    management sik) es emberkozpontu beszelgetesben mer, es csak ket uj (a
    szerzotol nem atvett) kifejezesnel indit ujrairast.

    2026-08-10 (v5), ket user-dontes eles meres alapjan:
      - a framework-reflex hatokore a `management` sikra is kiterjed
        (`_FINGERPRINT_LEVELS`); a `business` szandekosan kimarad,
      - a sablonos NYITAS az elso KET MONDATRA mer, nem csak sorelejere
        (`_opening_window`),
      - a marketing-klise (`_MARKETING_CLICHE_PATTERNS`) FELTETEL NELKUL mer.

    2026-08-10: az `auth_score`/`auth_min` parameterek TOROLVE az Authenticity
    rubrikaval egyutt (harom eles meres, harom 10/10 — nulla variancia). Innentol
    a kapu KIZAROLAG merheto dolgokat mer, onertekelest nem hasznal. Reszletes
    indoklas a `_COMPOSE_SCHEMA` felett.

    `image_attached` (2026-07-31): ha a REASON kepet is kapott, a kommentben a
    KEPRE hivatkozas sertes — az ilyen allitast kodban nem tudjuk ellenorizni.

    `recent_openings` (2026-08-11): a legutobbi kommentek nyitas-ujjlenyomatai
    (`opening_fingerprint`). Ha a mostani nyitas kozottuk van, az sertes. None vagy
    ures lista eseten a kapu nem meri — igy a REGI hivasok es a kikapcsolt
    `opening_echo_gate` bajtra a korabbi viselkedest adjak. A fuggveny TISZTA marad:
    a gyűrűt a hivo adja at, nem a modul-allapotbol olvassuk.
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

    # Dicsero nyitas: CSAK az elso ket mondatra, de FELTETEL NELKUL — ld.
    # `_PRAISE_OPENING_PATTERNS`. A mert eset minden meglevo kapun atment.
    praise_window = " ".join(_opening_window(text)).lower()
    for pattern, label in _PRAISE_OPENING_PATTERNS:
        if re.search(pattern, praise_window, re.IGNORECASE | re.MULTILINE):
            issues.append(f"{_PRAISE_ISSUE_PREFIX} ({label})")
            break

    # Marketing-klise: FELTETEL NELKUL mer, minden sikon es minden intenten —
    # ld. `_MARKETING_CLICHE_PATTERNS`. A mert eset (`management` sik) pont azt
    # mutatta, hogy a szinthez kotott kapuk itt nem segitenek.
    for pattern, label in _MARKETING_CLICHE_PATTERNS:
        if re.search(pattern, low, re.IGNORECASE | re.MULTILINE):
            issues.append(f"marketing-klise ({label})")

    # Tanacsadoi hang: az EGESZ kommentre mer, nem csak a nyitasra — a mert hiba
    # eppen az volt, hogy a frazis a 3. mondatba hatralt ki a nyitas-ablakbol.
    # Feltetel nelkul, mint a marketing-klise; ld. `_CONSULTANT_VOICE_PATTERNS`.
    for pattern, label in _CONSULTANT_VOICE_PATTERNS:
        if re.search(pattern, low, re.IGNORECASE | re.MULTILINE):
            issues.append(label)

    if shaping_active:
        # Az ELSO KET MONDATRA merunk, nem csak sorelejere — ld. `_opening_window`.
        # A mintak `^`-hoz kotottek, ezert mondatonkent illesztunk; MULTILINE itt
        # mar nem kell, mert egy ablak-elem sosem tartalmaz sortorest.
        window = _opening_window(text)
        for pattern, label in _STOCK_OPENING_PATTERNS:
            if any(re.search(pattern, s, re.IGNORECASE) for s in window):
                issues.append(label)

        tail = low[-220:]
        for pattern, label in _EFFICIENCY_ENDING_PATTERNS:
            if re.search(pattern, tail, re.IGNORECASE | re.MULTILINE):
                issues.append(label)

    # Nyitas-visszhang: nem szotarhoz, hanem a SAJAT legutobbi kimeneteinkhez mer.
    # Szandekosan a `shaping_active` blokkon KIVUL: a mert hiba (haromszor "What
    # strikes me") nem az intent layertol fugg, hanem attol, hogy a modell ugyanazt
    # a mozdulatot ismetli. A hatokort a hivo szabja meg azzal, hogy atadja-e a
    # gyűrűt (`opening_echo_gate`).
    if recent_openings:
        opening_fp = opening_fingerprint(text)
        if opening_fp and opening_fp in set(recent_openings):
            issues.append(f"ismetlodo nyitas (a legutobbi kommentek egyikevel "
                          f"azonos kezdes: '{opening_fp}')")

    # Tartalmi mozdulat: ugyanaz a mechanizmus egy szinttel beljebb — nem a NYITAS,
    # hanem a GONDOLAT ismetlodese. NEM ismetles-osztaly (`_REPHRASABLE_PREFIXES`):
    # ezt nem mas szoval, hanem MAS gondolattal kell javitani, ezert nem is jar ra
    # harmadik kor.
    if recent_moves:
        move = content_move(text)
        if move and move in set(recent_moves):
            issues.append(f"ismetlodo gondolat (a legutobbi kommentek egyike "
                          f"ugyanide futott ki: '{move}')")

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
    if ((discourse_level in _FINGERPRINT_LEVELS) or
            (intent in _HUMAN_CENTERED_INTENTS)) and len(fingerprint) >= 2:
        # A cimke "AI-ujjlenyomat" prefixe SZANDEKOSAN valtozatlan (tesztek erre
        # illesztenek); a masodik fele viszont mar "enterprise-regiszter", mert a
        # lista 2026-08-10 ota tulmutat a framework->process->governance klaszteren
        # (`robust`, `leverage`).
        issues.append(f"AI-ujjlenyomat / enterprise-regiszter ({', '.join(fingerprint[:3])})")

    # HOMALYOSSAG (2026-08-11, v22): a `concreteness` eddig CSAK diagnosztika volt
    # („a kapu nem hasznalja"). Egy eles komment megmutatta, miert kell kapu is:
    # nulla hozott horgony, HET absztrakt fonev (collaboration, framework, potential,
    # challenge, stakeholder(s), capabilities) es NEGY tompitas 115 szoban — a kapu
    # minden meglevo szabalyt teljesitett, es tisztan kiengedte. A komment nem
    # hibas, hanem SULYTALAN: pontosan az, amit egy tanacsado ir, hogy okosnak
    # tunjon, es amire senki nem valaszol.
    #
    # A KUSZOB MERT, NEM TALALT: a 96 soros naplon a 0-horgonyu tiszta sorok
    # fog-pontszama (absztrakt + tompitas) 0-7 kozott tomorul, a 8 URES, es 9-tol
    # jonnek a kiugrok. A kuszob ezert 8 — a mert szakadekba esik, tehat egy kis
    # elmozdulas sem billent at sort. Igy a mert korpusz tiszta sorainak 6%-a
    # bukna el rajta, nem a 71%-a (annyinak van 0 horgonya — ezert nem szabad
    # magara a horgony-hianyra kapuzni: az a NORMAL allapot, nem a hiba).
    #
    # KET FELTETEL EGYUTT: a horgony-hiany onmagaban nem hiba (a szotar szűk), a
    # sok absztrakcio onmagaban sem (egy business-szintű beszelgetes joggal
    # absztrakt). A KETTO EGYUTT az, ami azt jelenti: a komment semmit nem nevez
    # meg, es kozben tele van kodszoval.
    if concreteness_gate:
        co = concreteness(text, post_text)
        fog = co["abstract_count"] + co["hedges"]
        if co["anchors_added"] == 0 and fog >= FOG_SCORE_FLOOR:
            issues.append(
                f"homalyos, konkretum nelkul (0 hozott horgony, "
                f"fog-pontszam {fog}: {co['abstract_count']} absztrakt + "
                f"{co['hedges']} tompitas)")

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


# --- Kihivas-szenzor (2026-08-11, engine v13) --------------------------------
# A MERT PROBLEMA: a `constructive_challenge` 33 generalasbol EGYSZER SEM nyert. A
# diagnozis kizart ket magyarazatot:
#   - NEM a bias: a CC nyers pontja sosem ment 7 fole, a gyoztes 32 sorban 9 volt,
#     tehat +2..+9,5 kellett volna. Nulla olyan sor, ahol 1 pont eleg — egy ilyen
#     bias mar teherhordo, amit a v8 dontes kizar.
#   - NEM redundancia: kenyszeritett CC-vel (`bench_linkedin.py --strategy`) az
#     egyik poszton a korpusz legjobb regiszter-erteket adta (anchors 1, hedges 0,
#     rewrites 0), es pont a kimondatlan feltetelt talalta meg.
# A hiba tehat a KIVALASZTASBAN van: a modell a 9-est rangsor-cimkeként hasznalja,
# amire egy strategia nem tud "felkapaszkodni".
#
# A MEGOLDAS a projekt sajat mintaja (`explicit_tool_request` + igazolt idezet ->
# markaemlites): a modell SZENZOR, a kod BIRO. Nem uj sulyt adunk, hanem uj TENYT —
# es a tenyt kodbol ellenorizzuk.
_CHALLENGE_INTENTS = {"professional_opinion", "industry_debate"}

# A PADLO-FELTETEL (2026-08-11, v19-ben atirva): a szenzornak van egy "a modell maga is
# jonak jelolte" feltetele. A v13-ban ez egy KULON konstans volt (`CHALLENGE_FIT_FLOOR
# = 7`, a CC akkori tortenelmi maximuma) a NYERS ponton. Ket dolog tortent azota:
#
#   1. NO-OP LETT. A v13-as `thesis_condition`-kerdes (ami a pontozas ELOTT all)
#      megemelte a CC nyers pontjat 5.7-rol 8.6-ra (v15: 9.0), tehat a 7-es padlo a
#      mert eloszlason SOSEM kot. Egy feltetel, ami mindig teljesul, ugy olvasodik,
#      mintha vedelem lenne — pedig nem az.
#   2. KETTOS DEFINICIO. A v16 bevezette a `STRATEGY_CANDIDATE_FLOOR`-t ugyanarra a
#      fogalomra ("a modell elfogadhatonak jelolte"), csak a SULYOZOTT ponton — es a
#      J6 teszt megmutatta, miert az a helyes (a nyers ponton szűrve a bias-korrekcio
#      kiesik). Ket kulon konstans ugyanarra a fogalomra drift-hazard: az egyiket
#      atirja valaki, a masikat elfelejti.
#
# EZERT: a szenzor a `strategy_candidates`-re delegal — EGY definicio, sulyozott
# ponton, a vetoval egyutt. A feltetel MARAD (nem toroltuk, mint a v18-as halott
# prompt-szoveget), mert regresszio-vedelem: ha a CC pontozasa valaha visszaesik (pl.
# a v12-es DISAGREEMENT-horgony kivezetesekor), a szenzor ne leptessen elo egy rosszul
# illeszkedo strategiat. Hogy elsul-e, az a `challenge_reason`-bol megszamolhato.

# --- A FELTETEL-MONOKULTURA (2026-08-11, engine v15) -------------------------
# A MERT HIBA: a v13-as szenzor bevezetese utan OT eles futasbol OT `thesis_condition`
# szerzodesi/incentiva-jellegű volt. A v14-es kimeneti kapu ezt DETEKTALTA, de nem
# gyogyitotta (harom elsules, ketto sertessel kiment, nulla elhagyta a keretet) —
# mert kimeneti kapu nem javit BEMENETI monokulturat.
#
# KET REZ, mert kulon egyik sem eleg:
#   1. PROMPT: a `thesis_condition` leirasa megnevezi a legkonnyebben elerheto
#      valaszt es elteriti tole (ugyanaz a technika, ami a v8-as kalibracios
#      ellenorzesnel es a v12-es "disagreement is not a risk" horgonynal bevalt).
#      Ez a MERT attraktort kezeli.
#   2. BIRO: ha a feltetel csaladja megegyezik a legutobbi ELFOGADOTT felteteleivel,
#      a feltetel nem szamit TENYNEK -> a szenzor nem sul el. Ez a KOVETKEZO
#      attraktort is kezeli, barmi is legyen az, es nem a modell jóindulatan all.
#
# MIERT >= 1 TALALAT ITT, es miert >= 2 a kommentnel (`_CONTENT_MOVE_MIN_HITS`): a
# komment 100+ szo, ott egy futo emlites meg nem a mozdulat. A feltetel EGY tagmondat
# — ott az elso kereskedelmi terminus mar a feltetel lenyege.
#
# KORREKCIO (2026-08-11, engine v20): a fenti "OT-bol OT szerzodesi" MERES egy
# egy-mintas detektor ARTEFAKTUMA volt, nem a modell tenyleges viselkedese. A
# `_CONTENT_MOVES`-nek addig KIZAROLAG a `move:commercial_frame` mintaja volt,
# tehat minden mas `thesis_condition` "" (nem kategorizalt) lett — LATHATATLAN a
# gyűrű szamara, nem "nem letezo". Egy 91 soros kotegen a "" halmazt kezzel
# atolvasva egy MASODIK, addig felugyelet nelkuli csalad rajzolodott ki (kozos
# CDE/BIM execution plan/koordinata-rendszer hianya, 5-6x ismetlodve) — ez most
# a `move:tool_interop_frame` mintaval fedve van. A tanulsag altalanos: egy
# monokultura-szenzor csak annyi csaladot lat, amennyit a lista nevesit; a "0%
# masik csalad" eredmeny ELOSZOR a detektor hianyat jelenti, masodszor a modell
# viselkedeset.
_CONDITION_FAMILY_MIN_HITS = 1

# Csak az ELFOGADOTT (a strategiat tenylegesen eldonto) feltetelek kerulnek ide: egy
# el nem sult szenzor feltetele nem befolyasolt kommentet, tehat nem is kell kizarnia
# egy kesobbit. Ugyanaz az elv, mint a nyitas-gyűrűnel ("csak sikeres komment utan").
_recent_condition_families: deque = deque(maxlen=_OPENING_RING_SIZE)


def condition_family(condition: str) -> str:
    """A kimondatlan feltetel csaladja, vagy "" ha egyik ismert csaladba sem esik."""
    low = (condition or "").lower()
    for pattern, name in _CONTENT_MOVES:
        if len(set(m.group(0).lower() for m in re.finditer(pattern, low))) \
                >= _CONDITION_FAMILY_MIN_HITS:
            return name
    return ""


def remember_condition_family(condition: str) -> None:
    """Az ELFOGADOTT feltetel csaladja a gyűrűbe — csak ha a szenzor elsult."""
    family = condition_family(condition)
    if family:
        _recent_condition_families.append(family)

# Az idezet-hossz padloja a TEZISRE. A `_quote_in_post` alapertelmezese 3 szo, ami a
# `tool_request_quote`-ra van kalibralva ("which software?" — egy rovid kerdes eleg
# bizonyitek). Egy TEZIS viszont ALLITAS: alany es allitmany kell hozza. Teszt
# talalta meg (K5.1): a "the concept model" harom szoval atment, holott az egy
# fonevi szerkezet, nem a poszt kozponti allitasa.
THESIS_QUOTE_MIN_WORDS = 6


def challenge_sensor_enabled(config: dict) -> bool:
    """`linkedin.challenge_sensor`: on (default) | off. YAML-boolean kezelve (§4/17).

    Kikapcsolva a dontes bajtra a v12-es (tiszta `pick_strategy` argmax), tehat a
    szenzor A/B-zheto — ugyanaz az elv, mint az `opening_echo_gate`-nel.
    """
    raw = (config.get("linkedin", {}) or {}).get("challenge_sensor", "on")
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() not in ("off", "false", "0", "no", "none")


def challenge_override(reasoning: dict, post_text: str, intent: str,
                       level: str,
                       recent_conditions: list[str] | None = None,
                       recent_strategies: list[str] | None = None) -> tuple[bool, str]:
    """Legyen-e `constructive_challenge` a strategia? (dontes, indok)

    HET feltetel, mind ellenorizhető, es az indok mindig visszajon (naplozzuk, hogy
    a dontes utolag megmagyarazhato legyen — `brand_mention_allowed` mintaja):
      1. a beszelgetes velemeny-jellegű (`_CHALLENGE_INTENTS`),
      2. a modell talalt kimondatlan feltetelt (`thesis_condition`),
      3. a feltetel csaladja NEM ismetli a legutobbi elfogadottakat (v15 — a mert
         monokultura: ot feltetelbol ot szerzodesi volt),
      4. az allitast SZO SZERINT idezte, es az idezet TENYLEG a posztban van,
      5. a szint nem vetozza a CC-t (`_LEVEL_VETO` — a mechanizmus tiszteletben
         tartasa; ma egyetlen szint sem vetozza),
      6. a CC JELOLT, azaz a modell sulyozott pontja eleri a `STRATEGY_CANDIDATE_FLOOR`-t
         (v19: `strategy_candidates`-re delegalva — egy definicio, nem ket konstans),
      7. a CC nincs a strategia-gyűrűben (v17 — a szenzor eloleptet, nem kenyszerit;
         a rotaciot nem irhatja felul).

    `recent_conditions`: a legutobbi ELFOGADOTT feltetel-csaladok. None/ures eseten a
    3. feltetel nem mer — igy a regi hivasok es a kikapcsolt szenzor valtozatlanok,
    es a fuggveny TISZTA marad (a gyűrűt a hivo adja at).
    """
    if intent not in _CHALLENGE_INTENTS:
        return False, f"az intent ({intent}) nem velemeny-jellegű"

    condition = str(reasoning.get("thesis_condition") or "").strip()
    if not condition:
        return False, "a modell nem talalt kimondatlan feltetelt a tezisben"

    family = condition_family(condition)
    if recent_conditions and family and family in set(recent_conditions):
        return False, (f"a feltetel ugyanabba a csaladba esik, mint a legutobbi "
                       f"elfogadottak ({family}) — nem uj teny")

    quote = reasoning.get("thesis_quote", "")
    if not _quote_in_post(quote, post_text, min_words=THESIS_QUOTE_MIN_WORDS):
        return False, f"az idezett tezis nem talalhato a posztban ({quote[:60]!r})"

    # A VETO ELOSZOR, hogy a specifikus indok nyerjen: a `strategy_candidates` a
    # vetozottakat is kiszűri, tehat utana mar nem lehetne megkulonboztetni a "kemeny
    # kapu" es a "padlo alatt" esetet. A telemetriaban ez ket kulonbozo jelenseg.
    if "constructive_challenge" in _LEVEL_VETO.get(level, set()):
        return False, f"a(z) {level} szint vetozza a CC-t"

    # EGY definicio a "modell elfogadhatonak jelolte"-re: `strategy_candidates`
    # (sulyozott pont, `STRATEGY_CANDIDATE_FLOOR`). Ide erve a veto mar kizarva, tehat
    # ha nem jelolt, az csak a padlo lehet.
    fit_source = reasoning.get("strategy_fit") or {}
    if "constructive_challenge" not in strategy_candidates(fit_source, intent, level):
        weighted = score_strategies(fit_source, intent, level)[0]["constructive_challenge"]
        return False, (f"a modell maga is alacsonyra tette a CC-t (sulyozva {weighted:g} "
                       f"< {STRATEGY_CANDIDATE_FLOOR})")

    # A ROTACIO TISZTELETBEN TARTASA (2026-08-11, v17). A MERT HIBA: a szenzor a
    # `decide_strategy` UTAN fut, tehat visszahozta a CC-t akkor is, amikor a
    # strategia-gyűrű epp kizarta — igy ket egymas utani CC-komment lett.
    #
    # MIERT NEM ALL ITT az "utasitas erosebb a visszhang-tilalomnal" elv (ami a
    # `shape_frame`-nel igen): ott a modell KAPOTT egy utasitast, es azt buntetni
    # ellentmondas lett volna. A szenzor viszont nem utasitas, hanem ELOLEPTETES: a
    # dolga az, hogy a CC LEHETSEGES legyen, nem az, hogy elkerulhetetlen.
    #
    # MIERT EZ AZ UTOLSO FELTETEL: igy az indok-string megkulonboztetheto — "a teny jo
    # volt, csak a rotacio zarta" vs. "nem volt teny". A telemetriaban ez ket
    # kulonbozo jelenseg, es kulon kell tudni szamolni oket.
    if recent_strategies and "constructive_challenge" in set(recent_strategies):
        return False, ("igazolt feltetel, de a CC a strategia-gyűrűben van "
                       "(rotacio) — nem sul el")

    return True, f"igazolt kimondatlan feltetel: {condition[:80]}"


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


def skip_vendor_promotion_enabled(config: dict) -> bool:
    """`linkedin.skip_vendor_promotion`: on (default) | off. YAML-boolean (§4/17)."""
    raw = (config.get("linkedin", {}) or {}).get("skip_vendor_promotion", "on")
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() not in ("off", "false", "0", "no", "none")


def vendor_promotion_skip(config: dict, reasoning: dict,
                          post_text: str) -> tuple[bool, str]:
    """Ki kell-e hagyni ezt a posztot? (skip, indok)

    USER-DONTES (2026-08-10): vendor-hirdetes ALATT nem akarunk megjelenni. Az
    indok nem stilisztikai, hanem uzleti: egy erdemi komment (a) ingyen
    engagementet ad a hirdetesnek (a LinkedIn kommentszam szerint rangsorol),
    (b) a szerzot azza teszi, aki egy SZOMSZEDOS versenytars marketingje alatt
    finoman ellenvetést tesz.

    MIERT NEM ELEG a `conversation_intent == product_demonstration`: az intent
    definicioja szerint "their own or someone else's" — vagyis egy gyakorlo
    szakember is ide esik, aki a sajat epitett eszkozet mutatja meg. Az PONT olyan
    poszt, amire VALASZOLNI akarunk. A kettot csak a REGISZTER valasztja el, ezert
    kell hozza sajat mezo.

    HAROM KAPU, ugyanaz a minta, mint a `brand_mention_allowed`-nal:
      1. a kapcsolo be van kapcsolva,
      2. a modell `vendor_promotion`-t allit,
      3. az idezet ELLENORIZHETOEN szerepel a posztban (zero-hallucination) —
         a modell "ez hirdetes" allitasat nem fogadjuk el szavara, mert a
         kovetkezmeny az, hogy EGYALTALAN nem generalunk kommentet.
    """
    if not skip_vendor_promotion_enabled(config):
        return False, "skip_vendor_promotion=off"
    if not reasoning.get("vendor_promotion"):
        return False, "nem vendor-hirdetes"

    quote = reasoning.get("promotion_evidence", "")
    if not _quote_in_post(quote, post_text):
        return False, f"vendor-hirdetesnek jelolve, de az idezet nem talalhato a posztban ({quote[:60]!r})"

    return True, f"vendor-hirdetes, igazolt idezet: {quote[:80]!r}"


def _compose_user_msg(post_text: str, author_line: str, reasoning: dict,
                      brand_allowed: bool, issues: list[str] | None = None,
                      intent_layer: bool = True, opening: str = "",
                      length_band: tuple[int, int] | None = None) -> str:
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

    `length_band` (v7): a POSZT hosszabol szamolt (min, max) cel-szohossz, vagy
    None. None eseten a fix "80-150 words" all elo, tehat a kikapcsolt skalazas
    BAJTRA a korabbi promptot adja.
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
        # A hossz a POSZTBOL szamolodik (v7) — a hossz is regiszter. `None` eseten a
        # fix mondat all elo, tehat a kikapcsolt skalazas bajtra a v6-os promptot adja.
        (f"{length_band[0]}-{length_band[1]} words — this range REPLACES the one in "
         f"your instructions, and it is scaled to the length of THIS post. A short, "
         f"sharp post gets a short, sharp reply; do not pad to fill space. "
         f"Max two paragraphs, ~20% acknowledgement / 80% new thinking."
         if length_band else
         "80-150 words, max two paragraphs, ~20% acknowledgement / 80% new thinking."),
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
                     image_mime: str = "image/jpeg",
                     force: bool = False) -> dict:
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
                               image_bytes=image_bytes, image_mime=image_mime,
                               force=force)
    record(config, result, post_text,
           elapsed_ms=int((time.monotonic() - started) * 1000))
    return result


def _generate_comment(config: dict, post_text: str, author_name: str = "",
                      author_role: str = "",
                      image_bytes: bytes | None = None,
                      image_mime: str = "image/jpeg",
                      force: bool = False) -> dict:
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
    # v21: a szerzonkenti gyűrűk kulcsa. Ismeretlen szerzonel ures ("") — ilyenkor
    # minden `_author_*` lekeres ures listat ad, tehat a viselkedes valtozatlan.
    akey = author_key(author_name)

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
    use_image = bool(image_bytes) and intent_layer and image_input_enabled(config)
    if image_bytes and not use_image:
        why = ("linkedin.image_input=off" if not image_input_enabled(config)
               else "az intent layer ki van kapcsolva, a kep besorolasa elveszne")
        print(f"[linkedin-tle] a kep NEM megy el ({why})")

    # --- Stage 1-5: reasoning (a kep CSAK ide) ---
    # v23: a GONDOLAT keretenek eltentese MAR ITT, nem a kimeneten. A merés (13-bol
    # 12) szerint a kereskedelmi keret mar az `insight`-ban benne volt, tehat a
    # compose-oldali kapu elvileg sem tud gyogyitani. Ures gyűrű eseten a blokk
    # ures string, tehat a hivas bajtra a v22-es.
    steer = (insight_steer_block(list(_recent_insight_families))
             if insight_frame_steer_enabled(config) else "")
    if steer:
        print(f"[linkedin-tle] insight-elterites: kerulendo keretek="
              f"{sorted(set(_recent_insight_families))}")
    try:
        reasoning = _call_json(
            client, model, reason_prompt_for(use_image),
            f"{author_line}POST:\n{post_text[:2000]}{steer}",
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

    # Stage 4: a dontest a kod hozza a modell pontszamaibol.
    # v16: a nyers pontszam SZURO (ki a jelolt), es a jelolt-halmazbol a kod dont —
    # a mert diagnozis szerint a pontozas nem rangsor (4-5 strategia mindig >= 7, a
    # maximum 13/21 sorban holtverseny). Kikapcsolva bajtra a v15-os argmax fut.
    # v21: a globalis ES a szerzonkenti strategia-gyűrű egyutt szamit — igy A
    # szerzo nem kaphatja ugyanazt a hangnemet ket egymas utani posztjara, meg
    # akkor sem, ha kozben mas szerzok kommentjei mar kiuritettek a globalis
    # gyűrűt.
    combined_strategy_ring = list(_recent_strategies) + list(_author_strategies.get(akey, ()))
    if strategy_candidates_enabled(config):
        strategy_cands = strategy_candidates(reasoning["strategy_fit"], intent, level)
        reasoning["strategy"], strategy_reason = decide_strategy(
            reasoning["strategy_fit"], post_text, intent, level,
            recent=combined_strategy_ring)
        print(f"[linkedin-tle] strategia-dontes: {strategy_reason} "
              f"| gyűrű={list(_recent_strategies)}"
              + (f" | szerzo-gyűrű={list(_author_strategies.get(akey, ()))}" if akey else ""))
    else:
        strategy_cands = []
        reasoning["strategy"] = pick_strategy(reasoning["strategy_fit"], intent, level)
        strategy_reason = "jelolt-szűres KIKAPCSOLVA -> sulyozott argmax"
    strategy_scores, strategy_vetoed = score_strategies(
        reasoning["strategy_fit"], intent, level)

    # Stage 4.5: kihivas-szenzor (v13). A pontszam nem tudta megvalasztani a
    # `constructive_challenge`-t (33/0), ezert itt egy IGAZOLT TENY dont, nem suly.
    # A `pick_strategy` eredmenyet megorizzuk a naploban: igy utolag latszik, mit
    # irt felul a szenzor, es mennyire volt indokolt.
    challenge_fires, challenge_reason = (False, "kikapcsolva")
    if intent_layer and challenge_sensor_enabled(config):
        challenge_fires, challenge_reason = challenge_override(
            reasoning, post_text, intent, level,
            recent_conditions=list(_recent_condition_families),
            recent_strategies=combined_strategy_ring)
    strategy_before_override = reasoning["strategy"]
    if challenge_fires:
        # A gyűrű CSAK elfogadott feltetelnel bővul: ez az a feltetel, ami tenylegesen
        # eldontotte a strategiat. Akkor is bővit, ha a `pick_strategy` mar CC-t adott —
        # a feltetelt ott is felhasznaltuk, tehat a kovetkezonek tudnia kell rola.
        remember_condition_family(reasoning.get("thesis_condition", ""))
    if challenge_fires and reasoning["strategy"] != "constructive_challenge":
        reasoning["strategy"] = "constructive_challenge"
        print(f"[linkedin-tle] KIHIVAS-SZENZOR: {strategy_before_override} -> "
              f"constructive_challenge ({challenge_reason})")
    print(f"[linkedin-tle] intent={intent} | szint={level} | szerep={responder_role} | "
          f"forma={response_mode} | gravity={(reasoning.get('topic_gravity') or '-')!r}"
          + (f" | kep={image_role}" if use_image else "")
          + (f" | vetozott={sorted(strategy_vetoed)}" if strategy_vetoed else "")
          + ("" if intent_layer else " | INTENT LAYER KIKAPCSOLVA"))

    # --- Stage 5.5: vendor-hirdetes -> KIHAGYAS (2026-08-10) ---
    # A COMPOSE ELE kerul, mert ha kihagyjuk, a masodik hivast MEG SEM inditjuk:
    # egy meg nem szuletett kommentert nem fizetunk. A `force` a UI "Megis
    # generalj" gombja — a dontes ajanlas, nem tilalom.
    skip, skip_reason = vendor_promotion_skip(config, reasoning, post_text)
    if skip and not force:
        print(f"[linkedin-tle] KIHAGYVA: {skip_reason}")
        return {
            "skipped": True,
            "skip_reason": skip_reason,
            # A legacy mezok jelen vannak, hogy a dashboard-szerzodes ne toljon
            # el; a UI a `skipped` flaget vizsgalja eloszor.
            "topic": reasoning.get("topic", "general"),
            "post_type": reasoning.get("post_type", "general"),
            "engagement_intent": "", "reply_style": "", "brand_mode": "none",
            "confidence": reasoning.get("confidence", 0.0),
            "reply_text": "", "rationale": skip_reason,
            "engine": ENGINE_VERSION,
            "conversation_intent": intent,
            "conversation_intent_label": CONVERSATION_INTENTS[intent]["label"],
            "discourse_level": level,
            "vendor_promotion": True,
            "promotion_evidence": reasoning.get("promotion_evidence", ""),
            "core_thesis": reasoning.get("core_thesis", ""),
            "author_objective": reasoning.get("author_objective", ""),
            "technical_depth": reasoning.get("technical_depth", ""),
            "topic_gravity": reasoning.get("topic_gravity", ""),
            "reason_temperature": reason_temp,
            "compose_temperature": compose_temp,
            "temperature": temp,
        }
    if skip and force:
        print(f"[linkedin-tle] vendor-hirdetes, de FORCE: {skip_reason}")

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
        # v21: ugyanaz az elv, mint a strategia-gyűrűnel — a szerzo sajat nyitas-
        # elozmenye is kizarja a formát, nem csak a globalis gyűrű.
        opening = pick_opening(
            post_text, response_mode,
            recent=list(_recent_openings) + list(_author_openings.get(akey, ())))
        print(f"[linkedin-tle] nyitas={opening or '(a valaszforma dontötte el)'}"
              f" | legutobbiak={list(_recent_openings)}"
              + (f" | szerzo-legutobbiak={list(_author_openings.get(akey, ()))}" if akey else ""))

    # --- Stage 6.6: cel-szohossz a POSZT hosszabol (v7) ---
    # A hossz is regiszter: egy 53 szavas, eles poszt nem erdemel 110 szavas valaszt.
    length_band = target_length(post_text) if length_scaling_enabled(config) else None
    if length_band:
        print(f"[linkedin-tle] cel-hossz={length_band[0]}-{length_band[1]} szo "
              f"(poszt: {len(_words(post_text))} szo)")

    # A visszhang-gyűrű a kapu szamara: a KIOSZTOTT forma sajat kerete kimarad, mert
    # az utasitast nem szabad sertesnek minositeni (`shape_frame` docstring).
    # v21: mindket gyűrű a szerzo sajat elozmenyevel is bővul.
    echo_ring = echo_ring_for(opening, extra=list(_author_opening_texts.get(akey, ())))
    # Ugyanez a tartalmi mozdulatra: a strategia sajat mozdulata kimarad
    # (`move_ring_for`) — a `business_impact` direktivaja EPPEN a kereskedelmi keret.
    move_ring = move_ring_for(reasoning["strategy"],
                              extra=list(_author_content_moves.get(akey, ())))

    # --- Stage 6-7: compose, + Stage 9: kapu, ket vagy harom korrel ---
    comment, issues, rewrites = "", ["nem futott le"], 0
    # Az ELSO kor sertesei kulon. A telemetria eddig csak a VEGSO `quality_issues`-t
    # naplozta (ures = atengedve), tehat egy `rewrites: 1`-es sornal nem lehetett
    # megtudni, MI valtotta ki az ujrairast — a 2026-08-10-i naplo-elemzes talalta
    # meg ezt a hianyt. A javito kort igy visszamenoleg is meg lehet magyarazni.
    issues_first: list[str] = []
    # AKKUMULALT sertesek. A mert hibamod (49./50. sor): az 1. kor "We often see"-re
    # bukott, a 2. kor pedig ugyanannak a mozdulatnak MAS alakjaval jott ("I often
    # find") — vagyis a modell valtozatot cserelt, nem viselkedest. Ha csak az utolso
    # kor serteset adjuk at, a modell nem is tudja, hogy az elozo alak is tilos.
    seen_issues: list[str] = []
    # A LEGJOBB kor, nem az UTOLSO (2026-08-11, v22). A hurok eddig azt a szoveget
    # adta ki, amit eppen utolsonak kapott — holott a 3. kor lehet ROSSZABB, mint az
    # 1. (a modell egy sertes javitasa kozben ujat vihet be). A jobbat eldobni tiszta
    # veszteseg: ugyanannyi hivas, rosszabb kimenet.
    best_comment, best_issues = "", None
    for attempt in range(MAX_COMPOSE_ATTEMPTS):
        # A nyitas-forma az ujrairo korben is UGYANAZ: az ujrairas a kapu konkret
        # serteseit javitja, nem a retorikai formát valtoztatja. Uj forma itt
        # ujabb valtozot vinne egy amugy is celzott javitasba.
        user_msg = _compose_user_msg(
            post_text, author_line, reasoning, brand_allowed,
            seen_issues if attempt else None, intent_layer=intent_layer,
            opening=opening, length_band=length_band,
        )
        try:
            out = _call_json(client, model, _COMPOSE_PROMPT, user_msg,
                             _COMPOSE_SCHEMA, max_tokens=700, temp=compose_temp)
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
            image_attached=use_image,
            # A gyűrű MEG NEM tartalmazza ezt a kommentet (a `remember_opening_text`
            # csak siker utan bővit), tehat a komment nem utkozhet onmagaval.
            # A KIOSZTOTT forma sajat kerete kimarad az osszehasonlitasbol — ld.
            # `shape_frame`: az utasitas erosebb, mint a visszhang-tilalom.
            recent_openings=(echo_ring if opening_echo_gate_enabled(config) else None),
            recent_moves=(move_ring if content_echo_gate_enabled(config) else None),
            concreteness_gate=concreteness_gate_enabled(config),
        )
        if attempt == 0:
            issues_first = list(issues)
        # A rangsor: eloszor a BLOKKOLO sertesek szama dont, aztan az osszes. Igy egy
        # ket apro hosszhibas, de kiadhato kor nyer egy egyetlen AI-jelet tartalmazo
        # korrel szemben — nem a puszta darabszam.
        if best_issues is None or (
                (len(blocking_issues(issues)), len(issues))
                < (len(blocking_issues(best_issues)), len(best_issues))):
            best_comment, best_issues = comment, list(issues)
        if not issues:
            break
        rewrites = attempt + 1
        print(f"[linkedin-tle] kapu elutasitotta ({attempt + 1}. kor): {', '.join(issues)}")
        for issue in issues:
            if issue not in seen_issues:
                seen_issues.append(issue)
        # A HARMADIK kor csak ismetles-osztalyra jar — ld. `_REPHRASABLE_PREFIXES`.
        if attempt >= 1 and not only_rephrasable(issues):
            break

    comment, issues = best_comment, (best_issues if best_issues is not None else issues)

    if not comment:
        return {"error": "A kompozíciós lépés üres kommentet adott."}

    # KEMENY BUKAS a kiadhatatlan serteseknel (v22). Eddig a hurok kimeneteként a meg
    # mindig serto szoveg SIKERKENT ment vissza, es a hivo (`ui/app.py`) csak az
    # `error` kulcsot vizsgalja — vagyis a sertes csendben kiment a felhasznalonak.
    # Inkabb ne adjunk kommentet, mint olyat, ami „Great post!"-tal nyit vagy nem
    # letezo kepre hivatkozik: a hurok itt mar HAROMSZOR probalta megjavitani.
    # A gyűrűk EZ ELOTT vannak, tehat egy soha meg nem jelent komment nem szennyezi
    # a kovetkezo dontest — ugyanaz az invariáns, mint a `remember_*`-eknel.
    blocked = blocking_issues(issues)
    if blocked:
        print(f"[linkedin-tle] KIADHATATLAN {rewrites} ujrairas utan: {', '.join(blocked)}")
        return {
            "error": ("A kapu " + str(rewrites) + " újraírás után is hibát talált, "
                      "ezért nem adok ki kommentet: " + "; ".join(blocked)
                      + ". Próbáld újra (a modell mintavétele változik), vagy "
                        "fogalmazd át kézzel."),
            # A diagnosztika a hibás uton is visszajon: enelkul a naploban csak egy
            # `ok: false` sor lenne, es nem lehetne megtudni, MI bukott el.
            "quality_issues": issues,
            "quality_issues_first": issues_first,
            "blocking_issues": blocked,
            "rewrites": rewrites,
            "reply_text": comment,   # a UI nem mutatja (error-ag), de merheto marad
            "engine": ENGINE_VERSION,
        }

    # A gyűrű CSAK itt bővul: egy meg nem jelent (hibara futott) komment nyitasa
    # nem okoz ismetlodest, tehat nem is kell kizarni a kovetkezo valasztasbol.
    remember_opening(opening)
    # Ugyanez a MEGVALOSULT nyitasra. Akkor is bővit, ha a kapu vegul atengedte a
    # kommentet serteessel (ket kor utan a motor visszaadja) — a komment ki fog
    # menni, tehat a kovetkezonek tudnia kell rola.
    remember_opening_text(comment)
    remember_content_move(comment)
    # A MEGVALOSULT insight kerete (v23). A gondolat akkor is elhasznalta a keretet,
    # ha a kesz komment szoveges mozdulata vegul nem erte el a ket talalatot — a
    # kovetkezo REASON-hivasnak errol tudnia kell, kulonben ugyanoda fut.
    remember_insight_family(reasoning.get("insight", ""))
    # A VEGSO strategia (a kihivas-szenzor felulirasa utan) — az ment ki, tehat azt
    # kell a kovetkezo dontesbol kizarni.
    remember_strategy(reasoning["strategy"])
    # v21: ugyanezek a SZERZO sajat gyűrűjebe is — csak akkor, ha ismert a szerzo.
    if akey:
        remember_author_opening(akey, opening)
        remember_author_opening_text(akey, comment)
        remember_author_content_move(akey, comment)
        remember_author_strategy(akey, reasoning["strategy"])

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
        # A MEGVALOSULT nyitas (2026-08-11). A `opening_shape` eddig csak azt mondta
        # meg, mit KERTUNK; ot eles generalas mutatta meg, hogy a modell haromszor
        # ugyanugy kezdett harom kulonbozo kijeloles mellett. Ez a ket mezo teszi a
        # kulonbseget merhetove. Mint az `opening_recent`, a gyűrű MAR tartalmazza
        # ezt a kommentet — a sor onmagaban is olvashato marad.
        "opening_fingerprint": opening_fingerprint(comment),
        "opening_echo_recent": list(_recent_opening_texts),
        # Tartalmi mozdulat (v14): a GONDOLAT visszhangja. A CC-kommentek 7-bol 6-szor
        # ugyanoda futottak ki (szerzodes/incentiva) — enelkul a ket mezo nelkul csak
        # azt latnank, hogy a strategia diverzifikalodott.
        "content_move": content_move(comment),
        "content_echo_recent": list(_recent_content_moves),
        # NYELV (2026-08-11). A naplo eddig egyaltalan nem tudta, milyen nyelven ment
        # ki a komment — pedig a merőszamaink FELE angolra kalibralt: a `concreteness`
        # horgony- es absztrakcio-lexikonja angol es BIM-specifikus, a hossz-sav pedig
        # angol szoszamon all. Egy magyar sort ugyanabba az atlagba szamolni azt jelenti,
        # hogy nem tudjuk, mit mertunk. Ez a ket mezo teszi a szegmentalast lehetsegesse
        # (`bench_report.py` §2). Tisztan additiv -> `TELEMETRY_SCHEMA` nem emelkedik.
        #
        # MIERT A MEGLEVO `looks_english` ES NEM NYELVFELISMERO KONYVTAR: a fuggveny
        # mar itt van (a gondolatjel-kapu hasznalja), determinisztikus, es a kerdes
        # amit fel kell tennunk binaris — "erre a sorra allnak-e az angol kalibraciok".
        "post_language": "en" if looks_english(post_text) else "other",
        "reply_language": "en" if looks_english(comment) else "other",
        # Cel-szohossz (v7): a KOD altal a poszt hosszabol szamolt sav. Naplozva, hogy
        # merheto legyen, betartja-e a modell — a sav utasitas, nem kapu.
        #
        # A `post_words` SZANDEKOSAN nem kerul ide: a telemetria `build_row`-ja mar
        # szamolja, es ha ketten szamolnank, ket KULONBOZO definicio kerulne ugyanabba
        # a naploba (`split()` vs a `_words()` regex — az 53 szavas teszt-poszton 53 vs
        # 52). Pont az a hazard, ami ellen a `TELEMETRY_SCHEMA` vedelmet ad.
        "target_length": list(length_band) if length_band else None,
        # Kep-bemenet: `image_attached` az ELKULDOTT kepet jelenti, nem a kapottat
        # (kikapcsolt layer / image_input=off eseten false, holott jott kep).
        "image_attached": use_image,
        "image_role": image_role,
        "topic_gravity": reasoning.get("topic_gravity", ""),
        "intent_layer": intent_layer,
        "strategy_scores": strategy_scores,          # sulyozott pontszamok
        "strategy_vetoed": sorted(strategy_vetoed),  # amit a szint kizart
        # v16: a jelolt-halmaz, a gyűrű es a dontes INDOKA. Enelkul nem lehetne
        # utolag megmondani, hogy egy strategia azert nem nyert, mert nem volt jelolt,
        # vagy mert a frissesseg kizarta, vagy mert a sulyozott max mast adott.
        "strategy_candidates": strategy_cands,
        "strategy_recent": list(_recent_strategies),
        # Szerzonkenti emlekezet (v21): a kulcs + a szerzo sajat gyűrűje a
        # dontes idejeben. Enelkul nem lenne merheto, hogy a szerzonkenti
        # ismetles-vedelem tenylegesen kizart-e valamit.
        "author_key": akey,
        "author_strategy_recent": list(_author_strategies.get(akey, ())) if akey else [],
        "strategy_decision_reason": strategy_reason,
        "strategy": reasoning["strategy"],
        "strategy_label": strat_label,
        "core_thesis": reasoning.get("core_thesis", ""),
        "missing_perspective": reasoning.get("missing_perspective", ""),
        "insight": reasoning.get("insight", ""),
        # Kihivas-szenzor (v13): a MODELL allitasa, a KOD dontese es az INDOK, kulon.
        # Igy meg akkor is merheto, ha a szenzor nem sult el: latszik, melyik feltetel
        # bukott el (`challenge_reason`), es hogy a modell talalt-e egyaltalan
        # kimondatlan feltetelt. Enelkul csak azt latnank, hogy a CC ismet nem nyert.
        "thesis_condition": reasoning.get("thesis_condition", ""),
        "thesis_quote": reasoning.get("thesis_quote", ""),
        "challenge_override": challenge_fires,
        "challenge_reason": challenge_reason,
        # A feltetel CSALADJA + a gyűrű (v15). Enelkul csak az egyedi szovegeket
        # latnank, es a monokulturat ujra kezzel kellene eszrevenni.
        "condition_family": condition_family(reasoning.get("thesis_condition", "")),
        "condition_echo_recent": list(_recent_condition_families),
        # A GONDOLAT kerete a FORRASNAL (v23). A mert diagnozis: 13 kereskedelmi
        # kommentbol 12-nel mar az `insight` tartalmazta a keretet, tehat ez az a
        # mezo, amin a monokultura eldol. `insight_steered`: kapott-e a hivas
        # elterito blokkot — enelkul nem lehetne A/B-t szamolni a naplobol.
        "insight_family": insight_family(reasoning.get("insight", "")),
        "insight_echo_recent": list(_recent_insight_families),
        "insight_steered": bool(steer),
        "strategy_before_override": strategy_before_override,
        "strategy_fit": reasoning.get("strategy_fit", {}),   # auditalhato dontes
        "explicit_tool_request": bool(reasoning.get("explicit_tool_request")),
        "tool_request_quote": reasoning.get("tool_request_quote", ""),
        # Vendor-hirdetes: ide csak ugy jutunk, hogy NEM hagytuk ki (vagy force).
        "skipped": False,
        "vendor_promotion": bool(reasoning.get("vendor_promotion")),
        "promotion_evidence": reasoning.get("promotion_evidence", ""),
        "skip_reason": skip_reason,
        "forced": bool(skip and force),
        # F2 konkretsag-diagnosztika — a kapu NEM hasznalja, csak merjuk (ld.
        # `concreteness`). Osszpontszam szandekosan nincs.
        "concreteness": concreteness(comment, post_text),
        "brand_allowed": brand_allowed,
        "brand_gate_reason": brand_reason,
        "author_objective": reasoning.get("author_objective", ""),
        "audience": reasoning.get("audience", ""),
        "technical_depth": reasoning.get("technical_depth", ""),
        "quality_issues": issues,          # ures = a kapu atengedte
        # Az ELSO kor sertesei: `rewrites >= 1` eseten ez mondja meg, MIERT kellett
        # ujrairni. Enelkul a naploban csak az latszott, hogy volt egy plusz kor.
        "quality_issues_first": issues_first,
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
