# 🌟 Akfen Energy Dashboard

Enerji üretim izleme ve tahmin sistemi - React, FastAPI, PostgreSQL ve XGBoost ile geliştirilmiş tam kapsamlı enerji yönetim platformu.

## ✨ Özellikler

### 📊 Dashboard
- Gerçek zamanlı enerji üretim takibi
- Saatlik ve günlük üretim grafikleri
- Anomali tespiti ve uyarılar
- Çoklu santral desteği
- Canlı bildirimler

### 📈 Raporlama Sistemi
- Haftalık, aylık ve özel tarih aralığı raporları
- PDF export özelliği
- Detaylı günlük ve saatlik analizler
- Performans metrikleri
- Dönemsel karşılaştırmalar

### 🤖 Makine Öğrenmesi (ML)
- **XGBoost** tabanlı tahmin modeli
- 24 saate kadar enerji üretim tahmini
- %87 doğruluk oranı (R² = 0.87)
- Model eğitimi ve metrik takibi
- Görsel tahmin grafikleri

### 📤 Veri Yönetimi
- Excel/CSV dosya yükleme
- Çoklu santral veri desteği
- Otomatik veri kalite kontrolü
- Anomali işaretleme

### 🔐 Güvenlik
- JWT tabanlı kimlik doğrulama
- Kullanıcı yönetimi
- Güvenli API endpoint'leri

## 🛠️ Teknolojiler

### Backend
- **FastAPI** - Modern Python web framework
- **PostgreSQL** - İlişkisel veritabanı
- **XGBoost** - ML modeli
- **Scikit-learn** - Veri işleme ve model değerlendirme
- **Pandas** - Veri analizi
- **JWT** - Kimlik doğrulama

### Frontend
- **React** - UI kütüphanesi
- **Recharts** - Grafik görselleştirme
- **Lucide Icons** - Icon seti
- **Vite** - Build tool

### ML Pipeline
- **XGBoost Regressor** - Ana model
- **StandardScaler** - Veri normalizasyonu
- **Feature Engineering** - Zaman serisi özellikleri

## 📦 Kurulum

### Gereksinimler
- Python 3.9+
- Node.js 16+
- PostgreSQL 13+

### Backend Kurulumu
```bash
# Klasöre git
cd backend

# Sanal ortam oluştur (opsiyonel)
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate  # Windows

# Kütüphaneleri kur
pip3 install -r requirements.txt --break-system-packages

# Mac için OpenMP kur (XGBoost için gerekli)
brew install libomp

# PostgreSQL veritabanını oluştur
psql -U postgres
CREATE DATABASE akfen_db;
\q

# Tabloları oluştur
python3 -c "from storage.pg_store import create_tables; create_tables()"

# Backend'i başlat
python3 -m uvicorn main:app --reload
```

Backend http://localhost:8000 adresinde çalışacak.

### Frontend Kurulumu
```bash
# Klasöre git
cd frontend

# Bağımlılıkları kur
npm install

# Development server'ı başlat
npm run dev
```

Frontend http://localhost:5173 adresinde çalışacak.

## 🚀 Kullanım

### 1. Kayıt Ol / Giriş Yap
- İlk kullanımda kayıt olun
- Email ve şifre ile giriş yapın

### 2. Dashboard
- Gerçek zamanlı üretim verilerini görün
- Santral seçici ile farklı santraller arasında geçiş yapın
- Anomalileri ve uyarıları takip edin

### 3. Raporlar
- Haftalık, aylık veya özel tarih aralığı seçin
- Detaylı grafik ve tablolarla analiz yapın
- PDF olarak rapor indirin

### 4. Tahminler
- "Modeli Eğit" butonu ile ML modelini güncelleyin
- 24 saatlik tahminleri görüntüleyin
- Model performans metriklerini takip edin

### 5. Veri Yükleme
- Excel/CSV dosyalarınızı yükleyin
- Otomatik veri doğrulama yapılır
- Toplu veri girişi yapın

