"""
YouTube Data API Connector — oktatóvideók és webinar kommentek figyeléséhez.
"""
import time
from datetime import datetime, timezone
from googleapiclient.discovery import build

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
        self.api_key = self.yc.get("api_key", "")

    def run(self) -> int:
        if not self.api_key or self.api_key == "YOUR_YOUTUBE_API_KEY":
            print("[youtube] API kulcs nincs megadva, kihagyva.")
            return 0

        started = _now()
        error_msg = None
        saved = 0

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
                        order="date",
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

                                combined = f"{video_title} {body}"
                                keywords, score = self.kf.match(combined)
                                
                                post = {
                                    "source": "youtube",
                                    "platform": "youtube",
                                    "external_id": f"yt_{comment_id}",
                                    "url": f"https://www.youtube.com/watch?v={video_id}&lc={comment_id}",
                                    "author": author,
                                    "title": f"Comment on: {video_title}",
                                    "body": body[:2000],
                                    "created_at": published_at or _now(),
                                    "fetched_at": _now(),
                                    "keywords": ", ".join(keywords) if keywords else "youtube",
                                    "score": max(score, 1),
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
        )
        print(f"[youtube] {saved} új bejegyzés mentve")
        return saved
