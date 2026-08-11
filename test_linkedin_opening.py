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

I) NYITAS-VISSZHANG (2026-08-11, engine v9) — a MEGVALOSULT nyitas kapuja.
A forma-rotacio egy meresen elbukott: ot eles generalasbol haromban HAROM
KULONBOZO forma volt kiosztva (`own_practice`, `strikes`, `pattern`), a modell
megis mindharomszor ugyanazzal a mondattal indult ("What strikes me ..."). A
kijeloles tehat utasitas, nem eredmeny. Ez a szekcio azt orzi, hogy a kapu a
SAJAT elozo kimeneteinkhez mer (nem szotarhoz), es hogy a ket gyűrű nem dolgozik
egymas ellen.
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
    # I) nyitas-visszhang (v9)
    _recent_opening_texts, _OPENING_ECHO_RING_SIZE, _OPENING_FINGERPRINT_WORDS,
    opening_fingerprint, remember_opening_text, opening_echo_gate_enabled,
    check_quality,
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
eng.reset_opening_state()
remember_opening("pattern")
remember_opening("strikes")
check("E1 a gyűrű a kijelolt formakat orzi",
      list(_recent_openings) == ["pattern", "strikes"], str(list(_recent_openings)))
check("E2 ures kulcs nem kerul be (szabad valaszforma nem eget el helyet)",
      (remember_opening(""), list(_recent_openings) == ["pattern", "strikes"])[1])

eng.reset_opening_state()
for k in list(OPENING_SHAPES):
    remember_opening(k)
check("E3 a gyűrű a legutobbi _OPENING_RING_SIZE elemre van vagva",
      len(_recent_openings) == _OPENING_RING_SIZE
      and list(_recent_openings) == list(OPENING_SHAPES)[-_OPENING_RING_SIZE:],
      str(list(_recent_openings)))
eng.reset_opening_state()

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
    # 2026-08-11: a `_CONSULTANT_VOICE_PATTERNS` is bekerult a korbe. Az uj lista
    # eppen "we/i + often + find/see" alakokat tilt, a katalogusban pedig ott van az
    # "I've found..." (`own_practice`) es a "We've learned..." (`learned`) — ha a
    # minta az altalanosito hatarozo nelkul is illeszkedne, MINDEN ilyen nyitasu
    # komment ujrairast kapna. Ez a check pontosan ezt zarja ki.
    for pattern, label in (_STOCK_OPENING_PATTERNS + _FORBIDDEN_PATTERNS
                           + eng._CONSULTANT_VOICE_PATTERNS):
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
    eng.reset_opening_state()
    res_on = eng.generate_comment({"linkedin": {}}, POST)
    ring_after = list(_recent_openings)
    msg_on = compose_msgs[-1]

    eng.reset_opening_state()
    res_off = eng.generate_comment(
        {"linkedin": {"opening_variety": "off"}}, POST)
    msg_off = compose_msgs[-1]
    ring_off = list(_recent_openings)
finally:
    eng._client = _real
    eng.reset_opening_state()

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

# --- I) nyitas-visszhang: a MEGVALOSULT nyitas kapuja (v9) --------------------
# A MERT ESET, szo szerint a harom eles kommentbol (bench_posts/01, 04, 05):
ECHO_1 = ("What strikes me about this is the challenge of disambiguating intent "
          "when a single stroke could represent a new element.")
ECHO_2 = ("What strikes me about the discussion around as-built accuracy is how "
          "often the biggest challenge isn't technical, but commercial.")
ECHO_3 = ("What strikes me is how often this perceived 'delay' in coordination is "
          "worsened by how we structure payments.")

# 2026-08-11 (v11): a VART ERTEK 'what strikes me' -> 'frame:notable'. A teszt
# ALLITASA valtozatlan (a harom mert nyitas EGY ujjlenyomatra esik) — csak az
# ujjlenyomat lett a keret neve, mert a szo-szintű varialas kijatszotta a harom-szavas
# valtozatot. Ld. J) szekcio.
check("I1 a harom MERT nyitas ugyanarra az ujjlenyomatra esik",
      opening_fingerprint(ECHO_1) == opening_fingerprint(ECHO_2)
      == opening_fingerprint(ECHO_3) == "frame:notable",
      f"{opening_fingerprint(ECHO_1)!r} / {opening_fingerprint(ECHO_2)!r} / "
      f"{opening_fingerprint(ECHO_3)!r}")

