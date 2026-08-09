"""
Nyitas-rotacio (2026-08-09, engine v5).

A MERT HIBA, amit ez old meg: a 2026-08-01-i Authenticity Layer hat termeszetes
nyito-formát AJANLOTT a compose-promptban, de a determinisztikus kapu csak a
TANACSADOI nyitasokat tiltja — a motor sajat whitelistjenek ismetlodese ellen
semmi nem vedett. A hiba a kommentek KOZOTT keletkezik, ezert egy kommenten
beluli regex elvileg sem lathatja: ket komment kulon-kulon hibatlan, sorozatban
megis felismerheto.

A) Katalogus es a system-prompt
B) BAJTRA-AZONOSSAG kikapcsolt rotacioval (a tiszta A/B feltetele)
C) pick_opening — determinizmus, kizaras, szoras, szabad valaszformak
D) A determinizmus PROCESSZEK KOZOTT is all (sha256, nem a randomizalt hash())
E) A gyűrű
F) Config-kapcsolo
G) A sajat nyitasok nem sertik a sajat kaput
H) Vegponttol vegpontig
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


import responder.linkedin_engine as eng  # noqa: E402
from responder.linkedin_engine import (  # noqa: E402
    OPENING_SHAPES, _V4_OPENING_KEYS, _OPENING_FREE_MODES, _OPENING_RING_SIZE,
    _COMPOSE_PROMPT, _STOCK_OPENING_PATTERNS, _FORBIDDEN_PATTERNS,
    _recent_openings, pick_opening, remember_opening, opening_variety_enabled,
    _compose_user_msg,
)

POST = "How do you keep shared parameters aligned across linked Revit models?"

REASONING = {
    "strategy": "field_experience",
    "conversation_intent": "engineering_problem",
    "discourse_level": "technical",
    "expected_responder_role": "peer_practitioner",
    "response_mode": "extend_one_insight",
    "human_temperature": "practical",
    "topic_gravity": "shared parameter mapping",
    "core_thesis": "Shared parameters drift across linked models.",
    "missing_perspective": "lifecycle",
    "missing_perspective_reason": "Handover is not discussed.",
    "insight": "The GUID travels with the definition file, not the model.",
}

# A v4-es nyitas-mondat SZO SZERINT. Ha ez a literal elavul, a B szekcio elbukik —
# ez a szandék: a bajtra-azonossag allitasat nem szabad csendben elveszíteni.
V4_OPENING_SENTENCE = (
    "Begin with the contribution itself, not a stock consultant opening "
    "such as 'We often see', 'One consideration', 'In practice' or 'One "
    "recurring challenge'. Vary the rhetorical shape naturally."
)


def _msg(opening="", **kw):
    return _compose_user_msg(POST, "", REASONING, False, opening=opening, **kw)


# --- A) katalogus es system-prompt ------------------------------------------
check("A1 nyolc nyito-forma, mind example+move parral",
      len(OPENING_SHAPES) == 8
      and all(set(v) >= {"example", "move"} and v["example"] and v["move"]
              for v in OPENING_SHAPES.values()),
      str(list(OPENING_SHAPES)))
check("A2 a v4-katalogus pontosan hat elemu, mind letezo kulcs",
      len(_V4_OPENING_KEYS) == 6
      and all(k in OPENING_SHAPES for k in _V4_OPENING_KEYS))
check("A3 a ket UJ forma NINCS a system-prompt katalogusaban (ez teszi A/B-zhetove)",
      set(OPENING_SHAPES) - set(_V4_OPENING_KEYS) == {"straight", "condition"})
check("A4 a system-prompt pontosan a hat v4-es peldat sorolja fel",
      all(OPENING_SHAPES[k]["example"] in _COMPOSE_PROMPT for k in _V4_OPENING_KEYS))
check("A5 a ket uj forma peldaja NEM szerepel a system-promptban",
      OPENING_SHAPES["condition"]["example"] not in _COMPOSE_PROMPT
      and "no framing at all" not in _COMPOSE_PROMPT)
check("A6 a gyűrű merete kisebb a katalogusnal (marad valaszthato jelolt)",
      0 < _OPENING_RING_SIZE < len(OPENING_SHAPES),
      f"{_OPENING_RING_SIZE} < {len(OPENING_SHAPES)}")

# --- B) BAJTRA-AZONOSSAG kikapcsolt rotacioval -------------------------------
plain = _msg("")
check("B1 kijeloles nelkul a v4-es nyitas-mondat all elo, SZO SZERINT",
      V4_OPENING_SENTENCE in plain)
check("B2 kijeloles nelkul nincs OPENING SHAPE sor",
      "OPENING SHAPE" not in plain)

assigned = _msg("pattern")
check("B3 kijelolessel a tiltas VALTOZATLANUL benne van",
      "not a stock consultant opening" in assigned
      and "One consideration" in assigned)
check("B4 kijelolessel a 'Vary the rhetorical shape naturally.' zaras elmarad",
      "Vary the rhetorical shape naturally" not in assigned)
check("B5 a kijelolt forma MOVE-leirasa bekerul",
      OPENING_SHAPES["pattern"]["move"] in assigned)
check("B6 a kijeloles felulirja a system-prompt listajat (kimondva)",
      "overrides the list of shapes" in assigned)
check("B7 ervenytelen kulcs -> visszaesik a v4-es mondatra (nem tor el)",
      V4_OPENING_SENTENCE in _msg("nincs_ilyen_forma"))
check("B8 kikapcsolt intent layer eseten nincs nyitas-sor (v1-es prompt)",
      "OPENING SHAPE" not in _msg("pattern", intent_layer=False)
      and V4_OPENING_SENTENCE not in _msg("pattern", intent_layer=False))

# --- C) pick_opening --------------------------------------------------------
a = pick_opening(POST, "extend_one_insight", recent=[])
b = pick_opening(POST, "extend_one_insight", recent=[])
check("C1 determinisztikus: ugyanaz a poszt -> ugyanaz a forma", a == b, f"{a} / {b}")
check("C2 ervenyes kulcsot ad", a in OPENING_SHAPES, a)

excluded = [a]
c = pick_opening(POST, "extend_one_insight", recent=excluded)
check("C3 a kizart forma NEM jon vissza", c != a and c in OPENING_SHAPES, f"{a} -> {c}")

all_but_one = [k for k in OPENING_SHAPES if k != "condition"]
check("C4 het kizarva -> pontosan a maradek jon",
      pick_opening(POST, "extend_one_insight", recent=all_but_one) == "condition")
check("C5 MIND kizarva -> nem urul ki a valasztas (vedoszabaly)",
      pick_opening(POST, "extend_one_insight", recent=list(OPENING_SHAPES))
      in OPENING_SHAPES)

posts = [f"Different LinkedIn post number {i} about IFC and Revit." for i in range(40)]
spread = {pick_opening(p, "extend_one_insight", recent=[]) for p in posts}
check("C6 kulonbozo posztok szórnak (nem egyetlen formára esnek)",
      len(spread) >= 5, f"{len(spread)}/8: {sorted(spread)}")

for mode in sorted(_OPENING_FREE_MODES):
    check(f"C7 '{mode}' -> NINCS kijeloles (a valaszforma dontotte el a nyitast)",
          pick_opening(POST, mode, recent=[]) == "")
check("C8 ismeretlen valaszforma -> a konzervativ default (extend_one_insight) fut",
      pick_opening(POST, "nincs_ilyen_mod", recent=[]) in OPENING_SHAPES)

# --- D) a determinizmus PROCESSZEK KOZOTT is all -----------------------------
# A CPython a string-hash-t processzenkent randomizalja. Ha a valasztas a beepitett
# hash()-re epulne, ugyanaz a poszt ujraindulas utan MAS formát kapna — a
# "reprodukalhato dontes" allitas bukna, es ez a teszt hol atmenne, hol nem.
_probe = (
    "import sys; sys.path.insert(0, r'%s');"
    "from responder.linkedin_engine import pick_opening;"
    "print(pick_opening('cross process determinism probe', 'extend_one_insight', recent=[]))"
    % os.path.dirname(os.path.abspath(__file__))
)


def _run(seed):
    env = {**os.environ, "PYTHONHASHSEED": seed}
    out = subprocess.run([sys.executable, "-c", _probe], capture_output=True,
                         text=True, env=env, timeout=120)
    return out.stdout.strip(), out.stderr.strip()

d1, e1 = _run("0")
d2, e2 = _run("12345")
check("D1 ket kulon processz, kulon PYTHONHASHSEED -> UGYANAZ a forma",
      bool(d1) and d1 == d2, f"{d1!r} vs {d2!r} | {e1[-200:]}{e2[-200:]}")

# --- E) a gyűrű -------------------------------------------------------------
_recent_openings.clear()
remember_opening("pattern")
remember_opening("strikes")
check("E1 a gyűrű a kijelolt formakat orzi",
      list(_recent_openings) == ["pattern", "strikes"], str(list(_recent_openings)))
check("E2 ures kulcs nem kerul be (szabad valaszforma nem eget el helyet)",
      (remember_opening(""), list(_recent_openings) == ["pattern", "strikes"])[1])

_recent_openings.clear()
for k in list(OPENING_SHAPES):
    remember_opening(k)
check("E3 a gyűrű a legutobbi _OPENING_RING_SIZE elemre van vagva",
      len(_recent_openings) == _OPENING_RING_SIZE
      and list(_recent_openings) == list(OPENING_SHAPES)[-_OPENING_RING_SIZE:],
      str(list(_recent_openings)))
_recent_openings.clear()

# --- F) config --------------------------------------------------------------
check("F1 default: bekapcsolva", opening_variety_enabled({}) is True)
check("F2 'off' -> kikapcsolva",
      opening_variety_enabled({"linkedin": {"opening_variety": "off"}}) is False)
check("F3 YAML-boolean False (idezojel nelkuli 'off') -> kikapcsolva",
      opening_variety_enabled({"linkedin": {"opening_variety": False}}) is False)
check("F4 YAML-boolean True (idezojel nelkuli 'on') -> bekapcsolva",
      opening_variety_enabled({"linkedin": {"opening_variety": True}}) is True)

# --- G) a sajat nyitasok nem sertik a sajat kaput ----------------------------
# Egy onmagat legyozo whitelist a legrosszabb eset: a prompt ajanlana, a kapu
# elutasitana, es minden komment ujrairast kapna.
import re as _re  # noqa: E402

collisions = []
for key, shape in OPENING_SHAPES.items():
    probe = shape["example"].strip('"')
    for pattern, label in _STOCK_OPENING_PATTERNS + _FORBIDDEN_PATTERNS:
        if _re.search(pattern, probe, _re.IGNORECASE | _re.MULTILINE):
            collisions.append(f"{key} -> {label}")
check("G1 egyetlen ajanlott nyitas sem esik a sajat kapuba",
      not collisions, "; ".join(collisions))

# --- H) vegponttol vegpontig ------------------------------------------------
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

compose_msgs = []


class _FakeResp:
    def __init__(self, text):
        self.text = text


class _FakeModels:
    def generate_content(self, model=None, contents=None, config=None):
        props = (config.response_schema or {}).get("properties", {})
        if "strategy_fit" in props:
            return _FakeResp(_json.dumps(REASON_OUT))
        compose_msgs.append(contents)
        return _FakeResp(_json.dumps({
            "comment": GOOD, "voice_professional": 2, "conversation_fit": 2,
            "one_step_insight": 2, "no_implementation_drift": 2, "natural_language": 2,
        }))


class _FakeClient:
    models = _FakeModels()


_real = eng._client
eng._client = lambda config: (_FakeClient(), "gemini-2.5-flash", None)
try:
    _recent_openings.clear()
    res_on = eng.generate_comment({"linkedin": {}}, POST)
    ring_after = list(_recent_openings)
    msg_on = compose_msgs[-1]

    _recent_openings.clear()
    res_off = eng.generate_comment(
        {"linkedin": {"opening_variety": "off"}}, POST)
    msg_off = compose_msgs[-1]
    ring_off = list(_recent_openings)
finally:
    eng._client = _real
    _recent_openings.clear()

check("H1 nincs hiba", "error" not in res_on, str(res_on.get("error", "")))
check("H2 a valasz visszaadja a kijelolt formát (auditalhato)",
      res_on.get("opening_shape") in OPENING_SHAPES, str(res_on.get("opening_shape")))
check("H3 a compose-uzenet a kijelolt forma MOVE-leirasat kapta",
      OPENING_SHAPES[res_on["opening_shape"]]["move"] in msg_on)
check("H4 sikeres komment utan a gyűrű bővult",
      ring_after == [res_on.get("opening_shape")], str(ring_after))
check("H5 opening_variety=off -> NINCS kijeloles, a v4-es mondat all elo",
      res_off.get("opening_shape") == ""
      and V4_OPENING_SENTENCE in msg_off
      and "OPENING SHAPE" not in msg_off)
check("H6 opening_variety=off -> a gyűrű nem bővul", ring_off == [], str(ring_off))
check("H7 a DASHBOARD-SZERZODES all (8 legacy mezo)",
      all(k in res_on for k in ("topic", "post_type", "engagement_intent",
                                "reply_style", "brand_mode", "confidence",
                                "reply_text", "rationale")))
check("H8 az uj mezok additivak, a UI-t nem torik",
      "opening_shape" in res_on and "opening_recent" in res_on)

print()
bad = 0
for name, ok, detail in results:
    if not ok:
        bad += 1
    print(f"  {'OK  ' if ok else 'FAIL'} {name}" + (f"   [{detail}]" if detail else ""))
print(f"\n{len(results) - bad}/{len(results)} teszt zold.")
sys.exit(1 if bad else 0)
