import os
import smtplib
import json
import sys
import time
import requests
from email.message import EmailMessage
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from env_secrets import get_secret  # noqa: E402

SLACK_WEBHOOK_ENV = "SLACK_WEBHOOK_URL"
_SLACK_URL_PREFIX = "https://hooks.slack.com/"

# Slack Block Kit kemeny korlatai (docs.slack.dev/reference/block-kit/blocks,
# .../blocks/section-block) es az incoming webhook rate limitje
# (docs.slack.dev/apis/web-api/rate-limits: 1 uzenet/masodperc, rovid burst OK).
# EZEK NEM HANGOLHATO ERTEKEK — a Slack API adja oket.
SLACK_MAX_BLOCKS_PER_MESSAGE = 50
SLACK_SECTION_MAX_CHARS = 3000
SLACK_MESSAGE_PAUSE_SECONDS = 1.2
# Ez viszont a MI valasztasunk: 20 jel/uzenet olvashato mennyiseg, es hagy helyet
# a fejlecnek (20+1 = 21 blokk, jol az 50-es korlat alatt). config: posts_per_message
SLACK_POSTS_PER_MESSAGE_DEFAULT = 20


def slack_webhook_url(alert_config: dict) -> str:
    """
    A Slack Incoming Webhook URL feloldasa: env -> .env -> config.yaml.

    Miert nem a config.yaml a hely: az git-tracked, es a webhook-URL ONMAGABAN
    a titok (aki ismeri, a csatornara irhat) — pontosan ugyanaz a helyzet, mint
    a GEMINI_API_KEY-nel, amit a GitHub push-protection joggal blokkolt
    (HANDOFF §5). A config.yaml-beli erteket visszafele-kompatibilitasbol meg
    elfogadjuk, de a `YOUR_...` placeholder-t a get_secret ures stringnek veszi.

    Ures string = nincs csatorna. A hivo ilyenkor KIHAGYJA magat (nem hiba),
    ugyanaz a minta, mint a kulcs nelkuli connectoroknal.
    """
    sc = alert_config.get("slack", {}) or {}
    url = get_secret(SLACK_WEBHOOK_ENV, sc.get("webhook_url"))
    if url and not url.startswith(_SLACK_URL_PREFIX):
        print(f"[alert] A Slack webhook-URL nem {_SLACK_URL_PREFIX}-kezdetu — kihagyva.")
        return ""
    return url


def slack_status(alert_config: dict) -> tuple[bool, str]:
    """
    (kesz-e, indoklas) — a `/health`, az admin UI es a `--test-slack` hasznalja,
    hogy a "miert nem megy ki riasztas" kerdes ne igenyeljen kodolvasast.
    """
    sc = alert_config.get("slack", {}) or {}
    if not sc.get("enabled"):
        return False, "alerts.slack.enabled: false a config.yaml-ben"
    if not slack_webhook_url(alert_config):
        return False, f"nincs webhook-URL ({SLACK_WEBHOOK_ENV} a .env-ben)"
    return True, "kesz"


def _format_post(post: dict) -> str:
    lines = [
        f"Platform: {post['platform']} | Source: {post['source']}",
        f"Title: {post.get('title', '')}",
        f"Author: {post.get('author', '')} | Date: {post.get('created_at', '')}",
    ]
    # A classifier mezoi csak a jel-vezerelt digestben vannak jelen (run_digest);
    # az ad-hoc/kulcsszo-utakon nincsenek, ezert opcionalisak.
    if post.get("severity") is not None:
        lines.append(
            f"Severity: {post.get('severity')} | Buying intent: {'igen' if post.get('buying_intent') else 'nem'}"
            f" | Confidence: {post.get('confidence')}"
        )
    if post.get("pain_summary"):
        lines.append(f"Pain: {post['pain_summary']}")
    if post.get("role_hypothesis"):
        lines.append(f"Role: {post['role_hypothesis']}")
    lines += [
        f"Score: {post.get('score', 0)} | Keywords: {post.get('keywords', '')}",
        f"URL: {post.get('url', '')}",
        f"---",
        (post.get("body") or "")[:400],
        "",
    ]
    return "\n".join(lines)


