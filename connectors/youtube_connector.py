"""
YouTube Data API Connector — oktatóvideók és webinar kommentek figyeléséhez.

Két, 2026-07-24-én javított hiba (ld. docs/02-lead-volume-audit-2026-07.md §3.5):

1. Az `external_id` a VIDEÓ azonosítója volt, nem a kommenté. Mivel a `posts`
   táblán `UNIQUE(platform, external_id)` van, videónként pontosan EGY komment
   került be, a többi (max. 19) csendben eldobódott `IntegrityError`-ral —
   megkülönböztethetetlenül egy valódi duplikátumtól. ~95% kiesés.

2. Nem volt kulcsszó-kapu, ellentétben az összes többi connectorral: minden
   komment bekerült `score >= 1`-gyel, így a classifier Gemini-hívásokat költött
   "Parametric Wall Art" típusú videócímekre (13 jelből 1 volt valódi fájdalom).

A kapu a KOMMENT szövegére szűr, nem a videócímre — különben egy releváns
címmel bíró videó összes kommentje bejönne. Aki tényleges adatcsere-fájdalmat
ír le, az szinte mindig megnevezi az eszközt vagy a formátumot. Ha kiderül,
hogy ez túl szigorú, a videócím-egyezés visszaengedése itt egy sor.
"""
import time
from datetime import datetime, timezone
from googleapiclient.discovery import build

from env_secrets import get_secret
from filters.keyword_filter import KeywordFilter
from storage.db import insert_post, log_run


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class YouTubeConnector:
    def __init__(self, config: dict, db_path: str):
        self.config = config
        self.db_path = db_path
        self.yc = config.get("youtube", {})
        self.kf = KeywordFilter(config)
        # env / .env elsobbseggel (ld. env_secrets.py) — a kulcs ne a config.yaml
        # plain textjeben eljen, mert az git-tracked.
        self.api_key = get_secret("YOUTUBE_API_KEY", self.yc.get("api_key"))

    def run(self) -> int:
        if not self.api_key or self.api_key == "YOUR_YOUTUBE_API_KEY":
            print("[youtube] API kulcs nincs megadva, kihagyva.")
            return 0

        started = _now()
        error_msg = None
        saved = 0
        seen = 0

        try:
            youtube = build("youtube", "v3", developerKey=self.api_key)
            queries = self.yc.get("search_queries", ["Revit Archicad IFC"])
            max_videos = self.yc.get("max_videos_per_query", 5)
            max_comments = self.yc.get("max_comments_per_video", 20)

            for query in queries:
                try:
                    search_response = youtube.search().list(
                        q=query,
                        part="id,snippet",
                        type="video",
                        order="relevance",
                        maxResults=max_videos
                    ).execute()

                    for item in search_response.get("items", []):
                        video_id = (item.get("id") or {}).get("videoId")
                        if not video_id:
                            continue
                        video_title = (item.get("snippet") or {}).get("title", "")

                        try:
                            comments_response = youtube.commentThreads().list(
                                part="snippet",
                                videoId=video_id,
                                maxResults=max_comments,
                                order="time"
                            ).execute()

                            for ct in comments_response.get("items", []):
                                snippet = (ct.get("snippet") or {}).get("topLevelComment", {}).get("snippet", {})
                                author = snippet.get("authorDisplayName", "")
                                body = snippet.get("textOriginal", "")
                                published_at = snippet.get("publishedAt", "")
                                comment_id = ct.get("id", "")
                                seen += 1

                                # Kulcsszo-kapu a KOMMENT szovegere (ld. modul-docstring).
                                keywords, _ = self.kf.match(body)
                                if not keywords:
                                    continue
                                # A pontszamot a videocimmel egyutt szamoljuk: a cim
                                # valodi relevancia-kontextus, csak kapunak nem jo.
                                _, score = self.kf.match(f"{video_title} {body}")

                                post = {
                                    "source": "youtube",
                                    "platform": "youtube",
                                    # Komment-ID, NEM video-ID — kulonben videonkent
                                    # csak egy komment fer be (UNIQUE(platform, external_id)).
                                    "external_id": f"yt_{comment_id}" if comment_id else f"yt_{video_id}",
                                    "url": f"https://www.youtube.com/watch?v={video_id}",
                                    "author": author,
                                    "title": video_title,
                                    "body": body[:2000],
                                    "created_at": published_at or _now(),
                                    "fetched_at": _now(),
                                    "keywords": ", ".join(keywords),
                                    "score": score,
                                }
                                if insert_post(self.db_path, post):
                                    saved += 1
                        except Exception as ce:
                            print(f"[youtube] Komment hiba ({video_id}): {ce}")

                except Exception as qe:
                    print(f"[youtube] Keresési hiba ({query}): {qe}")

        except Exception as e:
            error_msg = str(e)
            print(f"[youtube] HIBA: {e}")

        log_run(
            self.db_path,
            connector="youtube",
            started_at=started,
            finished_at=_now(),
            new_posts=saved,
            error=error_msg,
            items_seen=seen,
        )
        print(f"[youtube] {saved} új bejegyzés mentve ({seen} komment átvizsgálva)")
        return saved

    def search(self, query: str, search_term: str = None) -> int:
        """Ad-hoc keresés YouTube videók kommentjeiben a megadott kifejezésre."""
        if not self.api_key or self.api_key == "YOUR_YOUTUBE_API_KEY":
            print("[youtube] Ad-hoc keresés: Nincs API kulcs megadva.")
            return 0

        term = search_term or query
        saved = 0
        try:
            youtube = build("youtube", "v3", developerKey=self.api_key)
            search_response = youtube.search().list(
                q=query,
                part="id,snippet",
                type="video",
                order="relevance",
                maxResults=5
            ).execute()

            for item in search_response.get("items", []):
                video_id = (item.get("id") or {}).get("videoId")
                if not video_id:
                    continue
                video_title = (item.get("snippet") or {}).get("title", "")

                try:
                    comments_response = youtube.commentThreads().list(
                        part="snippet",
                        videoId=video_id,
                        maxResults=10,
                        order="relevance"
                    ).execute()

                    for ct in comments_response.get("items", []):
                        snippet = (ct.get("snippet") or {}).get("topLevelComment", {}).get("snippet", {})
                        author = snippet.get("authorDisplayName", "")
                        body = snippet.get("textOriginal", "")
                        published_at = snippet.get("publishedAt", "")
                        comment_id = ct.get("id", "")

                        combined = f"{video_title} {body}"
                        keywords, score = self.kf.match(combined)
                        post = {
                            "source": "youtube",
                            "platform": "youtube",
                            # Komment-ID (ld. run()); ad-hoc keresesnel szandekosan
                            # NINCS kulcsszo-kapu — ott a query maga a szuro.
                            "external_id": f"yt_adhoc_{comment_id or video_id}",
                            "url": f"https://www.youtube.com/watch?v={video_id}",
                            "author": author,
                            "title": video_title,
                            "body": body[:2000],
                            "created_at": published_at or _now(),
                            "fetched_at": _now(),
                            "keywords": ", ".join(keywords) if keywords else "youtube",
                            "score": max(score, 1),
                            "search_term": term,
                        }
                        if insert_post(self.db_path, post):
                            saved += 1
                except Exception as ce:
                    pass
        except Exception as e:
            print(f"[youtube] Ad-hoc hiba ({query}): {e}")

        print(f"[youtube] Ad-hoc '{query}': {saved} új komment mentve")
        return saved
