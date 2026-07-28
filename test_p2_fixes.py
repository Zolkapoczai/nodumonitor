"""
A 2026-07-28-i P2-es javitasok tesztje (docs/04-rendszer-audit-2026-07-28.md §3, §5).

A) §3.4  markaemlites REGEXBOL (nem LLM-dontes)
B) §3.5  competitor_name csak IGAZOLT idezettel fogadhato el
C) §3.2  a confidence kikerult a rendezesbol, a buying_intent elorebb
D) §3.3  a SalesOS-score a buying_intent-tol is fugg (nem csak 6/8)
E) §3.8  FIFO classifier-sor + kiserlet-szamlalo (nincs kiehezes, nincs vegtelen retry)
F) §3.6  a letiltott connector nincs sem az utemezoben, sem a heartbeat elvarasaiban
G) §12   snapshot-ellenorzes (integrity_check + tabla-olvasas), serult mentes elutasitva
H) §5/11 a draft token-keret 320
"""
import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


# --- A) markaemlites regexbol -----------------------------------------------
from classifier.pain_classifier import (  # noqa: E402
    detect_brand_mention, verify_competitor, _SCHEMA, CLASSIFIER_VERSION,
)

check("A1 'NODU Bridge' felismerve", detect_brand_mention("We tried NODU Bridge last week"))
check("A2 csak 'nodu' is felismerve", detect_brand_mention("anyone used nodu for this?"))
check("A3 kis/nagybetu fuggetlen", detect_brand_mention("NoDu bridge"))
check("A4 cim ES torzs is vizsgalva", detect_brand_mention("", "mentions nodu here"))
check("A5 nem talal ott, ahol nincs", not detect_brand_mention("Speckle and BIMcollab"))
check("A6 reszszo nem talalat", not detect_brand_mention("nodules in the model"))
check("A7 a nodu_mention KIKERULT a sema-mezokbol",
      "nodu_mention" not in _SCHEMA["properties"] and "nodu_mention" not in _SCHEMA["required"])
check("A8 a competitor_quote KOTELEZO lett", "competitor_quote" in _SCHEMA["required"])
check("A9 a classifier-verzio bumpolva", CLASSIFIER_VERSION.endswith("v4"), CLASSIFIER_VERSION)

# --- B) competitor-igazolas -------------------------------------------------
POST = {"title": "IFC roundtrip problem",
        "body": "We switched to Speckle for this workflow because IFC kept losing parameters."}

ok_flag, ok_name = verify_competitor(
    {"competitor_mentioned": True, "competitor_name": "Speckle",
     "competitor_quote": "We switched to Speckle for this workflow"}, POST)
check("B1 igazolt idezet -> elfogadva", ok_flag == 1 and ok_name == "Speckle")

bad_flag, _ = verify_competitor(
    {"competitor_mentioned": True, "competitor_name": "Navisworks, Solibri",
     "competitor_quote": "the user compares Navisworks and Solibri"}, POST)
check("B2 hallucinalt idezet -> ELDOBVA", bad_flag == 0)

short_flag, _ = verify_competitor(
    {"competitor_mentioned": True, "competitor_name": "Speckle", "competitor_quote": "Speckle"}, POST)
check("B3 tul rovid idezet -> ELDOBVA", short_flag == 0)

name_flag, _ = verify_competitor(
    {"competitor_mentioned": True, "competitor_name": "BIM Vision",
     "competitor_quote": "We switched to Speckle for this workflow"}, POST)
check("B4 a posztban nem szereplo NEV -> ELDOBVA", name_flag == 0)

none_flag, none_name = verify_competitor({"competitor_mentioned": False}, POST)
check("B5 nincs jeloles -> (0, '')", none_flag == 0 and none_name == "")

ws_flag, _ = verify_competitor(
    {"competitor_mentioned": True, "competitor_name": "Speckle",
     "competitor_quote": "we   switched\nto   Speckle  for this workflow"}, POST)
check("B6 whitespace-normalizalas mellett is talal", ws_flag == 1)

# --- C) rendezes ------------------------------------------------------------
db_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "storage", "db.py"), encoding="utf-8").read()
check("C1 nincs tobbe 'confidence DESC' rendezes", "confidence DESC" not in db_src)
check("C2 a buying_intent a severity ELE kerult a lehetosegeknel",
      db_src.count("s.buying_intent DESC, s.severity DESC") >= 2)

# --- D) SalesOS-score ------------------------------------------------------
from crm.salesos_client import severity_to_score, build_payload  # noqa: E402

check("D1 sev3 intent nelkul = 6 (Lead)", severity_to_score(3) == 6)
check("D2 sev3 + intent = 7 (Qualified)", severity_to_score(3, buying_intent=True) == 7)
check("D3 sev4 intent nelkul = 8", severity_to_score(4) == 8)
check("D4 sev4 + intent = 9", severity_to_score(4, buying_intent=True) == 9)
check("D5 solved_internally levonas", severity_to_score(4, solved_internally=True) == 7)
check("D6 sev5 + intent nem lep 10 fole", severity_to_score(5, buying_intent=True) == 10)
check("D7 nincs severity -> 0", severity_to_score(None) == 0)
check("D8 visszafele kompatibilis (parameter nelkul a regi ertek)",
      severity_to_score(4) == 8 and severity_to_score(3) == 6)
pay = build_payload({"id": 1, "url": "https://example.invalid/1", "sig_severity": 3,
                     "sig_buying_intent": 1, "created_at": "2026-07-20T10:00:00"},
                    {"name": "Teszt Kft", "domain": "teszt.invalid"}, summary="x")
