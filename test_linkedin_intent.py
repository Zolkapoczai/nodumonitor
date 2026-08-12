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
    # K) kihivas-szenzor (v13; a padlo v19-ben a jelolt-halmazra delegalva)
    _CHALLENGE_INTENTS, challenge_override, challenge_sensor_enabled,
    # L) a fit mint SZURO (v16)
    STRATEGY_CANDIDATE_FLOOR, _STRATEGY_RING_SIZE, strategy_candidates,
    decide_strategy, remember_strategy, strategy_candidates_enabled,
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
check("A8 az engine-verzio bumpolva", ENGINE_VERSION.endswith("v25"), ENGINE_VERSION)
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
check("J11 az engine-verzio a valaszban v25", res_on.get("engine") == "linkedin-tle-v25")
check("J12 KIKAPCSOLVA: ugyanezen a bemeneten a v1-es dontes (business_impact)",
      res_off.get("strategy") == "business_impact" and res_off.get("intent_layer") is False,
      str(res_off.get("strategy")))
check("J13 KIKAPCSOLVA: a veto-lista ures", res_off.get("strategy_vetoed") == [])

# --- K) kihivas-szenzor (2026-08-11, v13) ------------------------------------
# A MERT PROBLEMA: a `constructive_challenge` 33 generalasbol EGYSZER SEM nyert, es
# a diagnozis KIZARTA a bias-javitast (a CC nyers pontja sosem ment 7 fole, a gyoztes
# 32 sorban 9 volt -> +2..+9,5 kellett volna, ami mar teherhordo suly).
# A megoldas nem uj suly, hanem uj TENY: a modell szenzor, a kod biro.
CHALLENGE_POST = ("Archicad is getting a connection to an Autodesk tool. The advantage "
                  "sits with whoever already treats the concept model as structured "
                  "data instead of a picture. That habit costs nothing.")
CH_REASONING = {
    "strategy_fit": {"constructive_challenge": 7, "systems_thinking": 5,
                     "field_experience": 9, "business_impact": 6,
                     "future_outlook": 4, "practical_lesson": 8,
                     "missing_perspective": 9},
    "thesis_condition": "when the receiving office runs an older Archicad version",
    "thesis_quote": "The advantage sits with whoever already treats the concept model "
                    "as structured data",
}


def ch(**over):
    """Egy reasoning-dict a fenti alapbol, felulirt mezokkel."""
    return {**CH_REASONING, **over}


ok, why = challenge_override(ch(), CHALLENGE_POST, "professional_opinion", "management")
check("K1 minden feltetel teljesul -> a szenzor elsul", ok, why)
check("K1.1 az indok megnevezi a feltetelt (naplozhato dontes)",
      "older Archicad" in why, why)

ok, why = challenge_override(ch(), CHALLENGE_POST, "reflection", "management")
check("K2 NEM velemeny-jellegű intent -> nem sul el", not ok, why)
check("K2.1 az indok az intentre hivatkozik", "intent" in why, why)

ok, why = challenge_override(ch(thesis_condition=""), CHALLENGE_POST,
                             "professional_opinion", "management")
check("K3 ures thesis_condition -> nem sul el (ez ERVENYES es gyakori valasz)",
      not ok, why)

ok, why = challenge_override(ch(thesis_condition="   "), CHALLENGE_POST,
                             "professional_opinion", "management")
check("K3.1 csak szokoz sem szamit feltetelnek", not ok, why)

# A ZERO-HALLUCINATION ELV: az idezetet a kod MEGKERESI a posztban. Ez a felteteles
# allitas egyetlen kodbol ellenorizheto fele — ugyanaz a mechanizmus, mint a
# `tool_request_quote`-nal es a `promotion_evidence`-nel (`_quote_in_post`).
ok, why = challenge_override(ch(thesis_quote="the advantage belongs to the vendor "
                                             "with the bigger licence stack"),
                             CHALLENGE_POST, "professional_opinion", "management")
check("K4 KITALALT idezet -> nem sul el", not ok, why)
check("K4.1 az indok mutatja a nem talalt idezetet", "nem talalhato" in why, why)

