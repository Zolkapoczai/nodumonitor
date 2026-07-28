"""
A draft-dontes naplozasanak (drafts.decided_by/_at/_by_source) verifikacioja.

Amit mer:
 1. Migracio: a HAROM uj oszlop megjelenik egy regi sematu DB-n, a meglevo
    draftok adata valtozatlan, es a migracio ismetelheto (idempotens).
 2. mark_draft: nevvel naploz, nev nelkul a REGI viselkedes marad (NULL).
 3. A source default 'form', de felulirhato ('cli').
 4. get_decision_log: csak a nevvel rendelkezo dontesek, legfrissebb elol.
 5. A statusz-valtas akkor is megtortenik, ha nincs nev — a naplo nem kapu.
"""
import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage.db import init_db, insert_post, save_draft, mark_draft, get_decision_log  # noqa: E402

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


tmp = tempfile.mkdtemp()
db = os.path.join(tmp, "t.db")

# --- 1. REGI sematu DB, majd migracio ---------------------------------------
conn = sqlite3.connect(db)
conn.executescript("""
    CREATE TABLE posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT, platform TEXT,
        external_id TEXT, url TEXT, author TEXT, title TEXT, body TEXT,
        created_at TEXT NOT NULL, fetched_at TEXT NOT NULL, keywords TEXT,
        score INTEGER DEFAULT 0, status TEXT DEFAULT 'new',
        UNIQUE(platform, external_id));
    CREATE TABLE drafts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL REFERENCES posts(id),
        draft_text TEXT NOT NULL, generated_at TEXT NOT NULL,
        status TEXT DEFAULT 'pending', posted_at TEXT, note TEXT);
    INSERT INTO posts (source, platform, external_id, url, title, created_at, fetched_at)
        VALUES ('legacy.example', 'legacy', 'L1', 'https://example.invalid/l1',
                'Regi poszt', '2026-07-01T10:00:00', '2026-07-01T10:00:00');
    INSERT INTO drafts (post_id, draft_text, generated_at, status)
        VALUES (1, 'regi draft szoveg', '2026-07-01T11:00:00', 'approved');
""")
conn.commit()
conn.close()

init_db(db)

conn = sqlite3.connect(db)
cols = [r[1] for r in conn.execute("PRAGMA table_info(drafts)")]
check("1a decided_by oszlop letrejott", "decided_by" in cols)
check("1b decided_at oszlop letrejott", "decided_at" in cols)
check("1c decided_by_source oszlop letrejott", "decided_by_source" in cols)
old = conn.execute("SELECT draft_text, status, decided_by FROM drafts WHERE id=1").fetchone()
check("1d regi draft szovege valtozatlan", old[0] == "regi draft szoveg")
check("1e regi draft statusza valtozatlan", old[1] == "approved")
check("1f regi dontes decided_by-ja NULL ('nem tudjuk')", old[2] is None)
conn.close()

init_db(db)  # ismetelt migracio nem bukhat el
conn = sqlite3.connect(db)
check("1g migracio idempotens",
      len([r for r in conn.execute("PRAGMA table_info(drafts)") if r[1] == "decided_by"]) == 1)
conn.close()

# --- 2-3. naplozas ----------------------------------------------------------
insert_post(db, {"source": "s", "platform": "osarch", "external_id": "P2",
                 "url": "https://example.invalid/2", "author": "a", "title": "Uj poszt",
                 "body": "b", "created_at": "2026-07-20T10:00:00",
                 "fetched_at": "2026-07-20T10:00:00", "keywords": "ifc", "score": 5})
pid = sqlite3.connect(db).execute("SELECT id FROM posts WHERE external_id='P2'").fetchone()[0]

d_named = save_draft(db, pid, "draft A")
d_anon = save_draft(db, pid, "draft B")
d_cli = save_draft(db, pid, "draft C")

mark_draft(db, d_named, "approved", decided_by="  Zoltan  ")
mark_draft(db, d_anon, "approved")
mark_draft(db, d_cli, "rejected", "manualisan", decided_by="ZoltanPoczai", decided_by_source="cli")

conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
rows = {r["id"]: r for r in conn.execute("SELECT * FROM drafts")}
check("2a nev naplozva es trimmelve", rows[d_named]["decided_by"] == "Zoltan")
check("2b decided_at kitoltve", bool(rows[d_named]["decided_at"]))
check("2c default source 'form'", rows[d_named]["decided_by_source"] == "form")
check("2d nev nelkul NULL marad", rows[d_anon]["decided_by"] is None
      and rows[d_anon]["decided_at"] is None)
