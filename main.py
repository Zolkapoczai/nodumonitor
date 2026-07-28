"""
NODU Bridge Community Monitor

Futtatás:
    python main.py                  # egyszeri futás (minden connector)
    python main.py --reddit         # csak Reddit
    python main.py --forums         # Khoros/phpBB fórumok HTML scraping
    python main.py --playwright     # JS-alapú fórumok (Graphisoft/Autodesk Community)
    python main.py --stackoverflow  # Stack Overflow / Stack Exchange
    python main.py --discourse      # buildingSMART forum (Discourse API)
    python main.py --vanilla        # OSArch community (Vanilla Forums API)
    python main.py --zendesk        # Graphisoft support KB (Zendesk Help Center API)
    python main.py --github         # GitHub issues (IfcOpenShell, Speckle, xeokit)
    python main.py --classify       # Pain Classifier: LLM-osztályozás a meglévő posztokon
    python main.py --review-signals # osztályozott jelek kézi kiértékelő riportja
    python main.py --digest         # napi összefoglaló + n8n webhook küldése
    python main.py --generate-drafts  # Gemini API valasz-javaslatok generálása
    python main.py --review         # pending draft-ok áttekintése (interaktív CLI)
    python main.py --linkedin-content # heti LinkedIn poszt-javaslatok (Slack-re)
    python main.py --weekly-report  # heti Slack-összefoglaló (források, fájdalompontok)
    python main.py --health         # connector-egészség riport (néma hibák felderítése)
    python main.py --backup         # adatbázis-snapshot most (backups/, 7 napos rotáció)
    python main.py --schedule       # ütemezett futás (APScheduler)
    python main.py --test-rss       # RSS feed elérhetőség tesztelése
"""
import argparse
import sys
import os
import yaml
from datetime import datetime, timedelta, timezone

# A Windows konzol alapertelmezett kodlapja (pl. cp1250) nem tud minden
# Unicode karaktert abrazolni (pl. forumcimekben elofordulo "²", japan
# szoveg) — ez enelkul UnicodeEncodeError-ral OSSZEOMLASZTJA a folyamatot
# egy sima print() hivasnal (2026-07-20-i eles hiba a classifier-batchnel).
# A nem abrazolhato karaktereket helyettesitjuk, nem eldobjuk a futast.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(errors="replace")

sys.path.insert(0, os.path.dirname(__file__))

from env_secrets import get_secret
from storage.db import init_db, mark_alerted, get_weekly_stats
from connectors.html_connector import HTMLConnector
from alerts.notifier import send_alerts, send_weekly_digest, send_content_pipeline_ideas
from responder.draft_generator import generate_drafts, review_drafts, generate_content_pipeline