def _post_slack_blocks(webhook_url: str, blocks: list[dict]) -> None:
    """Slack Block Kit uzenet kuldese egy incoming webhook URL-re."""
    resp = requests.post(
        webhook_url,
        data=json.dumps({"blocks": blocks}),
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    resp.raise_for_status()


def send_email(posts: list[dict], alert_config: dict) -> None:
    ec = alert_config["email"]
    if not posts:
        return

    body_lines = [
        f"NODU Bridge Monitor: {len(posts)} uj relevans bejegyzes",
        f"Generalva: {datetime.now(tz=timezone.utc).isoformat()}",
        "=" * 60,
        "",
    ]
    for p in posts:
        body_lines.append(_format_post(p))

    msg = EmailMessage()
    msg["Subject"] = f"NODU Monitor: {len(posts)} uj találat"
    msg["From"] = ec["from_address"]
    msg["To"] = ec["to_address"]
    msg.set_content("\n".join(body_lines))

    with smtplib.SMTP(ec["smtp_host"], ec["smtp_port"]) as server:
        server.starttls()
        server.login(ec["from_address"], ec["app_password"])
        server.send_message(msg)

    print(f"[alert] Email elkuldve: {len(posts)} post")


def _post_section(post: dict) -> dict:
    """Egy jel egy Slack section-blokkja. A 3000 karakteres limit KEMENY korlat."""
    meta = f"Platform: {post['platform']} | Szerzo: {post.get('author', '')}"
    if post.get("severity") is not None:
        intent = " | 🎯 buying intent" if post.get("buying_intent") else ""
        meta += f"\nSúlyosság: *{post.get('severity')}/5*{intent}"
    pain = f"\n_{post['pain_summary']}_" if post.get("pain_summary") else ""
    text = (
        f"*{post.get('title', '(cim nelkul)')}*\n"
        f"{meta}{pain}\n"
        f"Kulcsszavak: `{post.get('keywords', '')}`\n"
        f"<{post.get('url', '')}|Megnyit>"
    )
    if len(text) > SLACK_SECTION_MAX_CHARS:
        text = text[:SLACK_SECTION_MAX_CHARS - 20].rstrip() + "\n_[levagva]_"
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def send_slack(posts: list[dict], alert_config: dict) -> bool:
    """
    MINDEN jelet kikuld, tobb uzenetre lapozva.

    Miert nem egy uzenet: a Slack Block Kit **50 blokk / uzenet** korlatot ir elo,
    a section-blokk `text` mezoje pedig max **3000 karakter**
    (docs.slack.dev/reference/block-kit/blocks es .../blocks/section-block).
    A korabbi verzio ezt ugy kerulte meg, hogy csak az elso 5 jelet reszletezte,
    a tobbit egy "... es meg N tovabbi" sorba osszesitette — a 2026-07-27-i
    allapotban ez 90 felgyult jelbol 85-ot gyakorlatilag lathatatlanul
    "elhasznalt" volna (a digest utana 'alerted'-re allitja mindet).

    A kikuldes koze 1,2 s szunet kerul: az incoming webhook limitje
    **1 uzenet / masodperc**, rovid burst megengedett, de nincs garancia a
    megjelenitesre (docs.slack.dev/apis/web-api/rate-limits).

    Visszaad: True CSAK ha minden lap kimen. Ha egy lap elbukik, False —
    a hivo (run_digest) ilyenkor NEM allitja 'alerted'-re a posztokat, tehat a
    kovetkezo futas ujra probalja. Ez tudatos csere: ismetles elfogadhato,
    jelvesztes nem.
    """
    if not posts:
        return False

    webhook = slack_webhook_url(alert_config)
    if not webhook:
        print(f"[alert] Slack be van kapcsolva, de nincs webhook-URL "
              f"({SLACK_WEBHOOK_ENV} a .env-ben) — kihagy.")
        return False

    sc = alert_config.get("slack", {}) or {}
    per_msg = int(sc.get("posts_per_message", SLACK_POSTS_PER_MESSAGE_DEFAULT))
    # Fejlec + jelek: a fejlec is EGY blokk, ezert a felso korlat 49 jel/uzenet.
    per_msg = max(1, min(per_msg, SLACK_MAX_BLOCKS_PER_MESSAGE - 1))

    chunks = [posts[i:i + per_msg] for i in range(0, len(posts), per_msg)]
    total_pages = len(chunks)

    for page, chunk in enumerate(chunks, 1):
        suffix = f" ({page}/{total_pages})" if total_pages > 1 else ""
        blocks = [{
            "type": "header",
            "text": {"type": "plain_text", "text": f"NODU Monitor: {len(posts)} uj talalat{suffix}"},
        }]
        blocks += [_post_section(p) for p in chunk]

        try:
            _post_slack_blocks(webhook, blocks)
        except Exception as e:
            remaining = len(posts) - sum(len(c) for c in chunks[:page - 1])
            print(f"[alert] Slack hiba a {page}/{total_pages}. lapon: {e}. "
                  f"{remaining} jel NEM ment ki — a posztok 'new'-ban maradnak.")
            return False

        print(f"[alert] Slack lap {page}/{total_pages} elkuldve ({len(chunk)} jel).")
        if page < total_pages:
            time.sleep(SLACK_MESSAGE_PAUSE_SECONDS)

    print(f"[alert] Slack uzenet elkuldve: {len(posts)} post, {total_pages} uzenetben")
    return True


def send_webhook(posts: list[dict], alert_config: dict) -> bool:
    """
    n8n webhook — SalesOS lead-létrehozáshoz.
    True, ha a payload tényleg kiment; False minden más esetben (letiltva,
    nincs URL, nincs küszöb feletti elem, vagy hiba).
    """
    wc = alert_config.get("webhook", {})
    if not wc.get("enabled") or not wc.get("url"):
        return False

    min_score = wc.get("min_score", 5)
    eligible = [p for p in posts if p.get("score", 0) >= min_score]
    if not eligible:
        return False

    payload = {
        "source": "nodu-monitor",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "leads": [
            {
                "platform": p["platform"],
                "source": p["source"],
                "title": p.get("title", ""),
                "author": p.get("author", ""),
                "url": p.get("url", ""),
                "score": p.get("score", 0),
                "keywords": p.get("keywords", ""),
                "body_excerpt": (p.get("body") or "")[:500],
                "created_at": p.get("created_at", ""),
            }
            for p in eligible
        ],
    }

    try:
        resp = requests.post(
            wc["url"],
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        print(f"[alert] Webhook elküldve: {len(eligible)} lead → n8n")
        return True
    except Exception as e:
        print(f"[alert] Webhook hiba: {e}")
        return False


_HEALTH_LABELS = {
    "error": "HIBÁS — minden vizsgált futás kivétellel állt le",
    "blind": "NEM LÁT SEMMIT — 0 nyers elem (szelektor/API-törés)",
    # A HIANYZO futas: utemezve van, de nem fut. 2026-07-28-ig lathatatlan volt,
    # mert a heartbeat csak a mar lefutott korokat vizsgalta (audit §2.2).
    "stale": "NEM FUT — az ütemezés szerint futnia kellene",
}


def send_health_alert(problems: list[dict], alert_config: dict) -> list[str]:
    """
    Connector-egeszseg riasztas (storage.db.get_connector_health kimenetebol).

    Ez a rendszer legfontosabb ora: 2026-07-21 → 07-24 kozott a Playwright 46
    egymast koveto futason keresztul halott volt, a revitforum 5+ heten at 0
    elemet hozott — es SEMMI nem jelezte, mert a "0 uj talalat" es a "csendben
    eltort" ugyanugy nezett ki (ld. docs/02-lead-volume-audit-2026-07.md §3.11).

    Visszaad: azon csatornak listaja, amelyekre a kuldes sikerult.
    """
    if not problems:
        return []

    lines = []
    for p in problems:
        label = _HEALTH_LABELS.get(p["status"], p["status"])
        detail = f"*{p['connector']}* — {label}"
        if p.get("items_seen_in_window") is not None:
            detail += f"\n  Utolsó {p['runs_considered']} futás: {p['items_seen_in_window']} elem, {p['new_posts_in_window']} új poszt"
        if p.get("last_error"):
            detail += f"\n  Hiba: `{str(p['last_error'])[:200]}`"
        if p.get("last_run"):
            detail += f"\n  Utolsó futás: {p['last_run'][:19]}"
        lines.append(detail)

    text = "\n\n".join(lines)
    delivered: list[str] = []

    sc = alert_config.get("slack", {})
    slack_url = slack_webhook_url(alert_config) if sc.get("enabled") else ""
    if slack_url:
        blocks = [
            {"type": "header", "text": {"type": "plain_text",
                                        "text": f"⚠️ NODU Monitor: {len(problems)} connector nem termel"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": text}},
        ]
        try:
            _post_slack_blocks(slack_url, blocks)
            delivered.append("slack")
        except Exception as e:
            print(f"[health] Slack-kuldes hiba: {e}")

    ec = alert_config.get("email", {})
    if ec.get("enabled"):
        try:
            msg = EmailMessage()
            msg["Subject"] = f"NODU Monitor: {len(problems)} connector nem termel"
            msg["From"] = ec["from_address"]
            msg["To"] = ec["to_address"]
            msg.set_content(text.replace("*", "").replace("`", ""))
            with smtplib.SMTP(ec["smtp_host"], ec["smtp_port"]) as server:
                server.starttls()
                server.login(ec["from_address"], ec["app_password"])
                server.send_message(msg)
            delivered.append("email")
        except Exception as e:
            print(f"[health] Email-kuldes hiba: {e}")

    return delivered


def send_weekly_digest(stats: dict, alert_config: dict, subscriber_count: int = None, trend_analysis: str = "") -> None:
    """
    Heti Slack-osszefoglalo a scraper statisztikaibol (storage.db.get_weekly_stats).
    Opcionálisan hozzáfűzi a Gemini AI trendelemzését (trend_analysis).
    """
    ready, reason = slack_status(alert_config)
    if not ready:
        print(f"[digest] Slack nincs engedelyezve ({reason}). Kihagy.")
        return
    slack_url = slack_webhook_url(alert_config)

    days = stats.get("lookback_days", 7)
    total = stats.get("total_posts", 0)
    pending = stats.get("pending_drafts", 0)
    by_platform = stats.get("by_platform", [])
    top_pain = stats.get("top_pain_points", [])[:8]

    plat_lines = "\n".join(f"- {p['platform']}: {p['count']}" for p in by_platform) or "- nincs uj poszt"
    pain_lines = "\n".join(f"- {p['keyword']}: {p['count']}" for p in top_pain) or "- nincs adat"

    summary = f"*Uj posztok:* {total}\n*Joovahagyasra varo draft:* {pending}"
    if subscriber_count is not None:
        summary += f"\n*Uj wishlist feliratkozo:* {subscriber_count}"

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"NODU heti osszefoglalo (utolso {days} nap)"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": summary}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Forrasonkent:*\n{plat_lines}"}}
    ]

    if trend_analysis:
        blocks.append({"type": "divider"})
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"🧠 *AI Trendelemzés (Fájdalom-klaszterek)*\n\n{trend_analysis}"}})
    else:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*Top fájdalompontok:*\n{pain_lines}"}})

    try:
        _post_slack_blocks(slack_url, blocks)
        print("[digest] Heti osszefoglalo elkuldve Slack-re.")
    except Exception as e:
        print(f"[digest] Heti osszefoglalo hiba: {e}")


