import os
import sys

# Proje kökünü (akfen-ingestion) import path'e ekle: storage/sqlite_store import edilsin
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
from datetime import datetime, date, time
from zoneinfo import ZoneInfo  # Python 3.9+

import json
from pathlib import Path

import pandas as pd

from storage.pg_store import init_db, insert_records


# =========================
# CONFIG
# =========================

# İSTER EXCEL, İSTER CSV:
INPUT_PATH = "data/GTSMahsup_6033042025 (1).xlsx"
# INPUT_PATH = "data/sample.csv"

SHEET_NAME = "Mahsup"  # CSV için kullanılmaz

PLANT_ID = "AKFEN_MAHSUP"
TZ = ZoneInfo("Europe/Istanbul")

COL_DATE = "Tarih"
COL_TIME = "Saat"
COL_STATUS = "Durum"

REPORT_PATH = "reports/data_validation_report.json"
LOG_PATH = "logs/ingestion.log"


# =========================
# HELPERS
# =========================

def _safe_strip(x) -> str:
    return str(x).strip()


def _log(msg: str):
    os.makedirs("logs", exist_ok=True)
    ts = datetime.now(tz=TZ).isoformat()
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"{ts} {msg}\n")


def _write_report(report: dict):
    os.makedirs("reports", exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def _parse_datetime(date_val, time_val):
    # Tarih parse
    if isinstance(date_val, pd.Timestamp):
        d = date_val.date()
    elif isinstance(date_val, date):
        d = date_val
    else:
        ds = _safe_strip(date_val)
        d = datetime.strptime(ds, "%d/%m/%Y").date()

    # Saat parse
    if isinstance(time_val, pd.Timestamp):
        t = time_val.time()
    elif isinstance(time_val, time):
        t = time_val
    else:
        ts = _safe_strip(time_val)
        t = datetime.strptime(ts, "%H:%M").time()

    dt = datetime.combine(d, t).replace(tzinfo=TZ)
    return dt


def _choose_value_column(columns):
    # 1) Mahsuplaşma Net Üretim
    candidates = [c for c in columns if ("Mahsuplaşma" in c and "Net Üretim" in c)]
    if candidates:
        return candidates[0]

    # 2) Genel Net Üretim
    candidates = [c for c in columns if "Net Üretim" in c]
    if candidates:
        return candidates[0]

    return None


def _detect_frequency(timestamps):
    if len(timestamps) < 3:
        return "unknown"

    diffs_min = []
    ts_sorted = sorted(timestamps)
    for a, b in zip(ts_sorted, ts_sorted[1:]):
        diffs_min.append(int((b - a).total_seconds() // 60))

    most_common = max(set(diffs_min), key=diffs_min.count)
    if most_common == 60:
        return "hourly"
    if most_common == 1440:
        return "daily"
    return f"irregular({most_common}min)"


def _compute_outlier_threshold(values):
    """
    Küçük datasetlerde de demo yapılabilsin diye min=5.
    p01-p99 bandı: pratik, hızlı.
    """
    if len(values) < 5:
        return None
    s = pd.Series(values)
    low = float(s.quantile(0.01))
    high = float(s.quantile(0.99))
    return {"method": "p01_p99", "low": low, "high": high}


def _find_missing_hours(timestamps_dt):
    if not timestamps_dt:
        return [], 0

    ts_sorted = sorted(timestamps_dt)
    start = ts_sorted[0]
    end = ts_sorted[-1]

    expected = set()
    cur = start
    while cur <= end:
        expected.add(cur)
        cur = cur + pd.Timedelta(hours=1)

    actual = set(ts_sorted)
    missing = sorted(expected - actual)
    return [t.isoformat() for t in missing[:50]], len(missing)


def _read_input_to_df(path: str) -> pd.DataFrame:
    """
    Adapter katmanı:
    - .xlsx/.xls -> Excel
    - .csv -> CSV (delimiter otomatik deneme: ',' ve ';')
    """
    ext = os.path.splitext(path.lower())[1]

    if ext in [".xlsx", ".xls"]:
        return pd.read_excel(path, sheet_name=SHEET_NAME)

    if ext == ".csv":
        df = pd.read_csv(path, delimiter=",")
        if df.shape[1] == 1:  # delimiter yanlışsa tek kolon olur
            df = pd.read_csv(path, delimiter=";")
        return df

    raise RuntimeError(f"unsupported_file_type: {ext}")


# =========================
# MAIN PIPELINE
# =========================

def ingest_validate_report_and_write_db():
    # 0) Dosya okuma (Excel/CSV)
    try:
        df = _read_input_to_df(INPUT_PATH)
    except Exception as e:
        # Veri gelmedi / dosya bozuk / sheet yok
        report = {
            "source_file": INPUT_PATH,
            "sheet": SHEET_NAME,
            "plant_id": PLANT_ID,
            "metric_type": "production",
            "unit": "kWh",
            "timezone_assumed": str(TZ),
            "counts": {
                "rows_in_sheet": 0,
                "records_normalized": 0,
                "records_written_candidate": 0,
                "skipped_rows": 0,
                "duplicate_rows": 0,
            },
            "validation": {
                "no_data": True,
                "timezone_ok": False,
                "frequency_detected": "unknown",
                "negative_values": 0,
                "outliers": 0,
                "outlier_rule": None,
                "missing_hours_count": 0,
            },
            "samples": {
                "first_3_records": [],
                "error_examples": [{"row": None, "reason": f"read_input_failed: {e}"}],
                "outlier_examples": [],
                "missing_hours_examples": [],
            },
        }
        _write_report(report)
        _log(f"ALARM no_data=true reason=read_input_failed error={e}")
        print("NO DATA: input okunamadı. Report yazıldı.")
        print(f"REPORT WRITTEN: {REPORT_PATH}")
        return [], report

    # Kolon adlarını normalize et
    df.columns = [str(c).strip() for c in df.columns]
    print("COLUMNS:", list(df.columns))

    col_value = _choose_value_column(df.columns)
    if not col_value:
        report = {
            "source_file": INPUT_PATH,
            "sheet": SHEET_NAME,
            "plant_id": PLANT_ID,
            "metric_type": "production",
            "unit": "kWh",
            "timezone_assumed": str(TZ),
            "counts": {
                "rows_in_sheet": int(len(df)),
                "records_normalized": 0,
                "records_written_candidate": 0,
                "skipped_rows": 0,
                "duplicate_rows": 0,
            },
            "validation": {
                "no_data": True,
                "timezone_ok": True,
                "frequency_detected": "unknown",
                "negative_values": 0,
                "outliers": 0,
                "outlier_rule": None,
                "missing_hours_count": 0,
            },
            "samples": {
                "first_3_records": [],
                "error_examples": [{"row": None, "reason": "value_column_not_found"}],
                "outlier_examples": [],
                "missing_hours_examples": [],
            },
        }
        _write_report(report)
        _log("ALARM no_data=true reason=value_column_not_found")
        raise RuntimeError("Net Üretim kolonu bulunamadı.")

    print("USING VALUE COLUMN:", col_value)

    # 1) Normalize + hard validation
    records = []
    errors = []
    skipped = 0

    for i, row in df.iterrows():
        try:
            dt = _parse_datetime(row[COL_DATE], row[COL_TIME])
            ts_iso = dt.isoformat()

            value = row[col_value]
            if pd.isna(value):
                raise ValueError("value is empty")

            value_f = float(value)

            status = "ok"
            if COL_STATUS in df.columns:
                s = row.get(COL_STATUS)
                if not pd.isna(s):
                    status = _safe_strip(s).lower()

            record = {
                "timestamp": ts_iso,
                "plant_id": PLANT_ID,
                "value": value_f,
                "metric_type": "production",
                "unit": "kWh",
                "source": "file",
                "quality_flag": status,
            }
            records.append(record)

        except Exception as e:
            skipped += 1
            errors.append({"row": int(i), "reason": str(e)})
            _log(f"SKIP row={int(i)} reason={e}")
            print(f"[SKIP] row={i} reason={e}")

    no_data = (len(records) == 0)

    # 2) Dedup
    seen = set()
    duplicates = 0
    deduped_records = []
    for r in records:
        key = (r["plant_id"], r["timestamp"], r["metric_type"])
        if key in seen:
            duplicates += 1
        else:
            seen.add(key)
            deduped_records.append(r)

    # 3) Frequency + timezone
    timestamps_dt = [datetime.fromisoformat(r["timestamp"]) for r in deduped_records]
    frequency = _detect_frequency(timestamps_dt)
    timezone_ok = all(t.tzinfo is not None for t in timestamps_dt)

    # 4) Negative + outlier
    values = [r["value"] for r in deduped_records if pd.notna(r["value"])]
    negatives = sum(1 for v in values if v < 0)

    outlier_count = 0
    outlier_samples = []
    outlier_rule = None

    thr = _compute_outlier_threshold(values)
    if thr is not None:
        outlier_rule = thr
        low = thr["low"]
        high = thr["high"]

        for r in deduped_records:
            v = r["value"]
            if v < 0:
                r["quality_flag"] = "negative"
            elif v < low or v > high:
                outlier_count += 1
                if r.get("quality_flag") in ["ok", "normal"]:
                    r["quality_flag"] = "outlier"
                if len(outlier_samples) < 5:
                    outlier_samples.append({"timestamp": r["timestamp"], "value": v})

    # 5) Missing hours
    missing_examples, missing_count = ([], 0)
    if frequency == "hourly":
        missing_examples, missing_count = _find_missing_hours(timestamps_dt)

    # 6) Report
    report = {
        "source_file": INPUT_PATH,
        "sheet": SHEET_NAME,
        "plant_id": PLANT_ID,
        "metric_type": "production",
        "unit": "kWh",
        "timezone_assumed": str(TZ),
        "counts": {
            "rows_in_sheet": int(len(df)),
            "records_normalized": int(len(records)),
            "records_written_candidate": int(len(deduped_records)),
            "skipped_rows": int(skipped),
            "duplicate_rows": int(duplicates),
        },
        "validation": {
            "no_data": bool(no_data),
            "timezone_ok": bool(timezone_ok),
            "frequency_detected": frequency,
            "negative_values": int(negatives),
            "outliers": int(outlier_count),
            "outlier_rule": outlier_rule,
            "missing_hours_count": int(missing_count),
        },
        "samples": {
            "first_3_records": deduped_records[:3],
            "error_examples": errors[:10],
            "outlier_examples": outlier_samples,
            "missing_hours_examples": missing_examples,
        },
    }

    _write_report(report)

    # 7) DB WRITE (başarılı akışta burada olmalı)
    init_db()
    inserted, dup_skipped = insert_records(deduped_records)
    print(f"DB WRITE: inserted={inserted} duplicate_skipped={dup_skipped}")
    _log(f"DB_WRITE inserted={inserted} duplicate_skipped={dup_skipped}")

    print(
        f"OK={len(records)} SKIPPED={skipped} DEDUPED={len(deduped_records)} "
        f"DUPLICATES={duplicates} OUTLIERS={outlier_count} NEGATIVES={negatives} "
        f"MISSING_HOURS={missing_count}"
    )
    print(f"REPORT WRITTEN: {REPORT_PATH}")

    _log(
        f"INGEST summary file={INPUT_PATH} rows={len(df)} normalized={len(records)} deduped={len(deduped_records)} "
        f"skipped={skipped} duplicates={duplicates} outliers={outlier_count} negatives={negatives} missing_hours={missing_count}"
    )

    return deduped_records, report


if __name__ == "__main__":
    data, report = ingest_validate_report_and_write_db()
    print("First 3 records:")
    for r in data[:3]:
        print(r)
