"""
Vendor-skip + F2 konkretsag-diagnosztika + szotar-ragozas (2026-08-10, engine v5).

MIND A HAROM EGY MERT ESETBOL JON — a 2026-08-10-i Newforma-benchmark (88/100
kulso pontszam, 10/10 belso authenticity-rubrika):

  1. A poszt VENDOR-HIRDETES volt. A felhasznaloi dontes: ilyen alatt nem
     jelenunk meg. Nem stilisztikai ok: a komment ingyen engagementet ad a
     hirdetesnek, es a szerzot azza teszi, aki egy szomszedos versenytars
     marketingje alatt ellenvetést fogalmaz.
  2. A komment KATEGORIAT nevezett meg, nem ESETET ("subtle variations in how
     they classify issues"). A REASON-prompt kert konkretsagot, de SEMMI nem
     merte, es a rubrika minden tengelyen 2/2-t adott.
  3. A kapu-szotarak csak a SZOTARI ALAKOT kerestek: "standardizing" nem
     egyezett a `standardi[sz]ation`-nel, "consistent" a `consistency`-vel.
     A komment a teljes framework-szokincset hasznalta, a kapu meg ures listat
     adott. Plusz: "unlock its full potential" egyik listan sem volt.

A) Vendor-skip: config + a harom kapu
B) Vendor-skip: idezet-ellenorzes (zero-hallucination)
C) F2: diszkriminal-e homalyos es konkret kozott
D) F2: relativizalas a poszthoz + egyes/tobbes
E) Szotar-ragozas: a MERT hianyok
F) Marketing-klise: feltetel nelkul mer
G) Vegponttol vegpontig: a skip MEGSPOROLJA a COMPOSE-hivast, a force nem
"""
import io
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


import responder.linkedin_engine as eng  # noqa: E402
from responder.linkedin_engine import (  # noqa: E402
    concreteness, check_quality, ai_fingerprint_terms, _anchor_key,
    skip_vendor_promotion_enabled, vendor_promotion_skip,
    _MARKETING_CLICHE_PATTERNS, _AI_FINGERPRINT_PATTERNS,
    _EXEC_ABSTRACTION_PATTERNS, _REASON_SCHEMA,
)

# A valodi benchmark-poszt (roviditve, de a bizonyitek-idezet benne van).
POST = (
    "BIM coordination isn't failing in the model itself. It fails in the gaps "
    "between tools. When clashes, issues, and RFIs live in separate systems, "
    "coordination items can be missed, ownership becomes unclear, and schedules "
    "slip.\n\nNewforma links your BIM ecosystem with 30+ integrations across "
    "Revit, Navisworks, Archicad and more - into a single, coordinated project "
    "record. Every issue is tracked in context.\n\nStop coordinating around the "
    "chaos."
)
EVIDENCE = "Stop coordinating around the chaos"

# A tenylegesen generalt, ChatGPT-vel 88/100-ra pontozott komment.
BENCHMARKED = (
    "One thing that stands out from experience is that while integrating tools "
    "like Newforma resolves many data silos, the real work often begins with "
    "standardizing the data schema itself. We've often found that different "
    "project teams, even within the same company, have subtle variations in how "
    "they classify issues, assign ownership, or define RFI types.\n\nBridging "
    "those semantic gaps across a federated model often requires a consensus on "
    "data protocols before a unified platform can truly unlock its full "
    "potential. The system brings the data together, but consistent "
    "interpretation across all parties is what makes it actionable."
)
# Ugyanaz az insight, de ESETET nevez meg kategoria helyett.
CONCRETE = (
    "I've run into this at handover rather than during coordination. One team "
    "logs a duct crossing as a clash, the next logs the same thing as an RFI, "
    "and the open-item count stops meaning anything to the client.\n\nWhat held "
    "up for us was agreeing the IFC property set for issue type before the "
    "first federated model went out, not after."
)


def R(**kw):
    """REASON-objektum a skip-dontes teszteléséhez."""
    base = {"vendor_promotion": True, "promotion_evidence": EVIDENCE}
    base.update(kw)
    return base


# --- A) vendor-skip: config es a harom kapu ---------------------------------
check("A1 default: bekapcsolva", skip_vendor_promotion_enabled({}) is True)
check("A2 'off' -> kikapcsolva",
      skip_vendor_promotion_enabled({"linkedin": {"skip_vendor_promotion": "off"}}) is False)
check("A3 YAML-boolean kezelve (§4/17)",
      skip_vendor_promotion_enabled({"linkedin": {"skip_vendor_promotion": False}}) is False
      and skip_vendor_promotion_enabled({"linkedin": {"skip_vendor_promotion": True}}) is True)

skip, why = vendor_promotion_skip({}, R(), POST)
check("A4 vendor_promotion + igazolt idezet -> KIHAGYAS", skip is True, why)

skip, why = vendor_promotion_skip({}, R(vendor_promotion=False), POST)
check("A5 vendor_promotion=False -> nincs kihagyas",
      skip is False and "nem vendor-hirdetes" in why, why)

skip, why = vendor_promotion_skip(
    {"linkedin": {"skip_vendor_promotion": "off"}}, R(), POST)
check("A6 kikapcsolt kapcsolo -> nincs kihagyas (a v4 viselkedes)",
      skip is False and "off" in why, why)

check("A7 a ket uj mezo KOTELEZO a REASON-semaban",
      "vendor_promotion" in _REASON_SCHEMA["required"]
      and "promotion_evidence" in _REASON_SCHEMA["required"])

