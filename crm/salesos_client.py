"""
SalesOS ingest-kliens — a CRM-iras kozvetlen uton, n8n NELKUL.

Ez valtja ki az `ui/app.py` "to-sales-os" gombjat, ami eddig az `alerts.webhook`
n8n-vegpontot hivta — az pedig `enabled: false` es placeholder URL-lel allt, tehat
a gomb MINDEN kattintasra hibat adott (ld. docs/02-lead-volume-audit-2026-07.md §4/9).

Kontraktus: `C:\\NODU\\SalesOS\\docs\\08-bridge-integracio.md` (v1.2, implementalva
es elesben verifikalva). A lenyeg, amit a hivo oldalnak tudni kell:

- `POST /api/bridge/ingest`, `Authorization: Bearer <BRIDGE_API_KEY>`
- **Ceg-adat nelkul 422** (account-centrikus elv, §5): ha se cegnev, se
  companiesHouseNumber, se ceges e-mail nincs, a SalesOS elutasitja. Ez SZANDEKOS:
  "az azonositatlan Reddit-posztok a Bridge oldalan maradnak, amig ceg nem
  kotheto hozzajuk."
- `externalId` = idempotencia-kulcs; ismetelt hivas no-op (200, `deduped: true`).
- `sourceUrl` kotelezo (zero-hallucination elv mindket oldalon).
- `score` 0-10; a SalesOS kuszobei: Qualified >= 7, Lead >= 5 (env-ben hangolhatok).
- `painConfirmed`-et a Monitor SOHA nem ir — az emberi MEDDIC-kvalifikacio (§5).

MIERT NEM AUTOMATIKUS: a Monitorban ma nincs Entity Resolver (a 01-es audit 3.
fazisa), tehat cegnevet gepileg nem tudunk rendelni egy fórum-poszthoz. A
kuldes ezert **emberi kapun** megy: a dashboardon a felhasznalo adja meg a ceget,
es o kattint. Ez pontosan az, amit a 01-es audit §6 elo is ir — nem hiany, hanem
a tervezett munkamegosztas.
"""
import requests

from env_secrets import get_secret

_DEFAULT_BASE_URL = "http://localhost:3000"
_ENDPOINT = "/api/bridge/ingest"


class SalesOSError(Exception):
    """Uzleti hiba (422/401/…) — a hivo ezt jeleniti meg a felhasznalonak."""


def severity_to_score(severity: int | None, buying_intent: bool = None,
                      solved_internally: bool = None) -> int:
    """
    Monitor-jel -> SalesOS score (0-10).

    MIERT NEM CSAK severity x 2: mert az a lekepezes 2026-07-28-ig **ket erteket
    tudott eloallitani**. Meres: a fajdalom-jelek 99,6%-a severity 3 vagy 4, tehat
    a score kizarolag 6 vagy 8 lett — a 0-10-es sav 8 erteke sosem fordult elo, es
    a stage-lekepezes (>=7 Qualified, 5-6 Lead) egy bináris ermefeldobasra
    redukalodott (docs/04-rendszer-audit-2026-07-28.md §3.3).

    A `buying_intent` viszont VALODI variancia: a jelek ~9%-a jeloli, es pont azt
    jelenti, amit egy sales-score-nak jelezni kell — a szerzo AKTIVAN keres
    megoldast. Ezert:

        alap = severity x 2                      (2, 4, 6, 8, 10)
        + 1   ha buying_intent                   (aktiv megoldas-kereses)
        - 1   ha solved_internally               (mar van sajat workaroundja)
        vegul 0-10 kozott vagva

    Igy a mai jelkeszlet a 5..9 savot hasznalja, es a Qualified-kuszob (>=7) valodi
    dontest jelent: sev4 + intent = 9 (Qualified), sev4 intent nelkul = 8 — de sev3
    + intent = 7 (Qualified), sev3 intent nelkul = 6 (Lead). A `solved_internally`
    levonas azert van, mert aki mar megoldotta belso scripttel, kevesbe surgos lead.

    A parameterek OPCIONALISAK: hivas nelkul a regi viselkedes marad (severity x 2),
    igy a fuggveny visszafele kompatibilis. Amikor a verziozott scoring-motor
    elkeszul (2. fazis), ez a fuggveny cserelheto — egy helyen van.
    """
    if not severity:
        return 0
    score = int(severity) * 2
    if buying_intent:
        score += 1
    if solved_internally:
        score -= 1
    return max(0, min(10, score))


