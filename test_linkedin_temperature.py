"""
Hivasonkenti homerseklet (2026-08-09, engine v5).

A HIBA, amit ez old meg: 2026-08-09-ig EGYETLEN `linkedin.temperature` hajtotta
mindket hivast, holott a kovetelmenyuk ellentetes.

  REASON  — enum + 0-10 pontszam a kimenet; az egesz architektura ez alatt van
            (intent -> bias -> veto -> strategia). Ingadozo osztalyozas = mas
            strategia = mas komment. -> ALACSONY a helyes.
  COMPOSE — nyilvanos proza; alacsony homerseklet a modalis, legaltalanosabb
            fogalmazas fele huz, ami maga az "LLM-hang". Es itt amugy is van
            precizebb kontroll: a determinisztikus kapu. -> NEM visszuk le.

A) `stage_temperature` szemantika
B) VISSZAFELE-KOMPATIBILITAS: regi config bitre valtozatlan
C) A kiszallitott config.yaml tenylegesen a szandekolt bontast adja
D) Vegponttol vegpontig: a ket hivas KULONBOZO erteket kap
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


import responder.linkedin_engine as eng  # noqa: E402
from responder.linkedin_engine import (  # noqa: E402
    _TEMPERATURE_STAGES, temperature, stage_temperature,
)

POST = "How do you keep shared parameters aligned across linked Revit models?"


def st(cfg, stage):
    return stage_temperature({"linkedin": cfg}, stage)


# --- A) szemantika ----------------------------------------------------------
check("A1 ket stage van definialva", _TEMPERATURE_STAGES == ("reason", "compose"))
check("A2 hianyzo kulcs -> orokli a bazist",
      st({"temperature": 0.7}, "reason") == 0.7
      and st({"temperature": 0.7}, "compose") == 0.7)
check("A3 'inherit' -> orokli a bazist",
      st({"temperature": 0.7, "reason_temperature": "inherit"}, "reason") == 0.7)
check("A4 explicit YAML-null -> orokli a bazist (nem csendes kikapcsolas)",
      st({"temperature": 0.7, "reason_temperature": None}, "reason") == 0.7)
check("A5 ures string -> orokli a bazist",
      st({"temperature": 0.7, "reason_temperature": ""}, "reason") == 0.7)
check("A6 'default' -> NEM allitjuk be (API-default), a bazistol fuggetlenul",
      st({"temperature": 0.7, "compose_temperature": "default"}, "compose") is None)
check("A7 'none' ugyanaz, mint 'default'",
      st({"temperature": 0.7, "compose_temperature": "none"}, "compose") is None)
check("A8 szam -> pontosan az az ertek",
      st({"temperature": 0.7, "reason_temperature": 0.2}, "reason") == 0.2)
check("A9 stringkent irt szam is elfogadott (YAML-idezojel)",
      st({"temperature": 0.7, "reason_temperature": "0.2"}, "reason") == 0.2)
check("A10 hataron kivuli ertek -> orokles (nem csendes viselkedes-valtas)",
      st({"temperature": 0.7, "reason_temperature": 5}, "reason") == 0.7
      and st({"temperature": 0.7, "reason_temperature": -1}, "reason") == 0.7)
check("A11 ertelmezhetetlen ertek -> orokles",
      st({"temperature": 0.7, "reason_temperature": "melegen"}, "reason") == 0.7)
check("A12 a hatar (0.0 es 2.0) BENNE van",
      st({"reason_temperature": 0.0}, "reason") == 0.0
      and st({"reason_temperature": 2.0}, "reason") == 2.0)

try:
    stage_temperature({}, "kompoze")
    bad_stage = False
except ValueError:
    bad_stage = True
check("A13 ismeretlen stage -> HANGOS hiba (programozoi hiba, nem csendes orokles)",
      bad_stage)

# --- B) visszafele-kompatibilitas -------------------------------------------
# Ez a szekcio a valodi kockazat: a szetvalasztas nem valtoztathat meg egyetlen
# meglevo konfiguraciot sem.
for base in (0.3, 0.0, 1.0, "default", "none", ""):
    cfg = {"temperature": base}
    want = temperature({"linkedin": cfg})
    got = (st(cfg, "reason"), st(cfg, "compose"))
    check(f"B1 regi config (temperature={base!r}) -> MINDKET hivas a bazison",
          got == (want, want), f"{got} vs {want}")

check("B2 teljesen ures config -> a kod-default (0.3) mindket hivason",
      stage_temperature({}, "reason") == stage_temperature({}, "compose")
      == temperature({}) == 0.3)
check("B3 linkedin-blokk nelkuli config sem tor el",
      stage_temperature({"scoring": {}}, "compose") == temperature({"scoring": {}}))

# --- C) a kiszallitott config.yaml ------------------------------------------
import yaml  # noqa: E402

with io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml"),
             encoding="utf-8") as fh:
    LIVE = yaml.safe_load(fh)

check("C1 a config.yaml parse-olhato es van linkedin-blokkja",
      isinstance(LIVE.get("linkedin"), dict))
check("C2 REASON alacsony (stabil osztalyozas)",
      stage_temperature(LIVE, "reason") == 0.2,
      str(stage_temperature(LIVE, "reason")))
check("C3 COMPOSE nincs levive (API-default marad)",
      stage_temperature(LIVE, "compose") is None,
      str(stage_temperature(LIVE, "compose")))
check("C4 a REASON nem 0.0 (a lapos pontszam-eloszlas a holtversenyt a "
      "constructive_challenge-re vinne)",
      stage_temperature(LIVE, "reason") > 0.0)
check("C5 a ket ertek TENYLEGESEN kulonbozik (a bontasnak van hatasa)",
      stage_temperature(LIVE, "reason") != stage_temperature(LIVE, "compose"))
check("C6 a YAML nem alakitotta booleanna a 'default'-ot",
      isinstance(LIVE["linkedin"]["compose_temperature"], str))

# --- D) vegponttol vegpontig ------------------------------------------------
import json as _json  # noqa: E402

REASON_OUT = {
    "topic": "revit", "post_type": "question",
    "conversation_intent": "engineering_problem", "discourse_level": "technical",
    "expected_responder_role": "peer_practitioner",
    "response_mode": "extend_one_insight", "human_temperature": "practical",
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
GOOD = ("I've run into this mostly at handover rather than during authoring. The "
        "shared parameter GUID travels with the definition file, not with the model, "
        "so once someone rebuilds that file the schedule mapping quietly detaches and "
        "nothing warns you. What has held up for us is versioning the definition file "
        "itself and treating it as project data rather than a local resource, because "
        "the drift only becomes visible weeks later when a schedule stops matching.")

calls = []


class _FakeResp:
    def __init__(self, text):
        self.text = text


class _FakeModels:
    def generate_content(self, model=None, contents=None, config=None):
        props = (config.response_schema or {}).get("properties", {})
        stage = "reason" if "strategy_fit" in props else "compose"
        calls.append({"stage": stage, "temperature": getattr(config, "temperature", None)})
        if stage == "reason":
            return _FakeResp(_json.dumps(REASON_OUT))
        return _FakeResp(_json.dumps({
            "comment": GOOD, "voice_professional": 2, "conversation_fit": 2,
            "one_step_insight": 2, "no_implementation_drift": 2, "natural_language": 2,
        }))


class _FakeClient:
    models = _FakeModels()


_real = eng._client
eng._client = lambda config: (_FakeClient(), "gemini-2.5-flash", None)
try:
    eng._recent_openings.clear()
    res_split = eng.generate_comment(
        {"linkedin": {"reason_temperature": 0.2, "compose_temperature": "default"}}, POST)
    calls_split = list(calls)
    calls.clear()

    eng._recent_openings.clear()
    res_legacy = eng.generate_comment({"linkedin": {"temperature": 0.3}}, POST)
    calls_legacy = list(calls)
finally:
    eng._client = _real
    eng._recent_openings.clear()

by_stage = {c["stage"]: c["temperature"] for c in calls_split}
check("D1 nincs hiba", "error" not in res_split, str(res_split.get("error", "")))
check("D2 a REASON-hivas 0.2-t kapott", by_stage.get("reason") == 0.2, str(calls_split))
check("D3 a COMPOSE-hivas NEM kapott temperature-t (API-default)",
      "compose" in by_stage and by_stage["compose"] is None, str(calls_split))
check("D4 a ket hivas tenylegesen kulonbozo erteken futott",
      by_stage.get("reason") != by_stage.get("compose"))
check("D5 a valasz mindket tenyleges erteket visszaadja (auditalhato)",
      res_split.get("reason_temperature") == 0.2
      and res_split.get("compose_temperature") is None,
      f"{res_split.get('reason_temperature')} / {res_split.get('compose_temperature')}")

check("D6 REGI config (csak `temperature`) -> MINDKET hivas 0.3, valtozatlanul",
      [c["temperature"] for c in calls_legacy] == [0.3, 0.3], str(calls_legacy))
check("D7 a `temperature` bazis-mezo megmaradt a valaszban (regi szerzodes)",
      res_legacy.get("temperature") == 0.3)
check("D8 a DASHBOARD-SZERZODES all (8 legacy mezo)",
      all(k in res_split for k in ("topic", "post_type", "engagement_intent",
                                   "reply_style", "brand_mode", "confidence",
                                   "reply_text", "rationale")))

print()
bad = 0
for name, ok, detail in results:
    if not ok:
        bad += 1
    print(f"  {'OK  ' if ok else 'FAIL'} {name}" + (f"   [{detail}]" if detail else ""))
print(f"\n{len(results) - bad}/{len(results)} teszt zold.")
sys.exit(1 if bad else 0)
