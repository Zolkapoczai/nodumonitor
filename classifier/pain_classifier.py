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
import re
import time
from datetime import datetime, timezone

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from env_secrets import get_secret
from storage.db import (get_unclassified_posts, get_signals_for_review, insert_signal,
                        log_run, bump_classify_attempt, get_classify_backlog)

# A modell + prompt verziojat kodolja — ha a promptot vagy a modellt valtjuk,
# ezt is bumpeljuk, hogy a regi/uj jelek megkulonboztethetok legyenek
# visszamenoleges ujraszamolasnal (audit §9, scoring_configs elozmenye).
CLASSIFIER_VERSION = "gemini-2.5-flash-v4"

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
- severity: 1-5 egesz szam. MIND AZ OT fokozat definialva van — hasznald a teljes
  skalat, ne huzodj a kozepe fele:
    1 = nincs fajdalom: info-kerdes, kivancsisag, semleges temaemlites
    2 = apro sulodas: megoldotta vagy trivialisan megoldhato, csak megjegyzi
    3 = valos, de kezelheto kellemetlenseg: van workaround, halad a munka
    4 = jelentos akadaly: ismetlodo manualis munka, adatveszteseg, lassitja a projektet
    5 = blokkolo: a munka ALL, VAGY hatarido-nyomas van, VAGY tobbszor is nekifutott
        es nem sikerult. Eleg AZ EGYIK feltetel, nem kell mindharom.
  Ha ket fokozat kozott ingadozol, dontsd el, hogy HALAD-E a munka: ha igen, 3;
  ha vontatottan, 4; ha egyaltalan nem, 5.
- buying_intent: mutat-e a szerzo aktiv megoldas-keresest (nem csak panaszkodik,
  hanem alternativat/eszkozt/tanacsot keres)
- buying_intent_signals: 0-4 rovid angol kifejezes, ami erre utal (pl.
  "asking for alternative tool", "mentions deadline pressure", "evaluating options")
- role_hypothesis: a szerzo valoszinu szerepe egy rovid angol kifejezesben
- solved_internally: true, ha a szerzo leirja, hogy KORABBAN volt adatcsere problemajuk, 
  de valamilyen belső workaronddal/scripttel (sajat megoldassal) mar "megoldottak",
  vagy manualisan oldjak meg a feladatot. Ez jelzi, hogy van/volt fajdalom.
- competitor_mentioned: true, ha a szerzo kifejezetten megemlit egy versenytars
  adatcsere megoldast (pl. Speckle, BIMcollab, DiRoots, Ideate, Flux, Konstru stb.)
  mint eszkozt, amivel probalkozik, vagy amire atvaltott.
- competitor_name: a megemlitett versenytars neve PONTOSAN UGY, AHOGY A SZOVEGBEN
  SZEREPEL (pl. "Speckle"), vagy ures string. NE vond ossze tobbet egy mezobe, es
  NE irj olyan nevet, ami a szovegben nincs ott.
- competitor_quote: a szoveg SZO SZERINTI reszlete (min. 3 szo), amiben a
  competitor_name szerepel. A kod ELLENORZI, hogy ez a reszlet valoban benne van-e
  a bejegyzesben; ha nem talalja, a versenytars-jelolest ELDOBJA. Ures string, ha
  competitor_mentioned=false.
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
        "competitor_mentioned": {"type": "BOOLEAN"},
        "competitor_name": {"type": "STRING"},
        "competitor_quote": {"type": "STRING"},
        "confidence": {"type": "NUMBER"},
        "rationale": {"type": "STRING"},
    },
    "required": [
        "is_pain", "pain_summary", "tech_summary", "archicad_probability",
        "revit_probability", "ifc_involved", "issue_types", "severity",
        "buying_intent", "buying_intent_signals", "role_hypothesis",
        "solved_internally", "competitor_mentioned",
        "competitor_name", "competitor_quote", "confidence", "rationale",
    ],
}


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# A markaemlites DETERMINISZTIKUS: nem az LLM-tol kerdezzuk meg, hogy szerepel-e a
# "nodu" szo a szovegben, mert az egy regex dolga. Meres (2026-07-28): a modell 1431
# jelbol 1-ben jelolte, es ugyanezt az egyet a regex is megtalalja — a mezo tehat
# semmit nem adott, viszont LLM-donteskent hallucinalhat is. Ugyanezt a mintat a
# responder/linkedin_engine.py `_BRAND_PATTERN`-je mar hasznalja
# (docs/04-rendszer-audit-2026-07-28.md §3.4; az elv: §4/16 — az LLM a szenzor,
# nem a biro).
_BRAND_MENTION = re.compile(r"\bnodu(?:\s*bridge)?\b", re.IGNORECASE)