# --- B) idezet-ellenorzes (zero-hallucination) ------------------------------
# A kovetkezmeny sulyos (EGYALTALAN nem generalunk), ezert a modell allitasat nem
# fogadjuk el szavara — ugyanaz az elv, mint a `tool_request_quote`-nal.
skip, why = vendor_promotion_skip({}, R(promotion_evidence="Ilyen mondat nincs a posztban"), POST)
check("B1 hallucinalt idezet -> NINCS kihagyas (inkabb generalunk, mint tevesen hallgatunk)",
      skip is False and "nem talalhato" in why, why)

skip, why = vendor_promotion_skip({}, R(promotion_evidence=""), POST)
check("B2 ures idezet -> nincs kihagyas", skip is False, why)

skip, why = vendor_promotion_skip({}, R(promotion_evidence="chaos"), POST)
check("B3 tul rovid idezet nem bizonyitek (min 3 szo)", skip is False, why)

skip, why = vendor_promotion_skip(
    {}, R(promotion_evidence="STOP  coordinating,  around the CHAOS!"), POST)
check("B4 az idezet normalizalva egyezik (kisbetu/szokoz/irasjel)", skip is True, why)

# --- C) F2: diszkriminal-e? -------------------------------------------------
m_bad, m_good = concreteness(BENCHMARKED, POST), concreteness(CONCRETE, POST)

check("C1 a homalyos komment NULLA uj konkret horgonyt hoz",
      m_bad["anchors_added"] == 0, str(m_bad["anchor_terms"]))
# A meningfull allitas az OSSZEHASONLITAS, nem egy abszolut szam: a `clash`/`rfi`
# helyesen KIESIK a hozott horgonyok kozul, mert a poszt mar hasznalja oket
# (`clashes`/`RFIs`) — ld. D1/D2. Ami marad, az a komment sajat hozzajarulasa.
check("C2 a konkret valtozat tobb uj horgonyt hoz, mint a homalyos",
      m_good["anchors_added"] >= 3
      and m_good["anchors_added"] > m_bad["anchors_added"],
      f'konkret={m_good["anchor_terms"]} vs homalyos={m_bad["anchor_terms"]}')
check("C3 absztrakt-suruseg: homalyos >> konkret",
      m_bad["abstract_count"] > m_good["abstract_count"],
      f'{m_bad["abstract_count"]} vs {m_good["abstract_count"]}')
check("C4 hedge-halmozas: a homalyos 5, a konkret 0",
      m_bad["hedges"] >= 5 and m_good["hedges"] == 0,
      f'{m_bad["hedges"]} vs {m_good["hedges"]}')
check("C5 a hedge DARABSZAM, nem tipusszam (3x 'often' -> 3)",
      any("often" in t and "3" in t for t in m_bad["hedge_terms"]),
      str(m_bad["hedge_terms"]))
check("C6 NINCS osszpontszam (egy kompozit azt sugallna, hogy a sulyozas validalt)",
      not any(k in m_bad for k in ("score", "concreteness_score", "total")),
      str(sorted(m_bad)))
check("C7 minden komponens onalloan kiolvashato (rangkorrelaciohoz)",
      all(k in m_bad for k in ("anchors_added", "abstract_count", "hedges", "words")))

# --- D) relativizalas + egyes/tobbes ---------------------------------------
check("D1 amit a szerzo MAR kimondott, az nem a komment erdeme",
      "rfi" in m_bad["anchors_shared_with_post"]
      and "rfi" not in m_bad["anchor_terms"],
      f'shared={m_bad["anchors_shared_with_post"]} added={m_bad["anchor_terms"]}')
check("D2 egyes/tobbes osszevonas (_anchor_key)",
      _anchor_key("rfis") == _anchor_key("rfi")
      and _anchor_key("clashes") == _anchor_key("clash")
      and _anchor_key("families") == _anchor_key("family"))
check("D3 a poszt nyelvi keszlete nem szamit horgonynak (ifc a posztban nincs)",
      "ifc" in m_good["anchor_terms"], str(m_good["anchor_terms"]))
# 2026-08-10, ELES futasbol: a komment "property sets"-et irt, a lista "property
# set"-et keresett -> a horgony elveszett, a mero 0-t jelentett. Egy ALULSZAMOLO
# diagnosztika a kesobbi korrelaciot rontja el, ezert ez sajat teszt.
check("D4 az utolso szo TOBBES szama is horgony ('property sets')",
      "property set" in concreteness(
          "We agreed the property sets before the first federated model.", "")["anchor_terms"])
check("D5 tobbes szamu szoveg is horgony ('clashes', 'families')",
      concreteness("two clashes appeared", "")["anchors_added"] == 1
      and concreteness("the families were rebuilt", "")["anchors_added"] == 1,
      f'{concreteness("two clashes appeared", "")["anchor_terms"]} / '
      f'{concreteness("the families were rebuilt", "")["anchor_terms"]}')
check("D6 EGY fogalom = EGY horgony (a 'clashes' nem szamol clash+clashes-kent)",
      concreteness("clash, clashes, RFI and RFIs everywhere", "")["anchors_added"] == 2,
      str(concreteness("clash, clashes, RFI and RFIs everywhere", "")["anchor_terms"]))

# --- E) szotar-ragozas: a MERT hianyok --------------------------------------
fp = ai_fingerprint_terms(BENCHMARKED, POST)
check("E1 'standardizing' MOST egyezik (korabban nem)", "standardisation" in fp, str(fp))
check("E2 'consistent' MOST egyezik (korabban nem)", "consistency" in fp, str(fp))
check("E3 a benchmarkolt komment legalabb KETTO fingerprint-elemet ad",
      len(fp) >= 2, str(fp))

import re as _re  # noqa: E402


