"""
GitHub Issues connector — fejlett BIM-eszkoz-fejlesztok fajdalmai elso kezbol.

A GitHub Search API (nyilt, hitelesites nelkul is mukodik, 10 keres/perc
korlattal — GITHUB_TOKEN-nel 30/perc) issue-kat keres a config-ban megadott
repo-kon. Cel-repok (2026-07-20-i felterkepezes, ld. docs/01-architektura-audit-2026-07.md):
  - IfcOpenShell/IfcOpenShell (az IfcOpenShell mag ES a Bonsai/BlenderBIM
    Blender-addon EGY monorepoban el — nincs kulon Bonsai-repo)
  - specklesystems/speckle-server
  - xeokit/xeokit-sdk

Dokumentacio: https://docs.github.com/en/rest/search/search#search-issues-and-pull-requests
"""
import time
from datetime import datetime, timezone

import requests

from filters.keyword_filter import KeywordFilter
from storage.db import insert_post, log_run

_SEARCH_URL = "https://api.github.com/search/issues"
_DELAY_S = 6.0  # hitelesites nelkul 10 keres/perc a limit — udvarias kozi szunet

_DEFAULT_REPOS = [
    "IfcOpenShell/IfcOpenShell",
    "specklesystems/speckle-server",
    "xeokit/xeokit-sdk",
]

_DEFAULT_QUERIES = [
    "archicad revit",
    "revit archicad",
    "archicad ifc export",
]


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class GitHubConnector:
    def __init__(self, config: dict, db_path: str):
        self.config = config
        self.db_path = db_path
        self.gh_config = config.get("github", {})
        self.kf = KeywordFilter(config)
        self.token = self.gh_config.get("token", "") or None

    def _headers(self) -> dict:
        h = {"User-Agent": "NODU-Bridge-Monitor/0.1", "Accept": "application/vnd.github+json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _search(self, query: str, repos: list[str]) -> list[dict]:
        repo_filter = " ".join(f"repo:{r}" for r in repos)
        params = {"q": f"{query} {repo_filter}", "per_page": 20, "sort": "updated", "order": "desc"}
        try:
            resp = requests.get(_SEARCH_URL, params=params, headers=self._headers(), timeout=15)
            resp.raise_for_status()
            return resp.json().get("items", [])
        except Exception as e:
            print(f"[github] API hiba: {e}")
            return []

    def _save(self, items: list[dict], search_term: str = None, require_keywords: bool = True) -> int:
        saved = 0
        for item in items:
            title = item.get("title", "")
            body = item.get("body") or ""
            repo_name = item.get("repository_url", "").split("/repos/")[-1]

            combined = f"{title} {body}"
            keywords, score = self.kf.match(combined)
            if require_keywords and not keywords:
                continue

            post = {
                "source": "github",
                "platform": repo_name or "github",
                "external_id": str(item.get("id", item.get("html_url", ""))),
                "url": item.get("html_url", ""),
                "author": (item.get("user") or {}).get("login", ""),
                "title": title,
                "body": body[:2000],
                "created_at": item.get("created_at", "") or _now(),
                "fetched_at": _now(),
                "keywords": ", ".join(keywords),
                "score": score,
                "search_term": search_term,
            }
            if insert_post(self.db_path, post):
                saved += 1
        return saved

    def run(self) -> int:
        repos = self.gh_config.get("repos", _DEFAULT_REPOS)
        queries = self.gh_config.get("queries", _DEFAULT_QUERIES)
        total = 0
        started = _now()
        error_msg = None

        try:
            for query in queries:
                items = self._search(query, repos)
                total += self._save(items)
                time.sleep(_DELAY_S)
        except Exception as e:
            error_msg = str(e)
            print(f"[github] HIBA: {e}")

        log_run(
            self.db_path,
            connector="github",
            started_at=started,
            finished_at=_now(),
            new_posts=total,
            error=error_msg,
        )
        print(f"[github] {total} uj bejegyzes mentve")
        return total

    def search(self, query: str, search_term: str = None) -> int:
        """Ad-hoc kereses: a konfiguralt repo-kon egy kifejezesre."""
        repos = self.gh_config.get("repos", _DEFAULT_REPOS)
        term = search_term or query
        items = self._search(query, repos)
        return self._save(items, search_term=term, require_keywords=False)
