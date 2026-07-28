"""
A 2026-07-28-i P1-es javitasok tesztje (docs/04-rendszer-audit-2026-07-28.md §2).

A) §2.1  a draft-generalas NEM allitja 'alerted'-re a posztot
B) §2.4  a tudasbazis nincs a forum-draft promptban, a heti uton pedig levagva van
C) §2.5  ujraindulas utan az elso futas az UTOLSO futasbol szamolodik, nem "most"
D) §2.2  a heartbeat 'stale'-nek jelzi azt, ami utemezve van, de nem fut
E) §2.3  a backup es a digest `runs`-bejegyzest ir
F) §2.6  a naplo-szuro maszkolja a kulcsokat es a webhook-URL-t
G) §2.7  a kapu minden mutalo vegponton zar, es a parhuzamos inditas 409
"""
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


def utc(delta_minutes=0):
    return (datetime.now(tz=timezone.utc) + timedelta(minutes=delta_minutes)).isoformat()


# --- A) §2.1: a draft nem "fogyasztja el" a jelet ---------------------------
import responder.draft_generator as dg  # noqa: E402

src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "responder", "draft_generator.py"), encoding="utf-8").read()
active_calls = [ln for ln in src.splitlines()
                if "mark_alerted(" in ln and not ln.strip().startswith("#")]
check("A1 nincs aktiv mark_alerted hivas a draft-generalasban",
      not active_calls, f"{active_calls}")
check("A2 a mark_alerted importja is kikerult", "mark_alerted" not in src.split("def ")[0]
      or "import" not in src.split("mark_alerted")[0].splitlines()[-1])

# --- B) §2.4: tudasbazis a promptban ---------------------------------------
kb_dir = tempfile.mkdtemp(prefix="nodu-kb-")
kb_file = os.path.join(kb_dir, "kb.md")
open(kb_file, "w", encoding="utf-8").write("BELSO SPRINT-TERV\n" + ("x" * 300_000))
cfg_kb = {"knowledge_base": {"output_file": kb_file, "prompt_max_chars": 8000}}

sys_prompt = dg._build_system_prompt(cfg_kb)
check("B1 a forum-draft system prompt NEM tartalmazza a tudasbazist",
      "BELSO SPRINT-TERV" not in sys_prompt and len(sys_prompt) < 10_000,
      f"hossz={len(sys_prompt)}")
excerpt = dg._load_knowledge_base(cfg_kb)
check("B2 a heti uton levagva jon (<=8000 + fejlec)", 0 < len(excerpt) <= 8200, f"{len(excerpt)}")
check("B3 a levagas jelolve van", "levagva" in excerpt)
check("B4 nem letezo fajlra ures string", dg._load_knowledge_base(
    {"knowledge_base": {"output_file": os.path.join(kb_dir, "nincs.md")}}) == "")

# --- C) §2.5: elso futas ujraindulas utan ----------------------------------
from storage.db import init_db, log_run, get_last_run_times  # noqa: E402
import main as m  # noqa: E402

db = os.path.join(tempfile.mkdtemp(prefix="nodu-sched-"), "t.db")
init_db(db)
# 'zendesk' 10 perce futott, a periodusa 720 perc -> NEM most kell futnia
log_run(db, "zendesk", utc(-10), utc(-9), new_posts=0, items_seen=5)
# 'playwright' 5 oraja futott, periodus 90 perc -> mar esedekes
log_run(db, "playwright", utc(-300), utc(-299), new_posts=1, items_seen=40)

check("C1 get_last_run_times mindket connectort adja",
      set(get_last_run_times(db)) == {"zendesk", "playwright"})

planner = m._FirstRunPlanner(db)
now = datetime.now(tz=timezone.utc)
zd_next = planner.next_run("zendesk", 720)
pw_next = planner.next_run("playwright", 90)
never_next = planner.next_run("uj-connector", 240)
check("C2 a friss zendesk NEM indul azonnal (~710 perc mulva)",
      600 < (zd_next - now).total_seconds() / 60 < 720,
      f"{(zd_next - now).total_seconds()/60:.0f} perc")
