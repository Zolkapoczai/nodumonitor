"""
Stack Overflow / Stack Exchange connector.

Stack Exchange API v2.3 — ingyenes, regisztráció nélkül 300 kérés/nap.
API kulccsal (stackapps.com): 10 000 kérés/nap.

Dokumentáció: https://api.stackexchange.com/docs
"""
import time
from datetime import datetime, timezone

import requests

from filters.keyword_filter import KeywordFilter
from storage.db import insert_post

_BASE = "https://api.stackexchange.com/2.3"
_DELAY_S = 1.0  # udvarias késleltetés kérések között


class StackOverflowConnector:
    def __init__(self, config: dict, db_path: str):
        self.config = config
        self.db_path = db_path
        self.so_config = config.get("stackoverflow", {})
        self.kf = KeywordFilter(config)
        self.api_key = self.so_config.get("api_key", "") or None

    def _get(self, endpoint: str, params: dict) -> list[dict]:
        if self.api_key:
            params["key"] = self.api_key
        params.setdefault("pagesize", 25)
        params.setdefault("order", "desc")
        params.setdefault("sort", "creation")
        params.setdefault("filter", "withbody")

        try:
            resp = requests.get(f"{_BASE}/{endpoint}", params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if data.get("quota_remaining", 1) == 0:
                print("[stackoverflow] API kvóta kimerítve.")
            return data.get("items", [])
        except Exception as e:
            print(f"[stackoverflow] API hiba: {e}")
            return []

    def _save_items(self, items: list[dict], platform: str,
                    search_term: str = None, require_keywords: bool = True) -> int:
        saved = 0
        for item in items:
            title = item.get("title", "")
            body = item.get("body", "") or item.get("body_markdown", "")
            # HTML entitások durva eltávolítása (teljes parse nem szükséges)
            body = (
                body.replace("&lt;", "<")
                    .replace("&gt;", ">")
                    .replace("&amp;", "&")
                    .replace("&quot;", '"')
            )
            author_info = item.get("owner", {})
            author = author_info.get("display_name", "")
            url = item.get("link", "")
            external_id = str(item.get("question_id") or item.get("answer_id") or url)
            created_epoch = item.get("creation_date", 0)
            created_at = datetime.fromtimestamp(created_epoch, tz=timezone.utc).isoformat() if created_epoch else ""

            combined = f"{title} {body}"
            keywords, score = self.kf.match(combined)
            if require_keywords and not keywords:
                continue

            post = {
                "source": "stackoverflow",
                "platform": platform,
                "external_id": external_id,
                "url": url,
                "author": author,
                "title": title,
                "body": body[:2000],
                "created_at": created_at,
                "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
                "keywords": ", ".join(keywords),
                "score": score,
                "search_term": search_term,
            }
            if insert_post(self.db_path, post):
                saved += 1

        return saved

    def run(self) -> int:
        sites = self.so_config.get("sites", ["stackoverflow"])
        tagged_queries = self.so_config.get("tagged_queries", [])
        text_queries = self.so_config.get("text_queries", [])
        total = 0

        for site in sites:
            # Tag-alapú keresés
            for tags in tagged_queries:
                items = self._get("search/advanced", {"site": site, "tagged": tags})
                n = self._save_items(items, f"stackoverflow:{site}")
                total += n
                time.sleep(_DELAY_S)

            # Szöveges keresés
            for query in text_queries:
                items = self._get("search/advanced", {"site": site, "q": query})
                n = self._save_items(items, f"stackoverflow:{site}")
                total += n
                time.sleep(_DELAY_S)

        print(f"[stackoverflow] {total} uj bejegyzes mentve")
        return total

    def search(self, query: str, sites: list[str] = None, search_term: str = None) -> int:
        """
        Ad-hoc kereses: tetszoleges kifejezes a Stack Exchange site-okon.
        Minden talalatot ment (a query maga a szuro); a pontszam relevancia-jelzo.
        """
        sites = sites or self.so_config.get("sites", ["stackoverflow"])
        term = search_term or query
        total = 0
        for site in sites:
            items = self._get("search/advanced", {"site": site, "q": query})
            total += self._save_items(
                items, f"stackoverflow:{site}", search_term=term, require_keywords=False
            )
            time.sleep(_DELAY_S)
        return total
