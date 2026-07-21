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
import sys
import threading
from datetime import datetime, timezone

import yaml
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
from storage.db import (
    init_db, get_pending_drafts, mark_draft, get_weekly_stats,
    get_adhoc_results, get_post, get_opportunities,
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
    key = f.get("gemini_api_key", "").strip()
    config["scoring"]["gemini_api_key"] = key if key else "YOUR_GEMINI_API_KEY"
    config["scoring"]["gemini_model"] = f.get("gemini_model", "gemini-2.5-flash").strip()

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
        def _weekly():
            days = config.get("weekly_report", {}).get("lookback_days", 7)
            stats = get_weekly_stats(db_path, days)
            send_weekly_digest(stats, config.get("alerts", {}))
            return "elküldve"
        _run_in_bg("weekly-report", _weekly)

    elif action == "linkedin-content":
        from responder.draft_generator import generate_linkedin_content
        from alerts.notifier import send_linkedin_suggestions
        def _linkedin():
            posts = generate_linkedin_content(config, db_path)
            if posts:
                send_linkedin_suggestions(posts, config.get("alerts", {}))
            return f"{len(posts)} javaslat"
        _run_in_bg("linkedin-content", _linkedin)

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
    results = get_adhoc_results(db_path, query or None, limit=50)
    return jsonify({"query": query, "results": results})


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
    return jsonify({"ok": True, **result})


# --- Lead-akciók (dashboard) ---

@app.route("/lead/<int:post_id>/draft", methods=["POST"])
def lead_draft(post_id):
    config = load_config()
    db_path = get_db_path(config)
    from responder.draft_generator import generate_draft_for_post
    draft_id = generate_draft_for_post(config, db_path, post_id)
    if draft_id:
        return jsonify({"ok": True, "draft_id": draft_id})
    return jsonify({"ok": False, "error": "Nem sikerült. Be van kapcsolva a Gemini API az Adminban?"})


@app.route("/lead/<int:post_id>/to-sales-os", methods=["POST"])
def lead_to_sales_os(post_id):
    config = load_config()
    db_path = get_db_path(config)
    post = get_post(db_path, post_id)
    if not post:
        return jsonify({"ok": False, "error": "Nincs ilyen lead."}), 404

    wc = config.get("alerts", {}).get("webhook", {})
    if not wc.get("enabled") or not wc.get("url") or wc.get("url") == "YOUR_N8N_WEBHOOK_URL":
        return jsonify({"ok": False, "error": "Az n8n webhook nincs beállítva (alerts.webhook)."})

    payload = {
        "source": "adhoc",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "leads": [{
            "platform": post.get("platform", ""),
            "source": post.get("source", ""),
            "title": post.get("title", ""),
            "author": post.get("author", ""),
            "url": post.get("url", ""),
            "score": post.get("score", 0),
            "keywords": post.get("keywords", ""),
            "body_excerpt": (post.get("body") or "")[:500],
            "created_at": post.get("created_at", ""),
        }],
    }
    try:
        resp = requests.post(wc["url"], json=payload,
                             headers={"Content-Type": "application/json"}, timeout=15)
        resp.raise_for_status()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


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