def load_config() -> dict:
    cfg_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(cfg_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_reddit(config: dict, db_path: str) -> int:
    try:
        from connectors.reddit_connector import RedditConnector, resolve_credentials
        client_id, client_secret = resolve_credentials(config)
        if not client_id or not client_secret:
            print(
                "[reddit] Nincs beállítva API kulcs. Kihagy. "
                "(REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET a projekt .env-jébe, "
                "vagy config.yaml -> reddit)"
            )
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


def run_vanilla(config: dict, db_path: str) -> int:
    try:
        from connectors.vanilla_connector import VanillaConnector
        connector = VanillaConnector(config, db_path)
        n = connector.run()
        return n
    except Exception as e:
        print(f"[vanilla] HIBA: {e}")
        return 0


def run_zendesk(config: dict, db_path: str) -> int:
    try:
        from connectors.zendesk_connector import ZendeskConnector
        connector = ZendeskConnector(config, db_path)
        n = connector.run()
        return n
    except Exception as e:
        print(f"[zendesk] HIBA: {e}")
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


def run_websearch(config: dict, db_path: str) -> int:
    try:
        from connectors.web_search_connector import WebSearchConnector
        return WebSearchConnector(config, db_path).run()
    except Exception as e:
        print(f"[websearch] HIBA: {e}")
        return 0


def run_youtube(config: dict, db_path: str) -> int:
    try:
        from connectors.youtube_connector import YouTubeConnector
        connector = YouTubeConnector(config, db_path)
        n = connector.run()
        return n
    except Exception as e:
        print(f"[youtube] HIBA: {e}")
        return 0


def run_classify(config: dict, db_path: str, batch_size: int = None) -> int:
    from classifier.pain_classifier import PainClassifier
    classifier = PainClassifier(config, db_path)
    return classifier.run(batch_size=batch_size)


def run_health_check(config: dict, db_path: str) -> list[dict]:
    """
    Connector-heartbeat: felderiti a nema hibakat (eltort szelektor, halott API,
    hianyzo kulcs) es riaszt. A `new_posts=0` magaban NEM hiba — csak az, ha a
    connector 0 NYERS elemet lat, vagy minden futasa kivetellel all le.
    Ld. docs/02-lead-volume-audit-2026-07.md §3.11.
    """
    from storage.db import get_connector_health
    from alerts.notifier import send_health_alert

    hc = config.get("health", {})
    window = hc.get("window", 5)
    ignore = set(hc.get("ignore", ["classifier"]))

    # Az ELVART connectorok (mikor kellett volna futniuk) ugyanabbol a tablabol
    # jonnek, amibol az utemezo dolgozik — igy a HIANYZO futas is latszik, nem
    # csak a rossz (docs/04-rendszer-audit-2026-07-28.md §2.2).
    expected = {e["name"]: e["interval"] for e in connector_schedule(config)
                if e.get("expect_runs", True)}

    report = get_connector_health(db_path, window=window,
                                  active_within_hours=hc.get("active_within_hours", 24),
                                  expected=expected,
                                  stale_factor=hc.get("stale_factor", 3.0))
    problems = [r for r in report
                if r["status"] in ("error", "blind", "stale") and r["connector"] not in ignore]

    print(f"[health] {len(report)} connector vizsgalva (ablak: {window} futas, "
          f"{len(expected)} utemezett).")
    for r in report:
        mark = {"ok": "OK   ", "blind": "VAK  ", "error": "HIBA ", "stale": "NEM FUT",
                "unknown": "?    "}.get(r["status"], "?    ")
        seen = "n/a" if r["items_seen_in_window"] is None else r["items_seen_in_window"]
        print(f"  {mark} {r['connector']:16} elem={seen:>5} uj={r['new_posts_in_window']:>4} ({r['runs_considered']} futas)")

    if not problems:
        return []

    # stderr -> a server.py ezt ERROR szinten naplozza, igy a logban is kiugrik
    # akkor is, ha egyetlen riasztasi csatorna sincs bekapcsolva.
    print(
        f"[health] FIGYELEM: {len(problems)} connector nem termel: "
        + ", ".join(f"{p['connector']}({p['status']})" for p in problems),
        file=sys.stderr,
    )
    delivered = send_health_alert(problems, config.get("alerts", {}))
    if delivered:
        print(f"[health] Riasztas elkuldve: {', '.join(delivered)}")
    else:
        print("[health] Nem ment ki riasztas (nincs bekapcsolt csatorna).", file=sys.stderr)
    return problems


def run_backup(config: dict, db_path: str) -> str | None:
    """
    DB-snapshot, `runs`-bejegyzessel.

    Miert naplozzuk: a napi backup 2026-07-25/26/27-en NEM futott (a szerver allt a
    03:30-as cron idejen, a memorias jobstore pedig nem potolja), es EZ SEHOL NEM
    TUNT FEL — se `runs`-sor, se health-ag nem volt ra. `keep: 7` rotacio igy soha
    nem is aktivalodott (docs/04-rendszer-audit-2026-07-28.md §2.3). A `runs`-sorral
    a heartbeat 'stale'-kent latja a kimaradast, es a `--health` kiirja.
    """
    from storage.backup import backup_db
    from storage.db import log_run
    keep = config.get("backup", {}).get("keep", 7)
    started = datetime.now(tz=timezone.utc).isoformat()
    path = None
    error = None
    try:
        path = backup_db(db_path, keep=keep)
        if not path:
            error = "a backup_db nem adott vissza utvonalat"
    except Exception as e:
        error = str(e)[:300]
    try:
        # items_seen=1: "latott munkat" — igy a heartbeat nem minositi 'blind'-nak
        # (a 0 nyers elem ott a szelektor-toresek jele).
        log_run(db_path, "backup", started, datetime.now(tz=timezone.utc).isoformat(),
                new_posts=1 if path else 0, error=error, items_seen=1)
    except Exception as e:
        print(f"[backup] A futas naplozasa nem sikerult: {e}")
    if error:
        print(f"[backup] HIBA: {error}", file=sys.stderr)
    return path


def run_digest(config: dict, db_path: str) -> None:
    """
    Napi osszefoglalo — a Pain Classifier JELEIRE epul, nem a nyers kulcsszo-
    score-ra.

    Korabban a `min_keyword_matches: 1` kuszob miatt gyakorlatilag MINDEN
    begyujtott elem "relevansnak" szamitott (pl. "Parametric Wall Art" YouTube-
    komment), es a `signals` tabla — a rendszer agya — teljesen ki volt hagyva az
    ertesitesi utbol. Most csak valodi fajdalom-jel (is_pain vagy nodu_mention)
    kerul be, `alerts.digest_min_severity` kuszob felett, es csak olyan poszt,
    amit meg nem riasztottunk ki. Ld. docs/02-lead-volume-audit-2026-07.md §3.6c.
    """
    from storage.db import get_opportunities

    from storage.db import count_opportunities

    digest_started = datetime.now(tz=timezone.utc).isoformat()
    ac = config.get("alerts", {})
    min_sev = ac.get("digest_min_severity", 3)

    # A statusz-szures az SQL-BEN van (post_status='new'), es a limitet a VALODI
    # darabszambol szamoljuk. Korabban a hivas limit nelkul ment (default 100), a
    # 'new' szurés pedig Pythonban futott a mar levagott listan — es mivel a
    # rendezes severity szerinti, nem ido szerinti, a mar 'alerted' sorok sosem
    # estek ki a halmazbol, tehat a 100-as hatar monoton lejjebb tolodott.
    # Meres (2026-07-28): 35 varakozo jelbol a digest 3-at latott, 32 STRANDOLT —
    # es strukturalisan sosem kerult volna sorra
    # (docs/04-rendszer-audit-2026-07-28.md §1.2).
    pending = count_opportunities(db_path, only_pain=True, min_severity=min_sev,
                                  post_status="new")
    opportunities = get_opportunities(db_path, only_pain=True, min_severity=min_sev,
                                      post_status="new", limit=max(pending, 1))

    if len(opportunities) < pending:
        # Ez ma nem fordulhat elo (a limit a szamlalobol jon), de ha egy jovobeli
        # valtozas megis csonkol, azt NE csendben tegye.
        print(f"[digest] FIGYELEM: {pending} varakozo jel kozul csak "
              f"{len(opportunities)} kerult a listaba.", file=sys.stderr)

    relevant = [{
        **o,
        "id": o["post_id"],
        "score": o.get("keyword_score", 0),
        "created_at": o.get("post_created_at", ""),
    } for o in opportunities]

    print(f"\nNapi osszefoglalo: {len(relevant)} fajdalom-jel (severity >= {min_sev})\n")
    for p in relevant[:20]:
        print(f"  [{p['platform']}] sev={p.get('severity')} intent={p.get('buying_intent')} {p.get('title', '')[:60]}")
        print(f"    {p.get('pain_summary') or '(nincs osszefoglalo)'}")
        print(f"    {p.get('url', '')}\n")

    delivered = send_alerts(relevant, config.get("alerts", {}))

    # A posztot CSAK akkor "fogyasztjuk el" (status: new -> alerted), ha a
    # riasztas tenylegesen kiment valahova. Korabban ez feltetel nelkul futott,
    # igy letiltott csatornak mellett a talalatok csendben eltuntek a 'new'
    # szurokbol anelkul, hogy barki latta volna oket
    # (ld. docs/02-lead-volume-audit-2026-07.md §3.6).
    if relevant and delivered:
        mark_alerted(db_path, [p["id"] for p in relevant])
        print(f"[digest] {len(relevant)} talalat 'alerted'-re allitva (kikuldve: {', '.join(delivered)}).")
    elif relevant:
        print(f"[digest] {len(relevant)} talalat 'new' statuszban MARAD (nem ment ki riasztas).")

    # A digest futasa is bekerul a `runs`-ba, hogy a heartbeat eszrevegye, ha egy
    # napon EL SEM INDULT (ugyanaz az ok, mint a backupnal — §2.3). A 0 kikuldott
    # jel NEM hiba: lehet, hogy nem volt mit kuldeni.
    try:
        from storage.db import log_run
        # items_seen=1 = "a job lefutott", NEM a varakozo jelek szama. A 0 nyers
        # elem a connectoroknal szelektor-torest jelent ('blind'), egy napi
        # cron-jobnal viszont teljesen normalis allapot, hogy nincs mit kuldeni —
        # ha ide `pending`-et irnank, 5 csendes nap utan a heartbeat HAMIS
        # 'blind' riasztast adna. A varakozo jelek szama a `new_posts`-ban van.
        log_run(db_path, "digest", digest_started,
                datetime.now(tz=timezone.utc).isoformat(),
                new_posts=len(relevant),
                error=None if (delivered or not relevant) else "nem ment ki riasztas",
                items_seen=1)
    except Exception as e:
        print(f"[digest] A futas naplozasa nem sikerult: {e}")


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

# Az elso futasok szetteritese ujraindulas utan: az i-edik job legalabb
# i * 20 masodperccel kesobb indul, hogy ne toduljon egyszerre 11 connector.
_STARTUP_STAGGER_SECONDS = 20


class _FirstRunPlanner:
    """
    Mikor fusson egy interval-job ELSO alkalommal a szerver indulasa utan?

    A valasz NEM "azonnal". Korabban mind a 11 job `next_run_time=now`-val
    regisztralt, ezert MINDEN szerver-ujrainditas teljes kimeno rajtaütest jelentett:
    meres 2026-07-27 19:00-22:00 kozott **71 futas** a varhato ~9 helyett; a napi
    egyszeri websearch aznap 12-szer futott (132 Brave-query), a 720 perces zendesk
    8-szor. A `poll_interval_minutes` igy latszolag hatott, valojaban csak a futasok
    kozti minimumot adta (docs/04-rendszer-audit-2026-07-28.md §2.5).

    Most a `runs` tabla utolso futasabol szamolunk: a kovetkezo esedekesseg
    `utolso_futas + interval`. Ha az mar elmult (vagy soha nem futott), akkor
    indulunk hamar — de szettertve, hogy ne egyszerre.
    """

    def __init__(self, db_path: str):
        from storage.db import get_last_run_times
        try:
            self._last = get_last_run_times(db_path)
        except Exception as e:
            print(f"[utemezo] Az utolso futasok nem olvashatok ({e}) — azonnali inditas.")
            self._last = {}
        self._n = 0

    def next_run(self, run_name: str, interval_minutes: int) -> datetime:
        now = datetime.now(tz=timezone.utc)
        self._n += 1
        soon = now + timedelta(seconds=self._n * _STARTUP_STAGGER_SECONDS)

        raw = self._last.get(run_name)
        if not raw:
            return soon
        try:
            last = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
        except ValueError:
            return soon

        due = last + timedelta(minutes=max(interval_minutes, 1))
        return due if due > soon else soon


def connector_schedule(config: dict) -> list[dict]:
    """
    Melyik connector fut, milyen periodussal — EGY IGAZSAG.

    Ezt olvassa (a) a `register_jobs`, amikor jobot regisztral, es (b) a
    `run_health_check`, amikor azt vizsgalja, hogy egy connector EGYALTALAN
    futott-e. Korabban a heartbeat csak a `runs` tablabol epitette a listat, ezert
    ami nem futott, az nem is szerepelt a riportban → `problems=[]` → HTTP 200.
    Meres (2026-07-28): 5 connector (reddit, revitforum, autodesk, graphisoft,
    search) igy volt lathatatlan, nulla riasztassal — a §4/6-os hibaosztaly
    visszatert, csak most a heartbeaten belulrol
    (docs/04-rendszer-audit-2026-07-28.md §2.2).

    A `name` a `runs.connector` ertekevel egyezik (a forumoknal a forum neve),
    kulonben a heartbeat nem talalna meg a futasokat.
    """
    # A reddit kulcs nelkul KIHAGYJA magat, es igy `runs`-sort sem ir — ezert
    # `expect_runs: False`, kulonben orokre 'stale' lenne, es a /health tartos
    # hamis 503-at adna. (§7/B: a kulcs jovahagyasra var; a tartalmat addig a
    # Brave-kereso potolja.) Ha a kulcs bekerul a .env-be, ez automatikusan
    # atvalt True-ra, es a heartbeat elvarja a futasokat.
    reddit_ready = bool(get_secret("REDDIT_CLIENT_ID",
                                   config.get("reddit", {}).get("client_id"))
                        and get_secret("REDDIT_CLIENT_SECRET",
                                       config.get("reddit", {}).get("client_secret")))
    entries: list[dict] = [
        {"name": "reddit", "interval": config.get("reddit", {}).get("poll_interval_minutes", 60),
         "expect_runs": reddit_ready},
        {"name": "playwright", "interval": config.get("playwright", {}).get("poll_interval_minutes", 90)},
        {"name": "discourse", "interval": config.get("discourse", {}).get("poll_interval_minutes", 240)},
        {"name": "github", "interval": config.get("github", {}).get("poll_interval_minutes", 240)},
        {"name": "youtube", "interval": config.get("youtube", {}).get("poll_interval_minutes", 180)},
        {"name": "classifier", "interval": config.get("classifier", {}).get("poll_interval_minutes", 60)},
    ]
    # `enabled` kapcsolos connectorok. A stackoverflow 2026-07-28-tol itt van, mert
    # `enabled: false`-ra allt (audit §3.6: 1887 nyers elem -> 5 poszt -> 0 jel).
    for key, name, default in (("vanilla", "vanilla", 240),
                               ("zendesk", "zendesk", 720),
                               ("stackoverflow", "stackoverflow", 180),
                               ("web_search", "websearch", 720)):
        section = config.get(key, {}) or {}
        if section.get("enabled", True):
            entries.append({"name": name,
                            "interval": section.get("poll_interval_minutes", default)})
    # HTML-forumok: a `forums` szekcio ma ures ({}), de ha visszakerul egy forum,
    # automatikusan bekerul az utemezobe ES a heartbeat latokorebe is.
    for fname, fcfg in (config.get("forums", {}) or {}).items():
        entries.append({"name": fname,
                        "interval": (fcfg or {}).get("poll_interval_minutes", 120),
                        "forum_config": fcfg})

    # NEM connectorok, de utemezett munkak, amiknek a KIMARADASA is hiba: a napi
    # backup 2026-07-25/26/27-en elmaradt, es semmi nem jelezte (§2.3). `cron_only`:
    # a register_jobs sajat cron-jobkent regisztralja oket, itt csak a heartbeat
    # szamara szerepelnek.
    if (config.get("backup", {}) or {}).get("enabled", True):
        entries.append({"name": "backup", "interval": 1440, "cron_only": True})
    if (config.get("alerts", {}) or {}).get("daily_digest", True):
        entries.append({"name": "digest", "interval": 1440, "cron_only": True})
    return entries


def register_jobs(scheduler, config: dict, db_path: str) -> None:
    """Job-regisztráció közösen a CLI (--schedule) és a server.py számára."""
    planner = _FirstRunPlanner(db_path)

    # A connector-jobok EGY tablabol regisztralodnak (connector_schedule), amit a
    # heartbeat is olvas — igy nem lehet olyan connector, ami fut, de a
    # heartbeat nem szamit ra (vagy forditva). Ld. §2.2 az auditban.
    runners = {
        "reddit": run_reddit,
        "playwright": run_playwright,
        "stackoverflow": run_stackoverflow,
        "discourse": run_discourse,
        "vanilla": run_vanilla,
        "zendesk": run_zendesk,
        "github": run_github,
        "youtube": run_youtube,
        "websearch": run_websearch,
        "classifier": run_classify,
    }

    for entry in connector_schedule(config):
        name, interval = entry["name"], entry["interval"]
        if entry.get("cron_only"):
            continue   # backup/digest: lentebb, sajat cron-jobkent
        if entry.get("forum_config") is not None:
            fn = (lambda n=name, c=entry["forum_config"]:
                  HTMLConnector(n, c, config, db_path).run())
            job_id = f"forum_{name}"
        else:
            runner = runners.get(name)
            if runner is None:
                print(f"[utemezo] Nincs futtato a '{name}' connectorhoz — kihagyva.")
                continue
            fn = (lambda r=runner: r(config, db_path))
            job_id = name
        scheduler.add_job(
            fn,
            "interval",
            minutes=interval,
            id=job_id,
            next_run_time=planner.next_run(name, interval),
        )

    digest_hour = config.get("alerts", {}).get("digest_hour", 8)
    scheduler.add_job(
        lambda: run_digest(config, db_path),
        "cron",
        hour=digest_hour,
        minute=0,
        id="digest",
    )

    # Valasz-draftok: a classifier fajdalom-jeleire (severity >= draft_min_severity)
    # generalunk javaslatot, hogy a dashboardon dontesre KESZ elemek varjanak. Az
    # emberi kapu tovabbra is a JOVAHAGYASNAL van, nem a generalasnal — korabban
    # viszont ez a lepes egyaltalan nem volt utemezve, ezert a DB-ben osszesen 1
    # draft keletkezett (ld. docs/02-lead-volume-audit-2026-07.md §3.12).
    rc_draft = config.get("responder", {})
    if rc_draft.get("auto_generate", True):
        scheduler.add_job(
            lambda: generate_drafts(config, db_path),
            "cron",
            hour=rc_draft.get("hour", 7),
            minute=30,
            id="generate_drafts",
        )

    # Connector-heartbeat: a nema hibak felderitese (§3.11).
    hc = config.get("health", {})
    if hc.get("enabled", True):
        scheduler.add_job(
            lambda: run_health_check(config, db_path),
            "interval",
            hours=hc.get("check_interval_hours", 6),
            id="health",
            next_run_time=datetime.now(tz=timezone.utc) + timedelta(minutes=5),
        )

    # Napi DB-snapshot rotacioval. Kozvetlenul a digest ELOTT fut, hogy a
    # statuszvaltasok (new -> alerted) elotti allapot is meglegyen.
    bc = config.get("backup", {})
    if bc.get("enabled", True):
        scheduler.add_job(
            lambda: run_backup(config, db_path),
            "cron",
            hour=bc.get("hour", 3),
            minute=30,
            id="backup",
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
    vn_interval = config.get("vanilla", {}).get("poll_interval_minutes", 240)
    gh_interval = config.get("github", {}).get("poll_interval_minutes", 240)
    yt_interval = config.get("youtube", {}).get("poll_interval_minutes", 180)
    cl_interval = config.get("classifier", {}).get("poll_interval_minutes", 60)
    digest_hour = config.get("alerts", {}).get("digest_hour", 8)
    wr = config.get("weekly_report", {})
    lines = [
        f"Reddit: {reddit_interval} perc | PW: {pw_interval} perc | SO: {so_interval} perc "
        f"| Disc: {dc_interval} perc | Van: {vn_interval} perc "
        f"| Git: {gh_interval} perc | YT: {yt_interval} perc "
        f"| Class: {cl_interval} perc",
        f"Napi digest: {digest_hour}:00",
    ]
    if wr.get("enabled", True):
        lines.append(f"Heti riport: {wr.get('day_of_week', 'mon')} {wr.get('hour', 8)}:00")
    rd = config.get("responder", {})
    if rd.get("auto_generate", True):
        lines.append(f"Draft-generalas: {rd.get('hour', 7)}:30")
    hc = config.get("health", {})
    if hc.get("enabled", True):
        lines.append(f"Health-check: {hc.get('check_interval_hours', 6)} orankent")
    bc = config.get("backup", {})
    if bc.get("enabled", True):
        lines.append(f"DB-backup: {bc.get('hour', 3)}:30 (megtartva {bc.get('keep', 7)} db)")
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
    parser.add_argument("--vanilla",          action="store_true", help="OSArch community (Vanilla Forums API)")
    parser.add_argument("--zendesk",          action="store_true", help="Graphisoft support KB (Zendesk Help Center API)")
    parser.add_argument("--github",           action="store_true", help="GitHub issues (IfcOpenShell, Speckle, xeokit)")
    parser.add_argument("--youtube",          action="store_true", help="YouTube kommentek lekérése")
    parser.add_argument("--websearch",        action="store_true", help="Web-kereses (SearchProvider: Brave)")
    parser.add_argument("--classify",         action="store_true", help="Pain Classifier: LLM-osztalyozas a meglevo posztokon")
    parser.add_argument("--review-signals",   action="store_true", help="Osztalyozott jelek kezi kiertekelo riportja")
    parser.add_argument("--digest",           action="store_true", help="Napi összefoglaló + n8n webhook")
    parser.add_argument("--generate-drafts",  action="store_true", help="Gemini API valasz-javaslatok generálása")
    parser.add_argument("--review",           action="store_true", help="Pending draft-ok interaktív áttekintése")
    parser.add_argument("--linkedin-content", action="store_true", help="Heti LinkedIn poszt-javaslatok (Slack-re)")
    parser.add_argument("--weekly-report",    action="store_true", help="Heti Slack-összefoglaló")
    parser.add_argument("--health",           action="store_true", help="Connector-egeszseg riport (nema hibak felderitese)")
    parser.add_argument("--backup",           action="store_true", help="Adatbazis-snapshot keszitese most")
    parser.add_argument("--schedule",         action="store_true", help="Ütemezett futás")
    parser.add_argument("--test-rss",         action="store_true", help="RSS/URL elérhetőség teszt")
    parser.add_argument("--test-slack",       action="store_true", help="Slack-webhook teszt (a valodi riasztasi uton)")
    parser.add_argument("--calibrate",        type=int, metavar="N", default=None,
                        help="N mar osztalyozott poszt UJRAERTEKELESE a mai prompttal, paros osszevetes (a DB nem valtozik)")
    args = parser.parse_args()

    config = load_config()
    db_path = os.path.join(os.path.dirname(__file__), config.get("database", {}).get("path", "nodu_monitor.db"))
    init_db(db_path)
    print(f"Adatbazis: {db_path}")

    if args.test_rss:
        test_rss_feeds(config)
        return

    if args.test_slack:
        from alerts.notifier import send_slack_test
        sys.exit(0 if send_slack_test(config.get("alerts", {})) else 1)

    if args.calibrate:
        from classifier.pain_classifier import calibrate
        calibrate(config, db_path, limit=args.calibrate)
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

    if args.health:
        run_health_check(config, db_path)
        return

    if args.backup:
        path = run_backup(config, db_path)
        print(f"[backup] {'Kesz: ' + path if path else 'Nem sikerult.'}")
        return

    if args.schedule:
        run_scheduled(config, db_path)
        return

    if args.digest:
        run_digest(config, db_path)
        return

    any_flag = (
        args.reddit or args.forums or args.playwright or args.stackoverflow
        or args.discourse or args.vanilla or args.zendesk or args.github
        or args.youtube or args.websearch
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

    if args.vanilla or not any_flag:
        if config.get("vanilla", {}).get("enabled", True):
            run_vanilla(config, db_path)

    if args.zendesk or not any_flag:
        if config.get("zendesk", {}).get("enabled", True):
            run_zendesk(config, db_path)

    if args.github or not any_flag:
        run_github(config, db_path)

    if args.youtube or not any_flag:
        run_youtube(config, db_path)

    if args.websearch or not any_flag:
        run_websearch(config, db_path)

    run_digest(config, db_path)


if __name__ == "__main__":
    main()
