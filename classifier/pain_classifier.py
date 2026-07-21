"""
Pain Classifier — a NODU Monitor "agya".

A kulcsszo-szures csak elo-szuro: megmondja, hogy egy bejegyzes EMLIT-e
Archicad/Revit/IFC-szeru kifejezeseket, de nem tudja megkulonboztetni a
valodi fajdalmat ("harom hete kuzdok az IFC-exporttal, hatarido pentek")
egy semleges emlitestol ("hasznalj Revitet vagy Archicadot, mindketto jo").

Ez a modul EZT a kulonbseget teszi meg: minden meg nem osztalyozott poszthoz
EGYETLEN strukturalt LLM-hivast kuld (koltseg/latencia miatt nem bontjuk
tobb kulon "agent-hivasra" — ld. docs/01-architektura-audit-2026-07.md §6/§7),
es a valaszt a `signals` tablaba menti.

Ez a fazis (audit Roadmap, 1. fazis) egy KAPUDONTES: a celt nem az automatizalas,
hanem annak bizonyitasa szolgalja, hogy a kimenet valoban jobb jelet ad, mint a
nyers kulcsszo-score. Ezert ez NINCS bekotve az utemezobe (register_jobs) —
csak kezi CLI-hivassal fut (`python main.py --classify` / `--review-signals`),
amig a jelminoseget nehany het valos adatan at nem igazoljuk.
"""
import json
import time
from datetime import datetime, timezone

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from storage.db import get_unclassified_posts, get_signals_for_review, insert_signal, log_run

# A modell + prompt verziojat kodolja — ha a promptot vagy a modellt valtjuk,
# ezt is bumpeljuk, hogy a regi/uj jelek megkulonboztethetok legyenek
# visszamenoleges ujraszamolasnal (audit §9, scoring_configs elozmenye).
CLASSIFIER_VERSION = "gemini-2.5-flash-v3"

_ISSUE_TYPES = ["parametric_data", "metadata", "geometry", "coordination", "other"]

