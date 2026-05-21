"""Camada SQLite para o histórico do clipboard."""
import hashlib
import sqlite3
import time
from pathlib import Path

DB_DIR = Path.home() / ".local" / "share" / "copyboard"
DB_PATH = DB_DIR / "history.db"


def init_db() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            content TEXT,
            content_lower TEXT,
            image_data BLOB,
            image_hash TEXT,
            has_image INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON items(timestamp DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_content_lower ON items(content_lower)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_image_hash ON items(image_hash)")
    conn.commit()
    return conn


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def insert_or_update_text(conn: sqlite3.Connection, content: str) -> bool:
    """Retorna True se inseriu novo; False se atualizou existente (move pro topo)."""
    cur = conn.execute("SELECT id FROM items WHERE content = ? LIMIT 1", (content,))
    row = cur.fetchone()
    now = time.time()
    if row:
        conn.execute("UPDATE items SET timestamp = ? WHERE id = ?", (now, row[0]))
        conn.commit()
        return False
    conn.execute(
        "INSERT INTO items (timestamp, content, content_lower, has_image) VALUES (?, ?, ?, 0)",
        (now, content, content.lower()),
    )
    conn.commit()
    return True


def insert_or_update_image(conn: sqlite3.Connection, data: bytes) -> bool:
    h = sha256_bytes(data)
    cur = conn.execute("SELECT id FROM items WHERE image_hash = ? LIMIT 1", (h,))
    row = cur.fetchone()
    now = time.time()
    if row:
        conn.execute("UPDATE items SET timestamp = ? WHERE id = ?", (now, row[0]))
        conn.commit()
        return False
    conn.execute(
        "INSERT INTO items (timestamp, image_data, image_hash, has_image) VALUES (?, ?, ?, 1)",
        (now, data, h),
    )
    conn.commit()
    return True


def fetch_items(conn: sqlite3.Connection, query: str = "", limit: int = 60, offset: int = 0):
    q = query.strip()
    if q == "*image":
        cur = conn.execute(
            "SELECT id, timestamp, content, image_hash, has_image FROM items "
            "WHERE has_image = 1 ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
    elif q == "":
        cur = conn.execute(
            "SELECT id, timestamp, content, image_hash, has_image FROM items "
            "ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
    else:
        like = f"%{q.lower()}%"
        cur = conn.execute(
            "SELECT id, timestamp, content, image_hash, has_image FROM items "
            "WHERE content_lower LIKE ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (like, limit, offset),
        )
    return cur.fetchall()


def get_item(conn: sqlite3.Connection, item_id: int):
    cur = conn.execute(
        "SELECT content, image_data, has_image FROM items WHERE id = ?", (item_id,)
    )
    return cur.fetchone()


def get_image_data(conn: sqlite3.Connection, item_id: int):
    cur = conn.execute("SELECT image_data FROM items WHERE id = ?", (item_id,))
    row = cur.fetchone()
    return row[0] if row else None


def delete_items(conn: sqlite3.Connection, ids: list[int]) -> None:
    if not ids:
        return
    placeholders = ",".join("?" * len(ids))
    conn.execute(f"DELETE FROM items WHERE id IN ({placeholders})", ids)
    conn.commit()


def prune_to_limit(conn: sqlite3.Connection, limit: int) -> None:
    cur = conn.execute("SELECT COUNT(*) FROM items")
    total = cur.fetchone()[0]
    if total <= limit:
        return
    extra = total - limit
    conn.execute(
        "DELETE FROM items WHERE id IN ("
        "  SELECT id FROM items ORDER BY timestamp ASC LIMIT ?"
        ")",
        (extra,),
    )
    conn.commit()


def cleanup_by_days(conn: sqlite3.Connection, mode: str, days: int) -> int:
    cutoff = time.time() - days * 86400
    if mode == "deleteRecent":
        cur = conn.execute("SELECT COUNT(*) FROM items WHERE timestamp >= ?", (cutoff,))
        n = cur.fetchone()[0]
        conn.execute("DELETE FROM items WHERE timestamp >= ?", (cutoff,))
    else:  # keepRecent
        cur = conn.execute("SELECT COUNT(*) FROM items WHERE timestamp < ?", (cutoff,))
        n = cur.fetchone()[0]
        conn.execute("DELETE FROM items WHERE timestamp < ?", (cutoff,))
    conn.commit()
    return n


def total_storage_size(conn: sqlite3.Connection) -> int:
    cur = conn.execute(
        "SELECT COALESCE(SUM(LENGTH(content)),0) + COALESCE(SUM(LENGTH(image_data)),0) FROM items"
    )
    return cur.fetchone()[0] or 0
