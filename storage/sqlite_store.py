import sqlite3
from typing import Iterable, Dict, Any, List, Tuple

DB_PATH = "db/akfen.db"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    plant_id TEXT NOT NULL,
    metric_type TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT,
    source TEXT,
    quality_flag TEXT,
    UNIQUE(plant_id, metric_type, timestamp)
);
"""

CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_measurements_plant_metric_time
ON measurements(plant_id, metric_type, timestamp);
"""


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(CREATE_TABLE_SQL)
        cur.execute(CREATE_INDEX_SQL)
        conn.commit()
    finally:
        conn.close()


def insert_records(records: Iterable[Dict[str, Any]]) -> Tuple[int, int]:
    """
    records: standart schema record list
    return: (inserted_count, duplicate_skipped_count)
    """
    conn = sqlite3.connect(DB_PATH)
    inserted = 0
    skipped = 0
    try:
        cur = conn.cursor()
        for r in records:
            try:
                cur.execute(
                    """
                    INSERT INTO measurements(timestamp, plant_id, metric_type, value, unit, source, quality_flag)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        r["timestamp"],
                        r["plant_id"],
                        r["metric_type"],
                        float(r["value"]),
                        r.get("unit"),
                        r.get("source"),
                        r.get("quality_flag"),
                    ),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                # UNIQUE constraint => duplicate
                skipped += 1

        conn.commit()
    finally:
        conn.close()

    return inserted, skipped


def fetch_count() -> int:
    """DB'deki toplam kayıt sayısı (kontrol için)"""
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM measurements;")
        (cnt,) = cur.fetchone()
        return int(cnt)
    finally:
        conn.close()

def fetch_series(plant_id: str, metric_type: str, limit: int = 2000):
    """
    DB'den zaman serisini çeker.
    return: list of (timestamp, value, quality_flag)
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT timestamp, value, COALESCE(quality_flag, 'ok') as quality_flag
            FROM measurements
            WHERE plant_id = ? AND metric_type = ?
            ORDER BY timestamp ASC
            LIMIT ?
            """,
            (plant_id, metric_type, limit),
        )
        return cur.fetchall()
    finally:
        conn.close()
