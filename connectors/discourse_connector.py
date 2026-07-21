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
from datetime import datetime, timezone

import requests

from filters.keyword_filter import KeywordFilter
from storage.db import insert_post, log_run

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

    def _search(self, base_url: str, query: str) -> list[dict]:
        try:
            resp = requests.get(
                f"{base_url}/search.json",
                params={"q": query},
                headers={"User-Agent": "NODU-Bridge-Monitor/0.1"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[discourse] API hiba ({base_url}): {e}")
            return []

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
        started = _now()
        error_msg = None

        try:
            for forum_name, forum_cfg in forums.items():
                base_url = forum_cfg.get("base_url", "").rstrip("/")
                if not base_url:
                    continue
                queries = forum_cfg.get("queries", _DEFAULT_QUERIES)
                for query in queries:
                    items = self._search(base_url, query)
                    n = self._save(forum_name, base_url, items)
                    total += n
                print(f"[discourse] {forum_name}: {total} uj bejegyzes eddig")
        except Exception as e:
            error_msg = str(e)
            print(f"[discourse] HIBA: {e}")

        log_run(
            self.db_path,
            connector="discourse",
            started_at=started,
            finished_at=_now(),
            new_posts=total,
            error=error_msg,
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
            items = self._search(base_url, query)
            total += self._save(forum_name, base_url, items, search_term=term, require_keywords=False)
        return total