check("2e nev nelkul is valt a statusz", rows[d_anon]["status"] == "approved")
check("3a 'cli' source atmegy", rows[d_cli]["decided_by_source"] == "cli")
check("3b elutasitas is naplozva", rows[d_cli]["status"] == "rejected"
      and rows[d_cli]["decided_by"] == "ZoltanPoczai")
check("3c note megmarad", rows[d_cli]["note"] == "manualisan")
conn.close()

# hosszu nev vagasa (80 karakter)
d_long = save_draft(db, pid, "draft D")
mark_draft(db, d_long, "approved", decided_by="x" * 200)
conn = sqlite3.connect(db)
check("3d 80 karakterre vagva",
      len(conn.execute("SELECT decided_by FROM drafts WHERE id=?", (d_long,)).fetchone()[0]) == 80)
conn.close()

# --- 4. olvasas -------------------------------------------------------------
log = get_decision_log(db)
check("4a csak a nevvel rendelkezo dontesek", len(log) == 3, f"kapott={len(log)}")
check("4b a regi (NULL) es a nevtelen kimaradt",
      all(r["decided_by"] for r in log))
check("4c legfrissebb elol",
      [r["decided_at"] for r in log] == sorted([r["decided_at"] for r in log], reverse=True))
check("4d poszt-adat is jon (join)", all(r.get("title") and r.get("url") for r in log))
check("4e limit mukodik", len(get_decision_log(db, limit=1)) == 1)

# --- 5. HTTP-route: a /draft/<id>/approve|reject naploz-e -------------------
# Hermetikus: az app get_db_path-jat a temp DB-re allitjuk, igy az eles
# nodu_monitor.db-t a teszt nem erinti.
import ui.app as uiapp  # noqa: E402

uiapp.get_db_path = lambda config: db
uiapp.app.config["TESTING"] = True
client = uiapp.app.test_client()

d_web = save_draft(db, pid, "draft WEB")
r = client.post(f"/draft/{d_web}/approve", json={"decided_by": "Kata"})
check("5a approve route 200", r.status_code == 200, f"status={r.status_code}")
check("5b a valasz visszaadja a nevet", r.get_json().get("decided_by") == "Kata")

conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
row = conn.execute("SELECT * FROM drafts WHERE id=?", (d_web,)).fetchone()
check("5c naplozva a DB-ben", row["decided_by"] == "Kata" and row["status"] == "approved")
check("5d source 'form' (nincs auth)", row["decided_by_source"] == "form")
conn.close()

d_web2 = save_draft(db, pid, "draft WEB2")
r = client.post(f"/draft/{d_web2}/reject", json={"decided_by": "Kata"})
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
row = conn.execute("SELECT * FROM drafts WHERE id=?", (d_web2,)).fetchone()
check("5e reject route is naploz",
      row["status"] == "rejected" and row["decided_by"] == "Kata")
conn.close()

# nev nelkuli keres: a REGI viselkedes marad, nem hiba
d_web3 = save_draft(db, pid, "draft WEB3")
r = client.post(f"/draft/{d_web3}/approve", json={})
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
row = conn.execute("SELECT * FROM drafts WHERE id=?", (d_web3,)).fetchone()
check("5f nev nelkul is jovahagy, de nem naploz",
      r.status_code == 200 and row["status"] == "approved" and row["decided_by"] is None)
conn.close()

# basic-auth username fallback (nev nelkuli body eseten)
import base64  # noqa: E402
d_web4 = save_draft(db, pid, "draft WEB4")
auth = base64.b64encode(b"bela:akarmi").decode()
r = client.post(f"/draft/{d_web4}/approve", json={},
                headers={"Authorization": f"Basic {auth}"})
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
row = conn.execute("SELECT * FROM drafts WHERE id=?", (d_web4,)).fetchone()
check("5g basic-auth username a fallback", row["decided_by"] == "bela")
conn.close()

r = client.get("/api/decisions?limit=100")
body = r.get_json()
check("5h /api/decisions listaz", r.status_code == 200 and body["count"] >= 6,
      f"count={body['count']}")
check("5i a naplo nem tartalmaz nevtelen dontest",
      all(d["decided_by"] for d in body["decisions"]))

print()
bad = 0
for name, ok, detail in results:
    if not ok:
        bad += 1
    print(f"  {'OK  ' if ok else 'FAIL'} {name}" + (f"   [{detail}]" if detail else ""))
print(f"\n{len(results) - bad}/{len(results)} teszt zold.")
sys.exit(1 if bad else 0)
