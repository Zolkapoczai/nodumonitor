"""
NODU Bridge Community Monitor

Futtatás:
    python main.py                  # egyszeri futás (minden connector)
    python main.py --reddit         # csak Reddit
    python main.py --forums         # Khoros/phpBB fórumok HTML scraping
    python main.py --playwright     # JS-alapú fórumok (Graphisoft/Autodesk Community)
    python main.py --stackoverflow  # Stack Overflow / Stack Exchange
    python main.py --discourse      # buildingSMART forum (Discourse API)
    python main.py --github         # GitHub issues (IfcOpenShell, Speckle, xeokit)
    python main.py --classify       # Pain Classifier: LLM-osztályozás a meglévő posztokon
    python main.py --review-signals # osztályozott jelek kézi kiértékelő riportja
    python main.py --digest         # napi összefoglaló + n8n webhook küldése
    python main.py --generate-drafts  # Gemini API valasz-javaslatok generálása
    python main.py --review         # pending draft-ok áttekintése (interaktív CLI)
    python main.py --linkedin-content # heti LinkedIn poszt-javaslatok (Slack-re)
    python main.py --weekly-report  # heti Slack-összefoglaló (források, fájdalompontok)
    python main.py --schedule       # ütemezett futás (APScheduler)
    python main.py --test-rss       # RSS feed elérhetőség tesztelése
"""
import argparse
import sys
import os
import yaml
from datetime import datetime, timezone

# A Windows konzol alapertelmezett kodlapja (pl. cp1250) nem tud minden
# Unicode karaktert abrazolni (pl. forumcimekben elofordulo "²", japan
# szoveg) — ez enelkul UnicodeEncodeError-ral OSSZEOMLASZTJA a folyamatot
# egy sima print() hivasnal (2026-07-20-i eles hiba a classifier-batchnel).
# A nem abrazolhato karaktereket helyettesitjuk, nem eldobjuk a futast.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(errors="replace")

sys.path.insert(0, os.path.dirname(__file__))

from storage.db import init_db, get_new_posts, mark_alerted, get_weekly_stats
from connectors.html_connector import HTMLConnector
from alerts.notifier import send_alerts, send_weekly_digest, send_content_pipeline_ideas
from responder.draft_generator import generate_drafts, review_drafts, generate_content_pipeline


