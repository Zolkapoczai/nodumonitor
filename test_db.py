import sys
sys.path.insert(0, ".")

# Windows-konzol encoding (HANDOFF §4/4): a cp1250 kimenet elhasal az emojin/
# specialis karakteren, es a script UnicodeEncodeError-ral all le — nem azert,
# mert a DB-vel baj van. A main.py ugyanezt a vedelmet hasznalja.
try:
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")
except Exception:
    pass

from storage.db import init_db, insert_post, get_new_posts, mark_alerted  # noqa: E402

# TEMP DB, nem az eles nodu_monitor.db: ez a script beszur egy hamis reddit-
# posztot ('test_abc123') es 'alerted'-re allitja. Az eles DB-ben ez egy kitalalt
# lead, ami beleszamit a poszt-totalokba es a "Nyers leadek" fulben is megjelenik
# (2026-07-27-en tenylegesen bekerult egy ilyen sor, id=1563 — kitorolve).
import os  # noqa: E402
import tempfile  # noqa: E402

db = os.path.join(tempfile.mkdtemp(prefix="nodu-test-"), "test_nodu.db")
print(f"Teszt-adatbazis (eldobhato): {db}")
init_db(db)

record = {
    "source": "r/Revit",
    "platform": "reddit",
    "external_id": "test_abc123",
    "url": "https://reddit.com/r/Revit/comments/test",
    "author": "bim_coordinator_joe",
    "title": "ArchiCAD to Revit IFC conversion - geometry disappears",
    "body": (
        "We are working on a mixed Archicad-Revit project. "
        "When I export IFC from ArchiCAD and import it in Revit, "
        "half the geometry disappears. Has anyone found a working workflow?"
    ),
    "created_at": "2026-06-16T10:00:00+00:00",
    "fetched_at": "2026-06-16T10:05:00+00:00",
    "keywords": "archicad to revit, ifc conversion, geometry disappears",
    "score": 8,
}

is_new = insert_post(db, record)
print(f"Bejegyzes hozzaadva (uj): {is_new}")
is_dup = insert_post(db, record)
print(f"Duplikat visszautasitva: {not is_dup}")

posts = get_new_posts(db)
print(f"\nUj bejegyzesek szama: {len(posts)}")
for p in posts:
    print(f"\n  Platform : {p['platform']} | Source: {p['source']}")
    print(f"  Cim      : {p['title']}")
    print(f"  Score    : {p['score']} | Keywords: {p['keywords']}")
    print(f"  URL      : {p['url']}")

mark_alerted(db, [p["id"] for p in posts])
posts_after = get_new_posts(db)
print(f"\nAlerted utan uj bejegyzesek: {len(posts_after)} (0 kell legyen)")
print("\nADATBAZIS TESZT: OK")
