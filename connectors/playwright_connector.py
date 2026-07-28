"""
Playwright connector — JS-alapú Khoros SPA fórumok scraperje.

Szükséges:
    pip install playwright
    playwright install chromium

Khoros (Graphisoft Community, Autodesk Community) JavaScript Single Page App,
amit a BeautifulSoup nem tud feldolgozni. Ez a connector headless Chromium
böngészővel rendereli az oldalakat és kinyeri a posztokat.
"""
import re
from datetime import datetime, timezone

from connectors.khoros_url import canonical_external_id, canonical_thread_url
from filters.keyword_filter import KeywordFilter
from storage.db import insert_post, log_run


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _title_from_slug(href: str) -> str:
    """Kereso-talalatoknal a Khoros nem mindig ad kulon cim-elemet — a
    thread-URL szlugjabol (pl. /t5/.../ifc-from-archicad-to-revit/m-p/123)
    olvashato cimet keszitunk tartalek megoldaskent."""
    m = re.search(r"/([a-z0-9][a-z0-9-]{5,})/m-p/\d+", href)
    if not m:
        return ""
    return m.group(1).replace("-", " ").capitalize()


class PlaywrightConnector:
    def __init__(self, config: dict, db_path: str):
        self.config = config
        self.db_path = db_path
        self.pw_config = config.get("playwright", {})
        self.kf = KeywordFilter(config)

    def _dismiss_cookie_banner(self, page, banner_text: str) -> None:
        """Legjobb-igyekezet cookie-elutasitas: a legkevesbe adatgyujto opciot
        valasztja (pl. 'Decline' / 'Use necessary cookies only'). Nem hiba,
        ha nincs banner vagy nem talalja meg — csendben tovabbmegy."""
        if not banner_text:
            return
        try:
            page.get_by_text(banner_text, exact=False).first.click(timeout=4000, force=True)
        except Exception:
            pass

    def _scrape_forum(self, page, forum_name: str, forum_cfg: dict) -> tuple[int, int]:
        """Visszaad: (elmentett uj poszt, latott nyers elem). A masodik ertek a
        nema szelektor-toresek felderiteséhez kell (runs.items_seen)."""
        title_sel = forum_cfg.get("title_selector", ".lia-message-subject a")
        body_sel = forum_cfg.get("body_selector", ".lia-message-body-content")
        author_sel = forum_cfg.get("author_selector", ".lia-user-name-link")
        msg_sel = forum_cfg.get("message_selector", ".lia-message-item")
        cookie_text = forum_cfg.get("cookie_banner_text", "")
        timeout = self.pw_config.get("timeout_ms", 15000)

        saved = 0
        seen = 0
        for url in forum_cfg.get("search_urls", []):
            try:
                # wait_until="domcontentloaded", NEM "networkidle": a Khoros-SPA
                # folyamatos telemetria-kereseket kuld, ezert a halozat sosem lesz
                # "idle" — 2026-07-24-en emiatt futott bele a Graphisoft egyik
                # keresesi URL-je a 15 s-os limitbe, es maradt ki a korbol.
                # A tartalomra varunk a lenti wait_for_selector-ral, nem a
                # halozati csendre (ld. docs/02-lead-volume-audit-2026-07.md §3.1).
                page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                self._dismiss_cookie_banner(page, cookie_text)
                # state="attached": a Khoros-fórumok üzenetlistája gyakran
                # nem kerül "visible" allapotba (virtualizalt/rejtett konteiner),
                # de a szoveges tartalom mar jelen van a DOM-ban.
                page.wait_for_selector(msg_sel, timeout=timeout, state="attached")
                page.wait_for_timeout(1000)
            except Exception as e:
                print(f"  [{forum_name}] Timeout/hiba: {url[:60]} — {e}")
                continue

            items = page.query_selector_all(msg_sel)
            seen += len(items)
            if not items:
                print(f"  [{forum_name}] FIGYELEM: 0 elem a '{msg_sel}' szelektorral: {url[:70]}")
            for item in items:
                try:
                    title_el = item.query_selector(title_sel)
                    # Kereso-talalat-nezetben a Khoros nem mindig ad kulon
                    # cim-linket — ilyenkor a teljes elemet beburkolo linkre
                    # esunk vissza (a.lia-link-navigation), es a cimet a
                    # thread-URL szlugjabol szarmaztatjuk.
                    link_el = title_el or item.query_selector("a.lia-link-navigation") or item.query_selector("a[href]")
                    href = link_el.get_attribute("href") if link_el else ""
                    if href and not href.startswith("http"):
                        base = re.match(r"https?://[^/]+", url)
                        href = (base.group(0) if base else "") + href

                    title = title_el.inner_text().strip() if title_el else ""
                    if not title and href:
                        title = _title_from_slug(href)

                    body_el = item.query_selector(body_sel)
                    body = body_el.inner_text().strip() if body_el else ""

                    author_el = item.query_selector(author_sel)
                    author = author_el.inner_text().strip() if author_el else ""

                    # Try to extract real date from the post
                    date_el = item.query_selector("time, span.local-date, .DateTime, .lia-message-posted-on .local-date")
                    created_at = _now()
                    if date_el:
                        dt_attr = date_el.get_attribute("datetime") or date_el.get_attribute("data-time")
                        if dt_attr:
                            created_at = dt_attr
                        else:
                            date_text = date_el.inner_text().strip()
                            if date_text:
                                created_at = date_text  # fallback: raw text

                    combined = f"{title} {body}"
                    keywords, score = self.kf.match(combined)
                    if not keywords:
                        continue

                    # A dedup-kulcs KANONIZALT (khoros_url.py): a nyers href
                    # tartalmazza a futasonkent valtozo `search-action-id`-t, ezert
                    # a UNIQUE(platform, external_id) sosem fogott — 1309 poszt = 33
                    # valodi szal (docs/04-rendszer-audit-2026-07-28.md §1.1).
                    post = {
                        "source": "playwright",
                        "platform": forum_name,
                        "external_id": canonical_external_id(href) or href,
                        "url": canonical_thread_url(href) or url,
                        "author": author,
                        "title": title,
                        "body": body[:2000],
                        "created_at": created_at,
                        "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
                        "keywords": ", ".join(keywords),
                        "score": score,
                    }
                    if insert_post(self.db_path, post):
                        saved += 1
                except Exception:
                    continue

        return saved, seen

    def run(self) -> int:
        if not self.pw_config.get("enabled", True):
            print("[playwright] Letiltva a configban.")
            return 0

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("[playwright] Nincs telepítve: pip install playwright && playwright install chromium")
            return 0

        headless = self.pw_config.get("headless", True)
        forums = self.pw_config.get("forums", {})
        total = 0
        total_seen = 0
        started = _now()
        error_msg = None

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=headless)
                ctx = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/125.0.0.0 Safari/537.36"
                    )
                )
                page = ctx.new_page()

                for forum_name, forum_cfg in forums.items():
                    print(f"[playwright] Scraping: {forum_name}")
                    n, seen = self._scrape_forum(page, forum_name, forum_cfg)
                    print(f"[playwright] {forum_name}: {n} uj bejegyzes ({seen} elem latva)")
                    total += n
                    total_seen += seen

                browser.close()
        except Exception as e:
            error_msg = str(e)
            print(f"[playwright] HIBA: {e}")

        log_run(
            self.db_path,
            connector="playwright",
            started_at=started,
            finished_at=_now(),
            new_posts=total,
            error=error_msg,
            items_seen=total_seen,
        )
        return total
