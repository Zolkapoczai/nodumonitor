"""
Vanilla Forums connector — OSArch (community.osarch.org).

MIERT KULON CONNECTOR ES NEM EGY DISCOURSE CONFIG-BLOKK?
A HANDOFF §7/A azt felteteleztem, hogy az OSArch Discourse-alapu. NEM AZ:
elesben merve (2026-07-26) a `/latest.json` es az `/about.json` 404-et ad, a
`/search.json` viszont 200-at — de Vanilla Forums-semaval (`SearchResults`,
`ThemeOptions`, `heroImageUrl`), nem Discourse-eval (`posts[]`/`topics[]`).
A DiscourseConnector tehat egy config-blokkal NEM fedi le: mas a ket vegpont
neve, mas a parameter (`Search=` vs `q=`), mas a valasz szerkezete.

KET NYITOTT VEGPONT (hitelesites nelkul, elesben verifikalva):

1. `GET /api/v2/discussions?limit=N&sort=-dateInserted&expand=insertUser`
   A Vanilla API v2. Ez a Discourse `latest.json` megfeleloje, DE annal
   ertekesebb: TELJES torzset ad (`body`, HTML-ben), nem csak kivonatot.
   Figyelem: a kitûzott (`pinned`) temak a rendezestol fuggetlenul elore
   kerulnek — ezert jon 2020-as elem is a lista elejen. Nem baj: az
   `insert_post` amugy is eldobja az 1 evnel regebbieket.

2. `GET /search.json?Search=<kifejezes>&Page=p<N>`
   A legacy Vanilla kereso JSON-ban. Lapoz (20 talalat/lap), es KOMMENT-
   szintu talalatot is ad (`RecordType: Comment`), nem csak temat — ez pont
   a fajdalom-jelek termeszetes helye.

RATE LIMIT: elesben 8 gyors keres MIND 200-at adott (0,5-0,8 s), tehat az
OSArch nem limitel ugy, mint a buildingSMART (ott 429 jott ~8 kercesnel, ezert
van ott 3 s szunet). Itt 1,5 s udvariassagi szunet boven eleg.

robots.txt: a `Disallow: /search/` prefix a HTML-keresore vonatkozik, a
`/search.json`-t nem fedi. A kor igy is keves keresbol all (~4 query x 2 lap).
"""
import html
import re
import time
from datetime import datetime, timezone

import requests

from filters.keyword_filter import KeywordFilter
from storage.db import insert_post, log_run

_DELAY_S = 1.5

_DEFAULT_QUERIES = [
    "revit archicad",
    "archicad revit",
    "ifc export revit",
    "archicad ifc",
]

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _strip_html(raw: str, limit: int = 2000) -> str:
    """
    A Vanilla HTML-t ad vissza (`<p>...</p>`, a keresoben `<mark>` kiemelessel).
    A csonkitas MEG a kulcsszo-szuro elott tortenik: a `keyword_filter` regexei
    erzekenyek a hosszu szovegre (HANDOFF §4/10).
    """
    if not raw:
        return ""
    text = _TAG_RE.sub(" ", raw)
    text = html.unescape(text)
    return _WS_RE.sub(" ", text).strip()[:limit]


def _iso(value: str) -> str:
    """
    A ket vegpont MAS datumformatumot ad:
      /api/v2/discussions -> "2026-07-24T17:36:58+00:00"
      /search.json        -> "2026-07-24 18:03:56"  (naiv, UTC)
    Az `insert_post` kor-szurese `fromisoformat`-tal parszol, ezert a naiv
    valtozatot is szabvanyos ISO-ra hozzuk.
    """
    value = (value or "").strip()
    if not value:
        return _now()
    if " " in value and "T" not in value:
        value = value.replace(" ", "T")
    if not re.search(r"(Z|[+-]\d{2}:?\d{2})$", value):
        value += "+00:00"
    return value


