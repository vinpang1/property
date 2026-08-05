import sqlite3
from contextlib import contextmanager
from pathlib import Path

from src.utils.config import get_db_path


def connect(db_name: str) -> sqlite3.Connection:
    path = get_db_path(db_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_connection(db_name: str):
    conn = connect(db_name)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database(db_name: str, schema_file: str) -> Path:
    from src.utils.paths import PROJECT_ROOT

    schema_path = PROJECT_ROOT / "database" / "schemas" / schema_file
    db_path = get_db_path(db_name)

    with open(schema_path, encoding="utf-8") as f:
        schema_sql = f.read()

    with get_connection(db_name) as conn:
        conn.executescript(schema_sql)
        if db_name == "tuen_mun":
            _migrate_tuen_mun_schema(conn)

    return db_path


def _migrate_tuen_mun_schema(conn: sqlite3.Connection) -> None:
    """Add new columns to existing databases without breaking old installs."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(tuen_mun_transactions)")}
    for column, col_type in (
        ("branch_name", "TEXT"),
        ("agent_name", "TEXT"),
        ("agent_phone", "TEXT"),
    ):
        if column not in existing:
            conn.execute(f"ALTER TABLE tuen_mun_transactions ADD COLUMN {column} {col_type}")