# A batch tobbi ket kommentjenek nyitasa — ezek NEM eshetnek egybe egymassal sem,
# sem a fentiekkel, kulonben a kapu hamis pozitivot adna ugyanarra a kotegre.
OTHER_1 = ("I've found that the conceptual stage often suffers most from undefined "
           "data ownership.")
OTHER_2 = "One thing that stood out in your example is how much the benefits go beyond."
check("I2 kulonbozo mozdulat -> kulonbozo ujjlenyomat (nincs hamis pozitiv)",
      len({opening_fingerprint(t) for t in (ECHO_1, OTHER_1, OTHER_2)}) == 3,
      str([opening_fingerprint(t) for t in (ECHO_1, OTHER_1, OTHER_2)]))

# A harom-szavas szabaly a KERETBE NEM eso nyitasokra all (a keret egy token).
check("I3 keret nelkuli nyitas: pontosan _OPENING_FINGERPRINT_WORDS szo",
      len(opening_fingerprint(OTHER_1).split()) == _OPENING_FINGERPRINT_WORDS,
      opening_fingerprint(OTHER_1))
check("I4 csak az ELSO mondat szamit (a masodik mar tartalom)",
      opening_fingerprint("Short one. What strikes me about this.") == "short one",
      opening_fingerprint("Short one. What strikes me about this."))
check("I5 az irasjel-valtozat nem hoz letre ket ujjlenyomatot",
      opening_fingerprint("I've found that X.") == opening_fingerprint("I’ve found that X."))
check("I6 ures komment -> ures ujjlenyomat, nem kivetel", opening_fingerprint("") == "")

# MERT HIBA (2026-08-11, eles magyar futas): az elso valtozat `[^a-z0-9]`-t
# hasznalt, ezert az ekezetes betu SZOHATAR lett -> 'egy visszat r' (masfel szo,
# harom helyett). Az ekezet-hajtogatas ezt javitja.
HU = "Egy visszatérő mintát látok, ahogy a „pipálgatós” auditok kudarcot vallanak."
check("I6.1 magyar nyitas: EGESZ szavak, nem ekezet-fragmentumok",
      opening_fingerprint(HU) == "egy visszatero mintat", opening_fingerprint(HU))
check("I6.2 az ekezet nelkul irt valtozat ugyanaz az ujjlenyomat",
      opening_fingerprint("Egy visszatero mintat latok.") == opening_fingerprint(HU))

# A kapu maga — TISZTA fuggveny, a gyűrűt a hivo adja at.
eng.reset_opening_state()
echo_issues = check_quality(ECHO_2, POST, intent="engineering_problem",
                           discourse_level="technical",
                           recent_openings=["frame:notable"])
check("I7 a kapu kifogja az ismetlodo MEGVALOSULT nyitast",
      any("azonos kezdes" in i for i in echo_issues), str(echo_issues))
check("I8 a sertes megnevezi a konkret ujjlenyomatot (az ujrairas igy celzott)",
      any("'frame:notable'" in i for i in echo_issues), str(echo_issues))
check("I9 gyűrű nelkul (None) a kapu NEM meri — regi hivas valtozatlan",
      not any("azonos kezdes" in i
              for i in check_quality(ECHO_2, POST, intent="engineering_problem",
                                     discourse_level="technical")))
check("I10 ures gyűrű -> nincs sertes",
      not any("azonos kezdes" in i
              for i in check_quality(ECHO_2, POST, intent="engineering_problem",
                                     discourse_level="technical",
                                     recent_openings=[])))
check("I11 mas nyitas ugyanazzal a gyűrűvel atmegy",
      not any("azonos kezdes" in i
              for i in check_quality(OTHER_1 + " " + OTHER_2, POST,
                                     intent="engineering_problem",
                                     discourse_level="technical",
                                     recent_openings=["what strikes me"])))