_SYSTEM_PROMPT = f"""
Te a NODU Bridge (Archicad <-> Revit parametrikus adatcsere eszkoz) fajdalom-
detektalo motorja vagy. A NODU Bridge egyetlen ertekajanlata: az elemek
LOGIKAJAT (nem statikus geometriajat) konvertalja Archicad es Revit kozott,
nativ mapping scriptekkel, nyitott IFC helyett.

Feladatod: eldonteni, hogy egy fórum/Reddit/GitHub/StackOverflow bejegyzes
VALODI FAJDALMAT fejez-e ki Archicad-Revit (vagy tagabban BIM-szoftverek
kozotti) adatcsere/interoperabilitas temaban — NEM az szamit, hogy a szoveg
tartalmazza-e a "revit"/"archicad"/"ifc" szavakat, hanem hogy a SZERZO
TENYLEGESEN KUZD-E egy problemaval, vagy csak semlegesen emliti a szavakat
(pl. dokumentacio, altalanos osszehasonlitas, egy masik temaju kerdes reszekent).

PELDA — NEM fajdalom (is_pain: false), csak kulcsszo-egyezes:
  "Ha BIM-koordinator vagy, erdemes ismerned mind az Archicadot, mind a Revitet."
  "Milyen IFC verziot tamogat a legujabb Revit?"  (tiszta info-kerdes, nincs kuzdelem)

PELDA — VALODI fajdalom (is_pain: true):
  "Harom hete probalom exportalni IFC-be az Archicad modellt, es minden parameter
   eltunik amikor Revitben megnyitjuk. Hatarido pentek, teljesen elakadtam."
  "A falak geometriaja teljesen elromlik minden IFC-korben-oda-vissza konverzional."

MEZOK:
- is_pain: van-e tenyleges, konkret problema/kuzdelem lecirva (nem csak temaemlites)
- pain_summary: 1-2 mondat angolul, mi a konkret problema (ures string ha is_pain=false)
- tech_summary: 1 mondat angolul, technikai kontextus (verziok, munkafolyamat, eszkozok)
- archicad_probability / revit_probability: 0.0-1.0, mennyire valoszinu hogy a szerzo
  ezt a szoftvert hasznalja/erinti (nem kizarolagos - lehet mindketto magas)
- ifc_involved: erintett-e az IFC formatum a leirt problemaban
- issue_types: 0-3 cimke a listabol: {_ISSUE_TYPES}
- severity: 1-5 egesz szam (1 = trivialis/kiváncsisagi kerdes, 3 = valos, de kezelheto
  kellemetlenseg, 5 = sulyos, blokkolo problema hatarido-nyomassal vagy tobbszori
  probalkozassal)
- buying_intent: mutat-e a szerzo aktiv megoldas-keresest (nem csak panaszkodik,
  hanem alternativat/eszkozt/tanacsot keres)
- buying_intent_signals: 0-4 rovid angol kifejezes, ami erre utal (pl.
  "asking for alternative tool", "mentions deadline pressure", "evaluating options")
- role_hypothesis: a szerzo valoszinu szerepe egy rovid angol kifejezesben
- solved_internally: true, ha a szerzo leirja, hogy KORABBAN volt adatcsere problemajuk, 
  de valamilyen belső workaronddal/scripttel (sajat megoldassal) mar "megoldottak",
  vagy manualisan oldjak meg a feladatot. Ez jelzi, hogy van/volt fajdalom.
- nodu_mention: true, ha a bejegyzes/komment organikusan MEGEMLITI a "nodu" vagy a
  "nodu bridge" nevet (pl. mert valaki mas ajanlja ezt a megoldast).
- competitor_mentioned: true, ha a szerzo kifejezetten megemlit egy versenytars
  adatcsere megoldast (pl. Speckle, BIMcollab, DiRoots, Ideate, Flux, Konstru stb.)
  mint eszkozt, amivel probalkozik, vagy amire atvaltott.
- competitor_name: a megemlitett versenytars neve (pl. "Speckle"), vagy ures string.
- confidence: 0.0-1.0, mennyire biztos a sajat osztalyozasodban
- rationale: 1 mondat angolul, MIERT ezt a dontest hoztad (kulonosen is_pain es
  severity indoklasa)

A bejegyzes barmilyen nyelven erkezhet (pl. japan, magyar) — olvasd es ertelmezd,
de MINDEN mezot ANGOLUL valaszolj, a konzisztens tovabbfeldolgozashoz.
Csak a keresett JSON-t add vissza, mas szoveget ne.
""".strip()

_USER_TEMPLATE = """
Platform: {platform} | Forras: {source}
Szerzo: {author}
Cim: {title}
Szoveg: {body}
(Elo-szures szerint egyezo kulcsszavak: {keywords})
""".strip()

