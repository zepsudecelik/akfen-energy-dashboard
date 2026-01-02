import os
import psycopg2
from psycopg2.extras import execute_values

# Bağlantı bilgileri (istersen sonra .env yaparız)
PG_HOST = "localhost"
PG_PORT = 5432
PG_DB = "akfen_db"
PG_USER = "akfen_user"
PG_PASSWORD = "akfen_pass"

def get_conn():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD,
    )

def init_db():
    """
    Tablo yoksa oluşturur.
    UNIQUE ile duplicate engellenir (plant_id, metric_type, timestamp)
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS measurements (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMPTZ NOT NULL,
                plant_id TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                value DOUBLE PRECISION NOT NULL,
                unit TEXT,
                source TEXT,
                quality_flag TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE (plant_id, metric_type, timestamp)
            );
        """)
        conn.commit()
    finally:
        conn.close()

def insert_records(records):
    """
    records: list of dict
    return: (inserted_count, duplicate_skipped_count)
    """
    if not records:
        return 0, 0

    rows = []
    for r in records:
        rows.append((
            r["timestamp"],      # ISO string -> psycopg TIMESTAMPTZ parse eder
            r["plant_id"],
            r["metric_type"],
            float(r["value"]),
            r.get("unit"),
            r.get("source"),
            r.get("quality_flag"),
        ))

    conn = get_conn()
    try:
        cur = conn.cursor()

        # Önce kaç satır var?
        cur.execute("SELECT COUNT(*) FROM measurements;")
        before = cur.fetchone()[0]

        sql = """
            INSERT INTO measurements
            (timestamp, plant_id, metric_type, value, unit, source, quality_flag)
            VALUES %s
            ON CONFLICT (plant_id, metric_type, timestamp) DO NOTHING;
        """
        execute_values(cur, sql, rows, page_size=1000)
        conn.commit()

        cur.execute("SELECT COUNT(*) FROM measurements;")
        after = cur.fetchone()[0]

        inserted = int(after - before)
        dup_skipped = int(len(rows) - inserted)
        return inserted, dup_skipped

    finally:
        conn.close()

def fetch_count():
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM measurements;")
        return int(cur.fetchone()[0])
    finally:
        conn.close()

def fetch_series(plant_id: str, metric_type: str, limit: int = 2000):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT timestamp, value, COALESCE(quality_flag, 'ok') as quality_flag
            FROM measurements
            WHERE plant_id = %s AND metric_type = %s
            ORDER BY timestamp ASC
            LIMIT %s
            """,
            (plant_id, metric_type, limit),
        )
        return cur.fetchall()
    finally:
        conn.close()
