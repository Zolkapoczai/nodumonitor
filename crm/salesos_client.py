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


def severity_to_score(severity: int | None) -> int:
    """
    Monitor severity (1-5) -> SalesOS score (0-10).

    A 01-es audit §6 a jovobeli `score_total` (0-100) / 10 lekepezest irja elo; a
    verziozott scoring-motor viszont a 2. fazis, ma csak a classifier severitye
    van. A x2 lekepezes a SalesOS kuszobeire ul ra ertelmesen:
        severity 5 -> 10  (Qualified)
        severity 4 ->  8  (Qualified, >= 7)
        severity 3 ->  6  (Lead, 5-6)
        severity 2 ->  4  (nincs Deal, csak jelzes-naplo)
        severity 1 ->  2  (nincs Deal)
    Amikor a scoring-motor elkeszul, ez a fuggveny cserelheto — egy helyen van.
    """
    if not severity:
        return 0
    return max(0, min(10, int(severity) * 2))


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
        "score": severity_to_score(post.get("sig_severity") or post.get("severity")),
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