ok, why = challenge_override(ch(thesis_quote=""), CHALLENGE_POST,
                             "professional_opinion", "management")
check("K5 ures idezet -> nem sul el (feltetel idezet nelkul nem tény)", not ok, why)

# A tezis ALLITAS, nem fonevi szerkezet: a `_quote_in_post` 3 szavas alapertelmezese
# a rovid tool-request-kerdesekre van kalibralva, ide keves. Ezt a teszt talalta meg.
ok, why = challenge_override(ch(thesis_quote="the concept model"), CHALLENGE_POST,
                             "professional_opinion", "management")
check("K5.1 tul rovid idezet nem bizonyitek (THESIS_QUOTE_MIN_WORDS)", not ok, why)
check("K5.2 a tezis-idezet padloja szigorubb a tool-request-nel",
      _eng_mod.THESIS_QUOTE_MIN_WORDS > 3, str(_eng_mod.THESIS_QUOTE_MIN_WORDS))

# A PADLO: a kod a rangsor-artefaktumot javitja, NEM a modell iteletet irja felul.
# Ha a modell maga is alacsonyra tette a CC-t, a szenzor hallgat.
for fit in (0, 3, 6):
    ok, why = challenge_override(
        ch(strategy_fit={**CH_REASONING["strategy_fit"], "constructive_challenge": fit}),
        CHALLENGE_POST, "professional_opinion", "management")
    check(f"K6 CC fit={fit} (< {STRATEGY_CANDIDATE_FLOOR}) -> nem sul el", not ok, why)
for fit in (7, 8, 10):
    ok, why = challenge_override(
        ch(strategy_fit={**CH_REASONING["strategy_fit"], "constructive_challenge": fit}),
        CHALLENGE_POST, "professional_opinion", "management")
    check(f"K6.1 CC fit={fit} (>= {STRATEGY_CANDIDATE_FLOOR}) -> elsul", ok, why)

# K7 ATIRVA (2026-08-11, v19). A `CHALLENGE_FIT_FLOOR` KULON konstans volt a NYERS
# ponton, es ket dolog tortent vele: (a) NO-OP lett, mert a v13-as
# `thesis_condition`-kerdes a CC nyers pontjat 5.7-rol 8.6-ra emelte, tehat a 7-es
# padlo a mert eloszlason sosem kotott; (b) a v16-os `STRATEGY_CANDIDATE_FLOOR`
# ugyanarra a fogalomra jott be, csak a SULYOZOTT ponton — ket konstans egy fogalomra
# drift-hazard. A szenzor mostantol a `strategy_candidates`-re delegal.
check("K7 NINCS masodik padlo-konstans a modulban (egy definicio)",
      not hasattr(_eng_mod, "CHALLENGE_FIT_FLOOR"),
      "a `CHALLENGE_FIT_FLOOR` visszakerult — ket konstans ugyanarra a fogalomra")
check("K7.1 a szenzor a JELOLT-halmazra delegal (sulyozott pont, egy padlo)",
      STRATEGY_CANDIDATE_FLOOR == 7, str(STRATEGY_CANDIDATE_FLOOR))

# A SULYOZOTT szemantika bizonyitasa. A `_CHALLENGE_INTENTS` ket intentje ma NULLA
# CC-biast ad, tehat ott sulyozott == nyers — a kulonbseg csak akkor lathato, ha van
# CC-bias. Ideiglenesen beteszunk egyet (ugyanaz a minta, mint a K9-es veto-teszt).
_saved_bias = dict(_LEVEL_STRATEGY_BIAS["management"])
_LEVEL_STRATEGY_BIAS["management"]["constructive_challenge"] = -3.0
ok, why = challenge_override(
    ch(strategy_fit={**CH_REASONING["strategy_fit"], "constructive_challenge": 8}),
    CHALLENGE_POST, "professional_opinion", "management")
check("K7.2 nyers 8, de a bias -3 -> sulyozva 5, a szenzor NEM sul el", not ok, why)
check("K7.3 az indok a SULYOZOTT erteket mondja (nem a nyerset)",
      "sulyozva 5" in why, why)
