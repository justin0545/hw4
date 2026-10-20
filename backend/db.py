"""SQLite connections for the Campus Customs backend."""
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
# Tests point this at a throwaway copy so they never touch the real database.
DB_PATH = Path(os.environ.get("CAMPUS_CUSTOMS_DB", DATA_DIR / "campus_customs.db"))


def connect() -> sqlite3.Connection:
    """Read-only connection, used for catalogue and inventory."""
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def connect_rw() -> sqlite3.Connection:
    """Read-write connection, used only by auth (users and sessions)."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("pragma foreign_keys = on")
    return con
