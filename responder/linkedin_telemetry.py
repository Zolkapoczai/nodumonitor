"""
LinkedIn-motor telemetria — soronkent egy generalt komment dontesi nyoma.

MIERT KELL: a motor MINDEN dontest visszaad a valaszban (`strategy_scores`,
`concreteness`, `opening_shape`, a ket homerseklet...), de a valasz a HTTP-korrel
eltunik. Emiatt kimondottan FONTOS kerdesekre nem lehetett valaszolni:

  1. Nyer-e valaha a `constructive_challenge`? A bias-terv szerint velemeny- es
     debate-poszton semleges, tehat nyerhetne. Ha a modell `strategy_fit`
     pontozasa szisztematikusan lehuzza, a terv nem valosul meg — es ez ma
     lathatatlan.
  2. MEGVALASZOLVA (2026-08-10): korrelal-e az authenticity-rubrika a kezi
     pontokkal? Nem — harom meres, harom 10/10, nulla variancia. A rubrika
     TOROLVE, es ezt a naplo dontotte el, nem velemeny. Ez a mezo maga is
     eltunt (`TELEMETRY_SCHEMA` 1 -> 2).
  3. Hat-e a hivasonkenti homerseklet-bontas (2026-08-09)?
  4. Szor-e tenylegesen a nyitas-rotacio, es no-e tole az ujrairasok szama?
  5. Homalyos-e a komment? (`concreteness`: hozott konkret horgony, absztrakt-
     suruseg, hedge-halmozas — harom kulon szam, osszpontszam SZANDEKOSAN nincs.)
  6. Ujramondja-e a komment a posztot? A `post_overlap` csak LEXIKAI visszhangot
     mer (4-gram), a mas szavakkal elmondott ugyanaz 0.0-t ad. Ehhez a REASON
     gondolatmenete kell: `insight` + `core_thesis` + `missing_perspective`.

Mind UGYANABBOL az egy sorbol megvalaszolhato, ezert egy fajl, nem sok kulon meres.
A 2. pont mutatja, hogy ez mukodik: egy igazolatlan meroszamot harom sor alapjan
lehetett kivezetni.

MIERT NEM DB-TABLA: a 03-composer-spec §Hatokor tiltja a "perzisztencia/
history-tablat". Az a tiltas ALLAPOTRA vonatkozik — approve/reject allapotgep,
piszkozat-tarolas, UI-bol olvasott elozmeny. Ez nem az: append-only tenynaplo,
az alkalmazas SOHA nem olvassa vissza, nincs hozza felulet es nincs migracio.
JSONL, mert igy barmilyen eszkozzel (pandas, jq, Excel) elemezheto anelkul, hogy
a semat elore el kellene donteni.

MIERT NEM TORHET EL SEMMIT: mire ide erunk, a fizetos LLM-hivas MAR lefutott es
a komment kesz van. Egy telemetria-hiba (nincs jogosultsag, tele a lemez, zarolt
fajl) nem veheti el a felhasznalotol a mar kifizetett eredmenyt. Ezert a `record`
SOHA nem dob kivetelt — minden hibat lenyel es kiir.

ADATVEDELEM
  - A poszt TELJES szovege NEM kerul a naploba: masvalaki tartalma. Helyette
    stabil `post_id` (sha256-prefix) + rovid `post_excerpt` — ennyi eleg ahhoz,
    hogy egy sort a benchmark-tabladhoz parosits, archivum nelkul.
  - A KEP soha, semmilyen formaban (a meglevo szabaly: "a kep sosem kerul lemezre
    es sosem kerul logba"). Csak az `image_attached` / `image_role` tenye.
  - A komment TELJES szovege benne van: az a sajat kimeneted, es pont az, amit
    pontozol.

A KOD-DEFAULT KIKAPCSOLT. A bekapcsolas a `config.yaml` dolga. Igy egyetlen
teszt- vagy import-ut sem ir csendben a lemezre, es egy regi config viselkedese
valtozatlan.
"""
import hashlib
import io
import json
import os
from datetime import datetime, timezone

# A `config.yaml` relativ utjait EHHEZ kepest oldjuk fel (a dashboard gyokere),
# nem a mindenkori munkakonyvtarhoz — ugyanaz a minta, mint a `ui/app.py`
# BASE_DIR-je. Igy a cron-, teszt- es szerver-indulas ugyanoda ir.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_PATH = os.path.join("storage", "linkedin_telemetry.jsonl")