def hits(patterns, text):
    return [lbl for pat, lbl in patterns if _re.search(pat, text, _re.I)]


check("E4 tobbes szam: 'frameworks'",
      "framework" in hits(_AI_FINGERPRINT_PATTERNS, "we built two frameworks"))
check("E5 kepzett alak: 'governing'",
      "governance" in hits(_AI_FINGERPRINT_PATTERNS, "the governing body"))
check("E6 exec-szotar tobbes: 'competitive advantages'",
      "versenyelony-keretezes" in hits(_EXEC_ABSTRACTION_PATTERNS,
                                       "clear competitive advantages here"))
check("E7 exec-szotar tobbes: 'business cases'",
      "business case" in hits(_EXEC_ABSTRACTION_PATTERNS, "we wrote two business cases"))
check("E8 a szotari alak TOVABBRA is egyezik (nincs regresszio)",
      "consistency" in hits(_AI_FINGERPRINT_PATTERNS, "data consistency matters")
      and "standardisation" in hits(_AI_FINGERPRINT_PATTERNS, "IFC standardisation"))
check("E9 NEM egyezik reszszora ('inconsistent' nem 'consistency')",
      "consistency" not in hits(_AI_FINGERPRINT_PATTERNS, "the data was inconsistent"))

# --- F) marketing-klise: feltetel nelkul mer --------------------------------
# A mert eset `management` sikon volt, ahol a szinthez kotott kapuk nem lepnek be —
# ezert ez a lista minden sikon es minden intenten mer.
iss_mgmt = check_quality(BENCHMARKED, POST, False, intent="product_demonstration",
                         discourse_level="management", human_temperature="practical")
check("F1 a MERT eseten a kapu MOST elkapja a marketing-kliset",
      any("marketing-klise" in i for i in iss_mgmt), str(iss_mgmt))
check("F2 'full potential' a talalat",
      any("full potential" in i for i in iss_mgmt), str(iss_mgmt))
# 2026-08-10, a Q1-dontes hozadeka: ugyanez a komment MOST a fingerprint-kapun is
# elhasal `management` sikon (standardizing + consistent), amit korabban a
# szint-feltetel atengedett.
check("F2.1 ugyanez a komment a fingerprint-kapun is elhasal (Q1-dontes)",
      any("AI-ujjlenyomat" in i for i in iss_mgmt), str(iss_mgmt))

for level in ("technical", "management", "business"):
    iss = check_quality("Ez game-changer lesz mindenkinek, komolyan mondom nektek most itt. " * 4,
                        POST, False, intent="professional_opinion",
                        discourse_level=level, human_temperature="practical")
    check(f"F3 '{level}' sikon is mer (nincs szint-feltetel)",
          any("marketing-klise" in i for i in iss), str(iss))

check("F4 a konkret valtozat NEM esik a marketing-kapuba",
      not any("marketing-klise" in i for i in
              check_quality(CONCRETE, POST, False, intent="product_demonstration",
                            discourse_level="management", human_temperature="practical")))
check("F5 legitim BIM-zsargon nincs a listan (architecture / pipeline / single source)",
      not hits(_MARKETING_CLICHE_PATTERNS,
               "the information architecture and the IFC pipeline are the single source of truth"))

# --- F') tanacsadoi hang: EGESZ kommentre mer (2026-08-11, engine v10) -------
# A MERES: a "We (often) see/found" szerkezet a 32 kiadott kommentbol TIZBEN volt
# benne, es a v9 ket kommentjeben mar a 3. MONDATBAN — vagyis kihatralt a
# ket-mondatos nyitas-ablakbol, ahol semmi nem fogta. SZO SZERINTI reszletek:
LEAK_3RD = ("I've run into similar challenges with adoption, and the inertia is real. "
            "It's often not about the perceived value of the new tool itself. "
            "We often see that the real bottleneck for users isn't just learning a new "
            "interface, but the broader ecosystem change it implies, and that is where "
            "the migration cost of existing project data starts to dominate everything.")
iss_leak = check_quality(LEAK_3RD, POST, False, intent="reflection",
                         discourse_level="technical", human_temperature="reflective")
check("F6 a 3. MONDATBAN levo 'We often see' MOST sertes (a nyitas-ablak nem latta)",
      any("tanacsadoi hang" in i for i in iss_leak), str(iss_leak))
check("F6.1 a cimke NEM 'ismetlodo nyitas' (nem nyitasi hiba, nem is annak hivjuk)",
      not any("ismetlodo nyitas" in i for i in iss_leak), str(iss_leak))

PERFECT_TENSE = ("The handover is where this usually bites. We've often found that the "
                 "shared parameter file drifts once someone rebuilds it, and the schedule "
                 "mapping detaches without a single warning in the model itself. "
                 "Versioning that file as project data is what held up for us over time.")
check("F7 a 'We've often found' valtozat is sertes (ez volt a leggyakoribb alak)",
      any("tanacsadoi hang" in i for i in
          check_quality(PERFECT_TENSE, POST, False, intent="engineering_problem",
                        discourse_level="technical", human_temperature="practical")))

for level in ("technical", "management", "business"):
    check(f"F8 '{level}' sikon is mer (nincs szint-feltetel, mint a klisenel)",
          any("tanacsadoi hang" in i for i in
              check_quality(LEAK_3RD, POST, False, intent="professional_opinion",
                            discourse_level=level, human_temperature="practical")))