def send_content_pipeline_ideas(pipeline_data: dict, alert_config: dict) -> None:
    """Tartalommarketing pipeline (blog + linkedin teaserek) Slack-re (responder.generate_content_pipeline)."""
    sc = alert_config.get("slack", {})
    slack_url = slack_webhook_url(alert_config) if sc.get("enabled") else ""
    if not slack_url or not pipeline_data:
        return

    blog_title = pipeline_data.get("blog_title", "Nincs cím")
    blog_audience = pipeline_data.get("blog_audience", "-")
    blog_problem = pipeline_data.get("blog_core_problem", "-")
    blog_outline = pipeline_data.get("blog_outline", "-")
    posts = pipeline_data.get("linkedin_posts", [])

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "📝 Tartalommarketing Javaslat (Content Pipeline)"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Új Szakmai Blogcikk Ötlet:*\n*{blog_title}*"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Célközönség:* {blog_audience}\n*Fő fájdalom:* {blog_problem}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Vázlat:*\n{blog_outline}"}},
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Kísérő LinkedIn Teaser posztok ({len(posts)} db):*"}}
    ]

    for i, p in enumerate(posts, 1):
        text = p if len(p) <= 2800 else p[:2800] + " [...]"
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*Poszt {i}*\n{text}"}})

    try:
        _post_slack_blocks(slack_url, blocks)
        print(f"[content-pipeline] Javaslat elküldve Slack-re.")
    except Exception as e:
        print(f"[content-pipeline] Slack-küldés hiba: {e}")