_LEVEL_STRATEGY_BIAS["management"].clear()
_LEVEL_STRATEGY_BIAS["management"].update(_saved_bias)
ok, why = challenge_override(
    ch(strategy_fit={**CH_REASONING["strategy_fit"], "constructive_challenge": 8}),
    CHALLENGE_POST, "professional_opinion", "management")
check("K7.4 a bias visszaallitasa utan ugyanaz a bemenet ismet elsul", ok, why)
check("K8 a szenzor-intentek leteznek a taxonomiaban",
      all(i in CONVERSATION_INTENTS for i in _CHALLENGE_INTENTS),
      str(sorted(_CHALLENGE_INTENTS)))

# A VETO-MECHANIZMUS tiszteletben tartasa: ma egyetlen szint sem vetozza a CC-t, de
# ha valaha bekerul, a szenzor NEM irhatja felul a kemeny kaput.
_saved_veto = set(_LEVEL_VETO["business"])
_LEVEL_VETO["business"].add("constructive_challenge")
ok, why = challenge_override(ch(), CHALLENGE_POST, "professional_opinion", "business")
check("K9 a szint-veto erosebb a szenzornal", not ok, why)
_LEVEL_VETO["business"].clear()
_LEVEL_VETO["business"].update(_saved_veto)

check("K10 config default: bekapcsolva", challenge_sensor_enabled({}) is True)
check("K10.1 'off' -> kikapcsolva",
      challenge_sensor_enabled({"linkedin": {"challenge_sensor": "off"}}) is False)
check("K10.2 YAML-boolean False -> kikapcsolva",
      challenge_sensor_enabled({"linkedin": {"challenge_sensor": False}}) is False)

# A SEMA es a PROMPT egyutt: egy kotelezo mezo, amirol a prompt nem beszel, olyan
# mezo, amit a modell talalgat (A13.1 ugyanezt orzi az osszes mezore).
check("K11 mindket uj mezo a semaban ES kotelezo",
      all(f in _REASON_SCHEMA["properties"] and f in _REASON_SCHEMA["required"]
          for f in ("thesis_condition", "thesis_quote")))
check("K12 a prompt kimondja, hogy az URES valasz ervenyes (nincs kitalalasra nyomas)",
      "an empty answer here is a valid and frequent answer" in _REASON_PROMPT)
check("K13 a prompt kimondja, hogy az idezetet ellenorizzuk",
      "voids the condition" in _REASON_PROMPT)

# --- K') FELTETEL-MONOKULTURA (2026-08-11, v15) ------------------------------
# A MERT HIBA: a v13-as szenzor utan OT eles futasbol OT `thesis_condition`
# szerzodesi/incentiva-jellegű volt, es a v14-es KIMENETI kapu ezt nem gyogyitotta —
# kimeneti kapu nem javit bemeneti monokulturat. SZO SZERINTI naplo-reszletek:
COND_COMMERCIAL = [
    "when project contracts do not explicitly reward or penalize data quality",
    "when the contractual frameworks and operational incentives align for continuous",
    "when the client's procurement process does not explicitly define and compensate",
    "when the contractual and liability frameworks for AI-generated design are clear",
    "when project contracts and team incentives are aligned to reward early",
]
COND_OTHER = [
    "when the model is federated late in the phase",
    "on refurbishment work where the as-built survey is unreliable",
    "when the receiving office runs an older Archicad version",
    "when the family was authored by a different discipline",
]
check("K14 mind az OT mert feltetel ugyanabba a csaladba esik",
      all(_eng_mod.condition_family(c) == "move:commercial_frame" for c in COND_COMMERCIAL),
      str([_eng_mod.condition_family(c) for c in COND_COMMERCIAL]))
check("K15 a technikai/helyzeti feltetelek NEM esnek csaladba (nincs hamis pozitiv)",
      all(_eng_mod.condition_family(c) == "" for c in COND_OTHER),
      str([_eng_mod.condition_family(c) for c in COND_OTHER]))
# A feltetel EGY tagmondat: ott az elso kereskedelmi terminus mar a lenyeg. A
# kommentnel (100+ szo) ezert szigorubb a kuszob — ket kulonbozo szo kell.
check("K16 a feltetel-kuszob 1, a komment-kuszob 2 (dokumentalt kulonbseg)",
      _eng_mod._CONDITION_FAMILY_MIN_HITS == 1 and _eng_mod._CONTENT_MOVE_MIN_HITS == 2)