# A KATALOGUS SAJAT FORMAI nem eshetnek a listaba: az `own_practice` ("I've found")
# es a `learned` ("We've learned") nyitas legitim — a tic az ALTALANOSITO hatarozo
# ("often"), nem a tapasztalat-ige. Kulonben minden ilyen komment ujrairast kapna.
check("F9 'I've found that...' (own_practice) NEM sertes",
      not any("tanacsadoi hang" in i for i in
              check_quality("I've found that the GUID travels with the definition file, "
                            "not with the model, so the mapping detaches on rebuild. "
                            "Versioning that file as project data is what fixed it here.",
                            POST, False, intent="engineering_problem",
                            discourse_level="technical", human_temperature="practical")))
check("F10 'We've learned...' (learned forma) NEM sertes",
      not any("tanacsadoi hang" in i for i in
              check_quality("We've learned to version the shared parameter file as project "
                            "data rather than a local resource, because the drift only "
                            "shows up weeks later when a schedule stops matching.",
                            POST, False, intent="engineering_problem",
                            discourse_level="technical", human_temperature="practical")))
check("F11 a 'gyakorlatban' onmagaban NEM sertes (csak a tapasztalat-igevel)",
      not any("tanacsadoi hang" in i for i in
              check_quality("A gyakorlatban ez tipikusan 10 mm alatti elmozdulas, "
                            "es eppen az a resz szokott lemaradni a jegyzokonyvbol.",
                            POST, False, intent="engineering_problem",
                            discourse_level="technical", human_temperature="practical")))
check("F12 a MERT magyar alak sertes",
      any("tanacsadoi hang" in i for i in
          check_quality("Ahogy felveted, ez kulcskerdes. A gyakorlatban azt tapasztaljuk, "
                        "hogy a tenyek gyakran inkonzisztensek a vallalati rendszerekben.",
                        POST, False, intent="engineering_problem",
                        discourse_level="technical", human_temperature="practical")))
# A "the real X" SZANDEKOSAN kimaradt: a v7-es A/B-ben eppen egy ilyen mondat volt a
# sorozat elso kiposztolhato kommentjenek magja. Ez tartalmi szerkezet, nem tic.
check("F13 'the real hit is downstream' NEM sertes (szandekos kihagyas, v7 A/B)",
      not any("tanacsadoi hang" in i for i in
              check_quality("When a custom stair form pushes us to generic models, the real "
                            "hit is often downstream: the 'I' in BIM vanishes on IFC export, "
                            "losing its data for facility management or quantity take-off.",
                            POST, False, intent="engineering_problem",
                            discourse_level="technical", human_temperature="frustrated")))

# --- H) user-dontes 1: framework-reflex a MANAGEMENT sikon is ---------------
# A 2026-08-10-i eles, kenyszeritett generalas SZO SZERINTI reszlete. Ket uj
# framework-kifejezest hozott (governance + consistently), a szint `management` volt,
# es a kapu NEM lepett be. Ez a dontes ezt forditja meg.
LIVE_MGMT = (
    "Newforma's approach to centralising coordination items across tools is "
    "valuable, as disconnected systems are a real friction point. We have found "
    "that even with excellent integrations, maintaining data quality across 30+ "
    "different tools consistently requires significant upstream effort. The "
    "critical step becomes establishing strict naming conventions and property "
    "sets at the authoring source, long before the data ever hits a federated "
    "model. Without that foundational governance, the integrated project record "
    "still carries inconsistencies from the source, making data hard to trust."
)
fp_live = ai_fingerprint_terms(LIVE_MGMT, POST)
check("H1 az eles komment KETTO framework-kifejezest hoz (a ragozas-javitas nelkul nulla volt)",
      len(fp_live) >= 2, str(fp_live))
check("H2 MANAGEMENT sikon MOST sertes (ez volt a dontes)",
      any("AI-ujjlenyomat" in i for i in
          check_quality(LIVE_MGMT, POST, False, intent="product_demonstration",
                        discourse_level="management", human_temperature="practical")),
      str(check_quality(LIVE_MGMT, POST, False, intent="product_demonstration",
                        discourse_level="management", human_temperature="practical")))
check("H3 TECHNICAL sikon tovabbra is sertes (nincs regresszio)",
      any("AI-ujjlenyomat" in i for i in
          check_quality(LIVE_MGMT, POST, False, intent="engineering_problem",
                        discourse_level="technical", human_temperature="practical")))
check("H4 BUSINESS sikon SZANDEKOSAN nem sertes",
      not any("AI-ujjlenyomat" in i for i in
              check_quality(LIVE_MGMT, POST, False, intent="professional_opinion",
                            discourse_level="business", human_temperature="practical")),
      "ha a szerzo mar uzleti sikon beszel, ott folytatni nem drift")
check("H5 a relativizalas MANAGEMENT sikon is vedi a szerzot",
      ai_fingerprint_terms(
          "Their governance model and consistency rules are the right frame.",
          "Our governance model needs consistency rules across teams.") == [],
      "amit a szerzo maga kimondott, az nem szamolodik")
check("H6 EGY kifejezes management sikon sem hamis pozitiv",
      not any("AI-ujjlenyomat" in i for i in
              check_quality(CONCRETE + " The governance question stays open.", POST,
                            False, intent="product_demonstration",
                            discourse_level="management", human_temperature="practical")))

# --- I) user-dontes 2: a nyitas-kapu az ELSO KET MONDATRA mer --------------
from responder.linkedin_engine import _opening_window, _OPENING_SENTENCES  # noqa: E402

