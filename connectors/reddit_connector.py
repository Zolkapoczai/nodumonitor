import praw
from datetime import datetime, timezone

from env_secrets import get_secret
from filters.keyword_filter import KeywordFilter
from storage.db import insert_post, log_run


def resolve_credentials(config: dict) -> tuple[str, str]:
    """
    Reddit client_id/secret feloldasa: kornyezeti valtozo -> projekt `.env` ->
    config.yaml (ld. env_secrets.py). Ures string, ha nincs beallitva vagy
    placeholder maradt.

    Miert env: a Reddit-kulcs igy nem kerul a config.yaml plain textjebe (amit az
    admin UI vissza is ir), es a `.env` git-ignoralt. A hivo (main.run_reddit)
    ugyanezt a fuggvenyt hasznalja a "van-e kulcs" ellenorzesre, hogy a ket hely
    ne csuszhasson el egymastol.
    """
    rc = config.get("reddit", {})
    client_id = get_secret("REDDIT_CLIENT_ID", rc.get("client_id"))
    client_secret = get_secret("REDDIT_CLIENT_SECRET", rc.get("client_secret"))
    return client_id, client_secret


_FALLBACK_QUERIES = [
    "archicad revit", "revit archicad", "ifc conversion",
    "ifc export", "ifc import", "ifc interoperability",
]


class RedditConnector:
    def __init__(self, config: dict, db_path: str):
        rc = config["reddit"]
        client_id, client_secret = resolve_credentials(config)
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=rc["user_agent"],
        )
        self.subreddits = rc.get("subreddits", [])
        self.post_limit = rc.get("post_limit", 25)
        self.db_path = db_path
        self.kf = KeywordFilter(config)
        self.search_queries = self._build_queries(config, rc)

    @staticmethod
    def _build_queries(config: dict, rc: dict) -> list[str]:
        """
        Kereso-query-k. Ha a config nem ad explicit listat (`reddit.search_queries`),
        a `keywords.primary` + `keywords.pain_points` listabol epulnek — igy egy
        uj kulcsszo felvetele az Adminban AUTOMATIKUSAN uj Reddit-kereses is lesz,
        nem csak szuro. Korabban a lista a kodba volt egetve, 6 fix kifejezessel
        (ld. docs/02-lead-volume-audit-2026-07.md P2/15).
        """
        explicit = rc.get("search_queries")
        if explicit:
            return list(explicit)

        kw = config.get("keywords", {})
        limit = rc.get("max_search_queries", 12)
        seen: set[str] = set()
        queries: list[str] = []
        # Csak a tobbszavas kifejezesek jo kereso-query-k: az egyszavasak
        # ("nodu") tul szuk vagy tul altalanos talalati halmazt adnanak.
        for group in ("primary", "pain_points"):
            for term in kw.get(group, []):
                t = term.strip().lower()
                if len(t.split()) < 2 or t in seen:
                    continue
                seen.add(t)
                queries.append(t)
                if len(queries) >= limit:
                    return queries
        return queries or _FALLBACK_QUERIES

    def _ts(self, unix: float) -> str:
        return datetime.fromtimestamp(unix, tz=timezone.utc).isoformat()

    def run(self) -> int:
        started = datetime.now(tz=timezone.utc).isoformat()
        new_total = 0
        seen_total = 0
        error_msg = None

        try:
            for sub_name in self.subreddits:
                sub = self.reddit.subreddit(sub_name)

                # --- 1) Legfrissebb posztok listázása ---
                for submission in sub.new(limit=self.post_limit):
                    seen_total += 1
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
                        seen_total += 1
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

                # --- 2) Kulcsszó-alapú keresés az elmúlt 1 évben ---
                for sq in self.search_queries:
                    try:
                        for submission in sub.search(sq, sort="new", time_filter="year", limit=25):
                            seen_total += 1
                            text = f"{submission.title} {submission.selftext}"
                            keywords, score = self.kf.match(text)
                            if not keywords:
                                continue
                            record = {
                                "source": f"r/{sub_name} (search)",
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
                    except Exception:
                        pass

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
            items_seen=seen_total,
        )
        print(f"[reddit] {new_total} uj bejegyzes ({seen_total} elem atvizsgalva)")
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
