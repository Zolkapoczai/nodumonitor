"""
Általános RSS/Atom feed connector Graphisoft Community, Autodesk Community
és RevitForum.org forrásokhoz.
"""
import feedparser
import requests
from datetime import datetime, timezone
from filters.keyword_filter import KeywordFilter
from storage.db import insert_post, log_run


def _parse_date(entry) -> str:
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
    return datetime.now(tz=timezone.utc).isoformat()


class RSSConnector:
    def __init__(self, name: str, forum_config: dict, config: dict, db_path: str):
        self.name = name
        self.rss_url = forum_config["rss_url"]
        self.user_agent = forum_config.get("user_agent", "NODU-Monitor/0.1")
        self.db_path = db_path
        self.kf = KeywordFilter(config)

    def _fetch_feed(self) -> feedparser.FeedParserDict:
        headers = {"User-Agent": self.user_agent}
        resp = requests.get(self.rss_url, headers=headers, timeout=15)
        resp.raise_for_status()
        return feedparser.parse(resp.content)

    def run(self) -> int:
        started = datetime.now(tz=timezone.utc).isoformat()
        new_total = 0
        error_msg = None

        try:
            feed = self._fetch_feed()
            for entry in feed.entries:
                title = entry.get("title", "")
                summary = entry.get("summary", "") or entry.get("content", [{}])[0].get("value", "")
                text = f"{title} {summary}"
                keywords, score = self.kf.match(text)
                if not keywords:
                    continue

                url = entry.get("link", "")
                external_id = entry.get("id", url)

                record = {
                    "source": self.name,
                    "platform": self.name.lower().replace(" ", "_"),
                    "external_id": external_id[:500],
                    "url": url,
                    "author": entry.get("author", ""),
                    "title": title[:500],
                    "body": summary[:2000],
                    "created_at": _parse_date(entry),
                    "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
                    "keywords": ", ".join(keywords),
                    "score": score,
                }
                if insert_post(self.db_path, record):
                    new_total += 1

        except Exception as e:
            error_msg = str(e)
            print(f"[{self.name}] ERROR: {e}")

        log_run(
            self.db_path,
            connector=self.name,
            started_at=started,
            finished_at=datetime.now(tz=timezone.utc).isoformat(),
            new_posts=new_total,
            error=error_msg,
        )
        return new_total
