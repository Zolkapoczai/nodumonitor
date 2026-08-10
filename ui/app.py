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
import base64
import binascii
import threading
from datetime import datetime, timezone
from urllib.parse import quote

import yaml
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
from markupsafe import escape
from storage.db import (
    init_db, get_pending_drafts, mark_draft, get_weekly_stats,
    get_adhoc_results, get_post, get_post_with_signal, get_opportunities,
    get_connector_health, count_opportunities, get_opportunity_platform_counts,
    get_decision_log,
)
from storage.config_writer import patch_config_file, ConfigPatchError

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")

_jobs: dict = {}

# Az utolso Tartalom Pipeline (blog + LinkedIn) generalas teljes eredmenye —
# kulon tarolva a `_jobs`-tol, mert az csak egy stringesitett osszefoglalot
# tart (pl. connector-darabszam), itt viszont a teljes strukturat meg kell
# orizni a Dashboard kiemelt kartyajanak megjelenitesehez. Folyamat-memoriaban
# el, ugyanugy nem eli tul az ujrainditast, mint a `_jobs` tobbi bejegyzese.
_last_content_pipeline: dict | None = None


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


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

    # A Tartalom Pipeline kiemelt kartyajahoz: a legutobbi eredmeny (ha van
    # ebben a szerver-munkameneteben), plusz hogy a Slack-csatorna el-e —
    # ugyanaz a mert allapot, amit az Admin is mutat, nem csak a config-flag.
    from alerts.notifier import slack_status
    slack_ready, _slack_reason = slack_status(config.get("alerts", {}))

    # A kep-atmeretezes a BONGESZOBEN tortenik (nincs Pillow-fuggoseg), ezert a
    # kliensnek tudnia kell a plafont — kulonben a config-kapcsolo hazudna.
    from responder.linkedin_engine import image_input_enabled, image_max_px

    return render_template("dashboard.html", config=config, drafts=drafts,
                           opportunities=opportunities, hot_count=hot_count,
                           opp_total=opp_total, opp_channels=opp_channels,
                           opp_limit=opp_limit, content_pipeline=_last_content_pipeline,
                           slack_ready=slack_ready,
                           li_image_enabled=image_input_enabled(config),
                           li_image_max_px=image_max_px(config),
                           stats=_stats(config), active_view="dashboard")


def _admin_context(config: dict) -> dict:
    db_path = get_db_path(config)
    init_db(db_path)
    # A Slack-csatorna allapota: az URL a .env-ben van, tehat a sablon a
    # config.yaml-bol NEM tudja megallapitani, hogy el-e a csatorna.
    from alerts.notifier import slack_status, slack_webhook_url
    slack_ready, slack_reason = slack_status(config.get("alerts", {}))
    slack_url = slack_webhook_url(config.get("alerts", {}))
    return dict(config=config, slack_ready=slack_ready, slack_reason=slack_reason,
                slack_url_masked=(slack_url[:30] + "..." if slack_url else ""),
                stats=_stats(config), active_view="admin")


@app.route("/admin")
def admin():
    config = load_config()
    gate = _admin_gate(config)
    if gate:
        return gate
    return render_template("admin.html", **_admin_context(config))


# --- Config mentés ---

def _bool_field(form, name):
    """
    None, ha a checkbox rejtett kiserto mezoje (`{name}__present`) hianyzik a
    POST-bol - igy egy reszleges POST (pl. curl egy mezovel) nem tud
    atfordítani egy boolt, amit meg sem emlitett. A valodi admin-urlap ezt a
    kiserto mezot MINDIG kuldi (ui/templates/admin.html), tehat a normal
    mentesi utat nem erinti (docs/04-rendszer-audit-2026-07-28.md §2.7 rokon
    hibaja: reszleges kapu rosszabb, mint a nyilvanvaloan nyitott).
    """
    if f"{name}__present" not in form:
        return None
    return name in form


