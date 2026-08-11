"""
Authenticity Layer (2026-08-01) — a munkaparancs ALKALMAZHATO resze.

Amit a spec kert es itt megvalosult:
  - termeszetes nyitasok WHITELISTJE a compose-promptban (eddig csak tiltolista volt)
  - bovitett tanacsadoi nyitas-tiltolista a determinisztikus kapuban
  - megnevezett anti-szerepek (standards committee / whitepaper / conference speaker)
  - temperature (a kodbazis eddig SOHA nem allitotta)
  - Authenticity Score MEGFORDITVA: a modell pontoz (szenzor), a kuszob a kodban (biro)

Amit a spec kert es NEM valositottam meg, indoklassal a jelentesben:
  - "Opus 5 Max / reasoning: high" — ez a motor gemini-2.5-flash-en fut, thinking
    kikapcsolva; a beallitas nem letezik
  - 220-250 token plafon — a projektben KETSZER volt csonkolas-hiba, es a kapu 175
    szoig engedi a kommentet; magyarul ez nem jon ki 220 tokenbol
  - "architecture" kemeny tiltolistara — egy AEC-eszkozben az iparag neve

A) A rubrika mint sema-mezo + a KODBELI kuszob
B) Bovitett nyitas-tiltolista
C) Nyitas-whitelist es anti-szerepek a promptban
D) Temperature
E) Gondolatjel CSAK angolban
F) Vegponttol vegpontig: alacsony pontszam -> pontosan EGY ujrairas
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


import responder.linkedin_engine as eng  # noqa: E402
from responder.linkedin_engine import (  # noqa: E402
    _COMPOSE_SCHEMA, _COMPOSE_PROMPT,
    _STOCK_OPENING_PATTERNS, _EM_DASH_PATTERN, DEFAULT_MODEL,
    temperature, check_quality, linkedin_model, looks_english,
)

POST = "How do you keep shared parameters aligned across linked Revit models?"
GOOD = ("I've run into this mostly at handover rather than during authoring. The "
        "shared parameter GUID travels with the definition file, not with the model, "
        "so once someone rebuilds that file the schedule mapping quietly detaches and "
        "nothing warns you. What has held up for us is versioning the definition file "
        "itself and treating it as project data rather than a local resource, because "
        "the drift only becomes visible weeks later when a schedule stops matching.")


# --- A) a rubrika TOROLVE (2026-08-10) --------------------------------------
# A 2026-08-01-i bevezetes sajat feltetelt szabott: "az egyetlen valodi proba, hogy
# korrelal-e a kezi benchmark-pontokkal. Ha nem, torolheto." HAROM eles meres, HAROM
# 10/10 — a `no_implementation_drift` mindharomszor 2 ("nulla drift"), kozben a
# harom komment "consultant mode"-ot, "foundational governance"-t es "cultural
# willingness to embed those capabilities"-t irt. Nem gyenge korrelacio: NULLA
# VARIANCIA. Ez a szekcio azt orzi, hogy a rubrika ne szivarogjon vissza csendben.
_AXES = ("voice_professional", "conversation_fit", "one_step_insight",
         "no_implementation_drift", "natural_language")

check("A1 a COMPOSE-sema CSAK a kommentet keri",
      list(_COMPOSE_SCHEMA["properties"]) == ["comment"]
      and _COMPOSE_SCHEMA["required"] == ["comment"],
      str(_COMPOSE_SCHEMA))
check("A2 egyetlen tengely sem maradt a semaban",
      not any(a in _COMPOSE_SCHEMA["properties"] for a in _AXES))
check("A3 a prompt MAR NEM ker onertekelest",
      "score it on five axes" not in _COMPOSE_PROMPT
      and "Higher is always better" not in _COMPOSE_PROMPT
      and not any(a in _COMPOSE_PROMPT for a in _AXES))
check("A4 a modul mar nem exportalja a rubrika szimbolumait",
      not any(hasattr(eng, n) for n in
              ("_AUTHENTICITY_DIMENSIONS", "AUTHENTICITY_MAX",
               "authenticity_score", "authenticity_min_score")),
      str([n for n in ("_AUTHENTICITY_DIMENSIONS", "AUTHENTICITY_MAX",
                       "authenticity_score", "authenticity_min_score")
           if hasattr(eng, n)]))

import inspect  # noqa: E402

_sig = inspect.signature(check_quality)
check("A5 a check_quality mar nem vesz auth_score/auth_min parametert",
      not any(p in _sig.parameters for p in ("auth_score", "auth_min")),
      str(list(_sig.parameters)))
check("A6 a kapu semmilyen bemenetre nem ad authenticity-sertest",
      not any("authenticity" in i for i in
              check_quality(GOOD, POST, False, "engineering_problem", "technical")))
check("A7 a REGI config-kulcs jelenlete nem tor el semmit (figyelmen kivul marad)",
      temperature({"linkedin": {"authenticity_min_score": 8, "temperature": 0.4}}) == 0.4)
check("A8 a parameter nelkuli hivas valtozatlanul atmegy",
      check_quality(GOOD, POST, False, "engineering_problem", "technical") == [],
      str(check_quality(GOOD, POST, False, "engineering_problem", "technical")))


# --- B) bovitett nyitas-tiltolista -----------------------------------------
NEW_OPENINGS = [
    "We frequently observe that parameter drift starts at handover. ",
    "One approach is to version the definition file. ",
    "Best practice is to keep the definition file under version control. ",
    "Organizations should treat the definition file as project data. ",
    "Implementation requires a versioned definition file. ",
    "Establishing a shared definition file avoids the drift. ",
    "Ensuring the definition file is versioned avoids the drift. ",
    "It is critical to version the definition file. ",
]
for i, opener in enumerate(NEW_OPENINGS, 1):
    issues = check_quality(opener + GOOD, POST, False, "engineering_problem", "technical")
    check(f"B{i} tiltott nyitas: {opener.split('.')[0][:38]}",
          any("nyitas" in x for x in issues), str(issues[:1]))

check("B9 a kifejezes a komment KOZEPEN nem serul (csak mondat-eleji egyezes)",
      not any("nyitas" in x for x in
              check_quality("I've run into the same thing, and what became best "
                            "practice for us was versioning that file. " + GOOD,
                            POST, False, "engineering_problem", "technical")),
      str(check_quality("I've run into the same thing, and what became best practice "
                        "for us was versioning that file. " + GOOD, POST, False,
                        "engineering_problem", "technical")))
check("B10 a whitelist nyitasai ATMENNEK a kapun",
      all(check_quality(o + GOOD[GOOD.index(' ') + 1:], POST, False,
                        "engineering_problem", "technical") == []
          for o in ("I've found that ", "One pattern I've noticed is that ")),
      "whitelist")
check("B11 minden minta forditható regex",
      all(re.compile(p) for p, _ in _STOCK_OPENING_PATTERNS))


# --- C) prompt: whitelist + anti-szerepek ---------------------------------
for shape in ("I've found", "I've run into", "One thing that stood out",
              "What strikes me", "We've learned", "One pattern I've noticed"):
    check(f"C1 whitelist a promptban: {shape}", shape in _COMPOSE_PROMPT)
for role in ("consultant", "standards committee", "solution architect",
             "whitepaper", "conference speaker"):
    check(f"C2 anti-szerep a promptban: {role}", role in _COMPOSE_PROMPT)
check("C3 a prompt tiltja a tanacs-zarast",
      "Do not end with advice" in _COMPOSE_PROMPT)
check("C4 a prompt kimondja: tarsakent, nem tanacsadokent",
      "PEER, NOT A CONSULTANT" in _COMPOSE_PROMPT)
check("C5 a prompt megfogalmazasa VISELKEDES-alapu, nem 'be authentic'",
      "be authentic" not in _COMPOSE_PROMPT.lower()
      and "be human" not in _COMPOSE_PROMPT.lower())


# --- D) temperature --------------------------------------------------------
check("D1 default 0.3", temperature({}) == 0.3)
check("D2 sajat ertek atmegy", temperature({"linkedin": {"temperature": 0.8}}) == 0.8)
check("D3 'default' -> None (API-default, a korabbi viselkedes)",
      temperature({"linkedin": {"temperature": "default"}}) is None
      and temperature({"linkedin": {"temperature": None}}) is None)
check("D4 ertelmetlen / hataron kivuli -> 0.3",
      temperature({"linkedin": {"temperature": "meleg"}}) == 0.3
      and temperature({"linkedin": {"temperature": 7}}) == 0.3
      and temperature({"linkedin": {"temperature": -1}}) == 0.3)
check("D5 a 0.0 ervenyes ertek (determinisztikus veg)",
      temperature({"linkedin": {"temperature": 0}}) == 0.0)


# --- G) modell-config szetvalasztasa ----------------------------------------
# A FO INVARIANS: ures `linkedin.model` eseten a viselkedes VALTOZATLAN — a
# szetvalasztas onmagaban semmit nem valtoztat, csak lehetove teszi a kulon
# hangolast (a classifier koltseg-erzekeny, a compose minoseg-erzekeny).
SHARED = {"scoring": {"gemini_model": "gemini-2.5-flash"}}
check("G1 ures linkedin.model -> orokli a globalist (VALTOZATLAN viselkedes)",
      linkedin_model({**SHARED, "linkedin": {"model": ""}}) == "gemini-2.5-flash")
check("G2 hianyzo linkedin.model -> orokli a globalist",
      linkedin_model(SHARED) == "gemini-2.5-flash")
check("G3 nincs linkedin szekcio sem -> orokli a globalist",
      linkedin_model({"scoring": {"gemini_model": "gemini-2.5-flash-lite"}})
      == "gemini-2.5-flash-lite")
check("G4 sajat modell FELULIRJA a globalist",
      linkedin_model({**SHARED, "linkedin": {"model": "gemini-3.6-flash"}})
      == "gemini-3.6-flash")
check("G5 a globalis valtozasa NEM erinti a sajatot",
      linkedin_model({"scoring": {"gemini_model": "gemini-2.5-flash-lite"},
                      "linkedin": {"model": "gemini-3.6-flash"}}) == "gemini-3.6-flash")
check("G6 'inherit'/'default'/'none' is oroklest jelent",
      all(linkedin_model({**SHARED, "linkedin": {"model": v}}) == "gemini-2.5-flash"
          for v in ("inherit", "default", "none", "INHERIT", "  ")))
check("G7 None ertek -> oroklés (nem TypeError)",
      linkedin_model({**SHARED, "linkedin": {"model": None}}) == "gemini-2.5-flash")
check("G8 teljesen ures config -> a kodbeli default",
      linkedin_model({}) == DEFAULT_MODEL and DEFAULT_MODEL == "gemini-2.5-flash")
check("G9 ures globalis + ures sajat -> a kodbeli default (nem ures string)",
      linkedin_model({"scoring": {"gemini_model": ""}, "linkedin": {"model": ""}})
      == DEFAULT_MODEL)
check("G10 korulvago szokoz nem szamit",
      linkedin_model({**SHARED, "linkedin": {"model": "  gemini-3.6-flash  "}})
      == "gemini-3.6-flash")

# A classifier es a draft-utak SZANDEKOSAN a globalis erteken maradnak: azok a
# nagy volumenu / alacsonyabb tetu utak. Ez a teszt rogziti, hogy a szetvalasztas
# NEM szivargott at oda.
_eng_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "responder", "draft_generator.py"), encoding="utf-8").read()
_clf_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "classifier", "pain_classifier.py"), encoding="utf-8").read()
check("G11 a classifier a GLOBALIS modellt olvassa, es nem tud a linkedin-knobrol",
      'sc.get("gemini_model"' in _clf_src
      and "linkedin_model" not in _clf_src
      and '"linkedin"' not in _clf_src)
check("G12 a draft-utak tovabbra is a GLOBALIS modellt hasznaljak",
      _eng_src.count('sc.get("gemini_model", "gemini-2.5-flash")') == 4
      and "linkedin_model" not in _eng_src)

# A `linkedin_model()` onmagaban helyes — de az szamit, hogy a HIVASBA is az kerul.
# A `_client()` a bekotesi pont; kulcs nelkul hibat ad, ezert azt is stubolni kell.
import responder.linkedin_engine as _eng_mod2  # noqa: E402

_real_secret = _eng_mod2.get_secret
_eng_mod2.get_secret = lambda *a, **k: "teszt-kulcs"


class _NullClient:
    def __init__(self, api_key=None):
        pass


_real_genai_client = _eng_mod2.genai.Client
_eng_mod2.genai.Client = _NullClient
try:
    ON = {"scoring": {"gemini_enabled": True, "gemini_model": "gemini-2.5-flash"}}
    _, m_inherit, _ = _eng_mod2._client({**ON, "linkedin": {"model": ""}})
    _, m_own, _ = _eng_mod2._client({**ON, "linkedin": {"model": "gemini-3.6-flash"}})
finally:
    _eng_mod2.get_secret = _real_secret
    _eng_mod2.genai.Client = _real_genai_client

check("G13 BEKOTVE: ures knob -> a hivas a globalis modellel megy",
      m_inherit == "gemini-2.5-flash", m_inherit)
check("G14 BEKOTVE: sajat knob -> a hivas a sajat modellel megy",
      m_own == "gemini-3.6-flash", m_own)


# --- E) gondolatjel csak angolban ------------------------------------------
EN_DASH_COMMENT = GOOD.replace("authoring. The", "authoring — the")
check("E1 gondolatjel ANGOL kommentben SERTES",
      any("gondolatjel" in i for i in
          check_quality(EN_DASH_COMMENT, POST, False, "engineering_problem", "technical")))
HU_POST = ("Hogyan tartjatok szinkronban a megosztott parametereket linkelt Revit "
           "modellek kozott? Nalunk mindig elcsuszik valami.")
HU_COMMENT = ("Nalunk ez inkabb az atadasnal jott elo, nem a szerkesztes alatt — a "
              "megosztott parameter GUID-ja a definicios fajlhoz tartozik, nem a "
              "modellhez, ezert amint valaki ujragyartja azt a fajlt, a kimutatas "
              "hozzarendelese csendben leszakad. Ami nalunk kitartott, az a definicios "
              "fajl verziozasa es projektadatkent kezelese, mert az elcsuszas csak "
              "hetekkel kesobb valik lathatova.")
check("E2 MAGYAR kommentben a gondolatjel NEM sertes (legitim irasjel)",
      not looks_english(HU_POST)
      and not any("gondolatjel" in i for i in
                  check_quality(HU_COMMENT, HU_POST, False, "craftsmanship", "technical")),
      str(check_quality(HU_COMMENT, HU_POST, False, "craftsmanship", "technical")))
check("E3 a minta csak a hosszu gondolatjelre (—) mer, a kotojelre nem",
      _EM_DASH_PATTERN.search("a—b") and not _EM_DASH_PATTERN.search("a-b")
      and not _EM_DASH_PATTERN.search("a–b"))


# --- F) vegponttol vegpontig ------------------------------------------------
import json as _json  # noqa: E402

REASON_OUT = {
    "topic": "revit", "post_type": "question",
    "conversation_intent": "question_to_community", "discourse_level": "technical",
    "expected_responder_role": "technical_advisor",
    "response_mode": "answer_the_question", "human_temperature": "practical",
    "topic_gravity": "shared parameter mapping",
    "author_objective": "get an answer", "audience": "BIM coordinators",
    "technical_depth": "practitioner", "emotional_tone": "neutral",
    "core_thesis": "Shared parameters drift across linked models.",
    "missing_perspective": "lifecycle",
    "missing_perspective_reason": "Handover is not discussed.",
    "strategy_fit": {"constructive_challenge": 2, "systems_thinking": 4,
                     "field_experience": 9, "business_impact": 3,
                     "future_outlook": 1, "practical_lesson": 8,
                     "missing_perspective": 4},
    "strategy_reason": "answer it usefully",
    "explicit_tool_request": False, "tool_request_quote": "",
    "insight": "The GUID travels with the definition file, not the model.",
    "confidence": 0.8,
}

REASON_OUT["vendor_promotion"] = False
REASON_OUT["promotion_evidence"] = ""

calls = []
# Az ujrairast mostantol VALODI kapu-sertes valtja ki, nem onertekelés: az elso
# kor marketing-kliset tartalmaz (`game-changer`), a masodik tiszta.
BAD_FIRST = "This is a game-changer for the whole industry. " + GOOD
# A fake EBBOL a sorbol ad vissza, korönként. Futasonkent EXPLICITEN allitjuk be —
# egy futas-fuggetlen szamlalo korabban a masodik futasra is a rossz valtozatot adta.
compose_outputs: list[str] = []


class _FakeResp:
    def __init__(self, text):
        self.text = text


class _FakeModels:
    def generate_content(self, model=None, contents=None, config=None):
        schema = config.response_schema or {}
        props = schema.get("properties", {})
        wants_reason = "strategy_fit" in props
        calls.append({"stage": "reason" if wants_reason else "compose",
                      "temperature": getattr(config, "temperature", None),
                      "schema_props": list(props)})
        if wants_reason:
            return _FakeResp(_json.dumps(REASON_OUT))
        n = sum(1 for c in calls if c["stage"] == "compose") - 1
        return _FakeResp(_json.dumps(
            {"comment": compose_outputs[min(n, len(compose_outputs) - 1)]}))


class _FakeClient:
    models = _FakeModels()


_real = eng._client
eng._client = lambda config: (_FakeClient(), "gemini-2.5-flash", None)
try:
    eng.reset_opening_state()
    compose_outputs[:] = [BAD_FIRST, GOOD]          # 1. kor sertes -> ujrairas
    res = eng.generate_comment({"linkedin": {"temperature": 0.3}}, POST)
    calls_scored = list(calls)
    calls.clear()
    eng.reset_opening_state()
    compose_outputs[:] = [GOOD]                      # mar az 1. kor tiszta
    res_off = eng.generate_comment({"linkedin": {"temperature": "default"}}, POST)
    calls_off = list(calls)
finally:
    eng._client = _real
    eng.reset_opening_state()

check("F1 nincs hiba", "error" not in res, str(res.get("error", "")))
check("F2 a KAPU-SERTES pontosan EGY ujrairast valtott ki (1 reason + 2 compose)",
      len(calls_scored) == 3 and [c["stage"] for c in calls_scored]
      == ["reason", "compose", "compose"], str([c["stage"] for c in calls_scored]))
check("F3 az ujrairas utan a kapu atengedte", res.get("quality_issues") == [],
      str(res.get("quality_issues")))
check("F4 az ELSO kor sertese naplozva van (megmagyarazza az ujrairast)",
      any("marketing-klise" in i for i in (res.get("quality_issues_first") or [])),
      str(res.get("quality_issues_first")))
check("F5 a valaszban NINCS egyetlen authenticity-mezo sem",
      not any(k.startswith("authenticity") for k in res),
      str([k for k in res if k.startswith("authenticity")]))
check("F5.1 BEKOTVE: a COMPOSE-hivas semaja CSAK a kommentet keri",
      all(c["schema_props"] == ["comment"]
          for c in calls_scored if c["stage"] == "compose"),
      str([c["schema_props"] for c in calls_scored if c["stage"] == "compose"]))
check("F6 a temperature MINDKET hivasba atmegy",
      all(c["temperature"] == 0.3 for c in calls_scored), str(calls_scored))
check("F7 a temperature a valaszban is szerepel (auditalhato)",
      res.get("temperature") == 0.3)
check("F8 rewrites=1 az ujrairas miatt", res.get("rewrites") == 1, str(res.get("rewrites")))

check("F9 tiszta elso kor -> NINCS ujrairas (1 reason + 1 compose)",
      len(calls_off) == 2, str([c["stage"] for c in calls_off]))
check("F10 'default' temperature -> nem allitjuk be (API-default)",
      all(c["temperature"] is None for c in calls_off)
      and res_off.get("temperature") is None, str(calls_off))
check("F11 a DASHBOARD-SZERZODES all (8 legacy mezo)",
      all(k in res for k in ("topic", "post_type", "engagement_intent", "reply_style",
                             "brand_mode", "confidence", "reply_text", "rationale")))

print()
bad = 0
for name, ok, detail in results:
    if not ok:
        bad += 1
    print(f"  {'OK  ' if ok else 'FAIL'} {name}" + (f"   [{detail}]" if detail else ""))
print(f"\n{len(results) - bad}/{len(results)} teszt zold.")
sys.exit(1 if bad else 0)
