"""
LinkedIn-motor telemetria (2026-08-09, engine v5).

A CEL: a motor minden dontest visszaad a valaszban, de a valasz a HTTP-korrel
eltunik — ezert ma nem tudod megvalaszolni, hogy nyer-e valaha a
`constructive_challenge`, homalyos-e a komment (`concreteness`),
hat-e a homerseklet-bontas, es szor-e a nyitas-rotacio.

A) Config: kapcsolo es utfeloldas
B) `build_row` — TISZTA fuggveny, fajlrendszer nelkul teszthető
C) ADATVEDELEM: mi NEM kerul a naploba
D) `record` — iras, hozzafuzes, es hogy SOHA nem dob
E) Vegponttol vegpontig, a sikeres ES a hibas uton is
"""
import io
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


import responder.linkedin_engine as eng  # noqa: E402
import responder.linkedin_telemetry as tel  # noqa: E402
from responder.linkedin_telemetry import (  # noqa: E402
    BASE_DIR, DEFAULT_PATH, TELEMETRY_SCHEMA, _COPIED_FIELDS,
    build_row, post_id, record, telemetry_enabled, telemetry_path,
)

POST = "How do you keep shared parameters aligned across linked Revit models?"
TMP = tempfile.mkdtemp(prefix="nodu-tel-")


def tmp_cfg(**extra):
    return {"linkedin": {"telemetry": "on",
                         "telemetry_path": os.path.join(TMP, "t.jsonl"), **extra}}


def read_lines(path):
    if not os.path.exists(path):
        return []
    with io.open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


# --- A) config --------------------------------------------------------------
check("A1 KOD-DEFAULT kikapcsolt (teszt/import nem ir csendben lemezre)",
      telemetry_enabled({}) is False and telemetry_enabled({"linkedin": {}}) is False)
check("A2 'on' -> bekapcsolva",
      telemetry_enabled({"linkedin": {"telemetry": "on"}}) is True)
check("A3 'off' -> kikapcsolva",
      telemetry_enabled({"linkedin": {"telemetry": "off"}}) is False)
check("A4 YAML-boolean True/False kezelve (§4/17)",
      telemetry_enabled({"linkedin": {"telemetry": True}}) is True
      and telemetry_enabled({"linkedin": {"telemetry": False}}) is False)
check("A5 ismeretlen ertek -> KIKAPCSOLT (a naplozas nem indul el veletlenul)",
      telemetry_enabled({"linkedin": {"telemetry": "talan"}}) is False)

check("A6 default ut a dashboard gyokerehez kepest oldodik fel",
      telemetry_path({}) == os.path.join(BASE_DIR, DEFAULT_PATH))
check("A7 relativ ut a gyokerhez kotodik, nem a munkakonyvtarhoz",
      telemetry_path({"linkedin": {"telemetry_path": "storage/x.jsonl"}})
      == os.path.join(BASE_DIR, "storage/x.jsonl"))
abs_path = os.path.join(TMP, "abs.jsonl")
check("A8 abszolut ut valtozatlanul marad",
      telemetry_path({"linkedin": {"telemetry_path": abs_path}}) == abs_path)
check("A9 ures ut -> a default",
      telemetry_path({"linkedin": {"telemetry_path": "  "}})
      == os.path.join(BASE_DIR, DEFAULT_PATH))

# --- B) build_row -----------------------------------------------------------
RESULT = {
    "reply_text": "I've run into this at handover rather than during authoring.",
    # A REASON gondolatmenete — a redundancia-diagnozishoz kell (2026-08-10).
    "insight": "The GUID travels with the definition file, not the model.",
    "core_thesis": "Shared parameters drift across linked models.",
    "missing_perspective": "lifecycle",
    "engine": "linkedin-tle-v8", "strategy": "field_experience",
    "strategy_label": "Field Experience",
    "strategy_fit": {"field_experience": 9, "constructive_challenge": 2},
    "strategy_scores": {"field_experience": 11.0, "constructive_challenge": 2.0},
    "strategy_vetoed": ["business_impact"],
    "conversation_intent": "engineering_problem", "discourse_level": "technical",
    "expected_responder_role": "peer_practitioner",
    "response_mode": "extend_one_insight", "human_temperature": "practical",
    "topic": "revit", "post_type": "question", "technical_depth": "practitioner",
    "topic_gravity": "shared parameter mapping", "intent_layer": True,
    "opening_shape": "encountered", "opening_recent": ["pattern"],
    "temperature": None, "reason_temperature": 0.2, "compose_temperature": None,
    "concreteness": {"words": 60, "anchors_added": 2,
                     "anchor_terms": ["ifc", "handover"], "abstract_count": 1,
                     "abstract_terms": ["coordination"], "hedges": 0,
                     "hedge_terms": [], "anchors_shared_with_post": []},
    "quality_issues": [], "quality_issues_first": [], "rewrites": 0,
    "post_overlap": 0.04, "ai_fingerprint_terms": [], "confidence": 0.8,
    "brand_mode": "none", "brand_allowed": False,
    "brand_gate_reason": "a poszt nem ker eszkozt",
    "image_attached": False, "image_role": "",
}

