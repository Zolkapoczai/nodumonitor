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
    get_connector_health,
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


def _run_in_bg(job_id: str, fn):
    def _worker():
        _jobs[job_id] = {"status": "running"}
        try:
            result = fn()
            _jobs[job_id] = {"status": "done", "result": str(result)}
        except Exception as e:
            _jobs[job_id] = {"status": "error", "error": str(e)}
    threading.Thread(target=_worker, daemon=True).start()


def _admin_gate(config: dict):
    """Opcionalis jelszovedelem az /admin nezetre. None ha szabad az atjaras."""
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
    opportunities = get_opportunities(db_path, only_pain=True)
    hot_count = sum(1 for o in opportunities if (o.get("severity") or 0) >= 4)
    return render_template("dashboard.html", config=config, drafts=drafts,
                           opportunities=opportunities, hot_count=hot_count,
                           stats=_stats(config), active_view="dashboard")


@app.route("/admin")
def admin():
    config = load_config()
    gate = _admin_gate(config)
    if gate:
        return gate
    db_path = get_db_path(config)
    init_db(db_path)
    return render_template("admin.html", config=config,
                           stats=_stats(config), active_view="admin")


# --- Config mentés ---

@app.route("/save", methods=["POST"])
def save():
    config = load_config()
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
    wh = f.get("slack_webhook", "").strip()
    config["alerts"]["slack"]["webhook_url"] = wh if wh else "YOUR_SLACK_WEBHOOK_URL"

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

    if request.args.get("ajax") == "1" or request.is_json:
        return jsonify({"ok": True, "action": action})
    return redirect(url_for("admin") + "?started=1")


# --- Ad-hoc keresés (dashboard) ---

@app.route("/search/adhoc", methods=["POST"])
def search_adhoc():
    config = load_config()
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
    
    from storage.db import search_posts
    results = search_posts(db_path, query, platforms, limit=100)
    return jsonify({"query": query, "platforms": platforms, "results": results})


# --- LinkedIn valaszgeneralas (dashboard) ---

@app.route("/linkedin/compose", methods=["POST"])
def linkedin_compose():
    config = load_config()
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
    db_path = get_db_path(config)
    from responder.draft_generator import generate_draft_for_post
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

@app.route("/draft/<int:draft_id>/approve", methods=["POST"])
def approve_draft(draft_id):
    config = load_config()
    mark_draft(get_db_path(config), draft_id, "approved")
    return jsonify({"ok": True})


@app.route("/draft/<int:draft_id>/reject", methods=["POST"])
def reject_draft(draft_id):
    config = load_config()
    mark_draft(get_db_path(config), draft_id, "rejected", "webes felületen visszautasítva")
    return jsonify({"ok": True})


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
        report = get_connector_health(
            db_path,
            window=hc.get("window", 5),
            active_within_hours=hc.get("active_within_hours", 24),
        )
    except Exception as e:
        return jsonify({"status": "error", "error": f"DB nem olvashato: {e}"}), 503

    problems = [r for r in report
                if r["status"] in ("error", "blind") and r["connector"] not in ignore]
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