ok, why = challenge_override(ch(), CHALLENGE_POST, "professional_opinion", "management",
                             recent_conditions=["move:commercial_frame"])
check("K17 NEM kereskedelmi feltetel atmegy a kereskedelmi gyűrűn is",
      ok, why)   # a CH_REASONING feltetele: "older Archicad version"
ok, why = challenge_override(ch(thesis_condition=COND_COMMERCIAL[0],
                                thesis_quote=CH_REASONING["thesis_quote"]),
                             CHALLENGE_POST, "professional_opinion", "management",
                             recent_conditions=["move:commercial_frame"])
check("K18 ISMETLODO csaladu feltetel -> a szenzor NEM sul el", not ok, why)
check("K18.1 az indok megnevezi a csaladot es azt, hogy nem uj teny",
      "move:commercial_frame" in why and "nem uj teny" in why, why)
ok, why = challenge_override(ch(thesis_condition=COND_COMMERCIAL[0],
                                thesis_quote=CH_REASONING["thesis_quote"]),
                             CHALLENGE_POST, "professional_opinion", "management")
check("K19 gyűrű nelkul (regi hivas) a kereskedelmi feltetel is elfogadott", ok, why)

_eng_mod.reset_opening_state()
_eng_mod.remember_condition_family(COND_COMMERCIAL[0])
check("K20 a gyűrű CSAK csaladba eso feltetellel bővul",
      list(_eng_mod._recent_condition_families) == ["move:commercial_frame"],
      str(list(_eng_mod._recent_condition_families)))
_eng_mod.remember_condition_family(COND_OTHER[0])
check("K20.1 csalad nelkuli feltetel nem eget el helyet",
      list(_eng_mod._recent_condition_families) == ["move:commercial_frame"],
      str(list(_eng_mod._recent_condition_families)))
check("K21 a feltetel-gyűrű ugyanolyan mely, mint a tobbi",
      _eng_mod._recent_condition_families.maxlen == _eng_mod._OPENING_RING_SIZE)
check("K22 reset_opening_state a feltetel-gyűrűt is nullazza",
      (_eng_mod.reset_opening_state(), not _eng_mod._recent_condition_families)[1])

check("K23 a prompt elteriti a legkonnyebben elerheto valasztol",
      "AVOID THE MOST AVAILABLE ANSWER" in _REASON_PROMPT
      and "fits almost every claim in this industry" in _REASON_PROMPT)

# --- L) a fit mint SZURO, nem rangsor (2026-08-11, v16) ----------------------
# A MERT DIAGNOZIS: 4-5 strategia MINDIG >= 7, a v8-as prompt-szabalyok a sorok
# 73-100%-aban serulnek, es a nyers maximum 21 v13+ sorbol 13-ban holtverseny. A
# pontozas tehat egy lapos "elfogadhato" sav, nem rangsor.
#
# A LAPOS eset, ami a diagnozisbol jon (ot strategia 7 fölött, holtverseny 9-en):
FLAT = {"constructive_challenge": 9, "systems_thinking": 7, "field_experience": 9,
        "business_impact": 8, "future_outlook": 5, "practical_lesson": 7,
        "missing_perspective": 9}
P1, P2 = "Egy poszt szovege.", "Egy MASIK poszt szovege."

check("L1 a jelolt = akit a MODELL is jonak jelolt (>= padlo), veto nelkul",
      strategy_candidates(FLAT, "professional_opinion", "management")
      == ["constructive_challenge", "systems_thinking", "field_experience",
          "business_impact", "practical_lesson", "missing_perspective"],
      str(strategy_candidates(FLAT, "professional_opinion", "management")))
check("L2 a padlo alatti kimarad (future_outlook=5)",
      "future_outlook" not in strategy_candidates(FLAT, "professional_opinion", "management"))
check("L3 a VETO is szur (technical szint -> business_impact)",
      "business_impact" not in strategy_candidates(FLAT, "engineering_problem", "technical"),
      str(strategy_candidates(FLAT, "engineering_problem", "technical")))
