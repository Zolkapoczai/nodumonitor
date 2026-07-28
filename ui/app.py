"""
NODU Monitor - webes vezérlőpult
Indítás: python ui/app.py  (a nodu-monitor/ mappából)
Megnyitás: http://localhost:5050

Két nézet:
  /dashboard  - sales: áttekintő, ad-hoc kereső, találatok, választervezetek
  /admin      - technikai: API kulcsok, riasztások, kulcsszavak, monitor, állapot
                (opcionálisan jelszóval védve: config.yaml -> ui.admin_password)
"""
import os
import sqlite3
import sys
import threading
from datetime import datetime, timezone

import yaml
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
from storage.db import (
    init_db, get_pending_drafts, mark_draft, get_weekly_stats,
    get_adhoc_results, get_post, get_post_with_signal, get_opportunities,
    get_connector_health, count_opportunities, get_opportunity_platform_counts,
    get_decision_log,
)

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")

_jobs: dict = {}


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_config(config: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def get_db_path(config: dict) -> str:
    return os.path.join(BASE_DIR, config.get("database", {}).get("path", "nodu_monitor.db"))


def _stats(config: dict) -> dict:
    days = config.get("weekly_report", {}).get("lookback_days", 7)
    s = get_weekly_stats(get_db_path(config), days)
    s["pending_drafts"] = len(get_pending_drafts(get_db_path(config)))
    return s


def _run_in_bg(job_id: str, fn) -> bool:
    """
    Hatterszal egy connector-futashoz. False, ha MAR FUT — nem indit masodikat.

    Miert: a `/run/<action>` korabban minden kattintasra uj szalat inditott es a
    `_jobs[job_id]`-t felulirta, tehat ket kattintasra ugyanaz a connector ket
    peldanyban futott, UGYANABBAN a processzben — az APScheduler `max_instances=1`
    vedelmen KIVUL (docs/04-rendszer-audit-2026-07-28.md §2.6/6). A Playwrightnal
    ez ket parhuzamos Chromiumot es versenyzo DB-irast jelent.
    """
    if (_jobs.get(job_id) or {}).get("status") == "running":
        return False

    def _worker():
        _jobs[job_id] = {"status": "running"}
        try:
            result = fn()
            _jobs[job_id] = {"status": "done", "result": str(result)}
        except Exception as e:
            _jobs[job_id] = {"status": "error", "error": str(e)}
    threading.Thread(target=_worker, daemon=True).start()
    return True


def _admin_gate(config: dict):
    """
    Opcionalis jelszovedelem. None, ha szabad az atjaras.

    FONTOS: ezt MINDEN mutalo vegpont hivja (`/save`, `/run/<action>`,
    `/draft/*/approve|reject`, `/lead/*/to-sales-os`), nem csak az `/admin` HTML-
    nezet. Korabban egyetlen hivasi helye volt (`/admin` GET), tehat egy beallitott
    jelszo HAMIS BIZTONSAGERZETET adott: az admin oldal kerdezett, a
    `POST /save` (config.yaml felulirasa) es a `POST /run/playwright` nem
    (docs/04-rendszer-audit-2026-07-28.md §2.7). A reszleges kapu rosszabb, mint a
    nyilvanvaloan nyitott.

    A `ui.admin_password` ma URES, tehat a kapu nem zar — a szerver 127.0.0.1-re
    kot (server.py). Ha a HOST kifele nyilik, a jelszo beallitasa mostantol
    tenylegesen VEDI az irasi utakat is.
    """
    pw = (config.get("ui", {}) or {}).get("admin_password", "") or ""
    if not pw:
        return None
    auth = request.authorization
    if not auth or auth.password != pw:
        return Response(
            "Admin belépés szükséges.", 401,
            {"WWW-Authenticate": 'Basic realm="NODU Admin"'},
        )
    return None


# --- Nézetek ---

@app.route("/")
def index():
    return dashboard()


@app.route("/dashboard")
def dashboard():
    config = load_config()
    db_path = get_db_path(config)
    init_db(db_path)
    drafts = get_pending_drafts(db_path)

    # A korabbi limit=100 csendben csonkolta a nezetet (305 lehetoseg volt), es a
    # badge a LISTA hosszat irta ki totalkent — ugyanaz a hiba, mint a Nyers
    # leadeknel (HANDOFF §7/J). Most: nagyobb keret + VALODI totalok SQL-bol, es
    # ha megis csonkolunk, azt a nezet kiirja.
    opp_limit = (config.get("ui") or {}).get("opportunities_limit", 400)
    opportunities = get_opportunities(db_path, only_pain=True, limit=opp_limit)
    opp_total = count_opportunities(db_path, only_pain=True)
    hot_count = count_opportunities(db_path, only_pain=True, min_severity=4)
    # A csatorna-szuro pilljei: a TELJES halmaz platformonkenti darabszama, hogy
    # egy uj forras automatikusan megjelenjen (ne beegetett lista legyen).
    opp_channels = get_opportunity_platform_counts(db_path, only_pain=True)

    return render_template("dashboard.html", config=config, drafts=drafts,
                           opportunities=opportunities, hot_count=hot_count,
                           opp_total=opp_total, opp_channels=opp_channels,
                           opp_limit=opp_limit,
                           stats=_stats(config), active_view="dashboard")


@app.route("/admin")
def admin():
    config = load_config()
    gate = _admin_gate(config)
    if gate:
        return gate
    db_path = get_db_path(config)
    init_db(db_path)
    # A Slack-csatorna allapota: az URL a .env-ben van, tehat a sablon a
    # config.yaml-bol NEM tudja megallapitani, hogy el-e a csatorna.
    from alerts.notifier import slack_status, slack_webhook_url
    slack_ready, slack_reason = slack_status(config.get("alerts", {}))
    slack_url = slack_webhook_url(config.get("alerts", {}))
    return render_template("admin.html", config=config,
                           slack_ready=slack_ready, slack_reason=slack_reason,
                           slack_url_masked=(slack_url[:30] + "..." if slack_url else ""),
                           stats=_stats(config), active_view="admin")


# --- Config mentés ---

@app.route("/save", methods=["POST"])
def save():
    config = load_config()
    gate = _admin_gate(config)   # §2.7: az irasi ut is vedve
    if gate:
        return gate
    f = request.form

    config["reddit"]["client_id"] = f.get("reddit_client_id", "").strip() or "YOUR_REDDIT_CLIENT_ID"
    config["reddit"]["client_secret"] = f.get("reddit_client_secret", "").strip() or "YOUR_REDDIT_CLIENT_SECRET"
    raw_subs = f.get("reddit_subreddits", "")
    config["reddit"]["subreddits"] = [s.strip() for s in raw_subs.split(",") if s.strip()]

    config["scoring"]["gemini_enabled"] = "gemini_enabled" in f
    config["scoring"]["gemini_model"] = f.get("gemini_model", "gemini-2.5-flash").strip()
    # A Gemini- es YouTube-kulcsot SZANDEKOSAN nem irjuk vissza a config.yaml-be:
    # az git-tracked, es a GitHub push-protection (joggal) blokkolja az ilyen
    # commitot. A kulcsok a git-ignoralt .env-ben elnek (GEMINI_API_KEY,
    # YOUTUBE_API_KEY), env_secrets.py olvassa oket. Ha az admin urlapon uj
    # kulcsot irsz be, azt a .env-be kell atvinni — a mezo csak megjelenit.

    config["alerts"]["email"]["enabled"] = "email_enabled" in f
    config["alerts"]["email"]["from_address"] = f.get("email_from", "").strip() or "YOUR_EMAIL@gmail.com"
    config["alerts"]["email"]["to_address"] = f.get("email_to", "").strip() or "poczai@nodu.build"
    pw = f.get("email_password", "").strip()
    config["alerts"]["email"]["app_password"] = pw if pw else "YOUR_APP_PASSWORD"

    config["alerts"]["slack"]["enabled"] = "slack_enabled" in f
    # A Slack webhook-URL-t SZANDEKOSAN nem irjuk vissza a config.yaml-be (ld. a
    # Gemini-kulcsnal fentebb): az URL onmagaban titok, a config.yaml pedig
    # git-tracked. A .env `SLACK_WEBHOOK_URL` sora a forras, env_secrets olvassa.
    # Az admin urlapon a mezo csak allapotot jelez, nem szerkesztheto.

    # Kulcsszavak (admin Kulcsszavak szekcio) — soronkent egy kifejezes
    if "kw_primary" in f:
        config.setdefault("keywords", {})
        config["keywords"]["primary"] = [s.strip() for s in f.get("kw_primary", "").splitlines() if s.strip()]
        config["keywords"]["pain_points"] = [s.strip() for s in f.get("kw_pain", "").splitlines() if s.strip()]
        config["keywords"]["context"] = [s.strip() for s in f.get("kw_context", "").splitlines() if s.strip()]

    if "content_language" in f:
        config.setdefault("linkedin_content", {})
        config["linkedin_content"]["language"] = f.get("content_language", "en").strip()

    if "report_language" in f:
        config.setdefault("weekly_report", {})
        config["weekly_report"]["language"] = f.get("report_language", "hu").strip()

    # A youtube_api_key mezot sem irjuk vissza (ld. a Gemini-nel fentebb).

    save_config(config)
    return redirect(url_for("admin") + "?saved=1")


# --- Connector futtatás (admin) ---

@app.route("/run/<action>", methods=["POST"])
def run_action(action):
    config = load_config()
    gate = _admin_gate(config)   # §2.7: connector-inditas is vedve
    if gate:
        return gate
    db_path = get_db_path(config)

    if action == "reddit":
        from connectors.reddit_connector import RedditConnector
        _run_in_bg("reddit", lambda: RedditConnector(config, db_path).run())

    elif action == "playwright":
        from connectors.playwright_connector import PlaywrightConnector
        _run_in_bg("playwright", lambda: PlaywrightConnector(config, db_path).run())

    elif action == "stackoverflow":
        from connectors.stackoverflow_connector import StackOverflowConnector
        _run_in_bg("stackoverflow", lambda: StackOverflowConnector(config, db_path).run())

    elif action == "discourse":
        from connectors.discourse_connector import DiscourseConnector
        _run_in_bg("discourse", lambda: DiscourseConnector(config, db_path).run())

    elif action == "vanilla":
        from connectors.vanilla_connector import VanillaConnector
        _run_in_bg("vanilla", lambda: VanillaConnector(config, db_path).run())

    elif action == "zendesk":
        from connectors.zendesk_connector import ZendeskConnector
        _run_in_bg("zendesk", lambda: ZendeskConnector(config, db_path).run())

    elif action == "github":
        from connectors.github_connector import GitHubConnector
        _run_in_bg("github", lambda: GitHubConnector(config, db_path).run())

    elif action == "youtube":
        from connectors.youtube_connector import YouTubeConnector
        _run_in_bg("youtube", lambda: YouTubeConnector(config, db_path).run())

    elif action == "forums":
        from connectors.html_connector import HTMLConnector
        def _forums():
            total = 0
            for name, fc in config.get("forums", {}).items():
                total += HTMLConnector(name, fc, config, db_path).run()
            return total
        _run_in_bg("forums", _forums)

    elif action == "generate-drafts":
        from responder.draft_generator import generate_drafts
        _run_in_bg("generate-drafts", lambda: generate_drafts(config, db_path))

    elif action == "weekly-report":
        from alerts.notifier import send_weekly_digest
        from responder.draft_generator import generate_trend_analysis
        def _weekly():
            days = config.get("weekly_report", {}).get("lookback_days", 7)
            stats = get_weekly_stats(db_path, days)
            trend = generate_trend_analysis(config, db_path)
            send_weekly_digest(stats, config.get("alerts", {}), trend_analysis=trend)
            return "elküldve"
        _run_in_bg("weekly-report", _weekly)

    elif action == "linkedin-content":
        from responder.draft_generator import generate_content_pipeline
        from alerts.notifier import send_content_pipeline_ideas
        def _linkedin():
            res = generate_content_pipeline(config, db_path)
            if res:
                send_content_pipeline_ideas(res, config.get("alerts", {}))
                return "1 cikk + " + str(len(res.get("linkedin_posts", []))) + " teaser"
            return "Nincs elég adat"
        _run_in_bg("linkedin-content", _linkedin)

    elif action == "build-knowledge":
        from storage.knowledge_builder import build_knowledge_base
        def _build_kb():
            kb_path = build_knowledge_base(config)
            kb_size = 0
            import os
            if os.path.exists(kb_path):
                kb_size = os.path.getsize(kb_path)
            return f"{kb_size // 1024} KB frissítve"
        _run_in_bg("build-knowledge", _build_kb)

    # Ha ugyanaz a job mar fut, a _run_in_bg NEM inditott masodikat (§2.7):
    # adjunk erre egyertelmu valaszt 409-cel, ne "ok"-ot.
    already_running = (_jobs.get(action) or {}).get("status") == "running"
    if request.args.get("ajax") == "1" or request.is_json:
        if already_running:
            return jsonify({"ok": False, "action": action,
                            "error": "Ez a futas mar folyamatban van."}), 409
        return jsonify({"ok": True, "action": action})
    return redirect(url_for("admin") + ("?running=1" if already_running else "?started=1"))


# --- Ad-hoc keresés (dashboard) ---

@app.route("/search/adhoc", methods=["POST"])
def search_adhoc():
    config = load_config()
    gate = _admin_gate(config)   # §2.7: kulso API-t hiv
    if gate:
        return gate
    db_path = get_db_path(config)
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    channels = data.get("channels") or None
    if not query:
        return jsonify({"ok": False, "error": "Üres keresési kifejezés."}), 400

    from connectors.adhoc_search import run_adhoc_search
    _run_in_bg("adhoc", lambda: run_adhoc_search(config, db_path, query, channels).get("total", 0))
    return jsonify({"ok": True, "query": query})


@app.route("/api/adhoc-results")
def api_adhoc_results():
    config = load_config()
    db_path = get_db_path(config)
    query = (request.args.get("query") or "").strip()
    try:
        offset = int(request.args.get("offset", 0))
    except ValueError:
        offset = 0
    results = get_adhoc_results(db_path, query or None, limit=10, offset=offset)
    return jsonify({"query": query, "results": results, "offset": offset})


@app.route("/api/posts")
def api_posts():
    config = load_config()
    db_path = get_db_path(config)
    query = (request.args.get("q") or "").strip()
    platforms_raw = request.args.get("platforms")
    platforms = [p.strip() for p in platforms_raw.split(",")] if platforms_raw else None

    # A `total` a szures OSSZES talalata, a `results` csak az aktualis lap. A
    # dashboard enelkul a lap meretet irta ki totalkent ("100 talalat", holott
    # 591 volt) — ld. HANDOFF §7/J.
    try:
        offset = max(0, int(request.args.get("offset", 0)))
    except ValueError:
        offset = 0
    limit = 100

    from storage.db import count_posts, search_posts
    results = search_posts(db_path, query, platforms, limit=limit, offset=offset)
    total = count_posts(db_path, query, platforms)
    return jsonify({
        "query": query,
        "platforms": platforms,
        "results": results,
        "total": total,
        "offset": offset,
        "limit": limit,
    })


# --- LinkedIn valaszgeneralas (dashboard) ---

@app.route("/linkedin/compose", methods=["POST"])
def linkedin_compose():
    config = load_config()
    gate = _admin_gate(config)   # §2.7: fizetos LLM-hivast indit
    if gate:
        return gate
    data = request.get_json(silent=True) or {}
    post_text = (data.get("post_text") or "").strip()
    if not post_text:
        return jsonify({"ok": False, "error": "Üres poszt-szöveg."}), 400

    from responder.draft_generator import generate_linkedin_reply
    result = generate_linkedin_reply(
        config, post_text,
        author_name=(data.get("author_name") or "").strip(),
        author_role=(data.get("author_role") or "").strip(),
    )
    if not result:
        return jsonify({"ok": False, "error": "Nem sikerült. Be van kapcsolva a Gemini API az Adminban?"})
    if "error" in result:
        return jsonify({"ok": False, "error": result["error"]})
    return jsonify({"ok": True, **result})


# --- Lead-akciók (dashboard) ---

@app.route("/lead/<int:post_id>/draft", methods=["POST"])
def lead_draft(post_id):
    config = load_config()
    gate = _admin_gate(config)   # §2.7: fizetos LLM-hivast indit
    if gate:
        return gate
    db_path = get_db_path(config)
    from responder.draft_generator import generate_draft_for_post, is_platform_excluded

    # A kizart platformokra (responder.exclude_platforms) itt is nemet mondunk,
    # de KONKRET indoklassal — kulonben a gomb csak a general "nem sikerult"
    # uzenetet adna, es ugy tunne, elromlott valami.
    from storage.db import get_post_with_signal
    post = get_post_with_signal(db_path, post_id)
    if post and is_platform_excluded(config, post.get("platform", "")):
        return jsonify({
            "ok": False,
            "error": f"A(z) „{post.get('platform')}” platformra szándékosan nem "
                     f"készül válasz (config: responder.exclude_platforms). "
                     f"Ez a forrás csak jelfigyelésre szolgál.",
        })

    draft_id = generate_draft_for_post(config, db_path, post_id)
    if draft_id:
        import sqlite3
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT draft_text FROM drafts WHERE id = ?", (draft_id,))
            row = c.fetchone()
            draft_text = row[0] if row else ""
        return jsonify({"ok": True, "draft_id": draft_id, "draft_text": draft_text})
    return jsonify({"ok": False, "error": "Nem sikerült. Be van kapcsolva a Gemini API az Adminban?"})


@app.route("/lead/<int:post_id>/to-sales-os", methods=["POST"])
def lead_to_sales_os(post_id):
    """
    Lead atadasa a SalesOS-nek: KOZVETLEN `POST /api/bridge/ingest`, n8n nelkul
    (01-es audit §6/§10 dontese). Korabban ez az `alerts.webhook` n8n-vegpontot
    hivta, ami letiltva es placeholder URL-lel allt — a gomb minden kattintasra
    hibat adott (02-es audit §4/9).

    A SalesOS account-centrikus: **ceg-adat nelkul 422**. A Monitorban nincs
    Entity Resolver (az a 3. fazis), ezert a cegnevet a FELHASZNALO adja meg —
    ez a tervezett emberi kapu, nem hianyossag.
    """
    config = load_config()
    gate = _admin_gate(config)   # §2.7: kulso rendszerbe (SalesOS) ir
    if gate:
        return gate
    db_path = get_db_path(config)
    post = get_post_with_signal(db_path, post_id) or get_post(db_path, post_id)
    if not post:
        return jsonify({"ok": False, "error": "Nincs ilyen lead."}), 404

    data = request.get_json(silent=True) or {}
    company = {
        "name": (data.get("company_name") or "").strip(),
        "domain": (data.get("company_domain") or "").strip(),
        "companiesHouseNumber": (data.get("company_house_no") or "").strip(),
    }
    contact = {
        "fullName": (data.get("contact_name") or "").strip(),
        "email": (data.get("contact_email") or "").strip(),
    }

    from crm.salesos_client import send_to_salesos, SalesOSError
    try:
        result = send_to_salesos(config, post, company,
                                 summary=(data.get("summary") or "").strip(),
                                 contact=contact)
    except SalesOSError as e:
        return jsonify({"ok": False, "error": str(e)})
    except Exception as e:  # varatlan hiba — ne 500-azzon a dashboard
        return jsonify({"ok": False, "error": f"Varatlan hiba: {e}"})

    with sqlite3.connect(db_path, timeout=30) as conn:
        conn.execute("UPDATE posts SET status = 'processed' WHERE id = ?", (post_id,))
    return jsonify({"ok": True, "deduped": bool(result.get("deduped")), "result": result})


# --- Draft jóváhagyás (dashboard) ---

def _decider() -> tuple[str, str]:
    """
    Ki hozza a dontest, es mennyire hiheto ez a nev.

    Ma NINCS felhasznalo-azonositas a dashboardon (a `ui.admin_password` egyetlen
    kozos jelszo, a basic-auth username-t senki nem ellenorzi), ezert a nev
    ONBEVALLAS — a source ezt `'form'`-kent jeloli, nem `'auth'`-kent. Ez tudatos:
    a naplo ne alliton tobbet, mint amit tud. Sorrend:
      1. urlap/JSON `decided_by` mezo (a dashboard ezt kuldi)
      2. HTTP basic-auth username (ha be van kapcsolva a jelszo)
      3. `ui.default_decider` a config.yaml-bol (egyszemelyes uzem)
    Ha egyik sincs, ures nev megy vissza -> a mark_draft nem ir naplot.
    """
    name = (request.form.get("decided_by") or "").strip()
    if not name and request.is_json:
        name = str((request.get_json(silent=True) or {}).get("decided_by") or "").strip()
    if not name and request.authorization and request.authorization.username:
        name = request.authorization.username.strip()
    if not name:
        name = str((load_config().get("ui", {}) or {}).get("default_decider", "") or "").strip()
    return name, "form"


@app.route("/draft/<int:draft_id>/approve", methods=["POST"])
def approve_draft(draft_id):
    config = load_config()
    gate = _admin_gate(config)   # §2.7: jovahagyas = naplozott dontes
    if gate:
        return gate
    who, src = _decider()
    mark_draft(get_db_path(config), draft_id, "approved",
               decided_by=who, decided_by_source=src)
    return jsonify({"ok": True, "decided_by": who or None})


@app.route("/draft/<int:draft_id>/reject", methods=["POST"])
def reject_draft(draft_id):
    config = load_config()
    gate = _admin_gate(config)   # §2.7
    if gate:
        return gate
    who, src = _decider()
    mark_draft(get_db_path(config), draft_id, "rejected", "webes felületen visszautasítva",
               decided_by=who, decided_by_source=src)
    return jsonify({"ok": True, "decided_by": who or None})


@app.route("/api/decisions")
def api_decisions():
    """
    Draft-dontesek naploja: ki hagyta jova / vetette el, es mikor.

    A `source` mezo a naplo sulya: 'cli' = a gepen bejelentkezett OS-felhasznalo,
    'form' = a webes felhasznalo onbevallasa (ma nincs auth, ld. _decider).
    """
    config = load_config()
    try:
        limit = max(1, min(int(request.args.get("limit", 50)), 500))
    except ValueError:
        limit = 50
    rows = get_decision_log(get_db_path(config), limit=limit)
    return jsonify({"decisions": rows, "count": len(rows)})


@app.route("/health")
def health():
    """
    Gep-olvashato allapot-vegpont (01-es audit §10 "Observability", 2. fazis).
    HTTP 200, ha minden aktiv connector rendben; **503**, ha barmelyik hibas vagy
    "vak" (0 nyers elemet lat) — igy egy kulso felugyelo (uptime-monitor, tunnel
    healthcheck, Windows service watchdog) eszreveszi a nema hibakat is.

    Auth nincs: csak aggregalt allapotot ad vissza, nem lead-adatot, es a szerver
    127.0.0.1-re kot (server.py). Ha kifele nyilik, ez ujragondolando.
    """
    config = load_config()
    db_path = get_db_path(config)
    hc = config.get("health", {})
    ignore = set(hc.get("ignore", ["classifier"]))

    try:
        # Az utemezett connectorok listaja ugyanabbol a tablabol, amibol a
        # register_jobs dolgozik — igy a HIANYZO futas is 503-at ad, nem csak a
        # hibas (docs/04-rendszer-audit-2026-07-28.md §2.2).
        from main import connector_schedule
        expected = {e["name"]: e["interval"] for e in connector_schedule(config)
                    if e.get("expect_runs", True)}
        report = get_connector_health(
            db_path,
            window=hc.get("window", 5),
            active_within_hours=hc.get("active_within_hours", 24),
            expected=expected,
            stale_factor=hc.get("stale_factor", 3.0),
        )
    except Exception as e:
        return jsonify({"status": "error", "error": f"DB nem olvashato: {e}"}), 503

    problems = [r for r in report
                if r["status"] in ("error", "blind", "stale") and r["connector"] not in ignore]
    body = {
        "status": "degraded" if problems else "ok",
        "checked_at": datetime.now(tz=timezone.utc).isoformat(),
        "connectors": report,
        "problems": [p["connector"] for p in problems],
        "pending_drafts": len(get_pending_drafts(db_path)),
    }
    return jsonify(body), (503 if problems else 200)


@app.route("/api/status")
def api_status():
    config = load_config()
    db_path = get_db_path(config)
    pending = len(get_pending_drafts(db_path))
    return jsonify({"jobs": _jobs, "pending_drafts": pending})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print(f"NODU Monitor vezérlőpult: http://localhost:{port}")
    app.jinja_env.auto_reload = True
    app.run(host="127.0.0.1", port=port, debug=False)