def detect_brand_mention(*texts: str) -> bool:
    """Szerepel-e a NODU/NODU Bridge nev a kapott szovegekben? Tiszta regex."""
    return any(_BRAND_MENTION.search(t or "") for t in texts)


def _normalize_for_quote(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def verify_competitor(parsed: dict, post: dict) -> tuple[int, str]:
    """
    A versenytars-jeloles ELLENORZESE. Visszaad: (competitor_mentioned, name).

    Miert: a modell `competitor_name`-je 2026-07-28-i meres szerint **53 jelbol
    8-ban (15%) olyan nevet adott, ami a szovegben SEHOL nem szerepel** — pl.
    "Navisworks, Solibri" (4x), "Graphisoft Archicad to Revit Add-in", es egy
    esetben magat az "ArchiCAD"-et jelolte versenytarskent. Semmi nem cafolta.
    Ezert most kotelezo a `competitor_quote`, es a kod megkeresi a posztban
    (normalizalt reszszoveg, min. 3 szo) — ha nincs meg, a jelolest ELDOBJUK.
    Ugyanaz az elv, mint a LinkedIn-motor `_quote_in_post`-janal (§4/18).
    """
    if not parsed.get("competitor_mentioned"):
        return 0, ""

    name = (parsed.get("competitor_name") or "").strip()
    quote = (parsed.get("competitor_quote") or "").strip()
    haystack = _normalize_for_quote(f"{post.get('title', '')} {post.get('body', '')}")

    if len(quote.split()) < 3:
        print(f"    [classifier] competitor ELDOBVA (tul rovid idezet): {quote!r}")
        return 0, ""
    if _normalize_for_quote(quote) not in haystack:
        print(f"    [classifier] competitor ELDOBVA (az idezet nincs a posztban): {quote[:60]!r}")
        return 0, ""
    if name and _normalize_for_quote(name) not in haystack:
        print(f"    [classifier] competitor ELDOBVA (a nev nincs a posztban): {name!r}")
        return 0, ""
    return 1, name


class PainClassifier:
    def __init__(self, config: dict, db_path: str):
        self.db_path = db_path
        cc = config.get("classifier", {})
        sc = config.get("scoring", {})
        self.enabled = cc.get("enabled", True)
        self.batch_size = cc.get("batch_size", 20)
        self.delay_seconds = cc.get("delay_seconds", 5)
        self.model = sc.get("gemini_model", "gemini-2.5-flash")
        # A kulcs env-bol vagy a git-ignoralt .env-bol jon (ld. env_secrets.py); a
        # config.yaml-beli ertek csak visszafele-kompatibilitasi tartalek. A
        # GitHub push-protection 2026-07-25-en (joggal) elutasitotta a commitot,
        # amiben a kulcs a config.yaml-ben volt.
        api_key = get_secret("GEMINI_API_KEY", sc.get("gemini_api_key"))
        self.api_key_ok = bool(api_key)
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

    def _to_record(self, post_id: int, parsed: dict, post: dict = None) -> dict:
        post = post or {}
        # A markaemlites regexbol, a versenytars idezettel igazolva — egyik sem
        # az LLM szava (§3.4, §3.5 az auditban).
        brand = detect_brand_mention(post.get("title", ""), post.get("body", ""))
        competitor_flag, competitor_name = verify_competitor(parsed, post)
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
            "nodu_mention": 1 if brand else 0,
            "competitor_mentioned": competitor_flag,
            "competitor_name": competitor_name,
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
            print("[classifier] Nincs Gemini API kulcs (GEMINI_API_KEY a .env-ben). Kihagy.")
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
            # A kiserlet-szamlalo a HIVAS ELOTT no: ha a valasz csonka JSON vagy a
            # hivas kivetellel all le, a poszt akkor is "megprobalt" allapotba kerul,
            # tehat a sor vegere csuszik, es `max_attempts` felett kiesik. Enelkul
            # egy tartosan hibas poszt orankent egy fizetos hivast egetett el
            # a vegtelenben (§3.8).
            bump_classify_attempt(self.db_path, post["id"])
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
                record = self._to_record(post["id"], parsed, post)
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
            items_seen=len(posts),
        )
        backlog = get_classify_backlog(self.db_path)
        print(f"[classifier] {classified}/{len(posts)} poszt osztalyozva. "
              f"Hatralek: {backlog['waiting']} poszt"
              + (f", a legregebbi: {str(backlog['oldest'])[:19]}" if backlog['oldest'] else "")
              + (f", kiserletszam miatt kiesett: {backlog['exhausted']}" if backlog['exhausted'] else ""))
        return classified


