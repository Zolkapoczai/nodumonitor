import smtplib
import json
import requests
from email.message import EmailMessage
from datetime import datetime, timezone


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


def send_slack(posts: list[dict], alert_config: dict) -> None:
    sc = alert_config["slack"]
    if not posts:
        return

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"NODU Monitor: {len(posts)} uj talalat"},
        }
    ]

    for p in posts[:5]:  # max 5 Slack blokk
        meta = f"Platform: {p['platform']} | Szerzo: {p.get('author', '')}"
        if p.get("severity") is not None:
            intent = " | 🎯 buying intent" if p.get("buying_intent") else ""
            meta += f"\nSúlyosság: *{p.get('severity')}/5*{intent}"
        pain = f"\n_{p['pain_summary']}_" if p.get("pain_summary") else ""
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{p.get('title', '(cim nelkul)')}*\n"
                    f"{meta}{pain}\n"
                    f"Kulcsszavak: `{p.get('keywords', '')}`\n"
                    f"<{p.get('url', '')}|Megnyit>"
                ),
            },
        })

    if len(posts) > 5:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"... es meg {len(posts) - 5} tovabbi találat."},
        })

    _post_slack_blocks(sc["webhook_url"], blocks)
    print(f"[alert] Slack uzenet elkuldve: {len(posts)} post")


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
    if sc.get("enabled") and sc.get("webhook_url"):
        blocks = [
            {"type": "header", "text": {"type": "plain_text",
                                        "text": f"⚠️ NODU Monitor: {len(problems)} connector nem termel"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": text}},
        ]
        try:
            _post_slack_blocks(sc["webhook_url"], blocks)
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
    sc = alert_config.get("slack", {})
    if not sc.get("enabled") or not sc.get("webhook_url"):
        print("[digest] Slack nincs engedelyezve. Kihagy.")
        return

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
        _post_slack_blocks(sc["webhook_url"], blocks)
        print("[digest] Heti osszefoglalo elkuldve Slack-re.")
    except Exception as e:
        print(f"[digest] Heti osszefoglalo hiba: {e}")


def send_content_pipeline_ideas(pipeline_data: dict, alert_config: dict) -> None:
    """Tartalommarketing pipeline (blog + linkedin teaserek) Slack-re (responder.generate_content_pipeline)."""
    sc = alert_config.get("slack", {})
    if not sc.get("enabled") or not sc.get("webhook_url") or not pipeline_data:
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
        _post_slack_blocks(sc["webhook_url"], blocks)
        print(f"[content-pipeline] Javaslat elküldve Slack-re.")
    except Exception as e:
        print(f"[content-pipeline] Slack-küldés hiba: {e}")


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
            send_slack(posts, alert_config)
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
