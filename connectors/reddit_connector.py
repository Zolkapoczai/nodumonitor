import praw
from datetime import datetime, timezone
from filters.keyword_filter import KeywordFilter
from storage.db import insert_post, log_run


class RedditConnector:
    def __init__(self, config: dict, db_path: str):
        rc = config["reddit"]
        self.reddit = praw.Reddit(
            client_id=rc["client_id"],
            client_secret=rc["client_secret"],
            user_agent=rc["user_agent"],
        )
        self.subreddits = rc.get("subreddits", [])
        self.post_limit = rc.get("post_limit", 25)
        self.db_path = db_path
        self.kf = KeywordFilter(config)

    def _ts(self, unix: float) -> str:
        return datetime.fromtimestamp(unix, tz=timezone.utc).isoformat()

    def run(self) -> int:
        started = datetime.now(tz=timezone.utc).isoformat()
        new_total = 0
        error_msg = None

        try:
            for sub_name in self.subreddits:
                sub = self.reddit.subreddit(sub_name)
                for submission in sub.new(limit=self.post_limit):
                    text = f"{submission.title} {submission.selftext}"
                    keywords, score = self.kf.match(text)
                    if not keywords:
                        continue

                    record = {
                        "source": f"r/{sub_name}",
                        "platform": "reddit",
                        "external_id": submission.id,
                        "url": f"https://reddit.com{submission.permalink}",
                        "author": str(submission.author) if submission.author else "[deleted]",
                        "title": submission.title[:500],
                        "body": submission.selftext[:2000],
                        "created_at": self._ts(submission.created_utc),
                        "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
                        "keywords": ", ".join(keywords),
                        "score": score,
                    }
                    if insert_post(self.db_path, record):
                        new_total += 1

                # also scan top comments from recent posts
                for submission in sub.new(limit=10):
                    submission.comments.replace_more(limit=0)
                    for comment in submission.comments.list()[:20]:
                        body = comment.body or ""
                        keywords, score = self.kf.match(body)
                        if not keywords:
                            continue
                        record = {
                            "source": f"r/{sub_name} (comment)",
                            "platform": "reddit",
                            "external_id": f"c_{comment.id}",
                            "url": f"https://reddit.com{comment.permalink}",
                            "author": str(comment.author) if comment.author else "[deleted]",
                            "title": submission.title[:500],
                            "body": body[:2000],
                            "created_at": self._ts(comment.created_utc),
                            "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
                            "keywords": ", ".join(keywords),
                            "score": score,
                        }
                        if insert_post(self.db_path, record):
                            new_total += 1

        except Exception as e:
            error_msg = str(e)
            print(f"[reddit] ERROR: {e}")

        log_run(
            self.db_path,
            connector="reddit",
            started_at=started,
            finished_at=datetime.now(tz=timezone.utc).isoformat(),
            new_posts=new_total,
            error=error_msg,
        )
        return new_total

    def search(self, query: str, limit: int = 25, search_term: str = None) -> int:
        """
        Ad-hoc kereses az egesz Redditen tetszoleges kifejezesre (subreddit 'all').
        Minden talalatot ment (a query maga a szuro); a pontszam relevancia-jelzo.
        """
        term = search_term or query
        saved = 0
        try:
            for submission in self.reddit.subreddit("all").search(
                query, sort="new", time_filter="month", limit=limit
            ):
                text = f"{submission.title} {submission.selftext}"
                keywords, score = self.kf.match(text)
                record = {
                    "source": "reddit:search",
                    "platform": "reddit",
                    "external_id": submission.id,
                    "url": f"https://reddit.com{submission.permalink}",
                    "author": str(submission.author) if submission.author else "[deleted]",
                    "title": submission.title[:500],
                    "body": (submission.selftext or "")[:2000],
                    "created_at": self._ts(submission.created_utc),
                    "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
                    "keywords": ", ".join(keywords),
                    "score": score,
                    "search_term": term,
                }
                if insert_post(self.db_path, record):
                    saved += 1
        except Exception as e:
            print(f"[reddit] ad-hoc kereses hiba: {e}")
        return saved