NOW = datetime(2026, 8, 9, 12, 30, tzinfo=timezone.utc)
row = build_row(RESULT, POST, elapsed_ms=1234, now=NOW)

check("B1 a sor jelolt: idobelyeg, sema-verzio, ok",
      row["ts"].startswith("2026-08-09T12:30")
      and row["schema"] == TELEMETRY_SCHEMA and row["ok"] is True)
check("B2 a NEGY nyitott kerdes mezoi mind benne vannak",
      all(k in row for k in ("strategy", "strategy_scores", "concreteness",
                             "reason_temperature", "compose_temperature",
                             "opening_shape", "rewrites")))
# 2026-08-10: a rubrika torolve (harom meres, harom 10/10 — nulla variancia). Ez a
# teszt orzi, hogy a mezoi ne kerulhessenek vissza csendben a naploba.
check("B2.1 az authenticity-mezok MAR NEM kerulnek a naploba",
      not any(k.startswith("authenticity") for k in row),
      str([k for k in row if k.startswith("authenticity")]))
# 2026-08-10: az otodik eles meres UJ hibatipust hozott (szemantikai redundancia:
# a komment 75%-a a poszt sajat teteleet mondta ujra, mas szavakkal -> a 4-gram
# `post_overlap` 0.0-t adott). A diagnozishoz a REASON gondolatmenete kell.
check("B2.2 a REASON gondolatmenete is naplozva van (redundancia-diagnozis)",
      all(k in row for k in ("insight", "core_thesis", "missing_perspective")),
      str([k for k in ("insight", "core_thesis", "missing_perspective")
           if k not in row]))
check("B3 minden atvett mezo bekerult, ha a valaszban volt",
      all(k in row for k in _COPIED_FIELDS if k in RESULT))
check("B4 a komment TELJES szovege benne van (ezt pontozod)",
      row["reply_text"] == RESULT["reply_text"] and row["reply_words"] == 10,
      str(row.get("reply_words")))
check("B5 elapsed_ms atmegy", row["elapsed_ms"] == 1234)
check("B6 JSON-serializalhato (a naplo sora ervenyes JSON)",
      json.loads(json.dumps(row, ensure_ascii=False))["strategy"] == "field_experience")

# --- C) adatvedelem: mi NEM kerul bele --------------------------------------
long_post = "Nagyon hosszu LinkedIn poszt. " * 40
row_long = build_row(RESULT, long_post)
check("C1 a poszt TELJES szovege NINCS a naploban (masvalaki tartalma)",
      long_post.strip() not in json.dumps(row_long, ensure_ascii=False))
check("C2 a reszlet 160 karakterre vagva", len(row_long["post_excerpt"]) == 160)
check("C3 a post_words a TELJES posztot meri (a reszlet ellenere)",
      row_long["post_words"] == len(long_post.split()))
check("C4 post_id stabil: ugyanaz a poszt -> ugyanaz az id",
      post_id(POST) == post_id(POST + "  ") == row["post_id"])
check("C5 post_id kulonbozik mas posztra", post_id(POST) != post_id("Mas poszt."))

leaky = {**RESULT, "image_bytes": b"\xff\xd8\xff", "post_text": POST,
         "valami_jovobeli_nyers_mezo": "titok"}
row_leaky = build_row(leaky, POST)
blob = json.dumps(row_leaky, ensure_ascii=False)
check("C6 CSAK a listazott mezok kerulnek at — uj valasz-mezo NEM szivarog be",
      "valami_jovobeli_nyers_mezo" not in row_leaky
      and "image_bytes" not in row_leaky and "post_text" not in row_leaky)
check("C7 a kep semmilyen formaban nincs a sorban", "titok" not in blob)

err_row = build_row({"error": "Gemini API hiba (reasoning): 429"}, POST)
check("C8 hibas ut: ok=false, a hiba benne, de NINCS reply_text",
      err_row["ok"] is False and "429" in err_row["error"]
      and "reply_text" not in err_row)
check("C9 a hibas sor is parosithato (van post_id)", err_row["post_id"] == row["post_id"])

# --- D) record --------------------------------------------------------------
off_path = os.path.join(TMP, "nem-szabad-letrejonnie.jsonl")
check("D1 kikapcsolva NEM ir es False-t ad",
      record({"linkedin": {"telemetry": "off", "telemetry_path": off_path}},
             RESULT, POST) is False
      and not os.path.exists(off_path))

