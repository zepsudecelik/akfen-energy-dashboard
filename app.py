import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import json
from pathlib import Path


from storage.pg_store import fetch_series


st.title("Akfen Ingestion Demo (SQLite)")
REPORT_PATH = Path("reports/data_validation_report.json")


plant_id = st.text_input("plant_id", "AKFEN_MAHSUP")
metric_type = st.text_input("metric_type", "production")
limit = st.slider("limit", 100, 5000, 2000, 100)

rows = fetch_series(plant_id=plant_id, metric_type=metric_type, limit=limit)

if not rows:
    st.warning("DB’de veri yok. Önce ingestion çalıştır: python3 adapters/excel_adapter.py")
    st.stop()

df = pd.DataFrame(rows, columns=["timestamp", "value", "quality_flag"])
df["timestamp"] = pd.to_datetime(df["timestamp"])

st.subheader("Son 20 kayıt")
st.dataframe(df.tail(20), use_container_width=True)

st.subheader("Validation Report")

if REPORT_PATH.exists():
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))

    # Kısa özet (poster/demo için güzel)
    c = report.get("counts", {})
    v = report.get("validation", {})

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Rows", c.get("rows_in_sheet", 0))
    col2.metric("Normalized", c.get("records_normalized", 0))
    col3.metric("Duplicates", c.get("duplicate_rows", 0))
    col4.metric("Skipped", c.get("skipped_rows", 0))

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Outliers", v.get("outliers", 0))
    col2.metric("Negatives", v.get("negative_values", 0))
    col3.metric("Missing Hours", v.get("missing_hours_count", 0))
    col4.metric("Frequency", v.get("frequency_detected", "unknown"))

    # Tam JSON’u aç/kapa
    with st.expander("Report JSON (full)"):
        st.json(report)

    # İndirme butonu
    st.download_button(
        "Download report JSON",
        data=REPORT_PATH.read_bytes(),
        file_name="data_validation_report.json",
        mime="application/json",
    )
else:
    st.warning("Validation raporu bulunamadı: reports/data_validation_report.json")
    st.info("Önce ingestion çalıştır: python3 adapters/excel_adapter.py")


st.subheader("Zaman serisi grafiği")
fig = plt.figure()
plt.plot(df["timestamp"], df["value"])
plt.xlabel("timestamp")
plt.ylabel("value (kWh)")
st.pyplot(fig)