def send_slack_test(alert_config: dict) -> bool:
    """
    Egyszeri teszt-uzenet a beallitott csatornara (`python main.py --test-slack`).

    Miert kell sajat ut: a napi digest csak akkor kuld, ha VAN kikuldheto jel,
    a heartbeat pedig csak akkor, ha VAN hibas connector — tehat egy friss
    webhook-beallitast egyik uttal sem lehet azonnal igazolni. Ez a fuggveny
    ugyanazt a `_post_slack_blocks` utat hasznalja, mint az eles riasztasok,
    igy amit itt latsz, az a valodi lanc.
    """
    ready, reason = slack_status(alert_config)
    if not ready:
        print(f"[test-slack] Nem kesz: {reason}")
        return False

    url = slack_webhook_url(alert_config)
    print(f"[test-slack] Webhook: {url[:34]}... (hossz: {len(url)})")
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "NODU Monitor: teszt-uzenet"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": (
            "Ez a `--test-slack` teszt-uzenete. Ha ezt latod, a riasztasi lanc kesz:\n"
            "- napi fajdalom-digest (`alerts.digest_hour`)\n"
            "- connector-heartbeat (`health.check_interval_hours`)\n"
            "- heti osszefoglalo + tartalom-javaslatok"
        )}},
        {"type": "context", "elements": [
            {"type": "mrkdwn", "text": f"Generalva: {datetime.now(tz=timezone.utc).isoformat(timespec='seconds')}"}
        ]},
    ]
    try:
        _post_slack_blocks(url, blocks)
        print("[test-slack] Elkuldve (HTTP 200).")
        return True
    except Exception as e:
        print(f"[test-slack] HIBA: {e}")
        return False


