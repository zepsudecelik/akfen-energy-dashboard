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
Database (SQLite / PostgreSQL)
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
- SQLite ve PostgreSQL desteği
- Streamlit tabanlı web arayüzü
- Zaman serisi grafikleri
- Validation raporunun UI üzerinden görüntülenmesi ve indirilmesi

---

## Proje Klasör Yapısı

akfen-ingestion/
├── adapters/
│ └── excel_adapter.py
├── storage/
│ ├── sqlite_store.py
│ └── pg_store.py
├── app.py
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
- Pandas
- SQLite
- PostgreSQL
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
Notlar
Proje demo amaçlıdır.
Gerçek sistemlerde TimescaleDB / InfluxDB gibi zaman serisi veritabanları tercih edilebilir.
Geliştirmeye açıktır.