def build_payload(post: dict, company: dict, summary: str = "",
                  contact: dict = None) -> dict:
    """
    Ingest-payload egy Monitor-posztbol. A `company` a HASZNALO altal megadott
    ceg-adat (a Resolver helyett) — enelkul a SalesOS 422-t ad.
    """
    payload = {
        "externalId": f"nodu-monitor-post-{post['id']}",
        "channel": "scraper",
        "sourceUrl": post.get("url", ""),
        # A score-ba a buying_intent es a solved_internally is beszamit — enelkul a
        # 0-10-es savbol csak 6 es 8 fordult elo (§3.3). A `get_post_with_signal`
        # `sig_`-prefixszel adja a signal-mezoket, a `get_opportunities` prefix nelkul.
        "score": severity_to_score(
            post.get("sig_severity") or post.get("severity"),
            buying_intent=post.get("sig_buying_intent") if post.get("sig_buying_intent") is not None
            else post.get("buying_intent"),
            solved_internally=post.get("sig_solved_internally")
            if post.get("sig_solved_internally") is not None else post.get("solved_internally"),
        ),
        "summary": summary or _default_summary(post),
        "occurredAt": post.get("created_at") or None,
    }
    company = {k: v for k, v in (company or {}).items() if v}
    if company:
        payload["company"] = company
    if contact:
        contact = {k: v for k, v in contact.items() if v}
        if contact:
            payload["contact"] = contact
    return {k: v for k, v in payload.items() if v not in (None, "")}


def _default_summary(post: dict) -> str:
    """Activity-torzs a SalesOS-ben. A classifier osszefoglaloja, ha van."""
    parts = []
    pain = post.get("sig_pain_summary") or post.get("pain_summary")
    tech = post.get("sig_tech_summary") or post.get("tech_summary")
    if pain:
        parts.append(f"Pain: {pain}")
    if tech:
        parts.append(f"Technikai kontextus: {tech}")
    if not parts:
        parts.append((post.get("title") or "")[:200])
    role = post.get("sig_role_hypothesis") or post.get("role_hypothesis")
    if role:
        parts.append(f"Feltetelezett szerep: {role}")
    # A forras-URL-t NEM tesszuk bele: a SalesOS a §6 szerint maga fuzi az
    # Activity torzsehez ("Forrás: <sourceUrl>"). Elesben ellenorizve
    # 2026-07-24-en — ket URL-sor lett belole. Csak a platformot adjuk meg.
    if post.get("platform"):
        parts.append(f"Forras-platform: {post['platform']}")
    return "\n".join(parts)


def send_to_salesos(config: dict, post: dict, company: dict,
                    summary: str = "", contact: dict = None) -> dict:
    """
    Egy poszt atadasa a SalesOS-nek. Visszaad: a SalesOS JSON-valasza
    (`{deduped: true}` ismetelt hivasnal). SalesOSError-t dob, ha nincs kulcs,
    vagy ha a SalesOS elutasitja.
    """
    sc = config.get("salesos", {})
    base_url = (sc.get("base_url") or _DEFAULT_BASE_URL).rstrip("/")
    api_key = get_secret(sc.get("api_key_env", "BRIDGE_API_KEY"))
    if not api_key:
        raise SalesOSError(
            "Nincs BRIDGE_API_KEY. Tedd a projekt .env fajljaba "
            "(a SalesOS .env-jeben megtalalod ugyanazt a kulcsot)."
        )

    if not post.get("url"):
        raise SalesOSError("A poszthoz nincs forras-URL — a SalesOS 422-t adna (zero-hallucination elv).")

    # A SalesOS negy jelzest fogad el ceg-azonositasra. A pontos halmazt az eles
    # 422-es valasz mondta meg (2026-07-24-i kulcs-proba):
    #   "Ceg-jelzes nelkul nincs ingest (cegnev, house-number, domain vagy ceges e-mail kell)."
    # A `domain` is eleg — a 08-spec §4/2 match-kulcsa a domain ↔ Company.website.
    has_company = any((company or {}).get(k) for k in ("name", "companiesHouseNumber", "domain"))
    has_business_email = bool((contact or {}).get("email"))
    if not has_company and not has_business_email:
        raise SalesOSError(
            "Ceg-adat nelkul a SalesOS elutasit (account-centrikus elv, 08-spec §5). "
            "Adj meg cegnevet, Companies House szamot, domaint vagy ceges e-mailt."
        )

    payload = build_payload(post, company, summary=summary, contact=contact)
    try:
        resp = requests.post(
            f"{base_url}{_ENDPOINT}",
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            timeout=20,
        )
    except requests.RequestException as e:
        raise SalesOSError(f"A SalesOS nem elerheto ({base_url}): {e}") from e

    if resp.status_code == 401:
        raise SalesOSError("401 — ervenytelen BRIDGE_API_KEY.")
    if resp.status_code == 422:
        raise SalesOSError(f"422 — a SalesOS elutasitotta a payloadot: {resp.text[:300]}")
    if not resp.ok:
        raise SalesOSError(f"HTTP {resp.status_code}: {resp.text[:300]}")

    try:
        return resp.json()
    except ValueError:
        return {"ok": True}