# A gyűrű
eng.reset_opening_state()
remember_opening_text(ECHO_1)
check("I12 sikeres komment utan a visszhang-gyűrű bővult",
      list(_recent_opening_texts) == ["frame:notable"], str(list(_recent_opening_texts)))
remember_opening_text("")
check("I13 ures komment nem eget el helyet a gyűrűben",
      list(_recent_opening_texts) == ["frame:notable"], str(list(_recent_opening_texts)))
for i in range(_OPENING_ECHO_RING_SIZE + 3):
    remember_opening_text(f"Sentence number {i} here.")
check("I14 a gyűrű a legutobbi _OPENING_ECHO_RING_SIZE elemre van vagva",
      len(_recent_opening_texts) == _OPENING_ECHO_RING_SIZE, str(list(_recent_opening_texts)))

# A KET GYŰRŰ EGYUTT: ha a visszhang-gyűrű melyebb lenne, olyan formát buntetne,
# amit a rotacio joggal ad ki ujra — ezert egyetlen szambol jon mindketto.
check("I15 a ket gyűrű egyforma melysegű (nem dolgoznak egymas ellen)",
      _OPENING_ECHO_RING_SIZE == _OPENING_RING_SIZE,
      f"{_OPENING_ECHO_RING_SIZE} vs {_OPENING_RING_SIZE}")

# Ugyanaz az onvedelem, mint a G1-nel: a sajat katalogusunk formai nem eshetnek
# egybe, kulonben ket egymas utani, KULONBOZO forma is sertest kapna.
_fps = {}
for key, shape in OPENING_SHAPES.items():
    fp = opening_fingerprint(shape["example"].strip('"'))
    _fps.setdefault(fp, []).append(key)
_fp_collisions = {fp: keys for fp, keys in _fps.items() if len(keys) > 1}
check("I16 a katalogus formai kulonbozo ujjlenyomatot adnak",
      not _fp_collisions, str(_fp_collisions))

check("I17 config default: bekapcsolva", opening_echo_gate_enabled({}) is True)
check("I18 'off' -> kikapcsolva",
      opening_echo_gate_enabled({"linkedin": {"opening_echo_gate": "off"}}) is False)
check("I19 YAML-boolean False -> kikapcsolva",
      opening_echo_gate_enabled({"linkedin": {"opening_echo_gate": False}}) is False)
check("I20 reset_opening_state MINDKET gyűrűt nullazza",
      (remember_opening("strikes"), remember_opening_text(ECHO_1),
       eng.reset_opening_state(),
       not _recent_openings and not _recent_opening_texts)[3])
eng.reset_opening_state()

# --- J) nyito-KERETEK: ugyanaz a mozdulat mas szavakkal (v11) -----------------
# A MERT KIJATSZAS: a v9-es kapu blokkolta a "What strikes me"-t, es a modell
# masodik kore "What's compelling about Frank's approach..."-szal indult. Harom szo
# szerint mas ujjlenyomat, retorikailag ugyanaz a mozdulat.
BYPASS = "What's compelling about Frank's approach is the clarity it brings to drawings."
check("J1 a MERT kijatszas-par ugyanarra az ujjlenyomatra esik",
      opening_fingerprint(ECHO_1) == opening_fingerprint(BYPASS) == "frame:notable",
      f"{opening_fingerprint(ECHO_1)!r} vs {opening_fingerprint(BYPASS)!r}")
check("J2 a keret-csalad tovabbi szinonimai is ugyanide esnek",
      all(opening_fingerprint(t) == "frame:notable" for t in (
          "What is interesting here is the ownership question.",
          "What struck me was the missing dimension case.",
          "What's so telling about this is the payment structure.")))

# A KOMMENT KOZEPEN allo ugyanilyen fordulat NEM nyitasi hiba: a poszt 13 kommentje
# valoban mas mozdulattal indult, csak kesobb hasznalta a keretet.
MID = ("I've run into similar challenges with adoption, and what strikes me is how "
       "much inertia there is against switching tools.")