check("L4 a padlo dokumentalt es 7", STRATEGY_CANDIDATE_FLOOR == 7)

# 1. A FRISSESSEG: a legutobbi ket strategia kiesik.
s1, why1 = decide_strategy(FLAT, P1, "professional_opinion", "management", recent=[])
s2, why2 = decide_strategy(FLAT, P1, "professional_opinion", "management", recent=[s1])
check("L5 ugyanaz a poszt, ures gyűrű -> REPRODUKALHATO",
      decide_strategy(FLAT, P1, "professional_opinion", "management", recent=[])[0] == s1)
check("L6 a gyűrűben levo strategia NEM nyer ujra", s2 != s1, f"{s1} -> {s2}")
check("L6.1 az indok megnevezi a kizarast", "kizarva ismetles miatt" in why2, why2)

# 2. A ROTACIO NEM URITHETI KI A DONTEST. A v16-ban ezt egy vedoszabaly biztositotta
# (ha minden jelolt a gyűrűben volt, a teljes lista maradt) — a v17-es ADAPTIV
# melyseg ota ez az ag elerhetetlen: legfeljebb annyit zarunk ki, hogy maradjon
# valaszthato. A hosszu `recent` lista igy sem uritheti ki a halmazt.
cands = strategy_candidates(FLAT, "professional_opinion", "management")
s3, why3 = decide_strategy(FLAT, P1, "professional_opinion", "management", recent=cands)
check("L7 a TELJES jelolt-lista a gyűrűben sem urit ki (melyseg-vagas)",
      s3 in cands and "mind a" not in why3, f"{s3} | {why3}")

# 3. A SULYOZOTT MAX dont a maradekbol, es CSAK holtversenyben a poszt-hash.
scores, _ = score_strategies(FLAT, "professional_opinion", "management")
top = max(scores[s] for s in cands)
check("L8 a gyoztes a sulyozott maximumon van", scores[s1] == top,
      f"{s1}={scores[s1]} vs top={top}")
check("L9 holtversenynel a poszt-hash dont (ket kulonbozo poszt szorhat)",
      "holtverseny" in why1 or "sulyozott max" in why1, why1)

# Egyetlen jelolt: nincs mit valasztani, es nem is szabad hash-elni.
ONE = {**FLAT, "constructive_challenge": 2, "systems_thinking": 2, "field_experience": 9,
       "business_impact": 2, "future_outlook": 2, "practical_lesson": 2,
       "missing_perspective": 2}
s, why = decide_strategy(ONE, P1, "professional_opinion", "management", recent=[])
check("L10 egyetlen jelolt -> az nyer", s == "field_experience", f"{s} | {why}")

# 4. FALLBACK: ha egy strategia sem eri el a padlot, a valtozatlan `pick_strategy`.
LOW = {k: 4 for k in STRATEGIES}
LOW["systems_thinking"] = 6
s, why = decide_strategy(LOW, P1, "professional_opinion", "management", recent=[])
check("L11 nincs jelolt -> a VALTOZATLAN sulyozott argmax dont",
      s == pick_strategy(LOW, "professional_opinion", "management")
      and "nincs jelolt" in why, f"{s} | {why}")
check("L11.1 a padlo nem urithet ki dontest (mindig van strategia)",
      all(decide_strategy({k: v for k in STRATEGIES}, P1, "general", "management",
                          recent=[])[0] in STRATEGIES for v in (0, 3, 6, 7, 10)))

# 5. A gyűrű
_eng_mod.reset_opening_state()
remember_strategy("field_experience")
remember_strategy("practical_lesson")
check("L12 a gyűrű a legutobbi strategiakat orzi",
      list(_eng_mod._recent_strategies) == ["field_experience", "practical_lesson"],
      str(list(_eng_mod._recent_strategies)))
remember_strategy("")
check("L12.1 ures kulcs nem kerul be",
      list(_eng_mod._recent_strategies) == ["field_experience", "practical_lesson"])
