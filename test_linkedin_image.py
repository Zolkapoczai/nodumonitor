"""
A poszt kepe mint BESOROLASI kontextus (2026-07-31).

A megrendelt viselkedes: a render-/foto-/screenshot-alapu posztokat a motor eddig
gyakorlatilag a caption alapjan sorolta be. A kep ezt pontositja — DE a komment
szovege tovabbra is a poszt szovegen all, mert a kep allitasait kodban NEM tudjuk
ellenorizni (ellentetben a `tool_request_quote`-tal).

A) Feltetelesseg — kep nelkul a REASON-hivas BAJTRA a korabbi (nulla token-koltseg)
B) A kep CSAK a REASON-be megy — a COMPOSE es az ujrairas nem fizeti ujra
C) Kapu: a kommentben a kepre hivatkozas SERTES (a szivargasi ut zarasa)
D) Config-kapcsolok (`image_input`, `image_max_px`) es az intent-layer interakcio
E) Route-validacio (`_decode_post_image`): JPEG-only, magic-byte, meret-plafon
F) A kliens-oldali atmeretezes szerzodese (a sablon es a szerver ugyanazt a
   plafont hasznalja)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


import responder.linkedin_engine as eng  # noqa: E402
from responder.linkedin_engine import (  # noqa: E402
    _IMAGE_ROLES, _IMAGE_REASON_BLOCK, _REASON_SCHEMA, _VISUAL_REFERENCE_PATTERNS,
    reason_prompt_for, reason_schema_for, check_quality,
    image_input_enabled, image_max_px,
)

POST = "Finished the facade panel family this week. Every mullion is parametric."
GOOD = ("Panel families like this usually survive handover only if the mullion "
        "parameters are driven from a single shared definition rather than typed per "
        "instance. Once a second person edits the family, per-instance values drift "
        "and the schedule stops matching the model. Flattening the nesting one level "
        "and pushing variation into a type catalogue keeps the structure readable for "
        "whoever opens it next, which matters more than the initial authoring speed.")


# --- A) feltetelesseg --------------------------------------------------------
check("A1 kep nelkul a REASON-prompt BAJTRA valtozatlan",
      reason_prompt_for(False) == eng._REASON_PROMPT)
check("A2 kep nelkul a REASON-sema UGYANAZ az objektum (nincs masolat sem)",
      reason_schema_for(False) is _REASON_SCHEMA)
check("A3 keppel a prompt hosszabb (a kep-blokk bekerul)",
      len(reason_prompt_for(True)) > len(reason_prompt_for(False))
      and _IMAGE_REASON_BLOCK in reason_prompt_for(True))
check("A4 keppel az image_role KOTELEZO sema-mezo",
      "image_role" in reason_schema_for(True)["properties"]
      and "image_role" in reason_schema_for(True)["required"])
check("A5 kep NELKUL az image_role nincs a semaban",
      "image_role" not in reason_schema_for(False)["properties"])
check("A6 az image_role enum == a kod szerinti roles",
      reason_schema_for(True)["properties"]["image_role"]["enum"] == _IMAGE_ROLES)
check("A7 a kep-blokk kimondja, hogy TILOS a kepet leirni",
      "do NOT describe the image" in _IMAGE_REASON_BLOCK
      and "insight" in _IMAGE_REASON_BLOCK)
check("A8 a keppel bovitett sema nem rontja el az eredetit (nincs mellekhatas)",
      "image_role" not in _REASON_SCHEMA["properties"]
      and "image_role" not in _REASON_SCHEMA["required"])


# --- C) kapu: kepre hivatkozas ----------------------------------------------
check("C1 tiszta komment ATMEGY, holott volt kep",
      check_quality(GOOD, POST, False, "craftsmanship", "technical",
                    image_attached=True) == [],
      str(check_quality(GOOD, POST, False, "craftsmanship", "technical", image_attached=True)))

REFS_EN = [
    "In the image the mullion spacing looks uneven. " + GOOD,
    GOOD + " The photo shows a cleaner joint than usual.",
    GOOD + " As seen in your render, the transom sits low.",
    GOOD + " The panel pictured has a deeper reveal.",
]
for i, txt in enumerate(REFS_EN, 1):
    check(f"C2.{i} angol kep-hivatkozas SERTES",
          any("kepre hivatkozik" in x for x in
              check_quality(txt, POST, False, "craftsmanship", "technical",
                            image_attached=True)),
          txt[:52])

HU_POST = "Elkeszult a homlokzati panel family. Minden borda parametrikus."
HU_GOOD = ("A panel-familyk jellemzoen csak akkor elik tul az atadast, ha a bordak "
           "parameterei egyetlen kozos definiciobol jonnek, nem peldanyonkent beirva. "
           "Amint egy masodik ember hozzaer, a peldany-ertekek elcsusznak, es a "
           "kimutatas mar nem egyezik a modellel. Egy szinttel kevesebb agyazas es "
           "tipus-katalogusba tolt valtozatok sokkal olvashatobbak annak, aki "
           "kesobb megnyitja, es ez tobbet er a gyorsabb elso szerkesztesnel.")
check("C3 magyar kep-hivatkozas SERTES",
      any("kepre hivatkozik" in x for x in
          check_quality(HU_GOOD + " A kepen jol latszik a csomopont.", HU_POST,
                        False, "craftsmanship", "technical", image_attached=True)))
check("C4 UGYANAZ a szoveg kep NELKUL nem sertes (a kapu csak keppel mer)",
      not any("kepre hivatkozik" in x for x in
              check_quality(REFS_EN[0], POST, False, "craftsmanship", "technical",
                            image_attached=False)))
check("C5 a kapu default-ja: nincs kep -> nem mer",
      not any("kepre hivatkozik" in x for x in
              check_quality(REFS_EN[0], POST, False, "craftsmanship", "technical")))
check("C6 minden minta forditható regex",
      all(__import__("re").compile(p) for p, _ in _VISUAL_REFERENCE_PATTERNS))


# --- D) config + intent-layer interakcio ------------------------------------
check("D1 image_input default: be", image_input_enabled({}) is True)
check("D2 'off' -> ki", image_input_enabled({"linkedin": {"image_input": "off"}}) is False)
check("D3 YAML-boolean False -> ki (a §4/17-es csapda)",
      image_input_enabled({"linkedin": {"image_input": False}}) is False)
check("D4 image_max_px default 384 (fix 258 token)", image_max_px({}) == 384)
check("D5 ervenyes ertek atmegy", image_max_px({"linkedin": {"image_max_px": 768}}) == 768)
check("D6 ertelmetlen ertek -> 384",
      image_max_px({"linkedin": {"image_max_px": "sok"}}) == 384
      and image_max_px({"linkedin": {"image_max_px": 99999}}) == 384
      and image_max_px({"linkedin": {"image_max_px": 4}}) == 384)


# --- E) route-validacio -----------------------------------------------------
import base64 as _b64  # noqa: E402

from ui.app import _decode_post_image, _LI_IMAGE_MAX_BYTES  # noqa: E402

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 200
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200


def as_b64(blob, prefix=""):
    return prefix + _b64.b64encode(blob).decode()


ok_blob, ok_err = _decode_post_image(as_b64(JPEG))
check("E1 nyers base64 JPEG elfogadva", ok_blob == JPEG and ok_err is None)

url_blob, url_err = _decode_post_image(as_b64(JPEG, "data:image/jpeg;base64,"))
check("E2 data-URL prefix is elfogadva", url_blob == JPEG and url_err is None)

none_blob, none_err = _decode_post_image("")
check("E3 ures bemenet -> nincs kep, nincs hiba", none_blob is None and none_err is None)

png_blob, png_err = _decode_post_image(as_b64(PNG))
check("E4 PNG ELUTASITVA magic-byte alapjan (a canvas mindig JPEG-et ad)",
      png_blob is None and "JPEG" in (png_err or ""), str(png_err))

lie_blob, lie_err = _decode_post_image(as_b64(PNG, "data:image/jpeg;base64,"))
check("E5 HAMIS jpeg-MIME sem segit: a bajtok dontenek",
      lie_blob is None and "JPEG" in (lie_err or ""), str(lie_err))

bad_blob, bad_err = _decode_post_image("nem-base64!!!")
check("E6 ervenytelen base64 elutasitva", bad_blob is None and bad_err is not None)

big_blob, big_err = _decode_post_image(as_b64(b"\xff\xd8\xff" + b"\x00" * _LI_IMAGE_MAX_BYTES))
check("E7 meret-plafon fog (max 2 MB)", big_blob is None and "nagy" in (big_err or ""),
      str(big_err))
check("E8 a plafon 2 MB", _LI_IMAGE_MAX_BYTES == 2 * 1024 * 1024)


# --- F) sablon-szerzodes ----------------------------------------------------
tpl = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "ui", "templates", "dashboard.html"), encoding="utf-8").read()
check("F1 a sablon a SZERVERTOL kapja a plafont (a knob nem hazudik)",
      "li_image_max_px" in tpl and "const LI_IMAGE_MAX_PX" in tpl)
check("F2 a canvas JPEG-et exportal (ezert JPEG-only a szerver)",
      "toDataURL('image/jpeg'" in tpl)
check("F3 a kep a keresben megy (image_b64)", "image_b64: liImageB64" in tpl)
check("F4 vagolap-figyelo van, es CSAK az aktiv LinkedIn-szekcioban",
      "'paste'" in tpl and "s-linkedin" in tpl and "classList.contains('active')" in tpl)
check("F5 a kep-valaszto csak image_input=on eseten kerul be",
      "{% if li_image_enabled %}" in tpl)
check("F6 a Torles a kepet is torli", "clearLiImage();" in tpl)


# --- B) vegponttol vegpontig: a kep NEM jut el a COMPOSE-ig ------------------
import json as _json  # noqa: E402

REASON_OUT = {
    "topic": "revit", "post_type": "experience",
    "conversation_intent": "craftsmanship", "discourse_level": "technical",
    "expected_responder_role": "peer_practitioner",
    "response_mode": "share_experience", "human_temperature": "practical",
    "topic_gravity": "Revit family authoring",
    "author_objective": "share craft", "audience": "BIM practitioners",
    "technical_depth": "expert", "emotional_tone": "reflective",
    "core_thesis": "Parametric mullions are worth the effort.",
    "missing_perspective": "lifecycle",
    "missing_perspective_reason": "Handover is never discussed.",
    "strategy_fit": {"constructive_challenge": 3, "systems_thinking": 4,
                     "field_experience": 9, "business_impact": 8,
                     "future_outlook": 2, "practical_lesson": 7,
                     "missing_perspective": 5},
    "strategy_reason": "give practitioners something usable",
    "explicit_tool_request": False, "tool_request_quote": "",
    "insight": "Nesting depth predicts breakage more than parameter count.",
    "confidence": 0.8,
    "image_role": "primary_content",
}

calls = []


class _FakeResp:
    def __init__(self, text):
        self.text = text


class _FakeModels:
    def generate_content(self, model=None, contents=None, config=None):
        has_image = isinstance(contents, list)
        wants_reason = "strategy_fit" in (config.response_schema or {}).get("properties", {})
        calls.append({"stage": "reason" if wants_reason else "compose",
                      "image": has_image,
                      "schema_has_image_role":
                          "image_role" in (config.response_schema or {}).get("properties", {})})
        return _FakeResp(_json.dumps(REASON_OUT if wants_reason else {"comment": GOOD}))


class _FakeClient:
    models = _FakeModels()


_real = eng._client
eng._client = lambda config: (_FakeClient(), "gemini-2.5-flash", None)
IMG = b"\xff\xd8\xff\xe0" + b"\x00" * 500
try:
    res = eng.generate_comment({"linkedin": {"intent_layer": "on", "image_input": "on"}},
                               POST, image_bytes=IMG)
    calls_with = list(calls)
    calls.clear()
    res_off_layer = eng.generate_comment(
        {"linkedin": {"intent_layer": "off", "image_input": "on"}}, POST, image_bytes=IMG)
    calls_layer_off = list(calls)
    calls.clear()
    res_off_img = eng.generate_comment(
        {"linkedin": {"intent_layer": "on", "image_input": "off"}}, POST, image_bytes=IMG)
    calls_img_off = list(calls)
    calls.clear()
    res_none = eng.generate_comment({"linkedin": {"intent_layer": "on"}}, POST)
    calls_none = list(calls)
finally:
    eng._client = _real

check("B1 nincs hiba a pipeline-ban", "error" not in res, str(res.get("error", "")))
check("B2 a hivas-szam VALTOZATLAN maradt (2, a kep nem ad kort)",
      len(calls_with) == 2, str(len(calls_with)))
check("B3 a REASON megkapta a kepet", calls_with[0]["stage"] == "reason"
      and calls_with[0]["image"] is True)
check("B4 a COMPOSE NEM kapta meg a kepet (a fo allitas)",
      calls_with[1]["stage"] == "compose" and calls_with[1]["image"] is False)
check("B5 a REASON semaja tartalmazta az image_role-t",
      calls_with[0]["schema_has_image_role"] is True)
check("B6 az image_role visszajon a valaszban",
      res.get("image_attached") is True and res.get("image_role") == "primary_content")
check("B7 a kep-besorolas hatott: field_experience nyert (a business_impact vetozott)",
      res.get("strategy") == "field_experience", str(res.get("strategy")))

check("B8 intent_layer=off -> a kep EL SEM MEGY (nincs token-veszteseg)",
      all(c["image"] is False for c in calls_layer_off)
      and res_off_layer.get("image_attached") is False)
check("B9 image_input=off -> a kep EL SEM MEGY",
      all(c["image"] is False for c in calls_img_off)
      and res_off_img.get("image_attached") is False)
check("B10 kep nelkul a REASON-sema NEM tartalmaz image_role-t",
      calls_none[0]["schema_has_image_role"] is False
      and res_none.get("image_attached") is False
      and res_none.get("image_role") == "")
check("B11 a DASHBOARD-SZERZODES all keppel is (8 legacy mezo)",
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
