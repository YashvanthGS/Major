import json
import os
import sqlite3
from .pricing import RateCard


def _db_path():
    return os.environ.get("DAIRY_DB", os.path.join(os.path.dirname(__file__), "..", "dairy.db"))


def get_conn():
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS farmers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            village TEXT
        );
        CREATE TABLE IF NOT EXISTS rate_card (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            data TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id INTEGER NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
            entry_date TEXT NOT NULL,
            session TEXT NOT NULL CHECK (session IN ('morning','evening')),
            litres REAL NOT NULL,
            fat REAL NOT NULL,
            snf REAL NOT NULL,
            total REAL NOT NULL,
            breakdown TEXT NOT NULL,
            UNIQUE (farmer_id, entry_date, session)
        );
        """
    )
    if conn.execute("SELECT 1 FROM rate_card WHERE id = 1").fetchone() is None:
        conn.execute("INSERT INTO rate_card (id, data) VALUES (1, ?)",
                     (json.dumps(RateCard().to_dict()),))
    conn.commit()
    conn.close()


def load_rate_card() -> RateCard:
    conn = get_conn()
    row = conn.execute("SELECT data FROM rate_card WHERE id = 1").fetchone()
    conn.close()
    return RateCard(**json.loads(row["data"]))


def save_rate_card(rc: RateCard):
    conn = get_conn()
    conn.execute("UPDATE rate_card SET data = ? WHERE id = 1", (json.dumps(rc.to_dict()),))
    conn.commit()
    conn.close()
