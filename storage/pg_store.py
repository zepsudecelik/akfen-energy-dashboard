# pg_store.py
import os
import psycopg2
from psycopg2.extras import execute_values

# Bağlantı bilgileri (istersen sonra .env yaparız)
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "akfen_db")
PG_USER = os.getenv("PG_USER", "zeynepsudecelik")
PG_PASSWORD = os.getenv("PG_PASSWORD", "akfen_pass")


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
    UNIQUE ile conflict anahtarı: (plant_id, metric_type, timestamp)
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
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
                """
            )
        conn.commit()
    finally:
        conn.close()


def upsert_records(records, batch_size=1000):
    """
    records: list[dict]
    batch_size: kayıt sayısı - büyük dosyalar için optimize edildi
    return: (inserted_count, updated_count)

    UPSERT + doğru inserted count (RETURNING):
      RETURNING (xmax = 0) AS inserted
      - inserted=True  => yeni insert
      - inserted=False => conflict oldu, update edildi

    PERFORMANCE OPTIMIZATIONS:
    1. execute_values ile batch insert (10-100x daha hızlı)
    2. Sub-batching: 50k+ records için multiple transactions
    3. Optimized page_size per batch

    BATCH_SIZE RECOMMENDATIONS:
    - Small files (<10k): 500-1000
    - Medium files (10k-100k): 1000-2000
    - Large files (100k+): 2000-5000
    - Maximum: 10000 (PostgreSQL parameter limit)
    """
    if not records:
        return 0, 0

    # Batch size validation
    if batch_size < 100:
        print(f"WARNING: batch_size={batch_size} is too small, using 100")
        batch_size = 100
    elif batch_size > 10000:
        print(f"WARNING: batch_size={batch_size} is too large, using 10000")
        batch_size = 10000

    # Prepare rows
    rows = []
    for r in records:
        rows.append(
            (
                r["timestamp"],  # ISO string -> psycopg2 TIMESTAMPTZ parse eder
                r["plant_id"],
                r["metric_type"],
                float(r["value"]),
                r.get("unit"),
                r.get("source"),
                r.get("quality_flag"),
            )
        )

    total_rows = len(rows)

    # OPTIMIZATION: Sub-batching for very large inserts (50k+)
    # Bu hem memory hem de transaction size'ı optimize eder
    MAX_ROWS_PER_TRANSACTION = 50000

    if total_rows > MAX_ROWS_PER_TRANSACTION:
        print(f"Large insert ({total_rows} rows): using sub-batching...")
        total_inserted = 0
        total_updated = 0

        # Process in sub-batches
        for i in range(0, total_rows, MAX_ROWS_PER_TRANSACTION):
            sub_rows = rows[i:i + MAX_ROWS_PER_TRANSACTION]
            batch_num = (i // MAX_ROWS_PER_TRANSACTION) + 1
            total_batches = (total_rows + MAX_ROWS_PER_TRANSACTION - 1) // MAX_ROWS_PER_TRANSACTION

            print(f"  Sub-batch {batch_num}/{total_batches}: {len(sub_rows)} rows...")
            ins, upd = _execute_batch(sub_rows, batch_size)
            total_inserted += ins
            total_updated += upd

        print(f"Sub-batching complete: {total_inserted} inserted, {total_updated} updated")
        return total_inserted, total_updated

    # Normal single-transaction insert
    return _execute_batch(rows, batch_size)


def _execute_batch(rows, page_size):
    """
    Internal: Execute a single batch insert.
    Returns (inserted_count, updated_count)
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            sql = """
                INSERT INTO measurements
                    (timestamp, plant_id, metric_type, value, unit, source, quality_flag)
                VALUES %s
                ON CONFLICT (plant_id, metric_type, timestamp)
                DO UPDATE SET
                    value        = EXCLUDED.value,
                    unit         = EXCLUDED.unit,
                    source       = EXCLUDED.source,
                    quality_flag = EXCLUDED.quality_flag
                RETURNING (xmax = 0) AS inserted;
            """

            # execute_values: page_size controls rows per network round-trip
            execute_values(cur, sql, rows, page_size=page_size)

            flags = cur.fetchall()  # [(True/False,), ...]
            inserted = sum(1 for (flag,) in flags if flag)
            updated = len(flags) - inserted

        conn.commit()
        return int(inserted), int(updated)

    except Exception as e:
        conn.rollback()
        print(f"ERROR during batch insert: {e}")
        raise

    finally:
        conn.close()


# Alias for backward compatibility
def insert_records(records, batch_size=1000):
    """
    Alias for upsert_records - backward compatibility.
    Returns (inserted_count, duplicates_skipped)
    """
    inserted, updated = upsert_records(records, batch_size)
    return inserted, updated  # updated = duplicates için


def fetch_count():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM measurements;")
            return int(cur.fetchone()[0])
    finally:
        conn.close()


def fetch_series(plant_id: str, metric_type: str, limit: int = 2000):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
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


if __name__ == "__main__":
    # Hızlı smoke test
    init_db()

    sample = [
        {
            "timestamp": "2026-01-21T10:00:00Z",
            "plant_id": "P1",
            "metric_type": "power",
            "value": 123.4,
            "unit": "kW",
            "source": "ingest",
            "quality_flag": "ok",
        },
        {
            "timestamp": "2026-01-21T10:00:00Z",  # aynı key -> UPDATE sayılmalı
            "plant_id": "P1",
            "metric_type": "power",
            "value": 200.0,
            "unit": "kW",
            "source": "ingest",
            "quality_flag": "ok",
        },
    ]

    ins, upd = upsert_records(sample)
    print("inserted:", ins, "updated:", upd, "total:", fetch_count())
