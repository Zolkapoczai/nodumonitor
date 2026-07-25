"""
Web-kereso connector — a `SearchProvider` adapter mogotti altalanos kereses.

Ez potolja a kivezetett Google CSE-t (`search_connector.py`). A szerepe NEM a
volumen: a merheto tortenetében a CSE 4 futas alatt 0 posztot termelt, mikozben a
Playwright 157-et (ld. docs/02-lead-volume-audit-2026-07.md §4/1). A szerepe a
**lefedettseg**: azok a forumok, blogok es Q&A-oldalak, amikre nincs sajat
connector — nemet/holland/skandinav BIM-kozossegek, Graphisoft-blogkommentek,
LinkedIn PUBLIKUS posztok (csak olvasas, kereson keresztul — scraping nelkul).

Kulcs nelkul csendben kihagyja magat, mint a tobbi connector. A kulcs env-bol
vagy `.env`-bol jon (BRAVE_API_KEY), NEM a config.yaml-bol — ld. env_secrets.py.
"""
from datetime import datetime, timezone

from env_secrets import get_secret
from filters.keyword_filter import KeywordFilter
from storage.db import insert_post, log_run

from connectors.search_provider import build_provider


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class WebSearchConnector:
    def __init__(self, config: dict, db_path: str):
        self.config = config
        self.db_path = db_path
        self.ws = config.get("web_search", {})
        self.kf = KeywordFilter(config)
        self.provider_name = self.ws.get("provider", "brave")
        key_env = self.ws.get("api_key_env", "BRAVE_API_KEY")
        self.api_key = get_secret(key_env, self.ws.get("api_key"))
        self.provider = build_provider(
            self.provider_name,
            self.api_key,
            {
                "freshness": self.ws.get("freshness", "pm"),
                "search_lang": self.ws.get("search_lang", ""),
            },
        )

    def _save(self, results, search_term: str = None, require_keywords: bool = True) -> int:
        saved = 0
        for r in results:
            combined = f"{r.title} {r.snippet}"
            keywords, score = self.kf.match(combined)
            if require_keywords and not keywords:
                continue
            post = {
                "source": f"websearch:{self.provider_name}",
                "platform": "websearch",
                # A URL a stabil azonosito: ugyanaz a talalat tobb query-n is
                # visszajohet, es a dedupnak ezt kell felismernie.
                "external_id": r.url[:500],
                "url": r.url,
                "author": "",
                "title": r.title[:500],
                "body": r.snippet[:2000],
                "created_at": r.published or _now(),
                "fetched_at": _now(),
                "keywords": ", ".join(keywords),
                "score": score,
                "search_term": search_term,
            }
            if insert_post(self.db_path, post):
                saved += 1
        return saved

    def run(self) -> int:
        if not self.ws.get("enabled", True):
            print("[websearch] Letiltva a configban.")
            return 0
        if self.provider is None:
            print(
                f"[websearch] Nincs API kulcs ({self.ws.get('api_key_env', 'BRAVE_API_KEY')}) "
                "— kihagyva. Kulcs: https://brave.com/search/api/"
            )
            return 0

        queries = self.ws.get("queries", [])
        count = self.ws.get("results_per_query", 20)
        total = 0
        total_seen = 0
        started = _now()
        error_msg = None

        try:
            for query in queries:
                results = self.provider.search(query, count=count)
                total_seen += len(results)
                total += self._save(results)
        except Exception as e:
            error_msg = str(e)
            print(f"[websearch] HIBA: {e}")

        log_run(
            self.db_path,
            connector="websearch",
            started_at=started,
            finished_at=_now(),
            new_posts=total,
            error=error_msg,
            items_seen=total_seen,
        )
        print(f"[websearch] {total} uj bejegyzes ({total_seen} talalat latva, provider: {self.provider_name})")
        return total

    def search(self, query: str, search_term: str = None) -> int:
        """Ad-hoc kereses a dashboardrol — itt a query maga a szuro."""
        if self.provider is None:
            print("[websearch] Ad-hoc: nincs API kulcs.")
            return 0
        results = self.provider.search(query, count=self.ws.get("results_per_query", 20))
        return self._save(results, search_term=search_term or query, require_keywords=False)