check("J3 a mondat KOZEPEN levo keret nem kanonizal (a nyitas valoban mas)",
      opening_fingerprint(MID) == "i ve run", opening_fingerprint(MID))

check("J4 negativ: nem minden 'What...' kezdes keret",
      all(opening_fingerprint(t) != "frame:notable" for t in (
          "What matters here is who maintains the script.",
          "What about the handover case?",
          "What a project like this needs is a versioned parameter file.")),
      str([opening_fingerprint(t) for t in (
          "What matters here is who maintains the script.",
          "What about the handover case?",
          "What a project like this needs is a versioned parameter file.")]))

eng.reset_opening_state()
check("J5 a kapu MOST kifogja a kijatszast (a gyűrűben csak a keret van)",
      any("azonos kezdes" in i for i in
          check_quality(BYPASS + " " + " ".join(["word"] * 40), POST,
                        intent="product_demonstration", discourse_level="management",
                        recent_openings=["frame:notable"])))

# A KET MECHANIZMUS SZERZODESE: ha a rotacio EPPEN a `strikes` formát adta ki, a
# `frame:notable` nem lehet sertes — kulonben a modell a sajat utasitasa miatt kapna
# ujrairast. (Merve: egy `stood_out` kiosztasu komment is elhasznalta a keretet.)
check("J6 csak a `strikes` formának van sajat kerete",
      eng.shape_frame("strikes") == "frame:notable"
      and all(eng.shape_frame(k) == "" for k in OPENING_SHAPES if k != "strikes"),
      str({k: eng.shape_frame(k) for k in OPENING_SHAPES}))
eng.reset_opening_state()
remember_opening_text(ECHO_1)          # a gyűrűben: frame:notable
check("J7 kiosztott `strikes` -> a sajat kerete KIMARAD a kapunak adott gyűrűből",
      eng.echo_ring_for("strikes") == [], str(eng.echo_ring_for("strikes")))
check("J8 MAS kiosztott forma -> a keret BENENE marad (a visszhang sertes)",
      eng.echo_ring_for("own_practice") == ["frame:notable"],
      str(eng.echo_ring_for("own_practice")))
check("J9 ures kiosztas (szabad valaszforma) -> a gyűrű valtozatlan",
      eng.echo_ring_for("") == ["frame:notable"], str(eng.echo_ring_for("")))
eng.reset_opening_state()

# --- K) nyelv-mezok: szegmentalas, nem kapuzas (v11) -------------------------
# A merőszamaink FELE angolra kalibralt (a `concreteness` lexikonja es a hossz-sav
# szoszama), a naplo viszont eddig nem tudta, milyen nyelven ment ki a komment.
HU_REPLY = ("Ahogy felveted, az, hogy az AI nemcsak elolvassa, hanem ertelmezi is a "
            "szabalyzatokat egy uzleti helyzetben, kulcsfontossagu kihivas.")
EN_REPLY = ("I have found that the shared parameter GUID travels with the definition "
            "file and not with the model itself.")
check("K1 a magyar komment nem 'en'", eng.looks_english(HU_REPLY) is False)
check("K2 az angol komment 'en'", eng.looks_english(EN_REPLY) is True)

# --- L) tartalmi mozdulat + a harmadik kor (v14) -----------------------------
# A MERT HIBA 1: a kihivas-szenzor utan HET CC-kommentbol HAT ugyanoda futott ki
# (szerzodes/incentiva-keret). SZO SZERINTI reszletek a naplobol:
MOVE_1 = ("What strikes me is the inherent shift in contractual frameworks it implies. "
          "Current contracts typically define a clear end to the design team's "
          "responsibility, so we would need engagement models that incentivise "
          "continuous data integrity beyond handover.")
MOVE_2 = ("One thing I've observed is that the real pressure point is aligning "
          "contractual incentives across all parties. Without that, the motivation to "
          "spend upfront on clash resolution isn't always there.")