## 📊 ML Model Detayları

### Özellikler (Features)
- **hour**: Günün saati (0-23)
- **day_of_week**: Haftanın günü (0-6)
- **month**: Ay (1-12)
- **lag_1**: 1 saat önceki üretim değeri
- **lag_24**: 24 saat önceki üretim değeri

### Model Performansı
- **MAE**: ~61 kWh
- **RMSE**: ~115 kWh
- **R² Score**: 0.87 (87% accuracy)

### Eğitim
```python
# Model otomatik olarak şunları yapar:
# 1. Normal verileri filtreler
# 2. Feature engineering uygular
# 3. Train/test split (80/20)
# 4. StandardScaler ile normalizasyon
# 5. XGBoost ile eğitim
# 6. Model kaydetme (models/ klasörü)
```

## 🗂️ Proje Yapısı
```
akfen-energy-dashboard/
├── backend/
│   ├── main.py              # FastAPI uygulaması
│   ├── auth.py              # JWT kimlik doğrulama
│   ├── storage/
│   │   └── pg_store.py      # PostgreSQL bağlantısı
│   └── models/              # Eğitilmiş ML modelleri
│       ├── xgboost_model.json
│       └── scaler.pkl
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Ana uygulama
│   │   ├── Login.jsx        # Giriş sayfası
│   │   ├── Reports.jsx      # Raporlama sayfası
│   │   ├── Predictions.jsx  # ML tahmin sayfası
│   │   ├── DataUpload.jsx   # Veri yükleme sayfası
│   │   └── App.css          # Stil dosyaları
│   └── package.json
├── ingestion/               # Veri çekme scriptleri
└── README.md
```

## 🔌 API Endpoints

### Authentication
- `POST /api/auth/register` - Kayıt ol
- `POST /api/auth/login` - Giriş yap
- `GET /api/auth/me` - Kullanıcı bilgileri

### Data
- `GET /api/stats` - Genel istatistikler
- `GET /api/hourly-production` - Saatlik üretim
- `GET /api/daily-production` - Günlük üretim
- `GET /api/anomalies` - Anomali listesi
- `GET /api/plants` - Santral listesi

### Reports
- `GET /api/reports/summary` - Özet rapor
- `GET /api/reports/comparison` - Dönem karşılaştırması
- `GET /api/reports/performance-metrics` - Performans metrikleri

### Machine Learning
- `POST /api/ml/train` - Model eğitimi
- `POST /api/ml/predict` - Tahmin yapma
- `GET /api/ml/metrics` - Model metrikleri

## 🌐 Deployment

### Vercel (Frontend)
```bash
cd frontend
vercel deploy --prod
```

### Railway/Render (Backend)
1. GitHub repository'yi bağla
2. Build command: `pip install -r requirements.txt`
3. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Environment variables ekle

## 📝 Environment Variables

### Backend (.env)
```
DATABASE_URL=postgresql://user:password@host:port/dbname
SECRET_KEY=your-secret-key-here
```

### Frontend (.env)
```
VITE_API_URL=http://localhost:8000/api
```

## 🤝 Katkıda Bulunma

1. Fork edin
2. Feature branch oluşturun (`git checkout -b feature/AmazingFeature`)
3. Commit edin (`git commit -m 'Add some AmazingFeature'`)
4. Push edin (`git push origin feature/AmazingFeature`)
5. Pull Request açın

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## 👥 İletişim

**Proje Sahibi:** Zeynep Sude Çelik  
**GitHub:** [@zepsudecelik](https://github.com/zepsudecelik)  
**Proje Linki:** [https://github.com/zepsudecelik/akfen-energy-dashboard](https://github.com/zepsudecelik/akfen-energy-dashboard)

## 🙏 Teşekkürler

- Akfen Holding için geliştirilmiştir
- XGBoost ekibine
- React ve FastAPI topluluklarına

---

⚡ **Powered by Akfen Energy** ⚡