# Az elso eles generalas SZO SZERINTI kezdete: a sablonos fordulat a MASODIK
# mondat elejen volt, ugyanabban a sorban -> a sorelejehez kotott kapu nem latta.
SECOND_SENTENCE = (
    "The challenge of disconnected tools is a real one in BIM coordination. "
    "We often see that even with integrated platforms, the initial lift to "
    "migrate active project data can be substantial and needs planning ahead "
    "of the first coordination cycle on any larger project delivery."
)
check("I1 a masodik mondat elejen levo sablonos nyitas MOST sertes",
      any("ismetlodo nyitas" in i for i in
          check_quality(SECOND_SENTENCE, POST, False, intent="product_demonstration",
                        discourse_level="management", human_temperature="practical")),
      str(check_quality(SECOND_SENTENCE, POST, False, intent="product_demonstration",
                        discourse_level="management", human_temperature="practical")))
check("I2 az ELSO mondat elejen tovabbra is sertes (nincs regresszio)",
      any("ismetlodo nyitas" in i for i in
          check_quality("We often see this after handover. " + CONCRETE, POST, False,
                        intent="engineering_problem", discourse_level="technical",
                        human_temperature="practical")))
check("I3 MONDAT KOZEPEN nem sertes (a dokumentalt szandek megorizve)",
      not any("ismetlodo nyitas" in i for i in
              check_quality("I've found that what became best practice for us was "
                            "versioning the definition file itself. " + CONCRETE,
                            POST, False, intent="engineering_problem",
                            discourse_level="technical", human_temperature="practical")),
      "'best practice' mondat kozepen legitim")
check("I4 a HARMADIK mondat elejen NEM nyitasi hiba (ez a hatokor-korlat)",
      not any("ismetlodo nyitas" in i for i in
              check_quality("First a real observation about the mapping. Then a second "
                            "one about the schedule. One approach is to version the "
                            "definition file itself and treat it as project data, "
                            "because the drift only shows up weeks later at handover.",
                            POST, False, intent="engineering_problem",
                            discourse_level="technical", human_temperature="practical")),
      "a 3. mondat mar nem nyitas — arra az _AI_FINGERPRINT_PATTERNS a mechanizmus")
check("I5 az ablak pontosan ket mondat", _OPENING_SENTENCES == 2
      and _opening_window("Egy. Ketto. Harom. Negy.") == ["Egy.", "Ketto."])
check("I6 a sortores is mondathatar (bekezdes)",
      _opening_window("Elso sor\nMasodik sor\nHarmadik") == ["Elso sor", "Masodik sor"])
check("I7 ures/hianyzo szoveg nem dob", _opening_window("") == [] and _opening_window(None) == [])

# --- J) a NEGYEDIK eles futas resei ----------------------------------------
# Ket regiszter-szo es a hianyos horgony-lexikon. A "robust" onkritikus tetel: az
# elso ertekelesemben a kulso spec lexikai tiltolistajat "2019-es AI-jelekkent"
# intéztem el — a szo ezutan eles kimenetben jelent meg, es egyik kapu sem fogta.
LIVE4 = (
    "What strikes me is how much the actual control depends on the human element, "
    "even with robust BIM tools. The practical benefits are gated by how mature the "
    "information management protocols truly are, and the team must fully leverage "
    "the insights before anything hits the site on a larger delivery."
)
fp4 = ai_fingerprint_terms(LIVE4, POST)
check("J1 'robust' ES 'leverage' MOST fingerprint-elem",
      "robust" in fp4 and "leverage" in fp4, str(fp4))
check("J2 igy a negyedik eles komment eleri a ketto-kuszobot -> SERTES",
      any("AI-ujjlenyomat" in i for i in
          check_quality(LIVE4, POST, False, intent="professional_opinion",
                        discourse_level="management", human_temperature="practical")),
      str(check_quality(LIVE4, POST, False, intent="professional_opinion",
                        discourse_level="management", human_temperature="practical")))
check("J3 a cimke prefixe valtozatlan (a regi tesztek erre illesztenek)",
      any(i.startswith("AI-ujjlenyomat") for i in
          check_quality(LIVE4, POST, False, intent="professional_opinion",
                        discourse_level="management", human_temperature="practical")))
check("J4 EGYETLEN 'robust' nem hamis pozitiv (kell a masodik elem)",
      not any("AI-ujjlenyomat" in i for i in
              check_quality(CONCRETE + " The mapping stayed robust after the rebuild.",
                            POST, False, intent="engineering_problem",
                            discourse_level="technical", human_temperature="practical")))
check("J5 ha a SZERZO hasznalta, nem szamolodik (relativizalas)",
      ai_fingerprint_terms(
          "We had to leverage a robust approach here.",
          "Our team had to leverage a robust workaround for this.") == [],
      "ezert kerult a fingerprint-listara, nem a marketing-listara")

check("J6 'full potential' MOST unlock NELKUL is sertes",
      any("marketing-klise" in i for i in
          check_quality(CONCRETE + " The full potential stays untapped otherwise.",
                        POST, False, intent="engineering_problem",
                        discourse_level="technical", human_temperature="practical")))
check("J7 az 'unlock its full potential' tovabbra is sertes (nincs regresszio)",
      any("marketing-klise" in i for i in
          check_quality(CONCRETE + " This unlocks its full potential at last.",
                        POST, False, intent="engineering_problem",
                        discourse_level="technical", human_temperature="practical")))

NEW_ANCHORS = ("We agreed the BIM execution plan before the 4D sequence, and the "
               "scan-to-BIM point cloud from the LiDAR drone fed the quantity "
               "takeoff and the QA/QC checks. SPI and CPI came from Power BI.")
m_new = concreteness(NEW_ANCHORS, "")
check("J8 az uj horgonyok mind szamolnak", m_new["anchors_added"] >= 10,
      f'{m_new["anchors_added"]}: {m_new["anchor_terms"]}')
