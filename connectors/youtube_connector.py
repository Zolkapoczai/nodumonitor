import os
from datetime import datetime, timezone
from googleapiclient.discovery import build

def poll_youtube(config: dict) -> list[dict]:
    """
    YouTube API hívás konfigurált kulcsszavakra és kommentek letöltése.
    """
    yc = config.get("youtube", {})
    api_key = yc.get("api_key")
    if not api_key or api_key == "YOUR_YOUTUBE_API_KEY":
        print("[youtube] API kulcs nincs megadva, kihagyva.")
        return []

    try:
        youtube = build("youtube", "v3", developerKey=api_key)
    except Exception as e:
        print(f"[youtube] API init hiba: {e}")
        return []

    queries = yc.get("search_queries", ["Revit Archicad IFC"])
    max_videos = yc.get("max_videos_per_query", 5)
    max_comments = yc.get("max_comments_per_video", 20)

    posts = []
    
    for query in queries:
        try:
            # 1. Keresés videókra
            search_response = youtube.search().list(
                q=query,
                part="id,snippet",
                type="video",
                order="date", # legújabbak előre
                maxResults=max_videos
            ).execute()
            
            for item in search_response.get("items", []):
                video_id = item["id"]["videoId"]
                video_title = item["snippet"]["title"]
                
                # 2. Kommentek lekérése
                try:
                    comments_response = youtube.commentThreads().list(
                        part="snippet",
                        videoId=video_id,
                        maxResults=max_comments,
                        order="time"
                    ).execute()
                    
                    for ct in comments_response.get("items", []):
                        top_comment = ct["snippet"]["topLevelComment"]["snippet"]
                        author = top_comment["authorDisplayName"]
                        text = top_comment["textOriginal"]
                        published_at = top_comment["publishedAt"]
                        comment_id = ct["id"]
                        
                        try:
                            # YouTube format: 2024-05-23T12:00:00Z
                            dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                            dt_str = dt.astimezone(timezone.utc).isoformat()
                        except:
                            dt_str = datetime.now(timezone.utc).isoformat()
                            
                        posts.append({
                            "platform": "youtube",
                            "source_id": f"yt_{comment_id}",
                            "title": f"Comment on: {video_title}",
                            "body": text,
                            "url": f"https://www.youtube.com/watch?v={video_id}&lc={comment_id}",
                            "author": author,
                            "created_at": dt_str
                        })
                except Exception as ce:
                    # Lehet hogy a kommentek ki vannak kapcsolva a videon
                    print(f"[youtube] Nem sikerült lekérni a kommenteket ({video_id}): {ce}")
                    
        except Exception as e:
            print(f"[youtube] Keresési hiba ({query}): {e}")

    print(f"[youtube] Összesen {len(posts)} komment letöltve.")
    return posts
