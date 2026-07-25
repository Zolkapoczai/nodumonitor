"""
SearchProvider adapter — a halott Google CSE potlasa.

Elozmeny: a `search_connector.py` a Google Custom Search JSON API-ra epult, amit
a Google 2026-ban lezart uj ugyfelek elol (elesben verifikalva 403-mal), ezert
2026-07-20-an kikerult. A 01-es audit §5/§10 ide `SearchProvider` interfeszt kert,
mogotte cserelheto szolgaltatoval.

**Miert Brave** (a 02-es audit §5 dontese): ma is self-serve regisztralhato (nem
"uj ugyfeleknek zarva" — pont ez oltre meg a CSE-t), sajat, fuggetlen index, es
nem SERP-scraping-proxy, tehat nem ismetli meg a Khoros-403 tipusu jogi/technikai
torekenyseget. A valos igeny (napi 10-20 query) belefer a legalacsonyabb szintbe.

**Masik provider hozzaadasa** (pl. Serper.dev, Exa): szarmaztass a
`SearchProvider`-bol, implementald a `search()`-et `SearchResult` listara, es
vedd fel a `_PROVIDERS` dict-be. A connector-oldalon semmit nem kell modositani.

FIGYELEM: a Brave valasz-mezonevei (`web.results[].title/url/description/age`)
kulcs nelkul nem voltak elesben verifikalhatok. Az elso eles futasnal ezt
ellenorizni kell; a parser vedve van a hianyzo mezok ellen (`.get()`), tehat
rossz esetben 0 talalatot ad, nem all le.
"""
from dataclasses import dataclass

import requests


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    published: str = ""


class SearchProvider:
    """Kereso-szolgaltato interfesz. Egy metodus, szandekosan."""

    name = "base"

    def __init__(self, api_key: str, options: dict = None):
        self.api_key = api_key
        self.options = options or {}

    def search(self, query: str, count: int = 20) -> list[SearchResult]:
        raise NotImplementedError


class BraveSearchProvider(SearchProvider):
    name = "brave"
    _URL = "https://api.search.brave.com/res/v1/web/search"
    _MAX_COUNT = 20  # a Brave API felso korlatja egy keresre

    def search(self, query: str, count: int = 20) -> list[SearchResult]:
        params = {"q": query, "count": min(count, self._MAX_COUNT)}
        # freshness: pd=nap, pw=het, pm=honap, py=ev. A monitoringhoz a "pm"
        # jo default: a friss fajdalom erdekes, a 3 eves thread nem.
        freshness = self.options.get("freshness", "pm")
        if freshness:
            params["freshness"] = freshness
        if self.options.get("search_lang"):
            params["search_lang"] = self.options["search_lang"]

        try:
            resp = requests.get(
                self._URL,
                params=params,
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": self.api_key,
                },
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[search:brave] API hiba ('{query}'): {e}")
            return []

        results = []
        for item in (data.get("web") or {}).get("results", []) or []:
            url = item.get("url", "")
            if not url:
                continue
            results.append(SearchResult(
                title=item.get("title", "") or "",
                url=url,
                snippet=item.get("description", "") or "",
                published=item.get("page_age", "") or item.get("age", "") or "",
            ))
        return results


_PROVIDERS: dict[str, type[SearchProvider]] = {
    "brave": BraveSearchProvider,
}


def build_provider(name: str, api_key: str, options: dict = None) -> SearchProvider | None:
    """Provider-peldany a config alapjan. None, ha nincs kulcs vagy ismeretlen a nev."""
    cls = _PROVIDERS.get((name or "").lower())
    if cls is None:
        print(f"[search] Ismeretlen provider: '{name}'. Elerheto: {', '.join(sorted(_PROVIDERS))}")
        return None
    if not api_key:
        return None
    return cls(api_key, options)