remember_strategy("business_impact")
check("L13 a gyűrű _STRATEGY_RING_SIZE-ra van vagva",
      len(_eng_mod._recent_strategies) == _STRATEGY_RING_SIZE
      and "field_experience" not in _eng_mod._recent_strategies,
      str(list(_eng_mod._recent_strategies)))
check("L14 a strategia-gyűrű SEKELYEBB a nyitas-gyűrűnel (mert kisebb a halmaz)",
      _STRATEGY_RING_SIZE < _eng_mod._OPENING_RING_SIZE,
      f"{_STRATEGY_RING_SIZE} vs {_eng_mod._OPENING_RING_SIZE}")
check("L15 reset_opening_state a strategia-gyűrűt is nullazza",
      (_eng_mod.reset_opening_state(), not _eng_mod._recent_strategies)[1])

# 6. Config + a `pick_strategy` VALTOZATLANSAGA (a B-blokk erre epul)
check("L16 config default: bekapcsolva", strategy_candidates_enabled({}) is True)
check("L16.1 'off' -> kikapcsolva",
      strategy_candidates_enabled({"linkedin": {"strategy_candidates": "off"}}) is False)
check("L17 a `pick_strategy` VALTOZATLAN: a v1-es dontest adja (a B-blokk erre epul)",
      all(pick_strategy(f, *_LAYER_OFF) == v1_pick(f) for f in FITS),
      str([(pick_strategy(f, *_LAYER_OFF), v1_pick(f)) for f in FITS]))

# A J6 TALALATA, kod-szintu zarral. A nyers pontra szűrve a v2 ota dokumentalt
# alaphiba visszajonne: a mesterseg-poszton a modell a `business_impact`-nek ad 10-et,
# a `field_experience`-nek 6-ot. A bias az utobbit 9.0-ra emeli — egy szűro, ami a
# bias ELOTT vag, pont ezt a korrekciót dobja ki.
CRAFT_FIT = {"constructive_challenge": 4, "systems_thinking": 7, "field_experience": 6,
             "business_impact": 10, "future_outlook": 5, "practical_lesson": 6,
             "missing_perspective": 5}
craft_cands = strategy_candidates(CRAFT_FIT, "craftsmanship", "technical")
check("L18 a padlo a SULYOZOTT pontra megy (a bias-korrekcio nem eshet ki)",
      set(craft_cands) == {"field_experience", "practical_lesson"}, str(craft_cands))
check("L18.1 a nyers 7-es systems_thinking NEM jelolt (sulyozva 5.0)",
      "systems_thinking" not in craft_cands)
check("L18.2 a mesterseg-poszton mesterseg-strategia nyer (a v2-es alaphiba zarva)",
      decide_strategy(CRAFT_FIT, P1, "craftsmanship", "technical", recent=[])[0]
      in ("field_experience", "practical_lesson"),
      str(decide_strategy(CRAFT_FIT, P1, "craftsmanship", "technical", recent=[])))

# --- L') ADAPTIV GYŰRŰ-MELYSEG (2026-08-11, v17) -----------------------------
# A MERT HIBA: nyolc eles posztbol KETTONEL mindossze ket jelolt volt, mindketto a
# ketmelysegű gyűrűben — a vedoszabaly visszaadta a teljes listat, es a rotacio nem
# tett semmit (ismetles). A melyseg ezert a jelolt-szamhoz igazodik.
TWO = {"constructive_challenge": 3, "systems_thinking": 3, "field_experience": 9,
       "business_impact": 3, "future_outlook": 3, "practical_lesson": 9,
       "missing_perspective": 3}
two_cands = strategy_candidates(TWO, "professional_opinion", "management")
check("L19 ket jelolt eseten a melyseg 1 -> a rotacio MEGIS hat",
      len(two_cands) == 2 and
      decide_strategy(TWO, P1, "professional_opinion", "management",
                      recent=["field_experience", "practical_lesson"])[0]
      == "field_experience",
      f"{two_cands} | {decide_strategy(TWO, P1, 'professional_opinion', 'management', recent=['field_experience', 'practical_lesson'])}")