check("J9 'naming convention' SZANDEKOSAN nem horgony",
      concreteness("We established strict naming conventions across teams.",
                   "")["anchors_added"] == 0,
      "az egyik mert komment eppen consultant-nyelvkent hasznalta")
check("J10 'quantity takeoff' EGY horgony, nem ketto",
      concreteness("the quantity takeoff was wrong", "")["anchors_added"] == 1,
      str(concreteness("the quantity takeoff was wrong", "")["anchor_terms"]))
check("J11 'BIM execution plan' EGY horgony",
      concreteness("the BIM execution plan was late", "")["anchors_added"] == 1,
      str(concreteness("the BIM execution plan was late", "")["anchor_terms"]))

# --- K) a POSZTHOZ skalazott cel-hossz (v7) --------------------------------
# A MERT HIBA: nyolc eles generalas, a komment 82-117 szo MINDEN esetben, barmi is
# volt a bemenet. Az 53 szavas poszt 102-116 szavas valaszt kapott — a poszt
# ketszereset. A hossz IS regiszter.
from responder.linkedin_engine import (  # noqa: E402
    target_length, length_scaling_enabled, MIN_WORDS, MAX_WORDS,
    LENGTH_TARGET_FLOOR, LENGTH_TARGET_CEILING,
    _compose_user_msg, _COMPOSE_PROMPT,
)

# A `_compose_user_msg` a mar KIVALASZTOTT strategiat varja (azt a `pick_strategy`
# teszi be a reasoning-be), ezert itt egy kesz reasoning-objektum kell. Onallo, hogy
# ne fuggjon a fajl kesobbi E2E-fixtureitol.
REASONING = {
    "strategy": "field_experience",
    "conversation_intent": "engineering_problem", "discourse_level": "technical",
    "expected_responder_role": "peer_practitioner",
    "response_mode": "extend_one_insight", "human_temperature": "practical",
    "topic_gravity": "shared parameter mapping",
    "core_thesis": "Coordination fails between tools.",
    "missing_perspective": "interoperability",
    "missing_perspective_reason": "Semantics are not discussed.",
    "insight": "Issue-type semantics differ per team.",
}


def band(n):
    return target_length("szo " * n)


check("K1 a MIN_WORDS 60 -> 35 (a legkisebb sav ALA)", MIN_WORDS == 35)
check("K2 rovid poszt -> rovid sav (a Revit-eset: 53 szo)", band(53) == (40, 70), str(band(53)))
# CSILLAPITAS (masodik iteracio): a padlo feletti resz feleresben szamit, mert a meres
# szerint minel tobb a hely, annyival tobb a toltelék (108 szavas poszt -> 95 szavas
# komment, abstract 5, es a zaro mondat mar homalyos volt).
check("K3 kozepes poszt: a CSILLAPITAS szukiti a savot (108 szo)",
      band(108) == (60, 100), str(band(108)))
check("K3.1 a csillapitas tenyleg szukit (nem a regi 80-135)",
      band(108)[1] < 135)
check("K4 hosszu poszt -> felso hataron all meg", band(254) == (90, 150), str(band(254)))
check("K4.1 a plafont csak ~185 szo fole eri el a cel (tehat a csillapitas hat)",
      band(180)[1] < 150 and band(200) == band(254), f'{band(180)} / {band(200)}')
check("K5 nagyon hosszu poszt sem visz 150 fole", band(1000)[1] == 150, str(band(1000)))
check("K6 ures/rovid poszt sem megy a padlo ala", band(0) == band(10) == (40, 70), str(band(0)))

# AZ INVARIANS: a sav sosem harcol a kapuval. Ha a sav minimuma a MIN_WORDS ala esne,
# vagy a maximuma a MAX_WORDS fole, MINDEN komment ujrairast kapna.
bad = [(n, band(n)) for n in range(0, 600, 7)
       if not (MIN_WORDS <= band(n)[0] and band(n)[1] <= MAX_WORDS)]
check("K7 INVARIANS: a sav minden poszt-hosszra a kapun BELUL van", not bad, str(bad[:3]))
check("K8 a sav monoton no a poszt hosszaval",
      all(band(n)[0] <= band(n + 10)[0] for n in range(0, 300, 10)))
from responder.linkedin_engine import LENGTH_DAMPING  # noqa: E402

# A plafon a CSILLAPITAS miatt nem a `LENGTH_TARGET_CEILING` szavas posztnal all be,
# hanem ott, ahol a csillapitott cel eleri a plafont. A hatart a konstansokbol
# szamoljuk, hogy a teszt ne avuljon el egy jovobeli csillapitas-valtozasnal (ez az
# elozo valtozat hibaja volt: a csillapitas ELOTTI osszefuggest kodolta be).
_CEIL_AT = LENGTH_TARGET_FLOOR + (LENGTH_TARGET_CEILING - LENGTH_TARGET_FLOOR) / LENGTH_DAMPING
check("K9 a padlo es a plafon is tenyleg hat",
      band(LENGTH_TARGET_FLOOR - 20) == band(LENGTH_TARGET_FLOOR)
      and band(int(_CEIL_AT) + 10) == band(600),
      f'padlo={band(LENGTH_TARGET_FLOOR)} plafon@{int(_CEIL_AT)}={band(int(_CEIL_AT) + 10)}')

check("K10 kapcsolo: default on, 'off' es YAML-boolean kezelve",
      length_scaling_enabled({}) is True
      and length_scaling_enabled({"linkedin": {"length_scaling": "off"}}) is False
      and length_scaling_enabled({"linkedin": {"length_scaling": False}}) is False)

