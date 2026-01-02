# Akfen Ingestion - Data Contract (v1)

Bu doküman, Excel’den gelen verinin sistem içinde tek bir standarda
çevrilmesi için kullanılan ortak veri şemasını tanımlar.

## Amaç
Kaynak veri (Excel / CSV / API) değişse bile sistem içinde veri
her zaman aynı formatta tutulur.

## Standard Schema (v1)

### Zorunlu Alanlar
- timestamp (datetime, timezone-aware)
  - Örnek: 2025-12-27T10:00:00+03:00
  - Kural: Timezone yoksa Europe/Istanbul varsayılır

- plant_id (string)
  - Örnek: AKF001

- value (number)
  - Örnek: 125.6

- metric_type (string)
  - Örnek: production

### Opsiyonel Alanlar
- unit (string) — Örnek: kWh
- quality_flag (string) — ok / outlier / negative / missing
- source (string) — excel
- ingested_at (datetime) — sistem tarafından eklenir

## Excel → Schema Mapping (örnek)
- TarihSaat → timestamp
- SantralID → plant_id
- Uretim → value
- metric_type → production (sabit)