@app.route("/save", methods=["POST"])
def save():
    config = load_config()
    gate = _admin_gate(config)   # §2.7: az irasi ut is vedve
    if gate:
        return gate
    f = request.form

    updates = {}
    skipped = []

    def add_text(name, path):
        # Ures/hianyzo mezo = VALTOZATLAN, nem placeholder-felulirás. A
        # korabbi `.strip() or "YOUR_..."` minta destruktiv volt: egy ures
        # mezovel bekuldott POST az elo titkot placeholderre cserelte
        # (d42c3c8-ban ez tortent a subreddit-listaval es a booleanokkal is).
        val = (f.get(name, "") or "").strip()
        if val:
            updates[path] = val
        else:
            skipped.append(name)

    def add_list(name, path, split):
        vals = [s.strip() for s in split(f.get(name, "") or "") if s.strip()]
        if vals:
            updates[path] = vals
        else:
            skipped.append(name)

    def add_bool(name, path):
        val = _bool_field(f, name)
        if val is not None:
            updates[path] = val

    add_text("reddit_client_id", ("reddit", "client_id"))
    add_text("reddit_client_secret", ("reddit", "client_secret"))
    add_list("reddit_subreddits", ("reddit", "subreddits"), lambda s: s.split(","))

    add_bool("gemini_enabled", ("scoring", "gemini_enabled"))
    add_text("gemini_model", ("scoring", "gemini_model"))
    # A Gemini- es YouTube-kulcsot SZANDEKOSAN nem irjuk vissza a config.yaml-be
    # (nincs is a config_writer.PATCHABLE-ben): az git-tracked, es a GitHub
    # push-protection (joggal) blokkolja az ilyen commitot. A kulcsok a
    # git-ignoralt .env-ben elnek (GEMINI_API_KEY, YOUTUBE_API_KEY),
    # env_secrets.py olvassa oket. Ha az admin urlapon uj kulcsot irsz be, azt
    # a .env-be kell atvinni — a mezo csak megjelenit.

    add_bool("email_enabled", ("alerts", "email", "enabled"))
    add_text("email_from", ("alerts", "email", "from_address"))
    add_text("email_to", ("alerts", "email", "to_address"))
    add_text("email_password", ("alerts", "email", "app_password"))

    add_bool("slack_enabled", ("alerts", "slack", "enabled"))
    # A Slack webhook-URL-t SZANDEKOSAN nem irjuk vissza a config.yaml-be (ld. a
    # Gemini-kulcsnal fentebb): az URL onmagaban titok, a config.yaml pedig
    # git-tracked. A .env `SLACK_WEBHOOK_URL` sora a forras, env_secrets olvassa.
    # Az admin urlapon a mezo csak allapotot jelez, nem szerkesztheto.

    # Kulcsszavak — harom FUGGETLEN feltetel (korabban egyetlen `if "kw_primary"
    # in f` orizte mindharmat: egy kw_primary-t tartalmazo, kw_pain-t nem
    # tartalmazo POST kinullazta volna az 54 pain-kulcsszot).
    add_list("kw_primary", ("keywords", "primary"), lambda s: s.splitlines())
    add_list("kw_pain", ("keywords", "pain_points"), lambda s: s.splitlines())
    add_list("kw_context", ("keywords", "context"), lambda s: s.splitlines())

    add_text("content_language", ("linkedin_content", "language"))
    add_text("report_language", ("weekly_report", "language"))

    # A youtube_api_key mezot sem irjuk vissza (ld. a Gemini-nel fentebb).

    try:
        patch_config_file(CONFIG_PATH, updates)
    except ConfigPatchError as e:
        # Lathato hibasav, nem stacktrace/500 (docs/04-rendszer-audit-2026-07-28.md
        # §2.7 rokon hibaja: a config["szekcio"] indexeles korabban KeyError->500-at
        # adott volna hianyzo szekcional). Szandekosan NEM az admin.html-t
        # renderelja ujra: pont azert bukott a patch, mert a config.yaml
        # valamelyik szekcioja hianyzik/serult, es az a sablon MINDEN
        # szekciot feltetelez (`config.scoring.gemini_enabled` stb.) — egy
        # ujrarenderelt admin.html ugyanezen a hianyon maga is elhasalna.
        return Response(
            "<!doctype html><meta charset=\"utf-8\">"
            "<div class=\"save-banner error\" style=\"margin:24px;font-family:sans-serif;"
            "padding:14px 18px;border-radius:8px;background:#FEF2F2;color:#DC2626;"
            "border:1px solid #FCA5A5;\">Mentés sikertelen: " + escape(str(e)) + "</div>"
            "<p style=\"margin:0 24px;font-family:sans-serif;\">"
            "<a href=\"/admin\">Vissza az Adminba</a></p>",
            400,
            {"Content-Type": "text/html; charset=utf-8"},
        )

    query = "?saved=1"
    if skipped:
        query += "&warn=" + quote(",".join(skipped))
    return redirect(url_for("admin") + query)


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
            global _last_content_pipeline
            res = generate_content_pipeline(config, db_path)
            stamp = datetime.now(tz=timezone.utc).isoformat()
            if res:
                send_content_pipeline_ideas(res, config.get("alerts", {}))
                _last_content_pipeline = {"ok": True, "generated_at": stamp, **res}
                return "1 cikk + " + str(len(res.get("linkedin_posts", []))) + " teaser"
            _last_content_pipeline = {
                "ok": False, "generated_at": stamp,
                "reason": "Nincs elég friss fájdalom-jel a beállított időszakban, "
                          "vagy a Gemini API nincs bekapcsolva az Adminban.",
            }
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