# A promptba tenylegesen bekerul-e — es a kikapcsolt allapot BAJTRA a v6-os?
V6_LENGTH = "80-150 words, max two paragraphs, ~20% acknowledgement / 80% new thinking."
msg_scaled = _compose_user_msg(POST, "", REASONING, False, length_band=(40, 70))
msg_fixed = _compose_user_msg(POST, "", REASONING, False, length_band=None)
check("K11 a kijelolt sav bekerul a feladat-uzenetbe", "40-70 words" in msg_scaled)
check("K12 kimondja, hogy FELULIRJA az instrukciot",
      "REPLACES the one in" in msg_scaled)
check("K13 kimondja, hogy ne tomjon (ez a mert hiba)",
      "do not pad" in msg_scaled.lower())
check("K14 kikapcsolva a v6-os mondat all elo, SZO SZERINT", V6_LENGTH in msg_fixed)
check("K15 kikapcsolva NINCS skalazasra utalo szoveg",
      "REPLACES the one in" not in msg_fixed and "do not pad" not in msg_fixed.lower())
check("K16 a system-prompt kimondja, hogy a feladat-uzenet sava nyer",
      "the task message gives a different range" in _COMPOSE_PROMPT)

# A kapu tovabbra is mer — a sav utasitas, nem kapu.
check("K17 a 35 szo alatti komment TOVABBRA is sertes",
      any("tul rovid" in i for i in
          check_quality("Egy rovid megjegyzes csak, semmi tobb.", POST, False,
                        intent="engineering_problem", discourse_level="technical",
                        human_temperature="practical")))
check("K18 egy 45 szavas komment MOST atmegy (a 60-as padlo blokkolta volna)",
      not any("tul rovid" in i for i in
              check_quality(" ".join(["word"] * 45), POST, False,
                            intent="engineering_problem", discourse_level="technical",
                            human_temperature="practical")),
      "ez volt a mert kar: a jo rovid valasz tomesre kenyszerult")

# --- L) a strategy_fit skala horgonyzasa -----------------------------------
# A MERT HIBA (10 poszt telemetriabol): a modell NYERS pontszamai gyakorlatilag
# ALLANDOAK. Egy strategian beluli szoras 1-2 pont, a strategiak kozti res 2-4:
#     missing_perspective 8-9 (atlag 8.8) | practical_lesson 7-9 | field_experience 7-8
#     systems_thinking 5-7 | business_impact 5-7 | constructive_challenge 4-7
#     future_outlook 3-7
# Nyers maximum 10-bol 8 esetben a DOKUMENTALT FALLBACK (`missing_perspective`).
# Vagyis a modell nem a POSZTOT pontozza, hanem a strategia-leirasokat: fix
# velemenye van arrol, melyik strategia altalaban ertekes.
#
# A BIAS NEM HIBAS — o az egyetlen, ami ezt megforditja (a -1.5-es fallback-levonas).
# Ezert a javitas a SKALAN van, nem a bias-szamokon: ugyanaz a hibatipus es ugyanaz a
# gyogyszer, mint a classifier severity-jenel (`docs/04-rendszer-audit`: "a
# severity-prompt mind az ot fokozatat horgonyoztuk", CLASSIFIER_VERSION -> v4).
from responder.linkedin_engine import _REASON_PROMPT, STRATEGIES, _STRATEGY_BIAS  # noqa: E402

check("L1 a skala mind a negy fokozata horgonyozva van",
      all(a in _REASON_PROMPT for a in ("0-2", "3-5", "6-8", "9-10")))
check("L2 a horgonyok KIMONDJAK, mit jelentenek (nem csak szamok)",
      "would MISS what the post is about" in _REASON_PROMPT
      and "single best available move" in _REASON_PROMPT)
# L3-L5 MEGFORDITVA (2026-08-11, v18). Eddig azt allitottak, hogy a v8-as kalibracios
# ellenorzes BENNE van a promptban. 50 telemetria-sor megmerte, hogy a modell soha nem
# tartotta be ("negy vagy tobb 7 fole" sertes: v8 86%, v9 73%, v13-v15 100%; a szoras
# soha nem erte el az 5-ot), es a v16 ota a dontes nem is tamaszkodik a rangsorra — a
# nyers pont SZURO, a valasztast a kod hozza. Ezert a szabalyokat kivezettuk, es ez a
# harom check mostantol a VISSZASZIVARGAST orzi: ugyanaz a banasmod, mint az
# authenticity-rubrikanal (torles + teszt, ami nem engedi vissza).
check("L3 a v8-as kalibracios ellenorzes NINCS a promptban (mert: soha nem tartotta be)",
      "CALIBRATION CHECK" not in _REASON_PROMPT
      and "four or more strategies a 7 or higher" not in _REASON_PROMPT)
check("L4 az absztrakt-vs-EZ-a-poszt mondat sincs vissza",
      "rating the strategies IN THE ABSTRACT" not in _REASON_PROMPT)
check("L5 minimum-szoras nincs eloirva (a v16 nem tamaszkodik a rangsorra)",
      "at least 5" not in _REASON_PROMPT)
check("L5.1 ami MARADT: a duplaszamolas tilalma (a padlo a SULYOZOTT pontra megy)",
      "Score on professional value ALONE" in _REASON_PROMPT
      and "weighted separately" in _REASON_PROMPT)
check("L6 a fallback-levonas VALTOZATLAN (a diagnozis szerint o mukodik)",
      _STRATEGY_BIAS == {"missing_perspective": -1.5}, str(_STRATEGY_BIAS))
check("L7 a strategia-keszlet valtozatlan (nem szuritettunk)", len(STRATEGIES) == 7)

