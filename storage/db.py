import sqlite3
import os
from datetime import datetime, timedelta, timezone


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> None:
    conn = get_connection(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS posts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            source      TEXT    NOT NULL,
            platform    TEXT    NOT NULL,
            external_id TEXT,
            url         TEXT    NOT NULL,
            author      TEXT,
            title       TEXT,
            body        TEXT,
            created_at  TEXT    NOT NULL,
            fetched_at  TEXT    NOT NULL,
            keywords    TEXT,
            score       INTEGER DEFAULT 0,
            status      TEXT    DEFAULT 'new',
            search_term TEXT,
            UNIQUE(platform, external_id)
        );

        CREATE TABLE IF NOT EXISTS runs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            connector   TEXT    NOT NULL,
            started_at  TEXT    NOT NULL,
            finished_at TEXT,
            new_posts   INTEGER DEFAULT 0,
            error       TEXT
        );

        CREATE TABLE IF NOT EXISTS drafts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id      INTEGER NOT NULL REFERENCES posts(id),
            draft_text   TEXT    NOT NULL,
            generated_at TEXT    NOT NULL,
            status       TEXT    DEFAULT 'pending',
            posted_at    TEXT,
            note         TEXT
        );

        CREATE TABLE IF NOT EXISTS signals (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id               INTEGER NOT NULL REFERENCES posts(id),
            is_pain               INTEGER NOT NULL DEFAULT 0,
            pain_summary          TEXT,
            tech_summary          TEXT,
            archicad_probability  REAL,
            revit_probability     REAL,
            ifc_involved          INTEGER DEFAULT 0,
            issue_types           TEXT,
            severity              INTEGER,
            buying_intent         INTEGER DEFAULT 0,
            buying_intent_signals TEXT,
            role_hypothesis       TEXT,
            confidence            REAL,
            rationale             TEXT,
            classifier_version    TEXT    NOT NULL,
            classified_at         TEXT    NOT NULL,
            solved_internally     INTEGER DEFAULT 0,
            nodu_mention          INTEGER DEFAULT 0,
            competitor_mentioned  INTEGER DEFAULT 0,
            competitor_name       TEXT,
            UNIQUE(post_id)
        );
    """)
    # Migracio regi adatbazisokhoz: a search_term oszlop hozzaadasa, ha meg hianyzik
    cols = [r[1] for r in conn.execute("PRAGMA table_info(posts)").fetchall()]
    if "search_term" not in cols:
        conn.execute("ALTER TABLE posts ADD COLUMN search_term TEXT")
        
    signal_cols = [r[1] for r in conn.execute("PRAGMA table_info(signals)").fetchall()]
    if "solved_internally" not in signal_cols:
        conn.execute("ALTER TABLE signals ADD COLUMN solved_internally INTEGER DEFAULT 0")
    if "nodu_mention" not in signal_cols:
        conn.execute("ALTER TABLE signals ADD COLUMN nodu_mention INTEGER DEFAULT 0")
    if "competitor_mentioned" not in signal_cols:
        conn.execute("ALTER TABLE signals ADD COLUMN competitor_mentioned INTEGER DEFAULT 0")
        conn.execute("ALTER TABLE signals ADD COLUMN competitor_name TEXT")
        
    conn.commit()
    conn.close()


def insert_post(db_path: str, record: dict) -> bool:
    """Insert a post. Returns True if new, False if already exists."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO posts
                (source, platform, external_id, url, author, title, body,
                 created_at, fetched_at, keywords, score, status, search_term)
            VALUES
                (:source, :platform, :external_id, :url, :author, :title, :body,
                 :created_at, :fetched_at, :keywords, :score, 'new', :search_term)
            """,
            {**record, "search_term": record.get("search_term")},
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_new_posts(db_path: str) -> list[dict]:
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM posts WHERE status = 'new' ORDER BY fetched_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_post(db_path: str, post_id: int) -> dict | None:
    """Egyetlen poszt lekerese id alapjan (draft-generalashoz, SalesOS-kuldeshez)."""
    conn = get_connection(db_path)
    row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_unclassified_posts(db_path: str, limit: int = 20, search_term_null_only: bool = True) -> list[dict]:
    """
    Meg nem osztalyozott posztok (nincs meg hozzajuk signals-sor) a Pain
    Classifier szamara. search_term_null_only=True (alapertelmezett) kizarja
    az ad-hoc keresesi zajokat (require_keywords=False mentesek), csak az
    utemezett connectorok mar elo-szurt talalatait osztalyozza.
    """
    conn = get_connection(db_path)
    where = "s.id IS NULL"
    if search_term_null_only:
        where += " AND p.search_term IS NULL"
    rows = conn.execute(
        f"""
        SELECT p.* FROM posts p
        LEFT JOIN signals s ON s.post_id = p.id
        WHERE {where}
        ORDER BY p.fetched_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def insert_signal(db_path: str, record: dict) -> bool:
    """Egy poszthoz tartozo osztalyozasi jel mentese. Returns True, ha uj (post_id meg nem volt osztalyozva)."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO signals
                (post_id, is_pain, pain_summary, tech_summary,
                 archicad_probability, revit_probability, ifc_involved,
                 issue_types, severity, buying_intent, buying_intent_signals,
                 role_hypothesis, confidence, rationale, classifier_version, classified_at,
                 solved_internally, nodu_mention, competitor_mentioned, competitor_name)
            VALUES
                (:post_id, :is_pain, :pain_summary, :tech_summary,
                 :archicad_probability, :revit_probability, :ifc_involved,
                 :issue_types, :severity, :buying_intent, :buying_intent_signals,
                 :role_hypothesis, :confidence, :rationale, :classifier_version, :classified_at,
                 :solved_internally, :nodu_mention, :competitor_mentioned, :competitor_name)
            """,
            record,
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_signals_for_review(db_path: str, min_severity: int = 0, limit: int = 100) -> list[dict]:
    """
    Osztalyozott jelek a poszt adataival egyutt, a kezi kiertekelo riporthoz
    (main.py --review-signals). Legsulyosabb/legbizton­sagosabb elol.
    """
    conn = get_connection(db_path)
    rows = conn.execute(
        """
        SELECT s.*, p.title, p.url, p.platform, p.source, p.author, p.body, p.keywords, p.score AS keyword_score
        FROM signals s JOIN posts p ON s.post_id = p.id
        WHERE s.severity >= ?
        ORDER BY s.severity DESC, s.confidence DESC, s.classified_at DESC
        LIMIT ?
        """,
        (min_severity, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_opportunities(db_path: str, only_pain: bool = True, min_severity: int = 1,
                      limit: int = 100) -> list[dict]:
    """
    A dashboard "Lehetosegek" nezet forrasa: osztalyozott jelek a poszt
    adataival, fajdalom-fokuszban. Rendezes (prezentacios rangsor, NEM
    perzisztalt pontszam — a verziozott scoring-motor a Phase 2):
    nodu_mention elsodleges (referralok), severity masodlagos, buying_intent tiebreaker, confidence.
    Az ad-hoc keresesi zajt kizarjuk (search_term IS NULL).
    """
    conn = get_connection(db_path)
    where = ["p.search_term IS NULL", "s.severity >= ?"]
    params: list = [min_severity]
    if only_pain:
        where.append("(s.is_pain = 1 OR s.nodu_mention = 1)")
    rows = conn.execute(
        f"""
        SELECT s.*, p.title, p.url, p.platform, p.source, p.author,
               p.body, p.keywords, p.score AS keyword_score, p.created_at AS post_created_at
        FROM signals s JOIN posts p ON s.post_id = p.id
        WHERE {' AND '.join(where)}
        ORDER BY s.nodu_mention DESC, s.is_pain DESC, s.severity DESC, s.buying_intent DESC,
                 s.confidence DESC, s.classified_at DESC
        LIMIT ?
        """,
        (*params, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_pain_signals(db_path: str, lookback_days: int = 7, limit: int = 8) -> list[dict]:
    """
    A heti LinkedIn poszt-javaslatok uj forrasa: az elmult N nap valodi
    fajdalom-jelei (is_pain=1), a Pain Classifier osszefoglalojaval —
    NEM a nyers kulcsszo-gyakorisag. Legsulyosabb elol. Ad-hoc zaj kizarva.
    """
    cutoff = (_utcnow() - timedelta(days=lookback_days)).isoformat()
    conn = get_connection(db_path)
    rows = conn.execute(
        """
        SELECT s.pain_summary, s.tech_summary, s.issue_types, s.severity,
               s.buying_intent, s.solved_internally, s.nodu_mention, 
               s.competitor_mentioned, s.competitor_name, p.platform, p.title
        FROM signals s JOIN posts p ON s.post_id = p.id
        WHERE s.is_pain = 1 AND p.search_term IS NULL AND p.fetched_at >= ?
        ORDER BY s.nodu_mention DESC, s.severity DESC, s.buying_intent DESC, s.confidence DESC
        LIMIT ?
        """,
        (cutoff, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_post_with_signal(db_path: str, post_id: int) -> dict | None:
    """
    Egy poszt + a hozza tartozo signal-mezok (ha van mar osztalyozva).
    A signal mezoi 'sig_' prefixszel jonnek, hogy ne utkozzenek a poszt
    oszlopaival (pl. mindket tablanak van id/score-szeru mezoje). None ha
    nincs ilyen poszt. A valaszgeneralas hasznalja a fajdalom-kontextushoz.
    """
    conn = get_connection(db_path)
    row = conn.execute(
        """
        SELECT p.*,
               s.is_pain          AS sig_is_pain,
               s.pain_summary     AS sig_pain_summary,
               s.tech_summary     AS sig_tech_summary,
               s.issue_types      AS sig_issue_types,
               s.severity         AS sig_severity,
               s.buying_intent    AS sig_buying_intent,
               s.role_hypothesis  AS sig_role_hypothesis,
               s.solved_internally AS sig_solved_internally,
               s.nodu_mention     AS sig_nodu_mention,
               s.competitor_mentioned AS sig_competitor_mentioned,
               s.competitor_name  AS sig_competitor_name
        FROM posts p LEFT JOIN signals s ON s.post_id = p.id
        WHERE p.id = ?
        """,
        (post_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_pain_posts_without_draft(db_path: str, min_severity: int = 3,
                                 limit: int = 10) -> list[dict]:
    """
    A signal-vezerelt batch-valaszgenerator forrasa: valodi fajdalom-jelek
    (is_pain=1, severity>=min), amelyekhez MEG NINCS draft. Az ad-hoc zajt
    kizarjuk. Legsulyosabb/buying-intentes elol.
    """
    conn = get_connection(db_path)
    rows = conn.execute(
        """
        SELECT p.*,
               s.pain_summary     AS sig_pain_summary,
               s.tech_summary     AS sig_tech_summary,
               s.issue_types      AS sig_issue_types,
               s.severity         AS sig_severity,
               s.buying_intent    AS sig_buying_intent,
               s.role_hypothesis  AS sig_role_hypothesis,
               s.solved_internally AS sig_solved_internally,
               s.nodu_mention     AS sig_nodu_mention,
               s.competitor_mentioned AS sig_competitor_mentioned,
               s.competitor_name  AS sig_competitor_name
        FROM signals s JOIN posts p ON s.post_id = p.id
        LEFT JOIN drafts d ON d.post_id = p.id
        WHERE (s.is_pain = 1 OR s.nodu_mention = 1) AND s.severity >= ? AND p.search_term IS NULL
              AND d.id IS NULL
        ORDER BY s.nodu_mention DESC, s.severity DESC, s.buying_intent DESC, s.confidence DESC
        LIMIT ?
        """,
        (min_severity, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_posts(db_path: str, query: str = "", platforms: list[str] = None, limit: int = 50) -> list[dict]:
    """
    Kereses a nyers, osszes begyujtott poszt kozott.
    query: reszleges egyezes a title vagy body mezoben (ha adott)
    platforms: szures adott platformokra (ha adott)
    """
    conn = get_connection(db_path)
    where_clauses = ["search_term IS NULL"]
    params = []

    if query:
        where_clauses.append("(title LIKE ? OR body LIKE ?)")
        like_q = f"%{query}%"
        params.extend([like_q, like_q])

    if platforms:
        placeholders = ",".join("?" * len(platforms))
        where_clauses.append(f"platform IN ({placeholders})")
        params.extend(platforms)

    where_str = " AND ".join(where_clauses)
    
    rows = conn.execute(
        f"""
        SELECT *
        FROM posts
        WHERE {where_str}
        ORDER BY fetched_at DESC
        LIMIT ?
        """,
        (*params, limit),
    ).fetchall()
    
    conn.close()
    return [dict(r) for r in rows]


def get_adhoc_results(db_path: str, query: str = None, limit: int = 50) -> list[dict]:
    """
    Ad-hoc keresesi talalatok (search_term-mel jelolt posztok).
    query megadasaval egy konkret keresesre szur, kulonben a legutobbi talalatok.
    """
    conn = get_connection(db_path)
    if query:
        rows = conn.execute(
            "SELECT * FROM posts WHERE search_term = ? ORDER BY score DESC, fetched_at DESC LIMIT ?",
            (query, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM posts WHERE search_term IS NOT NULL ORDER BY fetched_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_alerted(db_path: str, post_ids: list[int]) -> None:
    if not post_ids:
        return
    conn = get_connection(db_path)
    conn.execute(
        f"UPDATE posts SET status = 'alerted' WHERE id IN ({','.join('?' * len(post_ids))})",
        post_ids,
    )
    conn.commit()
    conn.close()


def save_draft(db_path: str, post_id: int, draft_text: str) -> int:
    conn = get_connection(db_path)
    cur = conn.execute(
        "INSERT INTO drafts (post_id, draft_text, generated_at) VALUES (?, ?, ?)",
        (post_id, draft_text, _utcnow().isoformat()),
    )
    draft_id = cur.lastrowid
    conn.execute("UPDATE posts SET status = 'draft_ready' WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    return draft_id


def get_pending_drafts(db_path: str) -> list[dict]:
    conn = get_connection(db_path)
    rows = conn.execute("""
        SELECT d.id AS draft_id, d.draft_text, d.generated_at, d.status AS draft_status,
               p.id AS post_id, p.platform, p.source, p.title, p.body, p.url,
               p.author, p.keywords, p.score, p.created_at
        FROM drafts d JOIN posts p ON d.post_id = p.id
        WHERE d.status = 'pending'
        ORDER BY d.generated_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_draft(db_path: str, draft_id: int, status: str, note: str = None) -> None:
    conn = get_connection(db_path)
    conn.execute(
        "UPDATE drafts SET status = ?, posted_at = ?, note = ? WHERE id = ?",
        (status, _utcnow().isoformat() if status == "posted" else None, note, draft_id),
    )
    conn.commit()
    conn.close()


def log_run(db_path: str, connector: str, started_at: str, finished_at: str,
            new_posts: int, error: str = None) -> None:
    conn = get_connection(db_path)
    conn.execute(
        "INSERT INTO runs (connector, started_at, finished_at, new_posts, error) VALUES (?,?,?,?,?)",
        (connector, started_at, finished_at, new_posts, error),
    )
    conn.commit()
    conn.close()


def get_weekly_stats(db_path: str, lookback_days: int = 7) -> dict:
    """
    Heti osszesito a riporthoz es a LinkedIn-tartalomhoz.

    A fetched_at alapjan szur az elmult N napra, es visszaadja:
      - total_posts: osszes uj poszt a periodusban
      - by_platform: forrasonkenti poszt-szam (csokkeno)
      - pending_drafts: joovahagyasra varo draftok szama (osszesen)
      - top_pain_points: leggyakoribb matched kulcsszavak (csokkeno)

    A kulcsszavak a posts.keywords (vesszovel elvalasztott) mezobol jonnek,
    es Python-oldalon aggregalodnak, mert az SQLite-ban nincs natív split.
    """
    cutoff = (_utcnow() - timedelta(days=lookback_days)).isoformat()
    conn = get_connection(db_path)

    total = conn.execute(
        "SELECT COUNT(*) AS cnt FROM posts WHERE fetched_at >= ?", (cutoff,)
    ).fetchone()["cnt"]

    by_platform = conn.execute(
        """
        SELECT platform, COUNT(*) AS cnt
        FROM posts WHERE fetched_at >= ?
        GROUP BY platform ORDER BY cnt DESC
        """,
        (cutoff,),
    ).fetchall()

    pending_drafts = conn.execute(
        "SELECT COUNT(*) AS cnt FROM drafts WHERE status = 'pending'"
    ).fetchone()["cnt"]

    kw_rows = conn.execute(
        """
        SELECT keywords FROM posts
        WHERE fetched_at >= ? AND keywords IS NOT NULL AND keywords != ''
        """,
        (cutoff,),
    ).fetchall()
    conn.close()

    counts: dict[str, int] = {}
    for r in kw_rows:
        for kw in (r["keywords"] or "").split(","):
            k = kw.strip().lower()
            if k:
                counts[k] = counts.get(k, 0) + 1
    top_pain = sorted(counts.items(), key=lambda x: x[1], reverse=True)

    return {
        "lookback_days": lookback_days,
        "total_posts": total,
        "by_platform": [{"platform": r["platform"], "count": r["cnt"]} for r in by_platform],
        "pending_drafts": pending_drafts,
        "top_pain_points": [{"keyword": k, "count": c} for k, c in top_pain],
    }