check("C3 a lejart playwright hamar indul (<5 perc)",
      0 < (pw_next - now).total_seconds() / 60 < 5)
check("C4 a sosem futott connector is hamar indul",
      0 < (never_next - now).total_seconds() / 60 < 5)
check("C5 a start szet van teritve (nem mind ugyanakkor)",
      pw_next != never_next)

# --- D) §2.2: stale statusz ------------------------------------------------
from storage.db import get_connector_health  # noqa: E402

db2 = os.path.join(tempfile.mkdtemp(prefix="nodu-health-"), "t.db")
init_db(db2)
for i in range(5):                      # egeszseges, most futott
    log_run(db2, "github", utc(-i * 10 - 5), utc(-i * 10 - 4), new_posts=1, items_seen=20)
for i in range(5):                      # regen futott: 'stale' jelolt
    log_run(db2, "vanilla", utc(-5000 - i * 10), utc(-4999 - i * 10), new_posts=0, items_seen=10)

expected = {"github": 240, "vanilla": 240, "sosem-futott": 60}
rep_old = {r["connector"]: r["status"] for r in get_connector_health(db2, window=5)}
rep_new = {r["connector"]: r["status"]
           for r in get_connector_health(db2, window=5, expected=expected, stale_factor=2.5)}
check("D1 a regi viselkedes csak a futott connectort latta",
      set(rep_old) == {"github"}, f"{rep_old}")
check("D2 a regen futott connector STALE", rep_new.get("vanilla") == "stale", f"{rep_new}")
check("D3 a sosem futott connector is STALE", rep_new.get("sosem-futott") == "stale")
check("D4 az egeszseges connector marad OK", rep_new.get("github") == "ok")
stale_row = next(r for r in get_connector_health(db2, window=5, expected=expected)
                 if r["connector"] == "sosem-futott")
check("D5 a stale sor indoklast is ad", "soha nem futott" in (stale_row["last_error"] or ""))

# --- E) §2.3: backup/digest runs-bejegyzes ---------------------------------
db3 = os.path.join(tempfile.mkdtemp(prefix="nodu-backup-"), "t.db")
init_db(db3)
# Kell bele legalabb egy poszt: a §12-es snapshot-ellenorzes ELUTASITJA a 0 posztos
# mentest ("gyanusan ures"), tehat egy teljesen ures DB-n a backup szandekosan
# None-t ad. Ez a ket javitas kolcsonhatasa, nem hiba.
from storage.db import insert_post as _insert_post  # noqa: E402
_insert_post(db3, {"source": "t", "platform": "osarch", "external_id": "b1",
                   "url": "https://example.invalid/b1", "author": "a", "title": "Backup fixture",
                   "body": "b", "created_at": "2026-07-27T10:00:00+00:00",
                   "fetched_at": "2026-07-27T10:00:00+00:00", "keywords": "ifc", "score": 5})
cfg_b = {"backup": {"enabled": True, "keep": 2}, "database": {"path": os.path.basename(db3)}}
path = m.run_backup(cfg_b, db3)
conn = sqlite3.connect(db3)
rows = conn.execute("SELECT connector, new_posts, error FROM runs WHERE connector='backup'").fetchall()
conn.close()
check("E1 a backup runs-bejegyzest ir", len(rows) == 1, f"{rows}")
check("E2 sikeres backup: nincs error es new_posts=1",
      rows and rows[0][1] == 1 and rows[0][2] is None, f"{rows}")
check("E3 a snapshot tenylegesen letrejott", bool(path) and os.path.exists(path))

sched = m.connector_schedule({"backup": {"enabled": True}, "alerts": {"daily_digest": True},
                              "vanilla": {"enabled": False}, "zendesk": {"enabled": False},
                              "web_search": {"enabled": False}})
