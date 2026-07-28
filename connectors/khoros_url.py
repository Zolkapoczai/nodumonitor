"""
Khoros-URL kanonizalas (Autodesk + Graphisoft forum).

MIERT KELL: a Khoros keresesi talalat URL-je futasonkent MAS, mert tartalmazza a
`search-action-id` parametert:

    .../m-p/13623288/highlight/true?search-action-id=1351577432174&search-result-uid=...#M136
    .../m-p/13623288/highlight/true?search-action-id=1352038633798&search-result-uid=...#M136

Ez a KET URL UGYANAZ A HOZZASZOLAS. A playwright_connector viszont a nyers href-et
tette az `external_id`-be, ezert a `UNIQUE(platform, external_id)` soha nem fogott:
2026-07-28-i meres szerint 1309 khoros-poszt = **33 valodi szal** (39,7x duplikacio).
A `posts` 77%-a duplikatum volt, es kb. 1150 fizetos Gemini-hivas duplikatumokra ment
el. A heartbeat ezt SOHA nem jelezte volna, mert a `new_posts` magas volt — vagyis
"egeszseges" (ld. docs/04-rendszer-audit-2026-07-28.md §1.1).

A modul KET fuggvenyt ad, es MINDKETTOT hasznalja a connector ES a migracio —
kulon implementacio eseten a ket kulcs elcsuszhatna, es a dedup ujra elromolna.
"""
import re
from urllib.parse import urlsplit

# Khoros uzenet-/cikk-azonositok: /m-p/<id> (message), /ta-p/<id> (tkb article),
# /td-p/<id> (discussion thread). Az <id> a forumon belul egyedi.
_MSG_ID = re.compile(r"/(?:m-p|ta-p|td-p|idi-p)/(\d+)")
# A nezet-modositokat a kanonikus URL-bol elhagyjuk: ugyanaz a tartalom.
_VIEW_SUFFIX = re.compile(r"/(?:highlight|page)/[^/]+/?$")


def canonical_thread_url(href: str) -> str:
    """
    A hozzaszolas stabil URL-je: query es fragment nelkul, nezet-modositok nelkul.
    Ures bemenetre ures stringet ad (a hivo dontse el, mit tesz vele).
    """
    if not href:
        return ""
    parts = urlsplit(href.strip())
    if not parts.scheme or not parts.netloc:
        return href.strip()
    path = _VIEW_SUFFIX.sub("", parts.path).rstrip("/")
    return f"{parts.scheme}://{parts.netloc}{path}"


def canonical_external_id(href: str) -> str:
    """
    Dedup-kulcs: `<host>:<message-id>`, pl. `forums.autodesk.com:13623288`.

    A host is benne van, mert a message-id csak forumon belul egyedi. Ha nincs
    felismerheto message-id (uj Khoros-nezet, atalakitott URL), a kanonikus URL-re
    esunk vissza — az legalabb a query-parametereket levagja, tehat a mai
    hibaosztaly akkor sem ismetlodik meg.
    """
    if not href:
        return ""
    m = _MSG_ID.search(href)
    host = urlsplit(href.strip()).netloc
    if m and host:
        return f"{host}:{m.group(1)}"
    return canonical_thread_url(href)
