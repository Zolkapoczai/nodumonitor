"""
Conversation Intent Layer tesztje (2026-07-29, linkedin-tle-v2).

A megrendelt viselkedes-valtozas: a strategia-valasztas ELOTT eldol, MILYEN
beszelgetesbe szall be a komment, es MELYIK absztrakcios sikon beszel a szerzo.

A) Taxonomia-integritas (elirt bias-kulcs csendben nem hat -> kotelezo ellenorizni)
B) NINCS REGRESSZIO a mukodo eseten (elfogadasi kriterium 1: "Opinion posts
   remain as strong as today") — a v1-es dontes bitre reprodukalva
C) A JELENTETT HIBA: mesterseg-/tutorial-/portfolio-poszt nem sodrodik uzleti sikra
D) A veto szemantikaja (kemeny kapu, de nem blanket-tilalom)
E) question_to_community: a feltett kerdesre valaszol, nem temat valt
F) engineering_problem: analitikus marad, business_impact csak moderalt levonas
G) Executive-absztrakcio kapu (determinisztikus, precizio-orientalt)
H) Kill switch (`linkedin.intent_layer`) — az A/B meres feltetele
I) A compose-uzenet tartalma
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


import responder.linkedin_engine as _eng_mod  # noqa: E402
from responder.linkedin_engine import (  # noqa: E402
    CONVERSATION_INTENTS, STRATEGIES, ENGINE_VERSION, _DISCOURSE_LEVELS,
    RESPONDER_ROLES, RESPONSE_MODES, HUMAN_TEMPERATURES,
    _LEVEL_VETO, _LEVEL_STRATEGY_BIAS, _STRATEGY_BIAS, _LAYER_OFF,
    _REASON_PROMPT, _REASON_SCHEMA, _NO_EXEC_ABSTRACTION_INTENTS,
    _EXEC_ABSTRACTION_PATTERNS,
    _intent_key, _level_key, _responder_role_key, _response_mode_key,
    _human_temperature_key, _intent_layer_enabled, _compose_user_msg,
    effective_bias, score_strategies, pick_strategy, check_quality,
    ai_fingerprint_terms,
)

STRAT_KEYS = set(STRATEGIES)


# --- A) taxonomia-integritas ------------------------------------------------
check("A1 minden intent teljes (label/recognise/directive/bias)",
      all({"label", "recognise", "directive", "bias"} <= set(v)
          for v in CONVERSATION_INTENTS.values()))

bad_bias = {f"{i}.{k}" for i, v in CONVERSATION_INTENTS.items()
            for k in v["bias"] if k not in STRAT_KEYS}
check("A2 minden intent-bias kulcs letezo strategia", not bad_bias, str(sorted(bad_bias)))

bad_veto = {f"{lv}.{s}" for lv, ss in _LEVEL_VETO.items()
            for s in ss if s not in STRAT_KEYS}
check("A3 minden veto-bejegyzes letezo strategia", not bad_veto, str(sorted(bad_veto)))

bad_lvl = {f"{lv}.{k}" for lv, d in _LEVEL_STRATEGY_BIAS.items()
           for k in d if k not in STRAT_KEYS}
check("A4 minden szint-bias kulcs letezo strategia", not bad_lvl, str(sorted(bad_lvl)))

check("A5 mindharom szinthez van veto- es bias-bejegyzes",
      all(lv in _LEVEL_VETO and lv in _LEVEL_STRATEGY_BIAS for lv in _DISCOURSE_LEVELS))

props, req = _REASON_SCHEMA["properties"], _REASON_SCHEMA["required"]
check("A6 az intent/szint/gravity/role/shape/temperature mezok a semaban ES kotelezoek",
      all(f in props and f in req
          for f in ("conversation_intent", "discourse_level", "topic_gravity",
                    "expected_responder_role", "response_mode", "human_temperature")))
check("A7 a sema enum == a taxonomia kulcsai",
      props["conversation_intent"]["enum"] == list(CONVERSATION_INTENTS)
      and props["discourse_level"]["enum"] == _DISCOURSE_LEVELS
      and props["expected_responder_role"]["enum"] == list(RESPONDER_ROLES)
      and props["response_mode"]["enum"] == list(RESPONSE_MODES)
      and props["human_temperature"]["enum"] == HUMAN_TEMPERATURES)
check("A8 az engine-verzio bumpolva", ENGINE_VERSION.endswith("v6"), ENGINE_VERSION)
check("A9 a legacy post_type mezo MEGMARADT (dashboard-szerzodes)",
      "post_type" in props and "post_type" in req)
check("A10 personal_experience intent letezik (human temperature vedelme)",
      "personal_experience" in CONVERSATION_INTENTS)

# A11-A13: a ket eddig KETSZER elkovetett hibaosztaly kod-szintu zara.
#
# A11 — DUPLA VALASZFORMA-SKALA. A v3 `RESPONSE_MODES`-a es a v4
# `CONVERSATION_RESPONSE_STRATEGIES`-e ugyanazt a dontest kerte ket atfedo skalan,
# kodbeli egyeztetes nelkul (2026-07-31-i osszevonas). Ez a teszt megbukik, ha
# barmelyik masodik "hogyan valaszolunk" enum visszakerul a modulba.
check("A11.0 a megszunt dupla-skala szimbolumai eltuntek",
      not hasattr(_eng_mod, "CONVERSATION_RESPONSE_STRATEGIES")
      and not hasattr(_eng_mod, "_conversation_response_strategy_key"))

# Barmely MAS publikus direktiva-dict, ami a RESPONSE_MODES kulcsaibol tartalmaz,
# definicio szerint ugyanazt a dontest kerdezi meg masodszor.
_directive_dicts = {n: getattr(_eng_mod, n) for n in dir(_eng_mod)
                    if not n.startswith("_") and n.isupper()
                    and isinstance(getattr(_eng_mod, n), dict)
                    and all(isinstance(v, str) for v in getattr(_eng_mod, n).values())}
_dupes = {n: sorted(set(d) & set(RESPONSE_MODES))
          for n, d in _directive_dicts.items()
          if n != "RESPONSE_MODES" and set(d) & set(RESPONSE_MODES)}
check("A11 nincs masodik, parhuzamos valaszforma-skala a modulban",
      not _dupes, str(_dupes))
check("A11.1 a valaszforma-skala az osszevont 5 agu",
      set(RESPONSE_MODES) == {"answer_the_question", "concrete_suggestion",
                              "extend_one_insight", "take_a_position",
                              "share_experience"},
      str(sorted(RESPONSE_MODES)))

# A12/A13 — ELCSUSZOTT LEPES-HIVATKOZAS. A REASON-prompt szamozott listaja ket
# egymast koveto commitban is elcsuszott az uj mezok beszurasakor ("step 10" ->
# valojaban 13., "step 3" -> valojaban 4.), mert a hivatkozas SZAMRA mutatott. A
# szamokra mutato kereszthivatkozas ezert tilos: mezonevre kell hivatkozni.
import re as _re  # noqa: E402

check("A12 a promptban NINCS szamra mutato lepes-kereszthivatkozas",
      not _re.search(r"\bstep\s+\d+", _REASON_PROMPT, _re.IGNORECASE),
      str(_re.findall(r"\bstep\s+\d+", _REASON_PROMPT, _re.IGNORECASE)))

_steps = [int(m.group(1)) for m in _re.finditer(r"^(\d+)\. ", _REASON_PROMPT, _re.M)]
check("A13 a prompt lepes-szamozasa hezag- es duplikatummentes (1..N)",
      _steps == list(range(1, len(_steps) + 1)), str(_steps))
# Minden KOTELEZO sema-mezot nevvel ki kell mondani a promptban: enelkul a modell
# kap egy kotelezo mezot, amirol nem tudja, mit kell bele irni.
_undocumented = [f for f in req if f not in _REASON_PROMPT]
check("A13.1 minden kotelezo sema-mezo szerepel a promptban is",
      not _undocumented, str(_undocumented))


# --- B) nincs regresszio a mukodo eseten ------------------------------------
def v1_pick(fit):
    """Az engine v1 dontese: alap-bias, se intent, se veto. Referencia-implementacio."""
    best, best_score = None, None
    for slug in STRATEGIES:
        raw = fit.get(slug)
        score = float(raw) if isinstance(raw, (int, float)) else 0.0
        score += -1.5 if slug == "missing_perspective" else 0.0
        if best_score is None or score > best_score:
            best, best_score = slug, score
    return best


FITS = [
    {"constructive_challenge": 9, "systems_thinking": 7, "field_experience": 4,
     "business_impact": 5, "future_outlook": 3, "practical_lesson": 2,
     "missing_perspective": 8},
    {"constructive_challenge": 3, "systems_thinking": 4, "field_experience": 9,
     "business_impact": 8, "future_outlook": 2, "practical_lesson": 7,
     "missing_perspective": 10},
    {"constructive_challenge": 5, "systems_thinking": 5, "field_experience": 5,
     "business_impact": 5, "future_outlook": 5, "practical_lesson": 5,
     "missing_perspective": 5},
    {"constructive_challenge": 0, "systems_thinking": 0, "field_experience": 0,
     "business_impact": 10, "future_outlook": 0, "practical_lesson": 0,
     "missing_perspective": 0},
]

check("B1 professional_opinion bias URES (a 91-95/100-as eset valtozatlan)",
      CONVERSATION_INTENTS["professional_opinion"]["bias"] == {})
check("B2 industry_debate bias URES", CONVERSATION_INTENTS["industry_debate"]["bias"] == {})
check("B3 a _LAYER_OFF par az EGYSEGELEM (bias == csak az alap-bias)",
      effective_bias(*_LAYER_OFF) == {s: _STRATEGY_BIAS.get(s, 0.0) for s in STRATEGIES})
check("B4 kikapcsolt layer == v1-es dontes MINDEN teszt-vektoron",
      all(pick_strategy(f, *_LAYER_OFF) == v1_pick(f) for f in FITS),
      str([(pick_strategy(f, *_LAYER_OFF), v1_pick(f)) for f in FITS]))
check("B5 velemeny-poszt management-sikon == v1-es dontes",
      all(pick_strategy(f, "professional_opinion", "management") == v1_pick(f)
          for f in FITS))
check("B6 debate-poszt management-sikon == v1-es dontes",
      all(pick_strategy(f, "industry_debate", "management") == v1_pick(f) for f in FITS))


# --- C) a jelentett hiba: nincs uzleti sodras -------------------------------
# A modell a business_impactet pontozza a LEGMAGASABBRA — a v1 itt valasztotta
# rosszul. Az intent+veto utan nem valaszthatja.
DRIFT_FIT = {"constructive_challenge": 4, "systems_thinking": 7,
             "field_experience": 6, "business_impact": 10, "future_outlook": 5,
             "practical_lesson": 6, "missing_perspective": 5}

check("C0 a v1 EZEN a vektoron tenyleg business_impactet valasztott (a hiba)",
      v1_pick(DRIFT_FIT) == "business_impact")

for intent in ("craftsmanship", "portfolio_showcase", "technical_tutorial"):
    win = pick_strategy(DRIFT_FIT, intent, "technical")
    check(f"C1 {intent}: business_impact NEM nyer", win != "business_impact", win)
    check(f"C2 {intent}: mesterseg-strategia nyer",
          win in ("field_experience", "practical_lesson"), win)

check("C3 craftsmanship a systems_thinkinget is levonja (a munkaparancs nevszerint "
      "ezt is elkovetokent nevezi meg)",
      CONVERSATION_INTENTS["craftsmanship"]["bias"].get("systems_thinking", 0) < 0)
check("C4 portfolio_showcase a publikus kritikat is levonja",
      CONVERSATION_INTENTS["portfolio_showcase"]["bias"].get("constructive_challenge", 0) < 0)


# --- D) veto-szemantika -----------------------------------------------------
_, veto_tech = score_strategies(DRIFT_FIT, "professional_opinion", "technical")
_, veto_mgmt = score_strategies(DRIFT_FIT, "professional_opinion", "management")
_, veto_biz = score_strategies(DRIFT_FIT, "professional_opinion", "business")
check("D1 technical sik: business_impact vetozott", veto_tech == {"business_impact"})
check("D2 management sik: nincs veto", veto_mgmt == set())
check("D3 business sik: nincs veto", veto_biz == set())
check("D4 business sikon a business_impact NYERHET (nem blanket-tilalom)",
      pick_strategy(DRIFT_FIT, "professional_opinion", "business") == "business_impact")
check("D5 velemeny-poszt TECHNIKAI sikon nem emel uzleti sikra (Critical Principle)",
      pick_strategy(DRIFT_FIT, "professional_opinion", "technical") != "business_impact")
check("D6 business sikon a business_impact bias POZITIV (a szerzo mar ott van)",
      _LEVEL_STRATEGY_BIAS["business"].get("business_impact", 0) > 0)
check("D7 a veto sosem urit ki: mindig ervenyes strategiat ad",
      pick_strategy({}, "craftsmanship", "technical") in STRAT_KEYS,
      pick_strategy({}, "craftsmanship", "technical"))
check("D8 ismeretlen intent -> 'general'", _intent_key("nonsense") == "general"
      and _intent_key(None) == "general")
check("D9 ismeretlen szint -> 'technical' (a SZIGORUBB ag)",
      _level_key("nonsense") == "technical" and _level_key(None) == "technical"
      and _level_key("") == "technical")
check("D10 a szint-normalizalas megorzi az ervenyes erteket",
      _level_key("BUSINESS") == "business" and _level_key(" management ") == "management")


# --- E) question_to_community: valaszol, nem temat valt ---------------------
Q_FIT = {"constructive_challenge": 3, "systems_thinking": 4, "field_experience": 7,
         "business_impact": 4, "future_outlook": 3, "practical_lesson": 6,
         "missing_perspective": 10}
check("E1 a kerdesre a missing_perspective a legrosszabb valasz -> nem nyer",
      pick_strategy(Q_FIT, "question_to_community", "technical") != "missing_perspective",
      pick_strategy(Q_FIT, "question_to_community", "technical"))
check("E2 helyette valaszolo strategia nyer",
      pick_strategy(Q_FIT, "question_to_community", "technical")
      in ("field_experience", "practical_lesson"))
check("E3 a missing_perspective netto levonasa itt a legnagyobb",
      effective_bias("question_to_community")["missing_perspective"] <= -3.0,
      str(effective_bias("question_to_community")["missing_perspective"]))


# --- F) engineering_problem -------------------------------------------------
eb = effective_bias("engineering_problem", "technical")
check("F1 systems_thinking / field_experience / practical_lesson felertekelve",
      eb["systems_thinking"] > 0 and eb["field_experience"] > 0
      and eb["practical_lesson"] > 0)
check("F2 business_impact csak MODERALT levonas (nem kizaras)",
      -2.0 <= eb["business_impact"] < 0, str(eb["business_impact"]))
check("F3 a missing_perspective alap-levonasa itt semlegesitve (netto 0)",
      abs(eb["missing_perspective"]) < 0.01, str(eb["missing_perspective"]))
check("F4 a constructive_challenge NEM kap levonast (hibas premissza kimondhato)",
      eb["constructive_challenge"] >= 0, str(eb["constructive_challenge"]))


# --- G) executive-absztrakcio kapu ------------------------------------------
POST = "How do you handle shared parameters across linked Revit models?"
TECH_OK = ("A recurring detail here is that shared parameter GUIDs travel with the "
           "definition file, not with the model, so a rebuilt definition silently "
           "breaks the schedule mapping downstream. In multidisciplinary setups the "
           "safer pattern is to version the definition file itself and treat it as "
           "project data rather than a local resource, because the cost of "
           "rebuilding a schedule after the fact is far higher than maintaining it.")

check("G1 tiszta technikai komment technikai sikon ATMEGY (nincs hamis pozitiv)",
      check_quality(TECH_OK, POST, False, "engineering_problem", "technical") == [],
      str(check_quality(TECH_OK, POST, False, "engineering_problem", "technical")))

roi = TECH_OK + " The ROI on that discipline is obvious."
check("G2 ROI technikai sikon SERTES",
      any("uzleti absztrakcio" in i for i in
          check_quality(roi, POST, False, "engineering_problem", "technical")))
check("G3 ugyanaz a komment business sikon NEM sertes",
      not any("uzleti absztrakcio" in i for i in
              check_quality(roi, POST, False, "professional_opinion", "business")))
check("G4 ures intent/szint -> v1-es kapu (visszafele kompatibilis)",
      not any("uzleti absztrakcio" in i for i in check_quality(roi, POST, False)))

hu_post = "Hogyan kezelitek a megosztott parametereket linkelt Revit modellek kozott?"
hu = ("Egy ismetlodo reszlet, hogy a megosztott parameter GUID-ja a definicios "
      "fajlhoz tartozik, nem a modellhez, ezert egy ujragyartott definicio csendben "
      "elrontja a kimutatas hozzarendeleset. Tobb szakagas kornyezetben ezert "
      "erdemes magat a definicios fajlt verziozni es projektadatkent kezelni, mert "
      "kesobb visszakeresni sokkal koltsegesebb, mint fenntartani. A megterules "
      "ilyenkor azonnal latszik.")
check("G5 magyar 'megterules' is SERTES technikai sikon",
      any("uzleti absztrakcio" in i for i in
          check_quality(hu, hu_post, False, "engineering_problem", "technical")))

comp = TECH_OK + " That is a real competitive advantage for the practice."
check("G6 'competitive advantage' SERTES",
      any("uzleti absztrakcio" in i for i in
          check_quality(comp, POST, False, "engineering_problem", "technical")))
check("G7 craftsmanship intent MANAGEMENT szinten is meri (masodik halo)",
      any("uzleti absztrakcio" in i for i in
          check_quality(roi, POST, False, "craftsmanship", "management")))
check("G8 a v1-es kapu-szabalyok tovabbra is elnek (dicseret-nyitas)",
      any("tiltott fordulat" in i for i in
          check_quality("Great post! " + TECH_OK, POST, False,
                        "professional_opinion", "management")))
check("G9 minden exec-minta forditható regex", all(
    __import__("re").compile(p) for p, _ in _EXEC_ABSTRACTION_PATTERNS))
check("G10 a munkaparancs 'Avoid' listaja mind a harom intentre all",
      _NO_EXEC_ABSTRACTION_INTENTS ==
      {"craftsmanship", "portfolio_showcase", "technical_tutorial"})


# --- G2) response shaping: emberi hang, konkretseg, stilus -----------------
check("G2.1 ismeretlen szerep konzervativ peer default",
      _responder_role_key("nonsense") == "peer_practitioner")
check("G2.2 ismeretlen response mode a legkevesbe invaziv default",
      _response_mode_key("nonsense") == "extend_one_insight")
check("G2.3 ismeretlen temperature gyakorlati default",
      _human_temperature_key("nonsense") == "practical")
check("G2.4 ervenyes role/mode/temperature normalizalva marad",
      _responder_role_key("PRODUCT_REVIEWER") == "product_reviewer"
      and _response_mode_key("ANSWER_THE_QUESTION") == "answer_the_question"
      and _response_mode_key(" share_experience ") == "share_experience"
      and _human_temperature_key("reflective") == "reflective")
check("G2.4.1 az osszevonas utan MINDEN korabbi ag lefedve (a v3 es a v4 kulcsai)",
      all(k in RESPONSE_MODES for k in
          ("answer_the_question",     # v3 direct_answer
           "share_experience",        # v3 experience_connection
           "extend_one_insight",      # v3 technical_extension
           "take_a_position",         # v3 analytical_response
           "concrete_suggestion")))   # csak a v3-ban volt, parja nem volt
check("G2.4.2 a megszunt v3/v4 kulcsok mar nem ervenyesek",
      all(_response_mode_key(old) == "extend_one_insight" for old in
          ("direct_answer", "technical_extension", "analytical_response",
           "experience_connection")))

stock = "We often see the parameter GUID become the real failure point after handover. " + TECH_OK
check("G2.5 sablonos nyitas SERTES", any("ismetlodo nyitas" in i for i in
      check_quality(stock, POST, False, "engineering_problem", "technical")))

efficiency_ending = TECH_OK + " This improves operational efficiency."
check("G2.6 sablonos hatekonysag-zaras SERTES", any("hatekony" in i for i in
      check_quality(efficiency_ending, POST, False, "engineering_problem", "technical")))

fingerprint = TECH_OK + " The governance framework creates operational efficiency."
check("G2.7 ket uj framework-kifejezes technikai sikon SERTES", any("AI-ujjlenyomat" in i for i in
      check_quality(fingerprint, POST, False, "engineering_problem", "technical")))
check("G2.8 egyetlen uj framework-kifejezes nem hamis pozitiv", not any("AI-ujjlenyomat" in i for i in
      check_quality(TECH_OK + " The governance question remains open.", POST, False,
                    "engineering_problem", "technical")))
source_framework = "The governance framework for this workflow needs attention."
check("G2.9 szerzo sajat framework-nyelve nem szamolodik",
      ai_fingerprint_terms("The governance framework changes slowly.", source_framework) == [])


# --- H) kill switch ---------------------------------------------------------
check("H1 default: bekapcsolva", _intent_layer_enabled({}) is True)
check("H2 'off' -> kikapcsolva",
      _intent_layer_enabled({"linkedin": {"intent_layer": "off"}}) is False)
check("H3 YAML-boolean False -> kikapcsolva (a §4/17-es csapda)",
      _intent_layer_enabled({"linkedin": {"intent_layer": False}}) is False)
check("H4 YAML-boolean True -> bekapcsolva",
      _intent_layer_enabled({"linkedin": {"intent_layer": True}}) is True)
check("H5 'on' -> bekapcsolva",
      _intent_layer_enabled({"linkedin": {"intent_layer": "on"}}) is True)


# --- I) compose-uzenet ------------------------------------------------------
REASONING = {
    "strategy": "field_experience",
    "conversation_intent": "craftsmanship",
    "discourse_level": "technical",
    "expected_responder_role": "peer_practitioner",
    "response_mode": "share_experience",
    "human_temperature": "practical",
    "topic_gravity": "Revit family authoring",
    "core_thesis": "Nested families are overused.",
    "missing_perspective": "lifecycle",
    "missing_perspective_reason": "Maintenance cost is never discussed.",
    "insight": "Nesting depth predicts breakage more than parameter count.",
}

on = _compose_user_msg("post body", "", REASONING, False, None, intent_layer=True)
off = _compose_user_msg("post body", "", REASONING, False, None, intent_layer=False)

check("I1 bekapcsolva: a beszelgetes-tipus a promptban van", "CONVERSATION TYPE" in on)
check("I2 bekapcsolva: az absztrakcios sik a promptban van", "TECHNICAL PLANE" in on)
check("I3 bekapcsolva: a centre of gravity atmegy", "Revit family authoring" in on)
check("I4 bekapcsolva: technikai sikon a ROI-tilalom kimondva",
      "no ROI" in on and "executive framing" in on)
check("I5 bekapcsolva: szerep, response shape es human temperature atmegy",
      "YOUR EXPECTED ROLE: peer_practitioner" in on
      and "RESPONSE SHAPE: share_experience" in on
      and "HUMAN TEMPERATURE: practical" in on
      and "exactly ONE conceptual step" in on
      and "practitioner language over whitepaper language" in on)
check("I5.1 a valaszforma PONTOSAN EGYSZER szerepel a promptban (nincs dupla skala)",
      on.count("RESPONSE SHAPE") == 1 and "CONVERSATION RESPONSE STRATEGY" not in on)
check("I6 KIKAPCSOLVA: egyik uj sor sem kerul be (v1-es prompt)",
      not any(s in off for s in ("CONVERSATION TYPE", "PLANE", "CENTRE OF GRAVITY",
                                 "YOUR EXPECTED ROLE", "RESPONSE SHAPE",
                                 "HUMAN TEMPERATURE",
                                 "exactly ONE conceptual step", "stock consultant opening",
                                 "generic payoff", "no ROI", "Do not reframe")))
check("I7 a reasoning-mezok mindket agban benne vannak",
      "core thesis" in on and "core thesis" in off
      and REASONING["insight"] in on and REASONING["insight"] in off)

biz = dict(REASONING, discourse_level="business", conversation_intent="professional_opinion")
biz_msg = _compose_user_msg("post body", "", biz, False, None, intent_layer=True)
check("I8 business sikon nincs technikai-tilalom sor", "no ROI" not in biz_msg)
check("I9 business sikon a sik-megjeloles BUSINESS", "BUSINESS PLANE" in biz_msg)

no_grav = dict(REASONING, topic_gravity="   ")
check("I10 ures gravity eseten a sor kimarad",
      "CENTRE OF GRAVITY" not in
      _compose_user_msg("p", "", no_grav, False, None, intent_layer=True))
check("I11 az ujrairo kor a konkret hibalistat atadja",
      "tul rovid (12 szo, min 60)" in
      _compose_user_msg("p", "", REASONING, False, ["tul rovid (12 szo, min 60)"],
                        intent_layer=True))
check("I12 minden intent directive-je bekerul a promptba (nincs KeyError)",
      all("CONVERSATION TYPE" in _compose_user_msg(
          "p", "", dict(REASONING, conversation_intent=i), False, None, True)
          for i in CONVERSATION_INTENTS))


# --- J) vegponttol vegpontig, STUBOLT Gemini-klienssel ----------------------
# A fenti szekciok tiszta fuggvenyeket mernek. Ez az orkesztraciot: hogy a layer
# tenylegesen BE VAN KOTVE a generate_comment-be, es a valasz-szerzodes all.
# Nincs halozati hivas — a klienst kicsereljuk.
import json as _json  # noqa: E402

import responder.linkedin_engine as eng  # noqa: E402

REASON_OUT = {
    "topic": "revit", "post_type": "experience",
    "conversation_intent": "craftsmanship", "discourse_level": "technical",
    "expected_responder_role": "peer_practitioner",
    "response_mode": "share_experience", "human_temperature": "practical",
    "topic_gravity": "Revit family authoring",
    "author_objective": "share craft", "audience": "BIM practitioners",
    "technical_depth": "expert", "emotional_tone": "reflective",
    "core_thesis": "Nested families are overused.",
    "missing_perspective": "lifecycle",
    "missing_perspective_reason": "Maintenance is never discussed.",
    # A modell a business_impactet pontozza a legmagasabbra — pontosan a
    # jelentett hiba bemenete.
    "strategy_fit": {"constructive_challenge": 4, "systems_thinking": 7,
                     "field_experience": 6, "business_impact": 10,
                     "future_outlook": 5, "practical_lesson": 6,
                     "missing_perspective": 5},
    "strategy_reason": "give practitioners something usable",
    "explicit_tool_request": False, "tool_request_quote": "",
    "insight": "Nesting depth predicts breakage more than parameter count.",
    "confidence": 0.8,
}
COMMENT_OUT = {"comment": (
    "One recurring detail in this kind of setup is that nesting depth, not "
    "parameter count, is what predicts breakage later on. Once a nested family "
    "is three levels deep the parameter associations stop being obvious to the "
    "next person who opens it, and a rename upstream quietly detaches the "
    "mapping without any warning in the model. Flattening one level and pushing "
    "the variation into type catalogues usually survives handover much better, "
    "because the structure stays readable to someone who did not build it. The "
    "trade-off is a longer catalogue, which is easier to audit than a deep tree."
)}

_calls = {"n": 0, "prompts": []}


class _FakeResp:
    def __init__(self, text):
        self.text = text


class _FakeModels:
    def generate_content(self, model=None, contents=None, config=None):
        _calls["n"] += 1
        _calls["prompts"].append(contents)
        # A REASON-hivas semaja tartalmazza a strategy_fitet; a COMPOSE-e nem.
        wants_reason = "strategy_fit" in (config.response_schema or {}).get("properties", {})
        return _FakeResp(_json.dumps(REASON_OUT if wants_reason else COMMENT_OUT))


class _FakeClient:
    models = _FakeModels()


_real_client = eng._client
eng._client = lambda config: (_FakeClient(), "gemini-2.5-flash", None)
try:
    res_on = eng.generate_comment({"linkedin": {"intent_layer": "on"}}, "Some post about families.")
    _calls_on = _calls["n"]
    prompts_on = list(_calls["prompts"])
    _calls["n"], _calls["prompts"] = 0, []
    res_off = eng.generate_comment({"linkedin": {"intent_layer": "off"}}, "Some post about families.")
finally:
    eng._client = _real_client

check("J1 nincs hiba a pipeline-ban", "error" not in res_on, str(res_on.get("error", "")))
check("J2 a hivas-szam VALTOZATLAN maradt (2, nem 3 — a kapu atengedte)",
      _calls_on == 2, str(_calls_on))
check("J3 az intent atkerult a valaszba",
      res_on.get("conversation_intent") == "craftsmanship"
      and res_on.get("conversation_intent_label") == "Craftsmanship")
check("J4 a discourse_level es a gravity atkerult",
      res_on.get("discourse_level") == "technical"
      and res_on.get("topic_gravity") == "Revit family authoring")
check("J4.1 role, response shape es human temperature atkerult",
      res_on.get("expected_responder_role") == "peer_practitioner"
      and res_on.get("response_mode") == "share_experience"
      and res_on.get("human_temperature") == "practical")
check("J4.2 a megszunt dupla-skala mezoi NEM kerulnek a valaszba",
      "conversation_response_strategy" not in res_on
      and "conversation_response_strategy_label" not in res_on)
check("J5 VEGPONTTOL VEGPONTIG: a top-pontszamu business_impact NEM nyert",
      res_on.get("strategy") != "business_impact", str(res_on.get("strategy")))
check("J6 helyette mesterseg-strategia nyert",
      res_on.get("strategy") in ("field_experience", "practical_lesson"),
      str(res_on.get("strategy")))
check("J7 a dontes nyoma visszajon (auditalhatosag)",
      isinstance(res_on.get("strategy_scores"), dict)
      and res_on.get("strategy_vetoed") == ["business_impact"])
check("J8 a compose-prompt megkapta az intent-sorokat",
      any("CONVERSATION TYPE" in p and "TECHNICAL PLANE" in p
          and "YOUR EXPECTED ROLE" in p and "RESPONSE SHAPE" in p
          and "HUMAN TEMPERATURE" in p for p in prompts_on))
check("J9 a DASHBOARD-SZERZODES all: mind a 8 legacy mezo megvan",
      all(k in res_on for k in ("topic", "post_type", "engagement_intent",
                                "reply_style", "brand_mode", "confidence",
                                "reply_text", "rationale")))
check("J10 a kapu atengedte a kommentet (nincs uzleti absztrakcio benne)",
      res_on.get("quality_issues") == [] and res_on.get("rewrites") == 0,
      str(res_on.get("quality_issues")))
check("J11 az engine-verzio a valaszban v6", res_on.get("engine") == "linkedin-tle-v6")
check("J12 KIKAPCSOLVA: ugyanezen a bemeneten a v1-es dontes (business_impact)",
      res_off.get("strategy") == "business_impact" and res_off.get("intent_layer") is False,
      str(res_off.get("strategy")))
check("J13 KIKAPCSOLVA: a veto-lista ures", res_off.get("strategy_vetoed") == [])

print()
bad = 0
for name, ok, detail in results:
    if not ok:
        bad += 1
    print(f"  {'OK  ' if ok else 'FAIL'} {name}" + (f"   [{detail}]" if detail else ""))
print(f"\n{len(results) - bad}/{len(results)} teszt zold.")
sys.exit(1 if bad else 0)
