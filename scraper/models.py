import os, re, hashlib, sqlite3, json
from datetime import datetime

DB_PATH = "data/mospi.db"
os.makedirs("data", exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Documents table (new)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            url TEXT UNIQUE,
            date_published TEXT,
            summary TEXT,
            category TEXT,
            doc_hash TEXT,
            created_at TEXT
        )
        """
    )
    # Files table (existing + new columns)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_url TEXT UNIQUE,
            file_path TEXT,
            file_hash TEXT,
            downloaded INTEGER DEFAULT 0,
            processed INTEGER DEFAULT 0,
            created_at TEXT
        )
        """
    )
    # Ensure new columns exist on files
    cur.execute("PRAGMA table_info(files)")
    cols = {row[1] for row in cur.fetchall()}
    if "document_id" not in cols:
        cur.execute("ALTER TABLE files ADD COLUMN document_id INTEGER")
    if "file_type" not in cols:
        cur.execute("ALTER TABLE files ADD COLUMN file_type TEXT")
    if "pages" not in cols:
        cur.execute("ALTER TABLE files ADD COLUMN pages INTEGER")

    # Tables table (extracted tables from PDFs)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            source_file_id INTEGER,
            table_json TEXT,
            n_rows INTEGER,
            n_cols INTEGER,
            created_at TEXT
        )
        """
    )

    conn.commit()
    conn.close()

def upsert_file_url(file_url: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO files (file_url, created_at) VALUES (?, ?)",
        (file_url, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()

def upsert_document(url: str, title: str = None, date_published: str = None, summary: str = None, category: str = None) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO documents (title, url, date_published, summary, category, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(url) DO UPDATE SET
            title=COALESCE(excluded.title, documents.title),
            date_published=COALESCE(excluded.date_published, documents.date_published),
            summary=COALESCE(excluded.summary, documents.summary),
            category=COALESCE(excluded.category, documents.category)
        """,
        (title, url, date_published, summary, category, datetime.utcnow().isoformat()),
    )
    conn.commit()
    cur.execute("SELECT id FROM documents WHERE url=?", (url,))
    doc_id = cur.fetchone()[0]
    conn.close()
    return doc_id

def upsert_file_for_document(document_id: int, file_url: str) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO files (file_url, created_at, document_id) VALUES (?, ?, ?)",
        (file_url, datetime.utcnow().isoformat(), document_id),
    )
    conn.commit()
    cur.execute("SELECT id FROM files WHERE file_url=?", (file_url,))
    file_id = cur.fetchone()[0]
    conn.close()
    return file_id

def get_unprocessed(limit=2):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, file_url, file_path, downloaded, processed FROM files WHERE processed=0 ORDER BY id ASC LIMIT ?",
        (limit,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def get_unprocessed_files(limit=10):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, document_id, file_url, file_path, downloaded, processed
        FROM files
        WHERE processed=0
        ORDER BY id ASC
        LIMIT ?
        """,
        (limit,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def update_after_download(file_id, file_path, file_hash):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "UPDATE files SET file_path=?, file_hash=?, downloaded=1 WHERE id=?",
        (file_path, file_hash, file_id)
    )
    conn.commit()
    conn.close()

def update_file_path(file_id: int, new_path: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "UPDATE files SET file_path=? WHERE id=?",
        (new_path, file_id),
    )
    conn.commit()
    conn.close()

def set_file_meta(file_id: int, file_type: str = None, pages: int = None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "UPDATE files SET file_type=COALESCE(?, file_type), pages=COALESCE(?, pages) WHERE id=?",
        (file_type, pages, file_id),
    )
    conn.commit()
    conn.close()

def mark_processed(file_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE files SET processed=1 WHERE id=?", (file_id,))
    conn.commit()
    conn.close()

def insert_table(document_id: int, source_file_id: int, table_rows: list[list[str]]):
    if not table_rows:
        return
    n_rows = len(table_rows)
    n_cols = max((len(r) for r in table_rows), default=0)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO tables (document_id, source_file_id, table_json, n_rows, n_cols, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (document_id, source_file_id, json.dumps(table_rows, ensure_ascii=False), n_rows, n_cols, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()

def sanitize_filename(name: str, max_len: int = 120) -> str:
    name = re.sub(r"[^\w\-.() ]+", "_", name)
    return name[:max_len].strip(" ._-")

def compute_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
