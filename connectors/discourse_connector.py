"""
Discourse connector — buildingSMART International fórum.

A buildingSMART forums.buildingsmart.org Discourse-alapu, nyilt JSON API-val
(nincs hitelesites, nincs kulcs): GET /search.json?q=<kifejezes>.
Dokumentacio: https://docs.discourse.org/ (search.json a hivatalos,
nem-authentikalt vegpont resze).

A valasz ket parhuzamos tombot ad: posts[] (poszt-szintu adat: szerzo, blurb,
letrehozas ideje) es topics[] (tema-szintu adat: cim, slug — ebbol epul a
teljes thread-URL: /t/<slug>/<id>).
"""
import time
from datetime import datetime, timezone

import requests

from filters.keyword_filter import KeywordFilter
from storage.db import insert_post, log_run

# A buildingSMART Discourse-a szigoruan rate-limitel: a query x rendezes bovites
# utan 429-et adott mar ~8 keresnel is, ha azok gyorsan kovetik egymast. 3 s
# szunet + `search_pages: 1` (config) tartja a kort a limit alatt: ~9 keres/kor,
# ~27 s, 4 oras poll-intervallum mellett ez elhanyagolhato.
_DELAY_S = 3.0

_DEFAULT_QUERIES = [
    "revit archicad",
    "archicad revit",
    "ifc export revit",
    "archicad ifc",
]


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class DiscourseConnector:
    def __init__(self, config: dict, db_path: str):
        self.config = config
        self.db_path = db_path
        self.dc_config = config.get("discourse", {})
        self.kf = KeywordFilter(config)
        self._failed_requests: list[str] = []

    def _get_json(self, url: str, params: dict) -> dict | None:
        try:
            resp = requests.get(
                url, params=params,
                headers={"User-Agent": "NODU-Bridge-Monitor/0.1"},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            # A HTTP-hibat (tipikusan 429) gyujtjuk, hogy a runs.error-ban
            # latszodjon — enelkul egy vegig rate-limitelt kor "0 elem"-nek,
            # azaz eltort connectornak tunne.
            self._failed_requests.append(f"{url.rsplit('/', 1)[-1]}: {e}")
            print(f"[discourse] API hiba ({url}): {e}")
            return None
        finally:
            time.sleep(_DELAY_S)

    @staticmethod
    def _rows_from_search(base_url: str, data: dict) -> list[dict]:
        posts = data.get("posts", [])
        topics = {t["id"]: t for t in data.get("topics", [])}

        results = []
        for post in posts:
            topic = topics.get(post.get("topic_id"))
            if not topic:
                continue
            slug = topic.get("slug", "")
            topic_id = topic.get("id")
            url = f"{base_url}/t/{slug}/{topic_id}" if slug else f"{base_url}/t/{topic_id}"
            results.append({
                "url": url,
                "title": topic.get("title", ""),
                "body": (post.get("blurb", "") or "")[:2000],
                "author": post.get("username", ""),
                "external_id": str(post.get("id", url)),
                "created_at": post.get("created_at", "") or _now(),
            })
        return results

    def _search(self, base_url: str, query: str, pages: int = 1,
                order_latest: bool = False) -> list[dict]:
        """
        Discourse `/search.json`. Ket, korabban kihasznalatlan lehetoseggel:

        - `order:latest` a query-ben: a `/search.json` alapbol RELEVANCIA szerint
          rendez, ezert 53 futason at nagyjabol ugyanazt a statikus top-50-et adta
          vissza (190 elem/kor, 38 uj OSSZESEN). Igy egy uj tema csak akkor jelent
          meg, ha berobbant a relevancia-rangsor tetejere.
        - `page=`: a Discourse lapoz; egy lap ~50 elem.
        Ld. docs/02-lead-volume-audit-2026-07.md §3.9.
        """
        q = f"{query} order:latest" if order_latest else query
        results: list[dict] = []
        for page in range(1, max(1, pages) + 1):
            params = {"q": q}
            if page > 1:
                params["page"] = page
            data = self._get_json(f"{base_url}/search.json", params)
            if not data:
                break
            rows = self._rows_from_search(base_url, data)
            if not rows:
                break  # nincs tobb lap
            results.extend(rows)
        return results

    def _latest(self, base_url: str, pages: int = 1) -> list[dict]:
        """
        A `/latest.json` a fórum FRISS temait adja (~30 db/lap), fuggetlenul
        attol, hogy azok bekerulnek-e barmelyik kereses relevancia-rangsoraba.
        A kulcsszo-szuro utana amugy is szur — ez a "semmi nem csuszik at" halo.

        `pages`: a Discourse a `/latest.json`-t is lapozza (`?page=N`, 0-tol).
        Ez ott fontos, ahol a kereses NEM hasznalhato (robots.txt, ld. a
        `use_search` kapcsolot a run()-ban): a lapozott latest adja a melyseget
        a kereses helyett. Elesben merve a speckle.community-n: 6 lap = 180
        egyedi tema, mindegyik excerpt-tel.
        """
        results = []
        for page in range(0, max(1, pages)):
            params = {} if page == 0 else {"page": page}
            data = self._get_json(f"{base_url}/latest.json", params)
            if not data:
                break
            topics = data.get("topic_list", {}).get("topics", [])
            if not topics:
                break  # nincs tobb lap
            for topic in topics:
                slug = topic.get("slug", "")
                topic_id = topic.get("id")
                if not topic_id:
                    continue
                url = f"{base_url}/t/{slug}/{topic_id}" if slug else f"{base_url}/t/{topic_id}"
                results.append({
                    "url": url,
                    "title": topic.get("title", ""),
                    # Ahol nincs excerpt, ott a cim + a kulcsszo-szuro dolgozik,
                    # a reszleteket a classifier a cimbol es a linkbol latja.
                    "body": (topic.get("excerpt") or "")[:2000],
                    "author": "",
                    "external_id": f"topic_{topic_id}",
                    "created_at": topic.get("created_at", "") or _now(),
                })
        return results

    def _save(self, forum_name: str, base_url: str, items: list[dict],
              search_term: str = None, require_keywords: bool = True) -> int:
        saved = 0
        for item in items:
            combined = f"{item['title']} {item['body']}"
            keywords, score = self.kf.match(combined)
            if require_keywords and not keywords:
                continue

            post = {
                "source": "discourse",
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
        forums = self.dc_config.get("forums", {})
        total = 0
        total_seen = 0
        started = _now()
        error_msg = None

        pages = self.dc_config.get("search_pages", 2)
        use_latest = self.dc_config.get("include_latest", True)

        try:
            for forum_name, forum_cfg in forums.items():
                base_url = forum_cfg.get("base_url", "").rstrip("/")
                if not base_url:
                    continue

                # Per-forum kapcsolok. A `use_search` azert kell, mert a
                # robots.txt forumonkent MAS: a speckle.community-n
                # `Disallow: /search` szerepel (ez a /search.json-ra is illik,
                # prefix-egyezes), ezert ott csak a lapozott /latest.json fut.
                # Ld. HANDOFF §4/15.
                if not forum_cfg.get("use_search", True):
                    print(f"[discourse] {forum_name}: kereses kihagyva (use_search: false)")
                else:
                    queries = forum_cfg.get("queries", _DEFAULT_QUERIES)
                    for query in queries:
                        # Relevancia-rendezes (a "regi klasszikusok") ES friss-rendezes
                        # (az uj temak) egyutt — ez a ketto mas halmazt ad.
                        items = self._search(base_url, query,
                                             pages=forum_cfg.get("search_pages", pages))
                        items += self._search(base_url, query,
                                              pages=forum_cfg.get("search_pages", pages),
                                              order_latest=True)
                        total_seen += len(items)
                        total += self._save(forum_name, base_url, items)

                if forum_cfg.get("include_latest", use_latest):
                    latest = self._latest(base_url, pages=forum_cfg.get("latest_pages", 1))
                    total_seen += len(latest)
                    total += self._save(forum_name, base_url, latest)
                    print(f"[discourse] {forum_name}: latest.json {len(latest)} friss tema")

                print(f"[discourse] {forum_name}: {total} uj bejegyzes eddig ({total_seen} elem latva)")
        except Exception as e:
            error_msg = str(e)
            print(f"[discourse] HIBA: {e}")

        if error_msg is None and self._failed_requests:
            error_msg = (f"{len(self._failed_requests)} keres hibara futott "
                         f"(elso: {self._failed_requests[0][:150]})")

        log_run(
            self.db_path,
            connector="discourse",
            started_at=started,
            finished_at=_now(),
            new_posts=total,
            error=error_msg,
            items_seen=total_seen,
        )
        return total

    def search(self, query: str, search_term: str = None) -> int:
        """Ad-hoc kereses: minden konfiguralt Discourse-forumon egy kifejezesre."""
        forums = self.dc_config.get("forums", {})
        term = search_term or query
        total = 0
        for forum_name, forum_cfg in forums.items():
            base_url = forum_cfg.get("base_url", "").rstrip("/")
            if not base_url:
                continue
            # Ahol a robots.txt tiltja a keresest, ott az ad-hoc kereses sem fut.
            if not forum_cfg.get("use_search", True):
                continue
            items = self._search(base_url, query)
            total += self._save(forum_name, base_url, items, search_term=term, require_keywords=False)
        return total