NO_MOVE = ("The GUID travels with the definition file, not with the model, so once "
           "someone rebuilds that file the schedule mapping quietly detaches and "
           "nothing warns you about it until a schedule stops matching.")
ONE_HIT = ("The incentive to model early is real, but the IFC property sets are where "
           "this actually breaks down on export.")

check("L1 a ket MERT komment ugyanarra a mozdulatra esik",
      eng.content_move(MOVE_1) == eng.content_move(MOVE_2) == "move:commercial_frame",
      f"{eng.content_move(MOVE_1)!r} / {eng.content_move(MOVE_2)!r}")
check("L2 technikai komment: nincs mozdulat", eng.content_move(NO_MOVE) == "",
      eng.content_move(NO_MOVE))
check("L3 EGY futo emlites nem a komment mozdulata (kuszob: 2 kulonbozo terminus)",
      eng.content_move(ONE_HIT) == "", eng.content_move(ONE_HIT))
check("L4 a kuszob dokumentalt es 2", eng._CONTENT_MOVE_MIN_HITS == 2)

check("L5 a kapu kifogja az ismetlodo GONDOLATOT",
      any("ismetlodo gondolat" in i for i in
          check_quality(MOVE_2 + " " + " ".join(["word"] * 30), POST,
                        intent="professional_opinion", discourse_level="business",
                        recent_moves=["move:commercial_frame"])),
      str(check_quality(MOVE_2, POST, recent_moves=["move:commercial_frame"])))
check("L6 gyűrű nelkul (None) NEM mer — regi hivas valtozatlan",
      not any("ismetlodo gondolat" in i for i in
              check_quality(MOVE_2, POST, intent="professional_opinion",
                            discourse_level="business")))

# A SZERZODES a strategiaval: a `business_impact` direktivaja EPPEN a kereskedelmi
# kovetkezmeny — ott a mozdulat utasitas, nem visszhang.
eng.reset_opening_state()
eng.remember_content_move(MOVE_1)
check("L7 a gyűrű bővult", list(eng._recent_content_moves) == ["move:commercial_frame"],
      str(list(eng._recent_content_moves)))
check("L8 `business_impact` -> a sajat mozdulata KIMARAD a gyűrűből",
      eng.move_ring_for("business_impact") == [], str(eng.move_ring_for("business_impact")))
check("L9 MAS strategia -> a mozdulat BENNE marad",
      eng.move_ring_for("constructive_challenge") == ["move:commercial_frame"],
      str(eng.move_ring_for("constructive_challenge")))
check("L10 a mozdulat-gyűrű ugyanolyan mely, mint a masik ketto",
      eng._recent_content_moves.maxlen == _OPENING_RING_SIZE,
      f"{eng._recent_content_moves.maxlen} vs {_OPENING_RING_SIZE}")
check("L11 reset_opening_state MINDHAROM gyűrűt nullazza",
      (eng.reset_opening_state(), not eng._recent_content_moves
       and not _recent_openings and not _recent_opening_texts)[1])


# --- N) EGYSZERI KEGYELEM, NEM OROK MENTESSEG (2026-08-11, v22) --------------
# A MERT HIBA: a kivetel a mozdulat MINDEN elofordulasat kivette a gyűrűből, tehat
# a `business_impact` sosem bukhatott kereskedelmi visszhangon — merve: harom
# `move:commercial_frame` mellett is URES gyűrűt kapott. Amig ez a strategia nyer,
# a monokultura korlatlanul futhatott, es a kapu visszakapcsolasa sem segitett volna.
# A kivetel INDOKA helyes (a direktiva eppen ezt keri), a MERTEKE volt hibas.
C_FRAME = "move:commercial_frame"


def _ring_with(n, extra=()):
    eng.reset_opening_state()
    for _ in range(n):
        eng._recent_content_moves.append(C_FRAME)
    for m in extra:
        eng._recent_content_moves.append(m)


_ring_with(1)
check("N1 EGY sajat mozdulat meg kegyelmet kap (utasitas-kovetes, nem visszhang)",
      C_FRAME not in eng.move_ring_for("business_impact"),
      str(eng.move_ring_for("business_impact")))
