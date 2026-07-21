"""
Ad-hoc (eseti) kereses koordinator.

A sales dashboardrol indithato: egy beirt kifejezesre fut minden valasztott
csatornan, es a talalatok search_term-mel jelolve kerulnek az adatbazisba.
A connectorok search() metodusait hasznalja (run() helyett).

Csatornak (a felhasznalo szemszogebol):
  reddit         -> Reddit nativ kereses (PRAW subreddit 'all' search)
  stackoverflow  -> Stack Exchange nativ kereses

A korabbi 'linkedin' es 'forums' csatorna a Google Custom Search API-ra
epult; a Google 2026-ban lezarta ezt az API-t uj ugyfelek elol (ld.
docs/01-architektura-audit-2026-07.md), ezert kikerult. A forum-tartalom
ezentul a playwright_connector utemezett futasabol jon — tudatosan nem
on-demand (ad-hoc), mert a gyakori, keresesenkenti Khoros-hivas novelne a
bot-vedelmi kockazatot (ld. audit 11. Kockazatok).
"""
from connectors.stackoverflow_connector import StackOverflowConnector

_DEFAULT_CHANNELS = ["youtube", "github", "reddit", "stackoverflow"]


def run_adhoc_search(config: dict, db_path: str, query: str, channels: list[str] = None) -> dict:
    """
    Lefuttatja az ad-hoc keresést a választott csatornákon.
    Visszaad: {"query": ..., "channels": {csatorna: találat-szám}, "total": ...}.
    """
    query = (query or "").strip()
    if not query:
        return {"query": "", "channels": {}, "total": 0}

    adhoc_cfg = config.get("adhoc", {})
    limit = adhoc_cfg.get("result_limit", 10)
    channels = channels or adhoc_cfg.get("default_channels", _DEFAULT_CHANNELS)
    per_channel: dict[str, int] = {}

    if "youtube" in channels:
        try:
            from connectors.youtube_connector import YouTubeConnector
            yt = YouTubeConnector(config, db_path)
            per_channel["youtube"] = yt.search(query, search_term=query)
        except Exception as e:
            print(f"[adhoc] YouTube hiba: {e}")

    if "github" in channels:
        try:
            from connectors.github_connector import GitHubConnector
            gh = GitHubConnector(config, db_path)
            per_channel["github"] = gh.search(query, search_term=query)
        except Exception as e:
            print(f"[adhoc] GitHub hiba: {e}")

    if "reddit" in channels:
        try:
            from connectors.reddit_connector import RedditConnector
            rc = RedditConnector(config, db_path)
            per_channel["reddit"] = rc.search(query, limit=max(limit, 25), search_term=query)
        except Exception as e:
            print(f"[adhoc] Reddit hiba: {e}")

    if "stackoverflow" in channels:
        try:
            from connectors.stackoverflow_connector import StackOverflowConnector
            so = StackOverflowConnector(config, db_path)
            per_channel["stackoverflow"] = so.search(query, search_term=query)
        except Exception as e:
            print(f"[adhoc] Stack Overflow hiba: {e}")

    total = sum(per_channel.values())
    print(f"[adhoc] '{query}': {total} találat ({per_channel})")
    return {"query": query, "channels": per_channel, "total": total}
