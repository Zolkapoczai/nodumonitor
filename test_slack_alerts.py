"""
A Slack-riasztasi lanc verifikacioja VALODI webhook nelkul.

Amit mer:
 1. URL nelkul: minden Slack-ut kihagyja magat, send_alerts NEM ad vissza 'slack'-et
    (ez a §3.6-os hibaosztaly: a digest nem "fogyaszthatja el" a posztokat).
 2. Rossz prefixu URL: elutasitva (nem megy ki HTTP-kereses egy random hostra).
 3. Ervenyes URL-lel: a 4 Slack-ut mind kikuld, a payload valid Block Kit,
    es send_alerts 'slack'-et ad vissza. A halozati hivas monkeypatchelve.
 4. HTTP-hiba eseten: send_alerts NEM jelenti kikuldottnek.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import alerts.notifier as N  # noqa: E402
import env_secrets  # noqa: E402

# HERMETIKUS: a teszt NEM olvashatja a valodi .env-et, kulonben az ott levo eles
# SLACK_WEBHOOK_URL miatt az "URL nelkul" csoport hamis allapotbol indul (ez 8
# tesztet buktatott, amikor a webhook elesedett — a kod nem valtozott kozben).
env_secrets._ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    ".env.does-not-exist-for-tests")
env_secrets._cache = None

# A teszt-webhook URL-t RESZEKBOL rakjuk ossze, nem egy literalbol. Ok: a GitHub
# secret-scanning push-protection a `hooks.slack.com/services/...` MINTAT blokkolja
# — helyesen, mert nem tudja megallapitani, hogy szintetikus-e. Egy teszt-fajl miatt
# nem kerunk kivetelt a vedelem alol.
FAKE = ("https://hooks.slack.com/" + "services/"
        + "T" + "0" * 8 + "/" + "B" + "0" * 8 + "/" + "X" * 24)
POSTS = [{
    "platform": "osarch", "source": "community.osarch.org", "title": "IFC roundtrip loses parameters",
    "author": "tester", "url": "https://example.invalid/t/1", "score": 12,
    "keywords": "ifc,revit", "severity": 4, "buying_intent": 1, "confidence": 0.8,
    "pain_summary": "Archicad->Revit atvitelnel elveszik a parameter.", "body": "x" * 50,
    "created_at": "2026-07-20T10:00:00", "id": 1,
}]
PROBLEMS = [{"connector": "playwright", "status": "blind", "items_seen_in_window": 0,
             "new_posts_in_window": 0, "runs_considered": 5, "last_error": None,
             "last_run": "2026-07-27T10:00:00"}]
STATS = {"lookback_days": 7, "total_posts": 5, "pending_drafts": 2,
         "by_platform": [{"platform": "github", "count": 3}], "top_pain_points": []}
PIPELINE = {"blog_title": "T", "blog_audience": "A", "blog_core_problem": "P",
            "blog_outline": "O", "linkedin_posts": ["p1"]}

sent = []
fails = []
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


class Resp:
    status_code = 200

    def raise_for_status(self):
        return None


class ErrResp:
    status_code = 404

    def raise_for_status(self):
        raise RuntimeError("404 no_service")


def fake_post(url, **kw):
    sent.append((url, json.loads(kw.get("data") or json.dumps(kw.get("json")))))
    return ErrResp() if fails else Resp()


N.requests.post = fake_post

# --- 1. URL nelkul -----------------------------------------------------------
os.environ.pop("SLACK_WEBHOOK_URL", None)
env_secrets._cache = None
cfg_no_url = {"slack": {"enabled": True, "webhook_url": ""}}
ready, reason = N.slack_status(cfg_no_url)
check("1a URL nelkul nem kesz", not ready, reason)
check("1b send_slack False-t ad", N.send_slack(POSTS, cfg_no_url) is False)
sent.clear()
delivered = N.send_alerts(POSTS, cfg_no_url)
check("1c send_alerts nem jelent slack-et", delivered == [], f"delivered={delivered}")
check("1d nem tortent HTTP-hivas", not sent, f"sent={len(sent)}")
check("1e health-alert sem kuld", N.send_health_alert(PROBLEMS, cfg_no_url) == [])
check("1f placeholder ures URL-nek szamit",
      N.slack_webhook_url({"slack": {"enabled": True, "webhook_url": "YOUR_SLACK_WEBHOOK_URL"}}) == "")

# --- 2. rossz prefix ---------------------------------------------------------
bad = {"slack": {"enabled": True, "webhook_url": "https://evil.example.invalid/hook"}}
check("2a rossz host elutasitva", N.slack_webhook_url(bad) == "")
sent.clear()
check("2b nem kuld ra", N.send_alerts(POSTS, bad) == [] and not sent)

# --- 3. ervenyes URL (env-bol, config.yaml URESEN) --------------------------
os.environ["SLACK_WEBHOOK_URL"] = FAKE
cfg = {"slack": {"enabled": True, "webhook_url": ""}}
check("3a env-bol oldja fel", N.slack_webhook_url(cfg) == FAKE)
ready, reason = N.slack_status(cfg)
check("3b kesz", ready, reason)

sent.clear()
delivered = N.send_alerts(POSTS, cfg)
check("3c send_alerts slack-et jelent", delivered == ["slack"], f"delivered={delivered}")
check("3d egy hivas a jo URL-re", len(sent) == 1 and sent[0][0] == FAKE)
body = sent[0][1]
check("3e Block Kit szerkezet", "blocks" in body and body["blocks"][0]["type"] == "header")
txt = json.dumps(body, ensure_ascii=False)
check("3f a jel tartalma benne van", "Archicad" in txt and "example.invalid" in txt)
check("3g severity megjelenik", "4/5" in txt)

sent.clear()
check("3h health-alert kikuld", N.send_health_alert(PROBLEMS, cfg) == ["slack"])
check("3i heartbeat-tartalom", "playwright" in json.dumps(sent[0][1], ensure_ascii=False))

sent.clear()
N.send_weekly_digest(STATS, cfg, trend_analysis="trend")
check("3j heti osszefoglalo kimegy", len(sent) == 1 and "trend" in json.dumps(sent[0][1]))

sent.clear()
N.send_content_pipeline_ideas(PIPELINE, cfg)
check("3k content-pipeline kimegy", len(sent) == 1)

sent.clear()
check("3l --test-slack ut", N.send_slack_test(cfg) is True and len(sent) == 1)

# --- 3M. lapozas: MINDEN jel kimegy, a Block Kit korlatokon belul -----------
N.time.sleep = lambda s: None  # a teszt ne varjon a rate-limit szunetekre


def many(n, body_len=200):
    out = []
    for i in range(n):
        p = dict(POSTS[0])
        p.update(id=i + 1, title=f"Jel #{i + 1}", url=f"https://example.invalid/t/{i + 1}",
                 pain_summary="x" * body_len)
        out.append(p)
    return out


sent.clear()
BIG = many(90)
check("3m1 90 jel kikuldve", N.send_slack(BIG, cfg) is True)
check("3m2 5 uzenetre lapozva (20/uzenet)", len(sent) == 5, f"uzenetek={len(sent)}")
check("3m3 blokk-limit betartva (<=50)",
      all(len(m[1]["blocks"]) <= 50 for m in sent),
      f"max={max(len(m[1]['blocks']) for m in sent)}")
check("3m4 section-limit betartva (<=3000)",
      all(len(b["text"]["text"]) <= 3000
          for m in sent for b in m[1]["blocks"] if b["type"] == "section"))
titles = "".join(json.dumps(m[1], ensure_ascii=False) for m in sent)
check("3m5 MIND a 90 jel benne van (nincs '... es meg N')",
      all(f"Jel #{i}" in titles for i in range(1, 91)) and "es meg" not in titles)
check("3m6 lapszamozas a fejlecben", "(1/5)" in titles and "(5/5)" in titles)
check("3m7 egy lapon nincs fejlec-suffix", "(1/1)" not in json.dumps(
    (sent.clear(), N.send_slack(POSTS, cfg), sent[0][1])[2], ensure_ascii=False))

# tul hosszu section levagva, nem hibara futva
sent.clear()
check("3m8 3000 feletti szoveg levagva",
      N.send_slack(many(1, body_len=5000), cfg) is True
      and len(sent[0][1]["blocks"][1]["text"]["text"]) <= 3000
      and "levagva" in sent[0][1]["blocks"][1]["text"]["text"])

# config-kapcsolo es a kemeny felso korlat
sent.clear()
cfg5 = {"slack": {"enabled": True, "webhook_url": "", "posts_per_message": 5}}
check("3m9 posts_per_message=5 -> 18 uzenet", N.send_slack(BIG, cfg5) and len(sent) == 18)
sent.clear()
cfg_over = {"slack": {"enabled": True, "webhook_url": "", "posts_per_message": 500}}
check("3m10 tul nagy ertek 49-re vagva (fejlec+49=50)",
      N.send_slack(BIG, cfg_over) and max(len(m[1]["blocks"]) for m in sent) == 50)

# reszleges hiba: NEM szamit kikuldottnek -> a jelek 'new'-ban maradnak
calls = {"n": 0}
_orig_post = N.requests.post


def flaky(url, **kw):
    calls["n"] += 1
    if calls["n"] == 3:
        sent.append((url, json.loads(kw.get("data"))))
        return ErrResp()
    return _orig_post(url, **kw)


sent.clear()
N.requests.post = flaky
check("3m11 reszleges hiba -> False", N.send_slack(BIG, cfg) is False)
check("3m12 a bukas utan nem kuld tovabb", len(sent) == 3, f"uzenetek={len(sent)}")
N.requests.post = _orig_post

sent.clear()
calls["n"] = 0
N.requests.post = flaky
check("3m13 send_alerts sem jelenti kikuldottnek reszleges hibanal",
      N.send_alerts(BIG, cfg) == [])
N.requests.post = _orig_post

# --- 4. HTTP-hiba ------------------------------------------------------------
fails.append(1)
sent.clear()
delivered = N.send_alerts(POSTS, cfg)
check("4a hibas kuldes nem 'delivered'", delivered == [], f"delivered={delivered}")
check("4b health-alert sem", N.send_health_alert(PROBLEMS, cfg) == [])
check("4c test-slack False", N.send_slack_test(cfg) is False)
fails.clear()

# --- 5. enabled: false ------------------------------------------------------
off = {"slack": {"enabled": False, "webhook_url": ""}}
sent.clear()
check("5a kikapcsolt csatorna nem kuld", N.send_alerts(POSTS, off) == [] and not sent)

print()
bad_count = 0
for name, ok, detail in results:
    if not ok:
        bad_count += 1
    print(f"  {'OK  ' if ok else 'FAIL'} {name}" + (f"   [{detail}]" if detail else ""))
print(f"\n{len(results) - bad_count}/{len(results)} teszt zold.")
sys.exit(1 if bad_count else 0)