cfg = tmp_cfg()
p = telemetry_path(cfg)
check("D2 bekapcsolva ir es True-t ad", record(cfg, RESULT, POST, 10) is True)
check("D3 pontosan egy sor", len(read_lines(p)) == 1)
record(cfg, RESULT, POST, 20)
record(cfg, {"error": "x"}, POST, 30)
lines = read_lines(p)
check("D4 HOZZAFUZ, nem felulir (3 sor)", len(lines) == 3, str(len(lines)))
check("D5 a hibas sor is bekerult", lines[-1]["ok"] is False)
check("D6 minden sor onalloan ervenyes JSON, sema-verzioval",
      all(l["schema"] == TELEMETRY_SCHEMA for l in lines))

deep = os.path.join(TMP, "nincs", "ilyen", "konyvtar", "t.jsonl")
check("D7 hianyzo konyvtarat letrehoz",
      record({"linkedin": {"telemetry": "on", "telemetry_path": deep}}, RESULT, POST)
      and os.path.exists(deep))

# A kritikus invarians: a naplozas hibaja NEM torolheti el a mar kifizetett
# LLM-hivas eredmenyet, tehat kivetel SEM johet ki innen.
bad = record({"linkedin": {"telemetry": "on", "telemetry_path": TMP}}, RESULT, POST)
check("D8 irhatatlan ut (konyvtar fajl helyett) -> False, de NEM dob kivetelt",
      bad is False)


class _Boom(dict):
    def get(self, *a, **k):
        raise RuntimeError("keyboom")


check("D9 hibas config-objektum sem dob kivetelt", record(_Boom(), RESULT, POST) is False)

# --- E) vegponttol vegpontig ------------------------------------------------
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


class _FakeResp:
    def __init__(self, text):
        self.text = text


class _FakeModels:
    def generate_content(self, model=None, contents=None, config=None):
        if "strategy_fit" in (config.response_schema or {}).get("properties", {}):
            return _FakeResp(json.dumps(REASON_OUT))
        return _FakeResp(json.dumps({
            "comment": GOOD, "voice_professional": 2, "conversation_fit": 2,
            "one_step_insight": 2, "no_implementation_drift": 2, "natural_language": 2,
        }))


class _FakeClient:
    models = _FakeModels()


e2e = os.path.join(TMP, "e2e.jsonl")
E2E_CFG = {"linkedin": {"telemetry": "on", "telemetry_path": e2e,
                        "reason_temperature": 0.2, "compose_temperature": "default"}}

_real = eng._client
eng._client = lambda config: (_FakeClient(), "gemini-2.5-flash", None)
try:
    eng._recent_openings.clear()
    res = eng.generate_comment(E2E_CFG, POST)
finally:
    eng._client = _real
    eng._recent_openings.clear()

# Hibas ut STUB NELKUL: kikapcsolt Gemini -> a motor korán visszater.
res_err = eng.generate_comment(
    {**E2E_CFG, "scoring": {"gemini_enabled": False}}, POST)

e2e_lines = read_lines(e2e)
check("E1 a sikeres hivas irt egy sort", len(e2e_lines) >= 1)
ok_row = e2e_lines[0]
check("E2 nincs hiba a generalasban", "error" not in res, str(res.get("error", "")))
check("E3 a sor a TENYLEGES dontest orzi (nem a stubot talalgatja)",
      ok_row["strategy"] == res["strategy"]
      and ok_row["opening_shape"] == res["opening_shape"]
      and ok_row["reply_text"] == res["reply_text"])
check("E4 a ket homerseklet kulon szerepel (a bontas merheto)",
      ok_row["reason_temperature"] == 0.2 and ok_row["compose_temperature"] is None)
check("E5 a strategia-pontszamok benne vannak (1. kerdes megvalaszolhato)",
      isinstance(ok_row.get("strategy_scores"), dict)
      and "constructive_challenge" in ok_row["strategy_scores"])
check("E6 a konkretsag-diagnosztika benne van (a rubrika helyere lepett)",
      isinstance(ok_row.get("concreteness"), dict)
      and "anchors_added" in ok_row["concreteness"],
      str(ok_row.get("concreteness")))
check("E7 elapsed_ms merve", isinstance(ok_row.get("elapsed_ms"), int))

check("E8 a HIBAS ut is sort ir (a korai return-oket a wrapper fogja)",
      len(e2e_lines) == 2 and e2e_lines[1]["ok"] is False, str(len(e2e_lines)))
check("E9 a hibas sor a valodi hibauzenetet orzi",
      "error" in res_err and e2e_lines[1]["error"].startswith(res_err["error"][:20]))

shutil.rmtree(TMP, ignore_errors=True)

print()
bad_n = 0
for name, ok, detail in results:
    if not ok:
        bad_n += 1
    print(f"  {'OK  ' if ok else 'FAIL'} {name}" + (f"   [{detail}]" if detail else ""))
print(f"\n{len(results) - bad_n}/{len(results)} teszt zold.")
sys.exit(1 if bad_n else 0)