check("L19.1 az indok kiirja a melyseget (auditalhato)",
      "gyűrű-melyseg 1" in decide_strategy(
          TWO, P1, "professional_opinion", "management",
          recent=["field_experience", "practical_lesson"])[1],
      decide_strategy(TWO, P1, "professional_opinion", "management",
                      recent=["field_experience", "practical_lesson"])[1])

# AZ INVARIANS: a vedoszabaly-ag ("mind a N jelolt szerepelt") mostantol ELERHETETLEN.
# Ha valaha megjelenik az indokban, a melyseg-szamitas elromlott.
_guard_hits = []
for n in range(1, 8):
    fit = {s: (9 if i < n else 3) for i, s in enumerate(STRATEGIES)}
    cands = strategy_candidates(fit, "professional_opinion", "management")
    for ring in ([], list(STRATEGIES), list(reversed(list(STRATEGIES))),
                 cands, cands[:1], cands[-2:]):
        s, why = decide_strategy(fit, P1, "professional_opinion", "management", recent=ring)
        if "mind a" in why:
            _guard_hits.append((n, ring, why))
        if s not in cands and cands:
            _guard_hits.append((n, ring, f"a gyoztes NEM jelolt: {s}"))
check("L19.2 a vedoszabaly-ag elerhetetlen, es a gyoztes MINDIG jelolt",
      not _guard_hits, str(_guard_hits[:2]))
check("L19.3 egyetlen jelolt: nincs kizaras, o nyer (melyseg 0)",
      decide_strategy(ONE, P1, "professional_opinion", "management",
                      recent=["field_experience"])[0] == "field_experience")

# --- K'') A SZENZOR TISZTELI A ROTACIOT (2026-08-11, v17) --------------------
# A MERT HIBA: a szenzor a `decide_strategy` UTAN fut, tehat visszahozta a CC-t akkor
# is, amikor a strategia-gyűrű epp kizarta -> ket egymas utani CC-komment.
ok, why = challenge_override(ch(), CHALLENGE_POST, "professional_opinion", "management",
                             recent_strategies=["constructive_challenge"])
check("K24 a CC a strategia-gyűrűben -> a szenzor NEM sul el", not ok, why)
check("K24.1 az indok kimondja, hogy a TENY jo volt, csak a rotacio zarta",
      "igazolt feltetel" in why and "rotacio" in why, why)
ok, why = challenge_override(ch(), CHALLENGE_POST, "professional_opinion", "management",
                             recent_strategies=["field_experience", "practical_lesson"])
check("K25 MAS strategiak a gyűrűben -> a szenzor elsul", ok, why)
ok, why = challenge_override(ch(), CHALLENGE_POST, "professional_opinion", "management")
check("K26 gyűrű nelkul (regi hivas) valtozatlan", ok, why)
# A sorrend SZANDEKOS: a rotacio-feltetel az UTOLSO, hogy az indok megkulonboztesse a
# "nem volt teny" es a "volt teny, de rotacio" esetet — a telemetriaban ket kulonbozo
# jelenseg, es kulon kell tudni szamolni oket.
ok, why = challenge_override(ch(thesis_condition=""), CHALLENGE_POST,
                             "professional_opinion", "management",
                             recent_strategies=["constructive_challenge"])
check("K27 ha NINCS teny, az indok a tenyre hivatkozik, nem a rotaciora",
      not ok and "nem talalt kimondatlan feltetelt" in why, why)


# --- O) A GONDOLAT KERETE A FORRASNAL (2026-08-11, engine v23) ---------------
# A MERES, ami ezt kikenyszeritette: a naploban 13 kereskedelmi keretű kommentbol
# TIZENKETTONEL mar az `insight` tartalmazta a keret szavait, tehat a dontes a
# REASON lepesben megszuletett, es a compose-oldali kapu elvileg sem gyogyithatta.
# 13-bol HATNAL nem is a szenzor valasztotta a strategiat, tehat a meglevo
# feltetel-gyűrű ott le sem futott.
from responder.linkedin_engine import (  # noqa: E402
    _MOVE_LABELS, _recent_insight_families, insight_family,
    insight_steer_block, insight_frame_steer_enabled, remember_insight_family,
    reason_prompt_for, reset_opening_state,
)