_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "is_pain": {"type": "BOOLEAN"},
        "pain_summary": {"type": "STRING"},
        "tech_summary": {"type": "STRING"},
        "archicad_probability": {"type": "NUMBER"},
        "revit_probability": {"type": "NUMBER"},
        "ifc_involved": {"type": "BOOLEAN"},
        "issue_types": {"type": "ARRAY", "items": {"type": "STRING", "enum": _ISSUE_TYPES}},
        "severity": {"type": "INTEGER"},
        "buying_intent": {"type": "BOOLEAN"},
        "buying_intent_signals": {"type": "ARRAY", "items": {"type": "STRING"}},
        "role_hypothesis": {"type": "STRING"},
        "solved_internally": {"type": "BOOLEAN"},
        "nodu_mention": {"type": "BOOLEAN"},
        "competitor_mentioned": {"type": "BOOLEAN"},
        "competitor_name": {"type": "STRING"},
        "confidence": {"type": "NUMBER"},
        "rationale": {"type": "STRING"},
    },
    "required": [
        "is_pain", "pain_summary", "tech_summary", "archicad_probability",
        "revit_probability", "ifc_involved", "issue_types", "severity",
        "buying_intent", "buying_intent_signals", "role_hypothesis",
        "solved_internally", "nodu_mention", "competitor_mentioned",
        "competitor_name", "confidence", "rationale",
    ],
}


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class PainClassifier:
    def __init__(self, config: dict, db_path: str):
        self.db_path = db_path
        cc = config.get("classifier", {})
        sc = config.get("scoring", {})
        self.enabled = cc.get("enabled", True)
        self.batch_size = cc.get("batch_size", 20)
        self.delay_seconds = cc.get("delay_seconds", 5)
        self.model = sc.get("gemini_model", "gemini-2.5-flash")
        api_key = sc.get("gemini_api_key", "")
        self.api_key_ok = bool(api_key) and api_key != "YOUR_GEMINI_API_KEY"
        self.client = genai.Client(api_key=api_key) if self.api_key_ok else None

    def _classify_one(self, post: dict) -> dict | None:
        user_msg = _USER_TEMPLATE.format(
            platform=post.get("platform", ""),
            source=post.get("source", ""),
            author=post.get("author", "") or "ismeretlen",
            title=post.get("title", ""),
            body=(post.get("body", "") or "")[:1500],
            keywords=post.get("keywords", ""),
        )
        try:
            resp = self.client.models.generate_content(
                model=self.model,
                contents=user_msg,
                config=types.GenerateContentConfig(
                    system_instruction=_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=_SCHEMA,
                    max_output_tokens=1536,
                    # A gemini-2.5-flash alapertelmezetten "gondolkodasi" tokeneket
                    # fogyaszt a max_output_tokens keretbol — strukturalt, gyors
                    # osztalyozashoz ez felesleges, es csonka JSON-t eredmenyezett
                    # (2026-07-20-i elo teszt). Kikapcsolva.
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
            if not resp.text:
                print(f"  [classifier] Ures valasz (post {post.get('id')})")
                return None
            return json.loads(resp.text)
        except json.JSONDecodeError as e:
            # Csonka/hibas JSON a modelltol — ez az adott poszt hibaja, a
            # batch tobbi eleme meg sikerulhet, nem eri meg leallni miatta.
            print(f"  [classifier] Ervenytelen JSON (post {post.get('id')}): {e}")
            return None
        except genai_errors.APIError:
            # Kvota/API-szintu hiba — a run() dontse el (napi kvota eseten
            # leallitja az egesz batchet, mert nincs ertelme tovabb probalkozni).
            raise

    def _to_record(self, post_id: int, parsed: dict) -> dict:
        return {
            "post_id": post_id,
            "is_pain": 1 if parsed.get("is_pain") else 0,
            "pain_summary": parsed.get("pain_summary", ""),
            "tech_summary": parsed.get("tech_summary", ""),
            "archicad_probability": parsed.get("archicad_probability"),
            "revit_probability": parsed.get("revit_probability"),
            "ifc_involved": 1 if parsed.get("ifc_involved") else 0,
            "issue_types": ", ".join(parsed.get("issue_types") or []),
            "severity": parsed.get("severity"),
            "buying_intent": 1 if parsed.get("buying_intent") else 0,
            "buying_intent_signals": ", ".join(parsed.get("buying_intent_signals") or []),
            "role_hypothesis": parsed.get("role_hypothesis", ""),
            "solved_internally": 1 if parsed.get("solved_internally") else 0,
            "nodu_mention": 1 if parsed.get("nodu_mention") else 0,
            "competitor_mentioned": 1 if parsed.get("competitor_mentioned") else 0,
            "competitor_name": parsed.get("competitor_name", ""),
            "confidence": parsed.get("confidence"),
            "rationale": parsed.get("rationale", ""),
            "classifier_version": CLASSIFIER_VERSION,
            "classified_at": _now(),
        }

    def run(self, batch_size: int = None) -> int:
        if not self.enabled:
            print("[classifier] Ki van kapcsolva (classifier.enabled: false). Kihagy.")
            return 0
        if not self.api_key_ok:
            print("[classifier] Nincs Gemini API kulcs beallitva (scoring.gemini_api_key). Kihagy.")
            return 0

        limit = batch_size or self.batch_size
        posts = get_unclassified_posts(self.db_path, limit=limit)
        if not posts:
            print("[classifier] Nincs osztalyozatlan poszt.")
            return 0

        started = _now()
        error_msg = None
        classified = 0

        for i, post in enumerate(posts):
            try:
                parsed = self._classify_one(post)
            except genai_errors.APIError as e:
                details = str(e)
                if "RESOURCE_EXHAUSTED" in details and "PerDay" in details:
                    print(
                        f"[classifier] Napi Gemini-kvóta elfogyott — leállok. "
                        f"{classified}/{len(posts)} posztot dolgoztam fel eddig. "
                        f"Folytatás holnap (vagy fizetős csomaggal, amelyre nincs napi limit)."
                    )
                    break
                if "RESOURCE_EXHAUSTED" in details:
                    print(f"  [classifier] Perc-kvóta elérve (post {post.get('id')}), 20mp várakozás...")
                    time.sleep(20)
                    continue
                error_msg = details
                print(f"  [classifier] API HIBA (post {post.get('id')}): {e}")
                continue

            if parsed is not None:
                record = self._to_record(post["id"], parsed)
                if insert_signal(self.db_path, record):
                    classified += 1
                    flag = "FAJDALOM" if parsed.get("is_pain") else "nem fajdalom"
                    print(
                        f"  [{i+1}/{len(posts)}] #{post['id']} '{post.get('title','')[:50]}' "
                        f"-> {flag} | sulyossag: {parsed.get('severity')} | "
                        f"bizalom: {parsed.get('confidence')}"
                    )
            if i < len(posts) - 1:
                time.sleep(self.delay_seconds)

        log_run(
            self.db_path,
            connector="classifier",
            started_at=started,
            finished_at=_now(),
            new_posts=classified,
            error=error_msg,
        )
        print(f"[classifier] {classified}/{len(posts)} poszt osztalyozva.")
        return classified


def review_signals(db_path: str, min_severity: int = 1, limit: int = 100) -> None:
    """
    Kezi kiertekelo riport (audit Roadmap 1. fazis: "2 het adatan bizonyitani,
    hogy a jelminoseg valos"). Nem donteshozo workflow — csak olvashato
    osszefoglalo, hogy Zoltan szemmel atlathassa: a classifier valoban
    fajdalmat lat-e a keresett szo helyett.
    """
    signals = get_signals_for_review(db_path, min_severity=min_severity, limit=limit)
    if not signals:
        print("Nincs meg osztalyozott jel (futtasd eloszor: python main.py --classify).")
        return

    pain_count = sum(1 for s in signals if s["is_pain"])
    intent_count = sum(1 for s in signals if s["buying_intent"])
    print(f"\n{len(signals)} osztalyozott jel (severity >= {min_severity}).")
    print(f"Ebbol fajdalom: {pain_count} | buying intent: {intent_count}\n")

    for i, s in enumerate(signals, 1):
        flag = "FAJDALOM" if s["is_pain"] else "nem fajdalom"
        intent = " | BUYING INTENT" if s["buying_intent"] else ""
        ref = " | REFERRAL" if s.get("nodu_mention") else ""
        hid = " | HIDDEN OPP" if s.get("solved_internally") else ""
        print("=" * 78)
        print(f"[{i}/{len(signals)}] {s['platform']} | {s['source']} | severity={s['severity']} "
              f"| confidence={s['confidence']} | {flag}{intent}{ref}{hid}")
        print(f"Cim : {s['title']}")
        print(f"URL : {s['url']}")
        print(f"Szerzo (feltetelezett szerep): {s['author'] or '?'} ({s['role_hypothesis']})")
        print(f"Kulcsszo-score (elo-szuro): {s['keyword_score']} | Kulcsszavak: {s['keywords']}")
        print(f"Archicad/Revit valoszinuseg: {s['archicad_probability']}/{s['revit_probability']} "
              f"| IFC: {bool(s['ifc_involved'])} | tipus: {s['issue_types']}")
        print(f"Fajdalom-osszefoglalo: {s['pain_summary'] or '(nincs)'}")
        print(f"Technikai kontextus  : {s['tech_summary']}")
        if s["buying_intent_signals"]:
            print(f"Buying-intent jelek  : {s['buying_intent_signals']}")
        print(f"Indoklas (LLM)       : {s['rationale']}")
        print()

    print("=" * 78)
    print(
        f"OSSZESITO: {len(signals)} jel | {pain_count} valodi fajdalom "
        f"({pain_count/len(signals)*100:.0f}%) | {intent_count} buying-intent jel.\n"
        "Kezi ellenorzes: nezd at a fenti pain_summary/rationale mezoket — "
        "a classifier tenyleg fajdalmat lat, vagy csak kulcsszo-egyezest indokol?"
    )