def calibrate(config: dict, db_path: str, limit: int = 25) -> dict:
    """
    PAROS meres: ugyanazokat a posztokat ujraosztalyozza a MAI prompttal, es a
    meglevo (regebbi verzioju) jellel osszeveti. A DB-t NEM irja.

    Miert kell: a v3 -> v4 osszevetes a nyers eloszlasokon FELREVEZETO, mert a ket
    kohorsz mas poszt-mixet tartalmaz (a v4 elso koreiben tulnyomoreszt GitHub/
    IfcOpenShell bug-reportok voltak, amik termeszetesen sulyosabbak). Ugyanazon a
    poszt-halmazon viszont a prompt-valtas hatasa kozvetlenul latszik. Ez a
    `docs/04-rendszer-audit-2026-07-28.md` §3.1-es javaslatanak a merese.
    """
    from storage.db import get_connection

    conn = get_connection(db_path)
    rows = conn.execute("""
        SELECT p.*, s.severity AS old_severity, s.is_pain AS old_is_pain,
               s.classifier_version AS old_version
        FROM signals s JOIN posts p ON p.id = s.post_id
        WHERE s.classifier_version != ?
        ORDER BY s.is_pain DESC, RANDOM()
        LIMIT ?
    """, (CLASSIFIER_VERSION, limit)).fetchall()
    conn.close()

    posts = [dict(r) for r in rows]
    if not posts:
        print("[calibrate] Nincs korabbi verzioval osztalyozott poszt.")
        return {}

    clf = PainClassifier(config, db_path)
    if not clf.api_key_ok:
        print("[calibrate] Nincs Gemini API kulcs. Kihagy.")
        return {}

    pairs = []
    print(f"[calibrate] {len(posts)} poszt ujraosztalyozasa a mai prompttal "
          f"({CLASSIFIER_VERSION}). A DB NEM valtozik.\n")
    for i, post in enumerate(posts, 1):
        parsed = clf._classify_one(post)
        if parsed is None:
            continue
        pairs.append({
            "post_id": post["id"],
            "title": (post.get("title") or "")[:45],
            "old_severity": post["old_severity"],
            "new_severity": parsed.get("severity"),
            "old_is_pain": post["old_is_pain"],
            "new_is_pain": 1 if parsed.get("is_pain") else 0,
        })
        mark = "=" if pairs[-1]["old_severity"] == pairs[-1]["new_severity"] else "->"
        print(f"  [{i}/{len(posts)}] #{post['id']} sev {post['old_severity']} {mark} "
              f"{parsed.get('severity')} | pain {post['old_is_pain']}->"
              f"{1 if parsed.get('is_pain') else 0} | {pairs[-1]['title']}")
        if i < len(posts):
            time.sleep(clf.delay_seconds)

    up = sum(1 for p in pairs if (p["new_severity"] or 0) > (p["old_severity"] or 0))
    down = sum(1 for p in pairs if (p["new_severity"] or 0) < (p["old_severity"] or 0))
    same = len(pairs) - up - down
    pain_flip = sum(1 for p in pairs if p["old_is_pain"] != p["new_is_pain"])

    def dist(key):
        d = {}
        for p in pairs:
            d[p[key]] = d.get(p[key], 0) + 1
        return dict(sorted(d.items(), key=lambda kv: (kv[0] is None, kv[0])))

    print(f"\n[calibrate] {len(pairs)} par: {up} feljebb, {down} lejjebb, {same} valtozatlan; "
          f"is_pain valtozott: {pain_flip}")
    print(f"  regi severity-eloszlas: {dist('old_severity')}")
    print(f"  uj  severity-eloszlas: {dist('new_severity')}")
    return {"pairs": pairs, "moved_up": up, "moved_down": down, "same": same,
            "pain_flips": pain_flip, "old_dist": dist("old_severity"),
            "new_dist": dist("new_severity")}


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