def load_config() -> dict:
    cfg_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(cfg_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_reddit(config: dict, db_path: str) -> int:
    try:
        from connectors.reddit_connector import RedditConnector
        rc = config.get("reddit", {})
        if not rc.get("client_id") or rc["client_id"] == "YOUR_REDDIT_CLIENT_ID":
            print("[reddit] Nincs beállítva API kulcs. Kihagy.")
            return 0
        connector = RedditConnector(config, db_path)
        n = connector.run()
        print(f"[reddit] {n} uj bejegyzes")
        return n
    except ImportError:
        print("[reddit] praw nincs telepítve (pip install praw)")
        return 0
    except Exception as e:
        print(f"[reddit] HIBA: {e}")
        return 0


def run_rss_forums(config: dict, db_path: str) -> int:
    forums = config.get("forums", {})
    total = 0
    for name, forum_cfg in forums.items():
        connector = HTMLConnector(
            name=name,
            forum_config=forum_cfg,
            config=config,
            db_path=db_path,
        )
        n = connector.run()
        print(f"[{name}] {n} uj bejegyzes")
        total += n
    return total


def run_playwright(config: dict, db_path: str) -> int:
    try:
        from connectors.playwright_connector import PlaywrightConnector
        connector = PlaywrightConnector(config, db_path)
        n = connector.run()
        print(f"[playwright] összesen {n} uj bejegyzes")
        return n
    except Exception as e:
        print(f"[playwright] HIBA: {e}")
        return 0


def run_stackoverflow(config: dict, db_path: str) -> int:
    try:
        from connectors.stackoverflow_connector import StackOverflowConnector
        connector = StackOverflowConnector(config, db_path)
        n = connector.run()
        return n
    except Exception as e:
        print(f"[stackoverflow] HIBA: {e}")
        return 0


def run_discourse(config: dict, db_path: str) -> int:
    try:
        from connectors.discourse_connector import DiscourseConnector
        connector = DiscourseConnector(config, db_path)
        n = connector.run()
        return n
    except Exception as e:
        print(f"[discourse] HIBA: {e}")
        return 0


def run_github(config: dict, db_path: str) -> int:
    try:
        from connectors.github_connector import GitHubConnector
        connector = GitHubConnector(config, db_path)
        n = connector.run()
        return n
    except Exception as e:
        print(f"[github] HIBA: {e}")
        return 0


def run_youtube(config: dict, db_path: str) -> int:
    try:
        from connectors.youtube_connector import poll_youtube
        from storage.db import filter_and_save_posts
        posts = poll_youtube(config)
        if not posts:
            return 0
        n = filter_and_save_posts(db_path, posts, config.get("alerts", {}).get("min_keyword_matches", 1))
        return n
    except ImportError as e:
        print(f"[youtube] Függőségi hiba: {e}")
        return 0
    except Exception as e:
        print(f"[youtube] HIBA: {e}")
        return 0


def run_classify(config: dict, db_path: str, batch_size: int = None) -> int:
    from classifier.pain_classifier import PainClassifier
    classifier = PainClassifier(config, db_path)
    return classifier.run(batch_size=batch_size)


def run_digest(config: dict, db_path: str) -> None:
    posts = get_new_posts(db_path)
    min_matches = config.get("alerts", {}).get("min_keyword_matches", 1)
    relevant = [p for p in posts if p.get("score", 0) >= min_matches]

    print(f"\nNapi osszefoglalo: {len(relevant)} releváns bejegyzes\n")
    for p in relevant[:20]:
        print(f"  [{p['platform']}] {p.get('title', '')[:70]}")
        print(f"    Score: {p['score']} | Keywords: {p.get('keywords', '')}")
        print(f"    {p.get('url', '')}\n")

    send_alerts(relevant, config.get("alerts", {}))

    if relevant:
        mark_alerted(db_path, [p["id"] for p in relevant])


def run_linkedin_content(config: dict, db_path: str) -> int:
    posts = generate_content_pipeline(config, db_path)
    if posts:
        send_content_pipeline_ideas(posts, config.get("alerts", {}))
    return len(posts) if posts else 0


def run_weekly_report(config: dict, db_path: str) -> None:
    from responder.draft_generator import generate_trend_analysis
    days = config.get("weekly_report", {}).get("lookback_days", 7)
    stats = get_weekly_stats(db_path, days)
    trend = generate_trend_analysis(config, db_path)
    send_weekly_digest(stats, config.get("alerts", {}), trend_analysis=trend)
    print(f"[weekly] {stats['total_posts']} uj poszt, {stats['pending_drafts']} pending draft az utolso {days} napban.")


def test_rss_feeds(config: dict) -> None:
    """Ellenőrzi, hogy az RSS URL-ek elérhetők-e."""
    import requests
    forums = config.get("forums", {})
    print("RSS feed elérhetőség teszt:\n")
    for name, forum_cfg in forums.items():
        rss_url = forum_cfg.get("rss_url", "")
        try:
            resp = requests.get(rss_url, timeout=10, headers={"User-Agent": forum_cfg.get("user_agent", "NODU/0.1")})
            status = resp.status_code
            content_type = resp.headers.get("Content-Type", "")
            print(f"  {name}: HTTP {status} | {content_type[:60]}")
            if status == 200 and ("xml" in content_type or "rss" in content_type or "atom" in content_type):
                print(f"    OK: RSS elérhető")
            elif status == 200:
                print(f"    FIGYELEM: HTTP 200 de nem XML content-type. Ellenőrizd kézzel.")
            else:
                print(f"    HIBA: HTTP {status}")
        except Exception as e:
            print(f"  {name}: HIBA - {e}")
    print()


# Egy job csak egyszer fusson egyszerre; kimaradt futásokat összevonjuk.
JOB_DEFAULTS = {"coalesce": True, "max_instances": 1, "misfire_grace_time": 300}


def register_jobs(scheduler, config: dict, db_path: str) -> None:
    """Job-regisztráció közösen a CLI (--schedule) és a server.py számára."""
    reddit_interval = config.get("reddit", {}).get("poll_interval_minutes", 60)
    scheduler.add_job(
        lambda: run_reddit(config, db_path),
        "interval",
        minutes=reddit_interval,
        id="reddit",
        next_run_time=datetime.now(tz=timezone.utc),
    )

    forums = config.get("forums", {})
    for name, forum_cfg in forums.items():
        interval = forum_cfg.get("poll_interval_minutes", 120)
        _name = name
        _cfg = forum_cfg
        scheduler.add_job(
            lambda n=_name, c=_cfg: HTMLConnector(n, c, config, db_path).run(),
            "interval",
            minutes=interval,
            id=f"forum_{name}",
            next_run_time=datetime.now(tz=timezone.utc),
        )

    pw_interval = config.get("playwright", {}).get("poll_interval_minutes", 90)
    scheduler.add_job(
        lambda: run_playwright(config, db_path),
        "interval",
        minutes=pw_interval,
        id="playwright",
        next_run_time=datetime.now(tz=timezone.utc),
    )

    so_interval = config.get("stackoverflow", {}).get("poll_interval_minutes", 180)
    scheduler.add_job(
        lambda: run_stackoverflow(config, db_path),
        "interval",
        minutes=so_interval,
        id="stackoverflow",
        next_run_time=datetime.now(tz=timezone.utc),
    )

    discourse_interval = config.get("discourse", {}).get("poll_interval_minutes", 240)
    scheduler.add_job(
        lambda: run_discourse(config, db_path),
        "interval",
        minutes=discourse_interval,
        id="discourse",
        next_run_time=datetime.now(tz=timezone.utc),
    )

    github_interval = config.get("github", {}).get("poll_interval_minutes", 240)
    scheduler.add_job(
        lambda: run_github(config, db_path),
        "interval",
        minutes=github_interval,
        id="github",
        next_run_time=datetime.now(tz=timezone.utc),
    )

    youtube_interval = config.get("youtube", {}).get("poll_interval_minutes", 180)
    scheduler.add_job(
        lambda: run_youtube(config, db_path),
        "interval",
        minutes=youtube_interval,
        id="youtube",
        next_run_time=datetime.now(tz=timezone.utc),
    )

    digest_hour = config.get("alerts", {}).get("digest_hour", 8)
    scheduler.add_job(
        lambda: run_digest(config, db_path),
        "cron",
        hour=digest_hour,
        minute=0,
        id="digest",
    )

    wr = config.get("weekly_report", {})
    if wr.get("enabled", True):
        scheduler.add_job(
            lambda: run_weekly_report(config, db_path),
            "cron",
            day_of_week=wr.get("day_of_week", "mon"),
            hour=wr.get("hour", 8),
            minute=5,
            id="weekly_report",
        )

    lc = config.get("linkedin_content", {})
    if lc.get("enabled", True):
        scheduler.add_job(
            lambda: run_linkedin_content(config, db_path),
            "cron",
            day_of_week=wr.get("day_of_week", "mon"),
            hour=wr.get("hour", 8),
            minute=15,
            id="linkedin_content",
        )


def describe_schedule(config: dict) -> str:
    reddit_interval = config.get("reddit", {}).get("poll_interval_minutes", 60)
    pw_interval = config.get("playwright", {}).get("poll_interval_minutes", 90)
    so_interval = config.get("stackoverflow", {}).get("poll_interval_minutes", 180)
    dc_interval = config.get("discourse", {}).get("poll_interval_minutes", 240)
    gh_interval = config.get("github", {}).get("poll_interval_minutes", 240)
    yt_interval = config.get("youtube", {}).get("poll_interval_minutes", 180)
    digest_hour = config.get("alerts", {}).get("digest_hour", 8)
    wr = config.get("weekly_report", {})
    lines = [
        f"Reddit: {reddit_interval} perc | PW: {pw_interval} perc | SO: {so_interval} perc "
        f"| Disc: {dc_interval} perc | Git: {gh_interval} perc | YT: {yt_interval} perc",
        f"Napi digest: {digest_hour}:00",
    ]
    if wr.get("enabled", True):
        lines.append(f"Heti riport: {wr.get('day_of_week', 'mon')} {wr.get('hour', 8)}:00")
    return " | ".join(lines)


def run_scheduled(config: dict, db_path: str) -> None:
    from apscheduler.schedulers.blocking import BlockingScheduler

    scheduler = BlockingScheduler(job_defaults=JOB_DEFAULTS)
    register_jobs(scheduler, config, db_path)
    print(f"Utemező elindítva. {describe_schedule(config)}")
    print("Ctrl+C a leállításhoz.")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("Leállítás.")


def main():
    parser = argparse.ArgumentParser(description="NODU Bridge Community Monitor")
    parser.add_argument("--reddit",           action="store_true", help="Csak Reddit")
    parser.add_argument("--forums",           action="store_true", help="Khoros/phpBB HTML scraping")
    parser.add_argument("--playwright",       action="store_true", help="JS-alapú fórumok (Playwright/Chromium)")
    parser.add_argument("--stackoverflow",    action="store_true", help="Stack Overflow / Stack Exchange")
    parser.add_argument("--discourse",        action="store_true", help="buildingSMART forum (Discourse API)")
    parser.add_argument("--github",           action="store_true", help="GitHub issues (IfcOpenShell, Speckle, xeokit)")
    parser.add_argument("--youtube",          action="store_true", help="YouTube kommentek lekérése")
    parser.add_argument("--classify",         action="store_true", help="Pain Classifier: LLM-osztalyozas a meglevo posztokon")
    parser.add_argument("--review-signals",   action="store_true", help="Osztalyozott jelek kezi kiertekelo riportja")
    parser.add_argument("--digest",           action="store_true", help="Napi összefoglaló + n8n webhook")
    parser.add_argument("--generate-drafts",  action="store_true", help="Gemini API valasz-javaslatok generálása")
    parser.add_argument("--review",           action="store_true", help="Pending draft-ok interaktív áttekintése")
    parser.add_argument("--linkedin-content", action="store_true", help="Heti LinkedIn poszt-javaslatok (Slack-re)")
    parser.add_argument("--weekly-report",    action="store_true", help="Heti Slack-összefoglaló")
    parser.add_argument("--schedule",         action="store_true", help="Ütemezett futás")
    parser.add_argument("--test-rss",         action="store_true", help="RSS/URL elérhetőség teszt")
    args = parser.parse_args()

    config = load_config()
    db_path = os.path.join(os.path.dirname(__file__), config.get("database", {}).get("path", "nodu_monitor.db"))
    init_db(db_path)
    print(f"Adatbazis: {db_path}")

    if args.test_rss:
        test_rss_feeds(config)
        return

    if args.generate_drafts:
        n = generate_drafts(config, db_path)
        print(f"[responder] {n} draft generálva")
        return

    if args.review:
        review_drafts(db_path)
        return

    if args.classify:
        run_classify(config, db_path)
        return

    if args.review_signals:
        from classifier.pain_classifier import review_signals
        review_signals(db_path)
        return

    if args.linkedin_content:
        n = run_linkedin_content(config, db_path)
        print(f"[linkedin] {n} poszt-javaslat")
        return

    if args.weekly_report:
        run_weekly_report(config, db_path)
        return

    if args.schedule:
        run_scheduled(config, db_path)
        return

    if args.digest:
        run_digest(config, db_path)
        return

    any_flag = (
        args.reddit or args.forums or args.playwright or args.stackoverflow
        or args.discourse or args.github or args.youtube
    )

    if args.reddit or not any_flag:
        run_reddit(config, db_path)

    if args.forums or not any_flag:
        run_rss_forums(config, db_path)

    if args.playwright or not any_flag:
        run_playwright(config, db_path)

    if args.stackoverflow or not any_flag:
        run_stackoverflow(config, db_path)

    if args.discourse or not any_flag:
        run_discourse(config, db_path)

    if args.github or not any_flag:
        run_github(config, db_path)

    if args.youtube or not any_flag:
        run_youtube(config, db_path)

    run_digest(config, db_path)


if __name__ == "__main__":
    main()