# A sor-sema verzioja. Ha kesobb mezo tunik el vagy valtozik a jelentese, ezt
# kell emelni — kulonben egy fel evvel kesobbi elemzes ket kulonbozo jelentesu
# oszlopot atlagolna ossze.
# MIKOR KELL EMELNI: ha mezo ELTUNIK, vagy egy meglevo mezo JELENTESE valtozik. Egy
# UJ mezo hozzaadasa NEM indokol emelest — a regi sorokban egyszeruen nincs benne, es
# ez nem teremti meg azt a hazardot, ami ellen a verzio vedelmet ad (ket kulonbozo
# jelentesu adat osszeatlagolasa).
#
# 1 -> 2 (2026-08-10): az `authenticity_score` / `authenticity_detail` /
# `authenticity_min` mezok ELTUNTEK a rubrika torlesevel. Ezt a bumpot a TORLES
# indokolja; az ugyanakkor bekerult `concreteness` / `quality_issues_first` /
# vendor-skip mezok onmagukban nem indokoltak volna. A 2026-08-10-i kesobbi,
# TISZTAN additiv bovites (`insight`, `core_thesis`, `missing_perspective`) ezert
# NEM emelte tovabb a verziot.
TELEMETRY_SCHEMA = 2

# Amit a motor valaszabol szo szerint atveszunk. Szandekosan EXPLICIT lista es nem
# "minden mezo": a valasz reply_text-en kivul is bovulhet, es egy naplo, ami
# magatol nyel le uj mezoket, eszrevetlenul kezdhet olyat tarolni, amit nem
# akarunk (pl. egy jovobeli nyers poszt-mezot).
_COPIED_FIELDS = (
    # dontes
    "engine", "strategy", "strategy_label", "strategy_fit", "strategy_scores",
    "strategy_vetoed", "conversation_intent", "discourse_level",
    "expected_responder_role", "response_mode", "human_temperature",
    "topic", "post_type", "technical_depth", "topic_gravity", "intent_layer",
    # A REASON GONDOLATMENETE (2026-08-10). Miert kellett: az otodik eles meres egy
    # UJ hibatipust hozott — SZEMANTIKAI REDUNDANCIA. A komment 75%-a a poszt sajat
    # tetelet mondta ujra, mas szavakkal; a `post_overlap` 4-gram-mero ezert 0.0-t
    # adott. A diagnozishoz azt kell latni, hogy a redundancia MAR a REASON
    # `insight`-jaban benne volt-e, vagy csak a COMPOSE hozta be — es ez a harom mezo
    # dönti el. Enelkul csak a vegtermeket latjuk, a gondolatmenetet nem.
    #
    # ADATVEDELEM: a `core_thesis` a szerzo allitasanak MODELL-ALTALI parafrazisa, nem
    # a szo szerinti szovege — vagyis kevesbe erzekeny, mint a mar tarolt
    # `post_excerpt`. A `missing_perspective` enum, az `insight` a sajat kimenetunk.
    "insight", "core_thesis", "missing_perspective",
    # nyitas-rotacio
    "opening_shape", "opening_recent",
    # cel-szohossz (2026-08-10, v7): a poszt hosszabol szamolt sav. A `reply_words`
    # mellett igy merheto, betartja-e a modell — es hogy a skalazas egyaltalan hat-e.
    "target_length",
    # homerseklet
    "temperature", "reason_temperature", "compose_temperature",
    # minoseg
    # (Az `authenticity_*` mezok 2026-08-10-en TOROLVE a rubrikaval egyutt: harom
    # meres, harom 10/10 — nulla variancia. A REGI sorok tovabbra is tartalmazzak
    # oket; a `schema` verzio alapjan kulonithetok el.)
    "quality_issues", "quality_issues_first", "rewrites", "post_overlap",
    "ai_fingerprint_terms", "confidence",
    # F2 konkretsag-diagnosztika (2026-08-10) — meres, nem kapu
    "concreteness",
    # vendor-hirdetes kihagyasa (2026-08-10). A `skipped=True` sorokban nincs
    # `reply_text`, de van `post_id` — igy szamolhato, milyen aranyban hagyunk ki.
    "skipped", "skip_reason", "vendor_promotion", "promotion_evidence", "forced",
    # marka + kep
    "brand_mode", "brand_allowed", "brand_gate_reason",
    "image_attached", "image_role",
)


