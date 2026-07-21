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
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{p.get('title', '(cim nelkul)')}*\n"
                    f"Platform: {p['platform']} | Szerzo: {p.get('author', '')}\n"
                    f"Kulcsszavak: `{p.get('keywords', '')}` | Pontszam: {p.get('score', 0)}\n"
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


def send_webhook(posts: list[dict], alert_config: dict) -> None:
    """n8n webhook — SalesOS lead-létrehozáshoz."""
    wc = alert_config.get("webhook", {})
    if not wc.get("enabled") or not wc.get("url"):
        return

    min_score = wc.get("min_score", 5)
    eligible = [p for p in posts if p.get("score", 0) >= min_score]
    if not eligible:
        return

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
    except Exception as e:
        print(f"[alert] Webhook hiba: {e}")


def send_weekly_digest(stats: dict, alert_config: dict, subscriber_count: int = None) -> None:
    """
    Heti Slack-osszefoglalo a scraper statisztikaibol (storage.db.get_weekly_stats).
    Csak akkor kuld, ha a Slack engedelyezve van (alerts.slack.enabled + webhook_url).
    A subscriber_count opcionalis (wishlist feliratkozok szama SalesOS/n8n felol).
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
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Forrasonkent:*\n{plat_lines}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Top fajdalompontok:*\n{pain_lines}"}},
    ]

    try:
        _post_slack_blocks(sc["webhook_url"], blocks)
        print("[digest] Heti osszefoglalo elkuldve Slack-re.")
    except Exception as e:
        print(f"[digest] Heti osszefoglalo hiba: {e}")


def send_linkedin_suggestions(posts: list[str], alert_config: dict) -> None:
    """LinkedIn poszt-javaslatok Slack-re, joovahagyasra (responder.generate_linkedin_content)."""
    sc = alert_config.get("slack", {})
    if not sc.get("enabled") or not sc.get("webhook_url") or not posts:
        return

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"LinkedIn poszt-javaslatok ({len(posts)})"}}
    ]
    for i, p in enumerate(posts, 1):
        text = p if len(p) <= 2800 else p[:2800] + " [...]"
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*Javaslat {i}*\n{text}"}})
        blocks.append({"type": "divider"})

    try:
        _post_slack_blocks(sc["webhook_url"], blocks)
        print(f"[linkedin] {len(posts)} javaslat elkuldve Slack-re.")
    except Exception as e:
        print(f"[linkedin] Slack-kuldes hiba: {e}")


def send_alerts(posts: list[dict], alert_config: dict) -> None:
    if not posts:
        print("[alert] Nincs uj releváns bejegyzes.")
        return

    if alert_config.get("email", {}).get("enabled"):
        try:
            send_email(posts, alert_config)
        except Exception as e:
            print(f"[alert] Email hiba: {e}")

    if alert_config.get("slack", {}).get("enabled"):
        try:
            send_slack(posts, alert_config)
        except Exception as e:
            print(f"[alert] Slack hiba: {e}")

    send_webhook(posts, alert_config)