names = {e["name"] for e in sched}
check("E4 a backup es a digest is a heartbeat latokoreben van",
      {"backup", "digest"} <= names, f"{sorted(names)}")
check("E5 a cron_only jelolt jobokat az utemezo kihagyja",
      all(e.get("cron_only") for e in sched if e["name"] in ("backup", "digest")))
check("E6 a letiltott connector nincs a listaban",
      not ({"vanilla", "zendesk", "websearch"} & names))

# --- F) §2.6: napló-maszkolás ---------------------------------------------
import server  # noqa: E402

red = server._SecretRedactingFilter.redact
# SZINTETIKUS kulcs, szandekosan osszerakva: a valodi (a logban talalt) kulcsot NEM
# irjuk teszt-fajlba, mert az a repoba kerulne — a GitHub push-protection joggal
# blokkolna, es a szivargas csak atkerulne a logbol a verziokezelobe.
FAKE_GOOGLE_KEY = "AIza" + "Sy" + ("X" * 33)
check("F1 Google-kulcs maszkolva",
      FAKE_GOOGLE_KEY not in red(
          f"GET https://www.googleapis.com/customsearch/v1?key={FAKE_GOOGLE_KEY}&cx=1"))
check("F2 Slack webhook maszkolva",
      "T0123" not in red("POST https://hooks.slack.com/services/T0123/B0456/abcdefgh failed"))
check("F3 ?key= parameter maszkolva", red("...?key=titkos123").endswith("***REDACTED***"))
check("F4 Bearer token maszkolva", "abcdefghijklmnop" not in red("Authorization: Bearer abcdefghijklmnop"))
check("F5 a normal szoveg valtozatlan",
      red("[playwright] graphisoft: 3 uj bejegyzes (48 elem latva)")
      == "[playwright] graphisoft: 3 uj bejegyzes (48 elem latva)")

# --- G) §2.7: kapu + egyidejuseg ------------------------------------------
import ui.app as uiapp  # noqa: E402

db4 = os.path.join(tempfile.mkdtemp(prefix="nodu-gate-"), "t.db")
init_db(db4)
uiapp.get_db_path = lambda config: db4
uiapp.load_config = lambda: {"ui": {"admin_password": "titok"}, "database": {"path": db4},
                             "alerts": {}, "health": {}, "scoring": {}}
uiapp.app.config["TESTING"] = True
client = uiapp.app.test_client()

for path_, name in (("/save", "G1 /save"), ("/run/playwright", "G2 /run/<action>"),
                    ("/draft/1/approve", "G3 /draft/approve"), ("/draft/1/reject", "G4 /draft/reject"),
                    ("/lead/1/to-sales-os", "G5 /lead/to-sales-os"),
                    ("/lead/1/draft", "G6 /lead/draft"), ("/linkedin/compose", "G7 /linkedin/compose"),
                    ("/search/adhoc", "G8 /search/adhoc")):
    r = client.post(path_)
    check(f"{name} jelszo nelkul 401", r.status_code == 401, f"status={r.status_code}")

r = client.get("/admin")
check("G9 /admin GET is vedve (regi viselkedes megmarad)", r.status_code == 401)

# egyidejuseg: a masodik inditas nem indit uj szalat
uiapp._jobs["playwright"] = {"status": "running"}
started = uiapp._run_in_bg("playwright", lambda: 1)
check("G10 mar futo job nem indul ujra", started is False)
uiapp._jobs["playwright"] = {"status": "done"}
check("G11 befejezett job ujrainditható", uiapp._run_in_bg("playwright", lambda: 1) is True)

print()
bad = 0
for name, ok, detail in results:
    if not ok:
        bad += 1
    print(f"  {'OK  ' if ok else 'FAIL'} {name}" + (f"   [{detail}]" if detail else ""))
print(f"\n{len(results) - bad}/{len(results)} teszt zold.")
sys.exit(1 if bad else 0)
