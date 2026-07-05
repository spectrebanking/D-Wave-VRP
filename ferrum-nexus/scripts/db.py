"""Encrypted-at-rest SQLite store (SQLCipher via sqlcipher3-binary)."""
from pathlib import Path

from sqlcipher3 import dbapi2 as sqlcipher

from credentials import get_or_create_db_key

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "ferrum_nexus.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def connect(db_path: Path | None = None, key: str | None = None):
    """Open (creating if needed) the encrypted store and ensure schema v1 exists."""
    db_path = db_path or DB_PATH
    db_path.parent.mkdir(exist_ok=True)
    key = key or get_or_create_db_key()

    conn = sqlcipher.connect(str(db_path))
    conn.execute(f"PRAGMA key = \"x'{key}'\"")
    # Touch the DB so PRAGMA key errors surface immediately on a wrong key,
    # instead of silently deferring to the first real query.
    conn.execute("SELECT count(*) FROM sqlite_master")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()
    return conn


def table_names(conn) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {r[0] for r in rows}
