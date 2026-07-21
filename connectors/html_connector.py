"""
HTML scraper Graphisoft Community, Autodesk Community és RevitForum forrásokhoz.

Stratégia: a Khoros keresési URL-ek és board listák HTML-jét parszolja.
Az RSS feed-ek ezeken a platformokon nem érhetők el publikusan.
"""
import requests
import time
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from filters.keyword_filter import KeywordFilter
from storage.db import insert_post, log_run

_DELAY_BETWEEN_REQUESTS = 3  # másodperc, hogy ne terheljük a szervert


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _make_session(user_agent: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    return s


def _safe_get(session: requests.Session, url: str, timeout: int = 15) -> BeautifulSoup | None:
    try:
        resp = session.get(url, timeout=timeout)
        if resp.status_code == 200:
            return BeautifulSoup(resp.text, "lxml")
        print(f"  HTTP {resp.status_code}: {url}")
        return None
    except Exception as e:
        print(f"  HIBA ({url}): {e}")
        return None


# ---------------------------------------------------------------------------
# Khoros (Lithium) board scraper
# Autodesk Community és Graphisoft Community egyaránt Khoros alapú.
# ---------------------------------------------------------------------------

def _parse_khoros_board(soup: BeautifulSoup, base_url: str) -> list[dict]:
    """
    Khoros board oldalból szedí ki a szálak adatait.
    A Khoros React SPA-vá alakult, de a statikus HTML-ben
    még megtalálhatók a szálak data- attribútumokban vagy
    strukturált listaelemekben.
    """
    results = []

    # Khoros jellemző szelektorok - próbáljuk meg a leggyakoribbakat
    selectors = [
        "li.lia-component-forums-widget-message-list-for-node",
        "div.MessageListForNodeByRecentActivityWidgetWrapper li",
        "article.message",
        "div.lia-message-item",
    ]

    items = []
    for sel in selectors:
        items = soup.select(sel)
        if items:
            break

    for item in items:
        title_el = (
            item.select_one("a.lia-link-navigation.lia-custom-event")
            or item.select_one("h3 a")
            or item.select_one("h2 a")
            or item.select_one(".lia-message-subject a")
        )
        if not title_el:
            continue

        title = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        if href.startswith("/"):
            href = base_url.rstrip("/") + href

        body_el = item.select_one(".lia-message-body-content, .message-content")
        body = body_el.get_text(" ", strip=True)[:500] if body_el else ""

        author_el = item.select_one(".UserName, .lia-user-name, .author")
        author = author_el.get_text(strip=True) if author_el else ""

        date_el = item.select_one("time, span.local-date")
        created_at = date_el.get("datetime", _now()) if date_el else _now()

        results.append({
            "title": title[:500],
            "url": href,
            "author": author,
            "body": body,
            "created_at": created_at,
            "external_id": href,
        })

    return results


def _parse_khoros_search(soup: BeautifulSoup, base_url: str) -> list[dict]:
    """
    Khoros keresési eredményoldal parszolása.
    A keresési eredmények struktúrája eltér a board listától.
    """
    results = []

    for item in soup.select("li.lia-search-result, div.search-result-item, article"):
        title_el = (
            item.select_one("a.lia-link-navigation")
            or item.select_one("h3 a")
            or item.select_one("h2 a")
        )
        if not title_el:
            continue

        title = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        if href.startswith("/"):
            href = base_url.rstrip("/") + href

        body_el = item.select_one(".search-content, .lia-message-body-content, p")
        body = body_el.get_text(" ", strip=True)[:500] if body_el else ""

        author_el = item.select_one(".UserName, .author, .lia-user-name")
        author = author_el.get_text(strip=True) if author_el else ""

        date_el = item.select_one("time, span.local-date")
        created_at = date_el.get("datetime", _now()) if date_el else _now()

        if title:
            results.append({
                "title": title[:500],
                "url": href,
                "author": author,
                "body": body,
                "created_at": created_at,
                "external_id": href,
            })

    return results


# ---------------------------------------------------------------------------
# phpBB (RevitForum) scraper
# ---------------------------------------------------------------------------

def _parse_phpbb_search(soup: BeautifulSoup, base_url: str) -> list[dict]:
    """phpBB keresési eredményoldal parszolása."""
    results = []

    for item in soup.select("li.bg1, li.bg2, dl.row, div.post"):
        title_el = (
            item.select_one("a.topictitle")
            or item.select_one("a[href*='viewtopic']")
            or item.select_one("dt a")
        )
        if not title_el:
            continue

        title = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        if href.startswith("."):
            href = base_url.rstrip("/") + "/" + href.lstrip("./")
        elif href.startswith("/"):
            href = base_url.rstrip("/") + href

        body_el = item.select_one("dd, .postbody, .search-result")
        body = body_el.get_text(" ", strip=True)[:500] if body_el else ""

        author_el = item.select_one(".username, .postauthor, .author")
        author = author_el.get_text(strip=True) if author_el else ""

        results.append({
            "title": title[:500],
            "url": href,
            "author": author,
            "body": body,
            "created_at": _now(),
            "external_id": href,
        })

    return results


# ---------------------------------------------------------------------------
# Fő connector osztály
# ---------------------------------------------------------------------------

class HTMLConnector:
    def __init__(self, name: str, forum_config: dict, config: dict, db_path: str):
        self.name = name
        self.base_url = forum_config["base_url"]
        self.search_urls = forum_config.get("search_urls", [])
        self.board_urls = forum_config.get("board_urls", [])
        self.db_path = db_path
        self.kf = KeywordFilter(config)
        self.session = _make_session(forum_config.get("user_agent", "NODU-Monitor/0.1"))

    def _process_items(self, items: list[dict]) -> int:
        new_count = 0
        for item in items:
            text = f"{item['title']} {item['body']}"
            keywords, score = self.kf.match(text)
            if not keywords:
                continue
            record = {
                "source": self.name,
                "platform": self.name.lower().replace(" ", "_"),
                "external_id": item["external_id"][:500],
                "url": item["url"],
                "author": item["author"],
                "title": item["title"],
                "body": item["body"],
                "created_at": item["created_at"],
                "fetched_at": _now(),
                "keywords": ", ".join(keywords),
                "score": score,
            }
            if insert_post(self.db_path, record):
                new_count += 1
        return new_count

    def run(self) -> int:
        started = _now()
        new_total = 0
        error_msg = None
        is_revitforum = "revitforum" in self.name.lower()

        try:
            # Keresési URL-ek feldolgozása
            for url in self.search_urls:
                soup = _safe_get(self.session, url)
                if soup:
                    if is_revitforum:
                        items = _parse_phpbb_search(soup, self.base_url)
                    else:
                        items = _parse_khoros_search(soup, self.base_url)
                    new_total += self._process_items(items)
                    print(f"  [{self.name}] search {url[-50:]}: {len(items)} elem")
                time.sleep(_DELAY_BETWEEN_REQUESTS)

            # Board listák feldolgozása
            for url in self.board_urls:
                soup = _safe_get(self.session, url)
                if soup:
                    if is_revitforum:
                        items = _parse_phpbb_search(soup, self.base_url)
                    else:
                        items = _parse_khoros_board(soup, self.base_url)
                    new_total += self._process_items(items)
                    print(f"  [{self.name}] board {url[-50:]}: {len(items)} elem")
                time.sleep(_DELAY_BETWEEN_REQUESTS)

        except Exception as e:
            error_msg = str(e)
            print(f"[{self.name}] HIBA: {e}")

        log_run(
            self.db_path,
            connector=self.name,
            started_at=started,
            finished_at=_now(),
            new_posts=new_total,
            error=error_msg,
        )
        return new_total
