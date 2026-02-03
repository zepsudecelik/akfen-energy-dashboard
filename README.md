# akfen-ingestion
Energy data ingestion, validation and visualization pipeline
# Akfen Ingestion Pipeline

Bu proje, enerji üretim verilerinin **Excel / CSV dosyalarından alınarak**
doğrulanması, normalize edilmesi, veritabanına yazılması ve
bir kullanıcı arayüzü üzerinden görselleştirilmesini amaçlayan
örnek bir **veri ingestion (veri alma) sistemi**dir.

## Projenin Amacı

- Farklı formatlardaki (Excel / CSV) ham verilerin tek bir standart şemaya dönüştürülmesi
- Veri kalitesinin ingestion aşamasında kontrol edilmesi
- Zaman serisi verilerinin veritabanında saklanması
- Sonuçların bir web arayüzü üzerinden incelenebilmesi

Bu yapı, gerçek hayattaki **enerji veri platformları** ve **ETL / ingestion pipeline**’larının
basitleştirilmiş bir demosu olarak tasarlanmıştır.

---

## Genel Mimari

Excel / CSV
↓
Adapter (excel_adapter.py)
↓
Validation & Quality Flagging
↓
Database (PostgreSQL)
↓
Streamlit UI

---

## Özellikler

- Excel ve CSV dosyalarını otomatik algılayan adapter
- Tarih + saat alanlarından timezone’lu timestamp üretimi
- Duplicate kayıtların engellenmesi
- Veri doğrulama (validation) raporu üretimi
- Quality flag atama:
  - `normal`
  - `outlier`
  - `negative`
- PostgreSQL database (production-ready)
- Streamlit tabanlı web arayüzü
- Zaman serisi grafikleri
- Validation raporunun UI üzerinden görüntülenmesi ve indirilmesi

---

## Proje Klasör Yapısı

akfen-ingestion/
├── adapters/
│ └── excel_adapter.py (PERFORMANCE OPTIMIZED)
├── storage/
│ └── pg_store.py (PostgreSQL backend)
├── app.py (Streamlit UI)
├── docs/
│ └── data_contract.md
├── logs/
├── reports/
└── README.md

---

## Ingestion Süreci

1. Girdi dosyası (Excel / CSV) okunur
2. Kolonlar normalize edilir
3. Timestamp oluşturulur
4. Kayıtlar standart şemaya dönüştürülür
5. Duplicate kayıtlar ayıklanır
6. Veri kalitesi kontrolleri yapılır
7. Validation raporu oluşturulur
8. Kayıtlar veritabanına yazılır

---

## Kullanılan Teknolojiler

- Python 3.9+
- Pandas (vectorized operations for performance)
- PostgreSQL (psycopg2 with batch insert optimization)
- Streamlit
- Matplotlib

---

## Çalıştırma

### Ingestion

```bash
python3 adapters/excel_adapter.py
Web Arayüzü
streamlit run app.py
Validation Raporu
Ingestion sonunda otomatik olarak
reports/data_validation_report.json
dosyası üretilir.
Bu rapor:

Okunan satır sayısını
Normalize edilen kayıtları
Outlier / negative değerleri
Zaman frekansını
Eksik saatleri
içerir ve Streamlit UI üzerinden görüntülenebilir.

---

## Performance

**Optimized for Large Files:**
- Vectorized operations (10-100x faster)
- Memory-efficient chunked processing
- Batch database inserts
- Supports 10M+ rows

See [adapters/excel_adapter.py](adapters/excel_adapter.py) header for performance details.

---

## Notlar

- Proje production-ready PostgreSQL backend kullanır
- Çok büyük dosyalar için (500k+ satır) chunked processing modu mevcuttur
- Gerçek sistemlerde TimescaleDB / InfluxDB gibi zaman serisi veritabanları da tercih edilebilir
- Geliştirmeye açıktır