def telemetry_enabled(config: dict) -> bool:
    """`linkedin.telemetry`: on | off (DEFAULT: off).

    Miert kikapcsolt a kod-default: bekapcsolva minden hivas ir a lemezre, es a
    tesztek is (azok minimalis config-dictekkel hivjak a motort). Egy naplo, ami
    teszt-sorokkal keveredik, pont arra alkalmatlan, amire keszult. A `config.yaml`
    bekapcsolja; egy regi config viselkedese valtozatlan.

    YAML-boolean kezelve (HANDOFF §4/17).
    """
    raw = (config.get("linkedin", {}) or {}).get("telemetry", "off")
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in ("on", "true", "1", "yes")


def telemetry_path(config: dict) -> str:
    """`linkedin.telemetry_path` — relativ utat a dashboard gyokerehez oldunk fel."""
    raw = (config.get("linkedin", {}) or {}).get("telemetry_path") or DEFAULT_PATH
    path = str(raw).strip() or DEFAULT_PATH
    return path if os.path.isabs(path) else os.path.join(BASE_DIR, path)


def post_id(post_text: str) -> str:
    """Stabil, rovid azonosito a POSZT szovegebol.

    Ugyanaz a poszt mindig ugyanazt az id-t kapja, tehat egy ujragenerals a
    benchmark-tabladban ugyanahhoz a sorhoz kotheto. Ugyanaz a normalizalas, mint
    a `pick_opening`-nel, hogy a ket dontes ugyanarra a kulcsra hivatkozzon.
    """
    norm = (post_text or "").strip().lower().encode("utf-8")
    return hashlib.sha256(norm).hexdigest()[:16]


def build_row(result: dict, post_text: str, elapsed_ms: int | None = None,
              now: datetime | None = None) -> dict:
    """A naplosor — TISZTA fuggveny, nincs benne I/O.

    Kulon van a `record`-tol, hogy a sor tartalma teszthető legyen fajlrendszer
    nelkul: a tartalmi allitasok (mi kerul bele, mi NEM) igy nem fuggnek attol,
    hogy sikerult-e az iras.
    """
    result = result or {}
    stamp = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    text = (post_text or "").strip()

    row = {
        "ts": stamp,
        "schema": TELEMETRY_SCHEMA,
        "ok": "error" not in result,
        # A poszt AZONOSITHATO, de nem archivalt: hash + rovid reszlet. Ennyi eleg
        # a benchmark-tabladhoz valo parositashoz.
        "post_id": post_id(text),
        "post_excerpt": text[:160],
        "post_words": len(text.split()),
        "elapsed_ms": elapsed_ms,
    }
    if "error" in result:
        # Hibas ut: a hiba maga a merendo tény (API-hiba, ervenytelen reasoning).
        # A sor rovid, de a `post_id` miatt ugyanugy parosithato.
        row["error"] = str(result.get("error", ""))[:400]
        return row

    row["reply_text"] = result.get("reply_text", "")
    row["reply_words"] = len((result.get("reply_text") or "").split())
    for key in _COPIED_FIELDS:
        if key in result:
            row[key] = result[key]
    return row


def record(config: dict, result: dict, post_text: str,
           elapsed_ms: int | None = None) -> bool:
    """Egy sor a naploba. SOHA nem dob kivetelt; True, ha tenylegesen irt.

    Mire idejutunk, a fizetos hivas mar lefutott es a komment kesz — egy
    telemetria-hiba nem veheti el a felhasznalotol a mar kifizetett eredmenyt.
    Ezert minden hiba lenyelve, de KIIRVA: a csendes adatvesztes rosszabb, mint a
    hangos.
    """
    try:
        if not telemetry_enabled(config):
            return False
        path = telemetry_path(config)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        line = json.dumps(build_row(result, post_text, elapsed_ms),
                          ensure_ascii=False)
        # Soronkent nyitjuk es zarjuk: egy hosszan nyitva tartott leiro egy
        # szinkron webutban semmit nem nyerne, viszont egy osszeomlas felig irt
        # sort hagyna. `a` mod + egy write hivas = a sor atomi marad a tipikus
        # meretnel.
        with io.open(path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(line + "\n")
        return True
    except Exception as e:                                   # noqa: BLE001
        print(f"[linkedin-telemetria] NEM sikerult a naplozas: {e}")
        return False