_ring_with(2)
check("N2 KETTO mar sorozat -> a `business_impact` is bukik",
      C_FRAME in eng.move_ring_for("business_impact"),
      str(eng.move_ring_for("business_impact")))
_ring_with(3)
check("N3 a kegyelem PONTOSAN egy (harombol ketto marad, nem nulla)",
      eng.move_ring_for("business_impact").count(C_FRAME) == 2,
      str(eng.move_ring_for("business_impact")))
check("N4 a kegyelem merteke egyetlen konstansbol jon (nincs beegetett szam)",
      eng._MOVE_EXEMPT_GRACE == 1, str(eng._MOVE_EXEMPT_GRACE))

# A kegyelem CSAK a sajat mozdulatra jar: egy masik csalad elso elofordulasa is szamit.
_ring_with(0, extra=["move:tool_interop_frame"])
check("N5 a kegyelem NEM terjed ki mas csaladra",
      eng.move_ring_for("business_impact") == ["move:tool_interop_frame"],
      str(eng.move_ring_for("business_impact")))

# A NEM kivetelezett strategiakat ez nem erinti: ott mar az elso elofordulas sertes.
_ring_with(1)
check("N6 nem kivetelezett strategianal valtozatlan (mar 1 elofordulas is sertes)",
      eng.move_ring_for("field_experience") == [C_FRAME],
      str(eng.move_ring_for("field_experience")))

# A szerzonkenti gyűrű (v21) ugyanabba a szamolasba megy: a kegyelem a KETTO
# egyuttesere jar egyszer, kulonben szerzot valtva ujraindulna a mentesseg.
_ring_with(1)
check("N7 a szerzonkenti gyűrű ugyanabba a szamolasba szamit bele",
      C_FRAME in eng.move_ring_for("business_impact", extra=[C_FRAME]),
      str(eng.move_ring_for("business_impact", extra=[C_FRAME])))
eng.reset_opening_state()

check("L12 config default: bekapcsolva", eng.content_echo_gate_enabled({}) is True)
check("L13 'off' -> kikapcsolva",
      eng.content_echo_gate_enabled({"linkedin": {"content_echo_gate": "off"}}) is False)

# A MERT HIBA 2: negy komment SERTESSEL ment ki, mert a ciklus `range(2)` volt es a
# modell a 2. korben ugyanannak a mozdulatnak MAS alakjat hozta ("We often see" ->
# "I often find"). A harmadik kor CSAK az ismetles-osztalyra jar.
check("L14 a harmadik kor letezik", eng.MAX_COMPOSE_ATTEMPTS == 3,
      str(eng.MAX_COMPOSE_ATTEMPTS))
check("L15 a NEGY mert eset mind ismetles-osztaly (ezert jar rajuk a 3. kor)",
      all(eng.only_rephrasable(iss) for iss in (
          ["ismetlodo nyitas (We often see)"],
          ["tanacsadoi hang (We often see/found)"],
          ["tanacsadoi hang (We often see/found)",
           "ismetlodo nyitas (a legutobbi kommentek egyikevel azonos kezdes: 'i ve found')"],
          ["tanacsadoi hang (We often see/found)", "tanacsadoi hang (I often find)"])))
check("L16 tartalmi sertes NEM ismetles-osztaly (arra nincs plusz kor)",
      not eng.only_rephrasable(["tul rovid (19 szo, min 35)"])
      and not eng.only_rephrasable(["ismetlodo gondolat (move:commercial_frame)"])
      and not eng.only_rephrasable(["ismetlodo nyitas (x)", "tul hosszu (200 szo)"]))
check("L17 ures lista nem 'csak ujrafogalmazhato' (a siker nem ok a 3. korre)",
      not eng.only_rephrasable([]))

print()
bad = 0
for name, ok, detail in results:
    if not ok:
        bad += 1
    print(f"  {'OK  ' if ok else 'FAIL'} {name}" + (f"   [{detail}]" if detail else ""))
print(f"\n{len(results) - bad}/{len(results)} teszt zold.")
sys.exit(1 if bad else 0)