# VALODI insight a naplobol (2026-08-11), nem kitalalt fixture.
O_COMMERCIAL = ("The 'tax' of rebuilding models by hand is often a direct "
                "consequence of project contracts that specify deliverables as "
                "drawings or PDFs, rather than models with embedded data.")
O_NEUTRAL = ("The underlying issue with Revit stairs is the rigid separation "
             "between sketch-based geometry and system family intelligence.")

check("O1 a MERT kereskedelmi insight csaladba esik",
      insight_family(O_COMMERCIAL) == "move:commercial_frame",
      insight_family(O_COMMERCIAL))
check("O2 a MERT technikai insight NEM esik csaladba (nincs hamis pozitiv)",
      insight_family(O_NEUTRAL) == "", insight_family(O_NEUTRAL))

# A LEGFONTOSABB GARANCIA: ures gyűrű -> ures blokk -> a REASON-hivas BAJTRA a
# korabbi. Enelkul a mechanizmus nem lenne tiszta A/B-kent merheto.
check("O3 ures gyűrű -> URES blokk (a hivas bajtra a v22-es)",
      insight_steer_block([]) == "" and insight_steer_block(None) == "")

_blk = insight_steer_block(["move:commercial_frame"])
check("O4 a blokk EMBERI leirast ad, nem a belso slugot",
      "contracts" in _blk and "move:commercial_frame" not in _blk, _blk[:70])
check("O5 a blokk NEM tilt, csak elterit (a poszt joga eldontheti)",
      "not wrong" in _blk and "no honest alternative" in _blk)
check("O6 ket ugyanolyan csalad -> EGY felsorolas-pont (dedup)",
      insight_steer_block(["move:commercial_frame"] * 3).count("\n  - ") == 1)
check("O7 ismeretlen csalad-kulcs csendben kimarad (nincs ures pont, nincs hiba)",
      insight_steer_block(["move:nincs_ilyen"]) == ""
      and insight_steer_block(["move:nincs_ilyen", "move:commercial_frame"]).count("\n  - ") == 1)
check("O8 mindket ismert csalad kap emberi cimket",
      set(_MOVE_LABELS) == {"move:commercial_frame", "move:tool_interop_frame"},
      str(sorted(_MOVE_LABELS)))

# A steer a USER-uzenetbe megy, NEM a system-promptba: kulonben minden hivas mas
# system-promptot kapna, es a prompt-gyorsitotarazas elveszne.
check("O9 a system-prompt valtozatlan (a steer nem oda kerul)",
      "FRAMES ALREADY USED" not in reason_prompt_for(False)
      and "FRAMES ALREADY USED" not in reason_prompt_for(True))

reset_opening_state()
check("O10 a gyűrű ures indulaskor", not list(_recent_insight_families))
remember_insight_family(O_COMMERCIAL)
check("O11 a MEGVALOSULT keret bekerul a gyűrűbe",
      list(_recent_insight_families) == ["move:commercial_frame"],
      str(list(_recent_insight_families)))
remember_insight_family(O_NEUTRAL)
check("O12 a csaladba nem eso insight NEM szennyezi a gyűrűt",
      list(_recent_insight_families) == ["move:commercial_frame"],
      str(list(_recent_insight_families)))
check("O13 a gyűrűbol felepul a kovetkezo hivas eltentese",
      "contracts" in insight_steer_block(list(_recent_insight_families)))
reset_opening_state()
check("O14 reset_opening_state az insight-gyűrűt is nullazza",
      not list(_recent_insight_families))

check("O15 kill switch: on a kod-default, 'off' es False is kikapcsol",
      insight_frame_steer_enabled({}) is True
      and insight_frame_steer_enabled({"linkedin": {"insight_frame_steer": "off"}}) is False
      and insight_frame_steer_enabled({"linkedin": {"insight_frame_steer": False}}) is False)

print()
bad = 0
for name, ok, detail in results:
    if not ok:
        bad += 1
    print(f"  {'OK  ' if ok else 'FAIL'} {name}" + (f"   [{detail}]" if detail else ""))
print(f"\n{len(results) - bad}/{len(results)} teszt zold.")
sys.exit(1 if bad else 0)