class VanillaConnector:
    def __init__(self, config: dict, db_path: str):
        self.config = config
        self.db_path = db_path
        self.vn_config = config.get("vanilla", {})
        self.kf = KeywordFilter(config)
        self._failed_requests: list[str] = []

    def _get_json(self, url: str, params: dict):
        try:
            resp = requests.get(
                url, params=params,
                headers={"User-Agent": "NODU-Bridge-Monitor/0.1"},
                timeout=20,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            # A hibat gyujtjuk, hogy a runs.error-ban latszodjon — enelkul egy
            # vegig hibas kor "0 elem"-nek, azaz eltort connectornak tunne.
            self._failed_requests.append(f"{url.rsplit('/', 1)[-1]}: {e}")
            print(f"[vanilla] API hiba ({url}): {e}")
            return None
        finally:
            time.sleep(_DELAY_S)

    @staticmethod
    def _rows_from_search(data: dict) -> list[dict]:
        results = []
        for hit in data.get("SearchResults", []):
            url = hit.get("Url", "")
            if not url:
                continue
            record = (hit.get("RecordType") or "record").lower()
            results.append({
                "url": url,
                "title": _strip_html(hit.get("Title", ""), limit=500),
                "body": _strip_html(hit.get("Summary", "")),
                "author": hit.get("Name", "") or "",
                "external_id": f"{record}_{hit.get('PrimaryID', url)}",
                "created_at": _iso(hit.get("DateInserted", "")),
            })
        return results

    @staticmethod
    def _rows_from_discussions(data: list) -> list[dict]:
        results = []
        for d in data or []:
            url = d.get("url") or d.get("canonicalUrl") or ""
            discussion_id = d.get("discussionID")
            if not url or discussion_id is None:
                continue
            results.append({
                "url": url,
                "title": _strip_html(d.get("name", ""), limit=500),
                "body": _strip_html(d.get("body", "")),
                "author": (d.get("insertUser") or {}).get("name", "") or "",
                "external_id": f"discussion_{discussion_id}",
                "created_at": _iso(d.get("dateInserted", "")),
            })
        return results

    def _search(self, base_url: str, query: str, pages: int = 1) -> list[dict]:
        results: list[dict] = []
        for page in range(1, max(1, pages) + 1):
            params = {"Search": query}
            if page > 1:
                params["Page"] = f"p{page}"
            data = self._get_json(f"{base_url}/search.json", params)
            if not data:
                break
            rows = self._rows_from_search(data)
            if not rows:
                break  # nincs tobb lap
            results.extend(rows)
        return results

    def _recent(self, base_url: str, limit: int) -> list[dict]:
        """
        A friss temak — fuggetlenul attol, hogy bekerulnek-e barmelyik kereses
        relevancia-rangsoraba. A kulcsszo-szuro utana amugy is szur; ez a
        "semmi nem csuszik at" halo (ugyanaz a szerep, mint a Discourse-nal a
        latest.json — de itt teljes torzsszoveggel).
        """
        data = self._get_json(f"{base_url}/api/v2/discussions", {
            "limit": limit,
            "sort": "-dateInserted",
            "expand": "insertUser",
        })
        if not isinstance(data, list):
            return []
        return self._rows_from_discussions(data)

    def _save(self, forum_name: str, items: list[dict],
              search_term: str = None, require_keywords: bool = True) -> int:
        saved = 0
        for item in items:
            combined = f"{item['title']} {item['body']}"
            keywords, score = self.kf.match(combined)
            if require_keywords and not keywords:
                continue

            post = {
                "source": "vanilla",
                "platform": forum_name,
                "external_id": item["external_id"],
                "url": item["url"],
                "author": item["author"],
                "title": item["title"],
                "body": item["body"],
                "created_at": item["created_at"],
                "fetched_at": _now(),
                "keywords": ", ".join(keywords),
                "score": score,
                "search_term": search_term,
            }
            if insert_post(self.db_path, post):
                saved += 1
        return saved

    def run(self) -> int:
        forums = self.vn_config.get("forums", {})
        total = 0
        total_seen = 0
        started = _now()
        error_msg = None

        pages = self.vn_config.get("search_pages", 2)
        use_recent = self.vn_config.get("include_recent", True)
        recent_limit = self.vn_config.get("recent_limit", 50)

        try:
            for forum_name, forum_cfg in forums.items():
                base_url = forum_cfg.get("base_url", "").rstrip("/")
                if not base_url:
                    continue
                queries = forum_cfg.get("queries", _DEFAULT_QUERIES)
                for query in queries:
                    items = self._search(base_url, query, pages=pages)
                    total_seen += len(items)
                    total += self._save(forum_name, items)

                if use_recent:
                    recent = self._recent(base_url, recent_limit)
                    total_seen += len(recent)
                    total += self._save(forum_name, recent)
                    print(f"[vanilla] {forum_name}: /api/v2/discussions {len(recent)} friss tema")

                print(f"[vanilla] {forum_name}: {total} uj bejegyzes eddig ({total_seen} elem latva)")
        except Exception as e:
            error_msg = str(e)
            print(f"[vanilla] HIBA: {e}")

        if error_msg is None and self._failed_requests:
            error_msg = (f"{len(self._failed_requests)} keres hibara futott "
                         f"(elso: {self._failed_requests[0][:150]})")

        log_run(
            self.db_path,
            connector="vanilla",
            started_at=started,
            finished_at=_now(),
            new_posts=total,
            error=error_msg,
            items_seen=total_seen,
        )
        return total

    def search(self, query: str, search_term: str = None) -> int:
        """Ad-hoc kereses: minden konfiguralt Vanilla-forumon egy kifejezesre."""
        forums = self.vn_config.get("forums", {})
        term = search_term or query
        total = 0
        for forum_name, forum_cfg in forums.items():
            base_url = forum_cfg.get("base_url", "").rstrip("/")
            if not base_url:
                continue
            items = self._search(base_url, query)
            total += self._save(forum_name, items, search_term=term, require_keywords=False)
        return total