check("D9 a payload a bovitett score-t hasznalja", pay["score"] == 7, f"{pay['score']}")

# --- E) FIFO + kiserlet-szamlalo -------------------------------------------
from storage.db import (init_db, insert_post, get_unclassified_posts,  # noqa: E402
                        bump_classify_attempt, get_classify_backlog, get_connection)

db = os.path.join(tempfile.mkdtemp(prefix="nodu-p2-"), "t.db")
init_db(db)
for i, stamp in enumerate(("2026-07-20T10:00:00+00:00", "2026-07-25T10:00:00+00:00",
                           "2026-07-27T10:00:00+00:00")):
    insert_post(db, {"source": "t", "platform": "osarch", "external_id": f"e{i}",
                     "url": f"https://example.invalid/{i}", "author": "a",
                     "title": f"Poszt {i}", "body": "b",
                     "created_at": "2026-07-27T10:00:00+00:00", "fetched_at": stamp,
                     "keywords": "ifc", "score": 5})
order = [p["title"] for p in get_unclassified_posts(db, limit=10)]
check("E1 FIFO: a legregebbi jon elso", order[0] == "Poszt 0", f"{order}")

conn = get_connection(db)
oldest_id = conn.execute("SELECT id FROM posts WHERE title='Poszt 0'").fetchone()["id"]
conn.close()
bump_classify_attempt(db, oldest_id)
order2 = [p["title"] for p in get_unclassified_posts(db, limit=10)]
check("E2 egy bukott kiserlet utan a sor VEGERE csuszik", order2[-1] == "Poszt 0", f"{order2}")

for _ in range(2):
    bump_classify_attempt(db, oldest_id)
order3 = [p["title"] for p in get_unclassified_posts(db, limit=10, max_attempts=3)]
check("E3 3 kiserlet utan KIESIK a sorbol", "Poszt 0" not in order3, f"{order3}")
check("E4 max_attempts=None-nal megis visszajon",
      "Poszt 0" in [p["title"] for p in get_unclassified_posts(db, limit=10, max_attempts=None)])
bl = get_classify_backlog(db)
check("E5 a hatralek-riport a kiesetteket is szamolja",
      bl["waiting"] == 3 and bl["exhausted"] == 1, f"{bl}")

# --- F) letiltott connector -------------------------------------------------
import main as m  # noqa: E402

sched_off = {e["name"] for e in m.connector_schedule(
    {"stackoverflow": {"enabled": False}, "vanilla": {"enabled": True},
     "backup": {"enabled": False}, "alerts": {"daily_digest": False}})}
check("F1 a letiltott stackoverflow nincs az utemezesben", "stackoverflow" not in sched_off,
      f"{sorted(sched_off)}")
sched_on = {e["name"] for e in m.connector_schedule(
    {"stackoverflow": {"enabled": True}, "backup": {"enabled": False},
     "alerts": {"daily_digest": False}})}
check("F2 enabled: true-val visszakapcsolhato", "stackoverflow" in sched_on)

import yaml  # noqa: E402
live_cfg = yaml.safe_load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "config.yaml"), encoding="utf-8"))
check("F3 az eles configban a stackoverflow ki van kapcsolva",
      live_cfg["stackoverflow"].get("enabled") is False)
check("F4 az eles configban delay_seconds a MERT ertek (2)",
      live_cfg["classifier"]["delay_seconds"] == 2, f"{live_cfg['classifier']['delay_seconds']}")
check("F5 a forums szekcio ures (revitforum kivezetve)", not live_cfg.get("forums"))

# --- G) snapshot-ellenorzes -------------------------------------------------
from storage.backup import backup_db, verify_snapshot  # noqa: E402

snap = backup_db(db, keep=3)
check("G1 a snapshot elkeszult es ellenorzott", bool(snap) and os.path.exists(snap))
check("G2 verify_snapshot ep fajlra True", verify_snapshot(snap) is True)

broken = snap + ".broken.db"
with open(snap, "rb") as f:
    data = bytearray(f.read())
for i in range(2000, min(len(data), 6000)):      # a fejlec utan rongalunk
    data[i] = 0
open(broken, "wb").write(bytes(data))
check("G3 verify_snapshot serult fajlra False", verify_snapshot(broken) is False)

empty_db = os.path.join(tempfile.mkdtemp(prefix="nodu-empty-"), "e.db")
init_db(empty_db)
empty_snap = backup_db(empty_db, keep=3)
check("G4 a 0 posztos snapshot elutasitva (gyanusan ures)", empty_snap is None)

# --- H) token-keret ---------------------------------------------------------
dg_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "responder", "draft_generator.py"), encoding="utf-8").read()
import re  # noqa: E402

check("H1 a draft-utakon 320 a token-keret", dg_src.count("max_output_tokens=320") == 2)
# Szo-hatarral, kulonben a "200" a "2000"-be (heti tartalom-pipeline) is beleillik.
check("H2 nincs tobbe 200-as keret",
      not re.search(r"max_output_tokens=200\b", dg_src),
      str(re.findall(r"max_output_tokens=\d+", dg_src)))

print()
bad = 0
for name, ok, detail in results:
    if not ok:
        bad += 1
    print(f"  {'OK  ' if ok else 'FAIL'} {name}" + (f"   [{detail}]" if detail else ""))
print(f"\n{len(results) - bad}/{len(results)} teszt zold.")
sys.exit(1 if bad else 0)