# --- G) vegponttol vegpontig ------------------------------------------------
TMP = tempfile.mkdtemp(prefix="nodu-conc-")
REASON_OUT = {
    "topic": "bim", "post_type": "product",
    "conversation_intent": "product_demonstration", "discourse_level": "management",
    "expected_responder_role": "product_reviewer",
    "response_mode": "concrete_suggestion", "human_temperature": "practical",
    "topic_gravity": "BIM coordination software integration",
    "author_objective": "sell", "audience": "BIM managers",
    "technical_depth": "surface", "emotional_tone": "promotional",
    "core_thesis": "Coordination fails between tools.",
    "missing_perspective": "interoperability",
    "missing_perspective_reason": "Semantics are not discussed.",
    "strategy_fit": {"constructive_challenge": 6, "systems_thinking": 6,
                     "field_experience": 9, "business_impact": 5,
                     "future_outlook": 3, "practical_lesson": 9,
                     "missing_perspective": 7},
    "strategy_reason": "add field nuance",
    "explicit_tool_request": False, "tool_request_quote": "",
    "vendor_promotion": True, "promotion_evidence": EVIDENCE,
    "insight": "Issue-type semantics differ per team.",
    "confidence": 0.8,
}
calls = []


class _FakeResp:
    def __init__(self, text):
        self.text = text


class _FakeModels:
    def generate_content(self, model=None, contents=None, config=None):
        props = (config.response_schema or {}).get("properties", {})
        stage = "reason" if "strategy_fit" in props else "compose"
        calls.append(stage)
        if stage == "reason":
            return _FakeResp(json.dumps(REASON_OUT))
        return _FakeResp(json.dumps({
            "comment": CONCRETE, "voice_professional": 2, "conversation_fit": 2,
            "one_step_insight": 2, "no_implementation_drift": 2, "natural_language": 2,
        }))


class _FakeClient:
    models = _FakeModels()


CFG = {"linkedin": {"telemetry": "on",
                    "telemetry_path": os.path.join(TMP, "t.jsonl")}}

_real = eng._client
eng._client = lambda config: (_FakeClient(), "gemini-2.5-flash", None)
try:
    eng.reset_opening_state()
    res_skip = eng.generate_comment(CFG, POST)
    calls_skip = list(calls); calls.clear()

    # Nullazas MINDEN forgatokonyv elott: a harom hivas ugyanazt a (fake) kommentet
    # adja vissza, tehat a nyitas-visszhang gyűrűje kulonben a masodiktol kezdve
    # ujrairast valtana ki, es a hivas-szamra allito checkek elbuknanak. Ez
    # teszt-izolacio, nem a kapu engedelye — v9, ld. test_linkedin_opening I).
    eng.reset_opening_state()
    res_force = eng.generate_comment(CFG, POST, force=True)
    calls_force = list(calls); calls.clear()

    eng.reset_opening_state()
    res_off = eng.generate_comment(
        {**CFG, "linkedin": {**CFG["linkedin"], "skip_vendor_promotion": "off"}}, POST)
    calls_off = list(calls)
finally:
    eng._client = _real
    eng.reset_opening_state()

check("G1 vendor-hirdetes -> skipped=True", res_skip.get("skipped") is True, str(res_skip.get("skip_reason")))
check("G2 a skip MEGSPOROLJA a COMPOSE-hivast (csak reason futott)",
      calls_skip == ["reason"], str(calls_skip))
check("G3 a skip nem hiba: nincs 'error' kulcs", "error" not in res_skip)
check("G4 a skip visszaadja az IGAZOLT bizonyitekot (a UI ezt mutatja)",
      res_skip.get("promotion_evidence") == EVIDENCE)
check("G5 a skip-sor is a dashboard-szerzodest tartja (8 legacy mezo)",
      all(k in res_skip for k in ("topic", "post_type", "engagement_intent",
                                  "reply_style", "brand_mode", "confidence",
                                  "reply_text", "rationale")))
check("G6 force=True -> generál, KET hivas", calls_force == ["reason", "compose"], str(calls_force))
check("G7 force eseten skipped=False es forced=True",
      res_force.get("skipped") is False and res_force.get("forced") is True)
check("G8 skip_vendor_promotion=off -> generál (v4 viselkedes)",
      res_off.get("skipped") is False and calls_off == ["reason", "compose"], str(calls_off))
check("G9 a valasz tartalmazza az F2 diagnosztikat",
      isinstance(res_force.get("concreteness"), dict)
      and "anchors_added" in res_force["concreteness"])
check("G10 quality_issues_first jelen van (a naplo megmagyarazza az ujrairast)",
      "quality_issues_first" in res_force)

rows = [json.loads(l) for l in io.open(os.path.join(TMP, "t.jsonl"), encoding="utf-8") if l.strip()]
check("G11 a KIHAGYOTT hivas is naplozva van (szamolhato a skip-arany)",
      len(rows) == 3 and rows[0].get("skipped") is True, str([r.get("skipped") for r in rows]))
check("G12 a naplo tartalmazza a konkretsag-merest",
      isinstance(rows[1].get("concreteness"), dict), str(list(rows[1])[:8]))
check("G13 a skip-sor is parosithato a benchmarkhoz (van post_id)",
      bool(rows[0].get("post_id")) and rows[0]["post_id"] == rows[1]["post_id"])

shutil.rmtree(TMP, ignore_errors=True)

print()
bad = 0
for name, ok, detail in results:
    if not ok:
        bad += 1
    print(f"  {'OK  ' if ok else 'FAIL'} {name}" + (f"   [{detail}]" if detail else ""))
print(f"\n{len(results) - bad}/{len(results)} teszt zold.")
sys.exit(1 if bad else 0)
