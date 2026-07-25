"""
Napi adatbazis-snapshot rotacioval.

Miert van: 2026-07-22-en a `posts`/`signals`/`drafts` tablak tartalma
elveszett (249 -> 28 poszt, AUTOINCREMENT-szamlalo nullazva), es NEM volt
belole semmilyen mentes — a repoban egyetlen .db fajl volt.
Reszletek: docs/02-lead-volume-audit-2026-07.md §3.3.

A `VACUUM INTO` konzisztens, tomoritett masolatot ir egy uj fajlba, ELO
adatbazisrol is (olvaso muvelet, nem zarolja ki az irokat), es SQLite 3.27+
ota elerheto. Nem sqlite3-fuggvenyt hivunk a fajl kopiralasa helyett, mert a
nyers fajl-kopia WAL-modban toredezett/serult snapshotot adhat.
"""
import glob
import os
import sqlite3
from datetime import datetime, timezone

DEFAULT_KEEP = 7


def _now_stamp() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def backup_dir_for(db_path: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(db_path)), "backups")


def prune_backups(backup_dir: str, base_name: str, keep: int = DEFAULT_KEEP) -> list[str]:
    """A legfrissebb `keep` darab snapshotot megtartja, a tobbit torli.
    Visszaadja a torolt fajlok listajat."""
    pattern = os.path.join(backup_dir, f"{base_name}.*.db")
    # A fajlnevben ISO-idobelyeg van, igy a nev szerinti rendezes = idorend.
    snapshots = sorted(glob.glob(pattern))
    removed = []
    for old in snapshots[:-keep] if keep > 0 else snapshots:
        try:
            os.remove(old)
            removed.append(old)
        except OSError as e:
            print(f"[backup] Nem sikerult torolni: {old} — {e}")
    return removed


def backup_db(db_path: str, keep: int = DEFAULT_KEEP) -> str | None:
    """
    Egy snapshot keszitese. Visszaadja a letrehozott fajl utjat, vagy None hiba
    eseten. Szandekosan NEM dob kivetelt: az utemezobol hivjuk, es egy sikeretlen
    mentes ne dontse el a tobbi jobot.
    """
    if not os.path.exists(db_path):
        print(f"[backup] Nincs ilyen adatbazis: {db_path}")
        return None

    out_dir = backup_dir_for(db_path)
    os.makedirs(out_dir, exist_ok=True)
    base_name = os.path.basename(db_path)
    target = os.path.join(out_dir, f"{base_name}.{_now_stamp()}.db")

    if os.path.exists(target):
        # VACUUM INTO hibara fut, ha a cel mar letezik (ugyanazon masodpercen
        # belul ket hivas) — ilyenkor nincs mit tenni, van friss mentes.
        print(f"[backup] Mar letezik ilyen snapshot: {target}")
        return target

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("VACUUM INTO ?", (target,))
        size_kb = os.path.getsize(target) // 1024
        print(f"[backup] Snapshot: {os.path.basename(target)} ({size_kb} KB)")
    except sqlite3.Error as e:
        print(f"[backup] HIBA: {e}")
        return None
    finally:
        conn.close()

    removed = prune_backups(out_dir, base_name, keep=keep)
    if removed:
        print(f"[backup] {len(removed)} regi snapshot torolve (megtartva: {keep}).")
    return target