# A kliens canvas-a MINDIG JPEG-et ad vissza (ld. dashboard.html resizeImage),
# ezert a szerver CSAK JPEG-et fogad. Ez sokkal szukebb tamadasi felulet, mint egy
# tobbformatumu allowlist, es semmit nem veszitunk vele.
_LI_IMAGE_MAX_BYTES = 2 * 1024 * 1024        # 2 MB dekodolt; 384 px-es JPEG ~30-60 KB
_JPEG_MAGIC = b"\xff\xd8\xff"


def _decode_post_image(raw: str) -> tuple[bytes | None, str | None]:
    """base64 data-URL -> (bytes, hibauzenet). Csak az egyiket adja vissza.

    A kepet SOSEM irjuk lemezre es SOSEM logoljuk (egy base64 blob elarasztana a
    logot) — a memoriaban dolgozzuk fel, majd elszall a keressel.
    """
    if not raw:
        return None, None
    payload = raw.split(",", 1)[1] if raw.startswith("data:") else raw
    # 4/3-szoros base64-tobblet + tartalek: a dekodolas elott vagunk, hogy egy
    # tulmeretes kerest ne is dekodoljunk.
    if len(payload) > _LI_IMAGE_MAX_BYTES * 4 // 3 + 1024:
        return None, "A kép túl nagy (max 2 MB)."
    try:
        blob = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        return None, "A kép nem érvényes base64."
    if len(blob) > _LI_IMAGE_MAX_BYTES:
        return None, "A kép túl nagy (max 2 MB)."
    # Magic-byte: a MIME-fejlec a kliens allitasa, a bajtok a bizonyitek.
    if not blob.startswith(_JPEG_MAGIC):
        return None, "Csak JPEG kép fogadható el."
    return blob, None


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

    image_bytes, image_err = _decode_post_image(data.get("image_b64") or "")
    if image_err:
        return jsonify({"ok": False, "error": image_err}), 400

    from responder.draft_generator import generate_linkedin_reply
    result = generate_linkedin_reply(
        config, post_text,
        author_name=(data.get("author_name") or "").strip(),
        author_role=(data.get("author_role") or "").strip(),
        image_bytes=image_bytes,
        # `force`: a UI "Megis generalj" gombja vendor-hirdetes eseten. A kihagyas
        # AJANLAS, nem tilalom — a vegso szot a felhasznalo mondja ki.
        force=bool(data.get("force")),
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


@app.route("/api/content-pipeline")
def api_content_pipeline():
    """A Dashboard kiemelt Tartalom Pipeline kartyajanak eredmenye — a job
    lezarulasa utan ezt hivja le a kliens, hogy a friss blog+LinkedIn
    javaslatot inline megjelenithesse (nem csak a Slack-csatornan).

    A `slack_ready`-t is idekeveri, hogy a kliens-oldali (JS) render
    ugyanazt a "elkuldve Slackre is" / "Slack nincs beallitva" jelzest tudja
    adni, mint a szerver-oldali (Jinja) elso betoltes."""
    from alerts.notifier import slack_status
    config = load_config()
    slack_ready, _reason = slack_status(config.get("alerts", {}))
    body = dict(_last_content_pipeline or {})
    body["slack_ready"] = slack_ready
    return jsonify(body)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print(f"NODU Monitor vezérlőpult: http://localhost:{port}")
    app.jinja_env.auto_reload = True
    app.run(host="127.0.0.1", port=port, debug=False)