def send_alerts(posts: list[dict], alert_config: dict) -> list[str]:
    """
    Riasztas kikuldese minden engedelyezett csatornara.

    Visszaad: azon csatornak listaja, amelyekre a kuldes TENYLEGESEN sikerult
    (pl. ["slack"]). Ures lista = semmi nem ment ki (minden csatorna le van
    tiltva, vagy mind hibara futott). A hivo ez alapjan dontheti el, hogy
    szabad-e a posztokat "alerted"-re allitani — korabban a napi digest akkor
    is elfogyasztotta oket, ha egyetlen csatorna sem volt bekapcsolva
    (ld. docs/02-lead-volume-audit-2026-07.md §3.6).
    """
    if not posts:
        print("[alert] Nincs uj releváns bejegyzes.")
        return []

    delivered: list[str] = []

    if alert_config.get("email", {}).get("enabled"):
        try:
            send_email(posts, alert_config)
            delivered.append("email")
        except Exception as e:
            print(f"[alert] Email hiba: {e}")

    if alert_config.get("slack", {}).get("enabled"):
        try:
            # A visszateresi ertek SZAMIT: `enabled: true` + hianyzo webhook-URL
            # eseten a send_slack kivetel nelkul kihagyja magat — ha itt vakon
            # "slack"-et irnank a delivered-be, a run_digest 'alerted'-re
            # allitana a posztokat anelkul, hogy barhova kimentek volna.
            # Ez ugyanaz a hibaosztaly, mint §3.6 (a digest "elfogyasztotta" oket).
            if send_slack(posts, alert_config):
                delivered.append("slack")
        except Exception as e:
            print(f"[alert] Slack hiba: {e}")

    if send_webhook(posts, alert_config):
        delivered.append("webhook")

    if not delivered:
        print(
            "[alert] FIGYELEM: egyetlen riasztasi csatorna sem kuldott ki semmit "
            "(alerts.email/slack/webhook mind letiltva vagy hibas). "
            f"{len(posts)} talalat a DB-ben marad 'new' statuszban."
        )

    return delivered
