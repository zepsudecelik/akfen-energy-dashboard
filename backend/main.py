"""
FastAPI Backend for Akfen Energy Dashboard
"""

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import sys
import os
import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.pg_store import get_conn
from auth import (
    UserCreate, UserLogin, Token, User,
    get_password_hash, verify_password, 
    create_access_token, verify_token
)

app = FastAPI(
    title="Akfen Energy API",
    description="Energy production monitoring API",
    version="1.0.0"
)

# CORS - React frontend için
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://172.20.10.3:5173",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Model dosya yolları
MODEL_PATH = "models/xgboost_model.json"
SCALER_PATH = "models/scaler.pkl"

# Models klasörünü oluştur
os.makedirs("models", exist_ok=True)


# =========================
# AUTHENTICATION ENDPOINTS
# =========================

@app.post("/api/auth/register", response_model=User)
def register(user: UserCreate):
    """Register new user"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # Check if user exists
            cur.execute("SELECT id FROM users WHERE email = %s", (user.email,))
            if cur.fetchone():
                raise HTTPException(
                    status_code=400, 
                    detail="Email already registered"
                )
            
            # Hash password
            hashed_password = get_password_hash(user.password)
            
            # Create user
            cur.execute("""
                INSERT INTO users (email, password_hash, full_name, created_at)
                VALUES (%s, %s, %s, NOW())
                RETURNING id, email, full_name, created_at
            """, (user.email, hashed_password, user.full_name))
            
            row = cur.fetchone()
            conn.commit()
            
            return User(
                id=row[0],
                email=row[1],
                full_name=row[2],
                created_at=row[3].isoformat()
            )
    finally:
        conn.close()


@app.post("/api/auth/login", response_model=Token)
def login(user: UserLogin):
    """Login user and return JWT token"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # Get user
            cur.execute("""
                SELECT id, email, password_hash, full_name 
                FROM users WHERE email = %s
            """, (user.email,))
            
            row = cur.fetchone()
            if not row:
                raise HTTPException(
                    status_code=401,
                    detail="Incorrect email or password"
                )
            
            user_id, email, password_hash, full_name = row
            
            # Verify password
            if not verify_password(user.password, password_hash):
                raise HTTPException(
                    status_code=401,
                    detail="Incorrect email or password"
                )
            
            # Create access token
            access_token = create_access_token(
                data={"sub": email, "user_id": user_id, "name": full_name}
            )
            
            return Token(access_token=access_token, token_type="bearer")
    finally:
        conn.close()


@app.get("/api/auth/me", response_model=User)
def get_current_user_info(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current logged in user"""
    token = credentials.credentials
    token_data = verify_token(token)
    
    if token_data is None or token_data.email is None:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials"
        )
    
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, email, full_name, created_at 
                FROM users WHERE email = %s
            """, (token_data.email,))
            
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="User not found")
            
            return User(
                id=row[0],
                email=row[1],
                full_name=row[2],
                created_at=row[3].isoformat()
            )
    finally:
        conn.close()


# =========================
# HEALTH CHECK
# =========================

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "Akfen Energy API",
        "version": "1.0.0"
    }


# =========================
# DATA ENDPOINTS
# =========================

@app.get("/api/stats")
def get_stats(plant_id: str = "AKFEN_MAHSUP"):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    COUNT(*) as total_records,
                    SUM(value) as total_production,
                    AVG(value) as avg_production,
                    MAX(value) as max_production,
                    MIN(timestamp) as first_date,
                    MAX(timestamp) as last_date,
                    COUNT(CASE WHEN quality_flag = 'outlier' THEN 1 END) as outliers,
                    COUNT(CASE WHEN quality_flag = 'negative' THEN 1 END) as negatives
                FROM measurements
                WHERE plant_id = %s
            """, (plant_id,))
            
            row = cur.fetchone()
            
            if not row or row[0] == 0:
                raise HTTPException(status_code=404, detail="No data found")
            
            return {
                "total_records": int(row[0]),
                "total_production": float(row[1] or 0),
                "average_production": float(row[2] or 0),
                "max_production": float(row[3] or 0),
                "date_range": {
                    "start": row[4].isoformat() if row[4] else None,
                    "end": row[5].isoformat() if row[5] else None,
                },
                "outliers_count": int(row[6]),
                "negatives_count": int(row[7])
            }
    finally:
        conn.close()


@app.get("/api/hourly-production")
def get_hourly_production(
    plant_id: str = "AKFEN_MAHSUP",
    days: int = Query(default=7, le=365)
):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    DATE_TRUNC('hour', timestamp) as hour,
                    AVG(value) as avg_value
                FROM measurements
                WHERE plant_id = %s 
                  AND timestamp >= NOW() - INTERVAL '%s days'
                GROUP BY DATE_TRUNC('hour', timestamp)
                ORDER BY hour ASC
            """, (plant_id, days))
            
            rows = cur.fetchall()
            
            return [
                {
                    "timestamp": row[0].isoformat(),
                    "avg": float(row[1])
                }
                for row in rows
            ]
    finally:
        conn.close()


@app.get("/api/daily-production")
def get_daily_production(
    plant_id: str = "AKFEN_MAHSUP",
    months: int = Query(default=1, le=12)
):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    DATE(timestamp) as day,
                    SUM(value) as total_production
                FROM measurements
                WHERE plant_id = %s 
                  AND timestamp >= NOW() - INTERVAL '%s months'
                GROUP BY DATE(timestamp)
                ORDER BY day ASC
            """, (plant_id, months))
            
            rows = cur.fetchall()
            
            return [
                {
                    "date": row[0].isoformat(),
                    "total": float(row[1])
                }
                for row in rows
            ]
    finally:
        conn.close()


@app.get("/api/anomalies")
def get_anomalies(
    plant_id: str = "AKFEN_MAHSUP",
    limit: int = Query(default=10, le=100)
):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # Get average for deviation calculation
            cur.execute("""
                SELECT AVG(value) 
                FROM measurements 
                WHERE plant_id = %s AND quality_flag = 'normal'
            """, (plant_id,))
            avg_value = cur.fetchone()[0] or 0
            
            # Get anomalies
            cur.execute("""
                SELECT timestamp, value, quality_flag
                FROM measurements
                WHERE plant_id = %s 
                  AND quality_flag IN ('outlier', 'negative')
                ORDER BY timestamp DESC
                LIMIT %s
            """, (plant_id, limit))
            
            rows = cur.fetchall()
            
            return [
                {
                    "timestamp": row[0].isoformat(),
                    "value": float(row[1]),
                    "quality_flag": row[2],
                    "deviation": float(row[1] - avg_value) if avg_value else None
                }
                for row in rows
            ]
    finally:
        conn.close()


# =========================
# REPORTING ENDPOINTS
# =========================

@app.get("/api/reports/summary")
def get_report_summary(
    plant_id: str = "AKFEN_MAHSUP",
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    period: str = Query("weekly", description="weekly, monthly, or custom")
):
    """Generate comprehensive report summary"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # Determine date range
            if period == "weekly":
                end = datetime.now()
                start = end - timedelta(days=7)
            elif period == "monthly":
                end = datetime.now()
                start = end - timedelta(days=30)
            else:  # custom
                if not start_date or not end_date:
                    raise HTTPException(status_code=400, detail="start_date and end_date required for custom period")
                start = datetime.fromisoformat(start_date)
                end = datetime.fromisoformat(end_date)
            
            # Overall statistics
            cur.execute("""
                SELECT 
                    COUNT(*) as total_records,
                    SUM(value) as total_production,
                    AVG(value) as avg_production,
                    MAX(value) as max_production,
                    MIN(value) as min_production,
                    COUNT(CASE WHEN quality_flag = 'outlier' THEN 1 END) as outliers,
                    COUNT(CASE WHEN quality_flag = 'negative' THEN 1 END) as negatives
                FROM measurements
                WHERE plant_id = %s
                  AND timestamp BETWEEN %s AND %s
            """, (plant_id, start, end))
            
            row = cur.fetchone()
            
            # Daily breakdown
            cur.execute("""
                SELECT 
                    DATE(timestamp) as day,
                    SUM(value) as daily_total,
                    AVG(value) as daily_avg,
                    MAX(value) as daily_max,
                    COUNT(*) as data_points
                FROM measurements
                WHERE plant_id = %s
                  AND timestamp BETWEEN %s AND %s
                GROUP BY DATE(timestamp)
                ORDER BY day ASC
            """, (plant_id, start, end))
            
            daily_breakdown = []
            for r in cur.fetchall():
                daily_breakdown.append({
                    "date": r[0].isoformat(),
                    "total": float(r[1] or 0),
                    "average": float(r[2] or 0),
                    "max": float(r[3] or 0),
                    "data_points": int(r[4])
                })
            
            # Hourly pattern
            cur.execute("""
                SELECT 
                    EXTRACT(HOUR FROM timestamp) as hour,
                    AVG(value) as avg_production
                FROM measurements
                WHERE plant_id = %s
                  AND timestamp BETWEEN %s AND %s
                GROUP BY EXTRACT(HOUR FROM timestamp)
                ORDER BY hour ASC
            """, (plant_id, start, end))
            
            hourly_pattern = []
            for r in cur.fetchall():
                hourly_pattern.append({
                    "hour": int(r[0]),
                    "average": float(r[1] or 0)
                })
            
            # Peak production day
            cur.execute("""
                SELECT 
                    DATE(timestamp) as day,
                    SUM(value) as daily_total
                FROM measurements
                WHERE plant_id = %s
                  AND timestamp BETWEEN %s AND %s
                GROUP BY DATE(timestamp)
                ORDER BY daily_total DESC
                LIMIT 1
            """, (plant_id, start, end))
            
            peak_day = cur.fetchone()
            
            return {
                "period": {
                    "type": period,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "days": (end - start).days
                },
                "summary": {
                    "total_records": int(row[0]),
                    "total_production_kwh": float(row[1] or 0),
                    "total_production_mwh": float(row[1] or 0) / 1000,
                    "average_production": float(row[2] or 0),
                    "max_production": float(row[3] or 0),
                    "min_production": float(row[4] or 0),
                    "outliers_count": int(row[5]),
                    "negatives_count": int(row[6]),
                    "data_quality": (1 - (int(row[5]) + int(row[6])) / int(row[0])) * 100 if row[0] > 0 else 100
                },
                "peak_day": {
                    "date": peak_day[0].isoformat() if peak_day else None,
                    "production": float(peak_day[1]) if peak_day else 0
                },
                "daily_breakdown": daily_breakdown,
                "hourly_pattern": hourly_pattern
            }
    finally:
        conn.close()


@app.get("/api/reports/comparison")
def get_comparison_report(
    plant_id: str = "AKFEN_MAHSUP",
    period1_start: str = Query(..., description="Period 1 start date"),
    period1_end: str = Query(..., description="Period 1 end date"),
    period2_start: str = Query(..., description="Period 2 start date"),
    period2_end: str = Query(..., description="Period 2 end date")
):
    """Compare two time periods"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # Period 1 stats
            cur.execute("""
                SELECT 
                    SUM(value) as total,
                    AVG(value) as avg,
                    MAX(value) as max,
                    COUNT(*) as records
                FROM measurements
                WHERE plant_id = %s
                  AND timestamp BETWEEN %s AND %s
            """, (plant_id, period1_start, period1_end))
            
            p1 = cur.fetchone()
            
            # Period 2 stats
            cur.execute("""
                SELECT 
                    SUM(value) as total,
                    AVG(value) as avg,
                    MAX(value) as max,
                    COUNT(*) as records
                FROM measurements
                WHERE plant_id = %s
                  AND timestamp BETWEEN %s AND %s
            """, (plant_id, period2_start, period2_end))
            
            p2 = cur.fetchone()
            
            # Calculate changes
            total_change = ((p2[0] - p1[0]) / p1[0] * 100) if p1[0] > 0 else 0
            avg_change = ((p2[1] - p1[1]) / p1[1] * 100) if p1[1] > 0 else 0
            
            return {
                "period1": {
                    "start": period1_start,
                    "end": period1_end,
                    "total_production": float(p1[0] or 0),
                    "average_production": float(p1[1] or 0),
                    "max_production": float(p1[2] or 0),
                    "records": int(p1[3])
                },
                "period2": {
                    "start": period2_start,
                    "end": period2_end,
                    "total_production": float(p2[0] or 0),
                    "average_production": float(p2[1] or 0),
                    "max_production": float(p2[2] or 0),
                    "records": int(p2[3])
                },
                "comparison": {
                    "total_change_percent": round(total_change, 2),
                    "average_change_percent": round(avg_change, 2),
                    "trend": "increase" if total_change > 0 else "decrease" if total_change < 0 else "stable"
                }
            }
    finally:
        conn.close()


@app.get("/api/reports/performance-metrics")
def get_performance_metrics(
    plant_id: str = "AKFEN_MAHSUP",
    days: int = Query(default=30, le=365)
):
    """Get performance metrics and trends"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # Weekly performance
            cur.execute("""
                SELECT 
                    DATE_TRUNC('week', timestamp) as week,
                    SUM(value) as weekly_total,
                    AVG(value) as weekly_avg,
                    COUNT(*) as data_points
                FROM measurements
                WHERE plant_id = %s
                  AND timestamp >= NOW() - INTERVAL '%s days'
                GROUP BY DATE_TRUNC('week', timestamp)
                ORDER BY week ASC
            """, (plant_id, days))
            
            weekly_trend = []
            for row in cur.fetchall():
                weekly_trend.append({
                    "week": row[0].isoformat(),
                    "total": float(row[1] or 0),
                    "average": float(row[2] or 0),
                    "data_points": int(row[3])
                })
            
            # Capacity factor
            cur.execute("""
                SELECT 
                    SUM(value) as total_production,
                    COUNT(DISTINCT DATE(timestamp)) as days_operated
                FROM measurements
                WHERE plant_id = %s
                  AND timestamp >= NOW() - INTERVAL '%s days'
            """, (plant_id, days))
            
            row = cur.fetchone()
            total_production = float(row[0] or 0)
            days_operated = int(row[1])
            
            theoretical_max = 1000 * 24 * days_operated
            capacity_factor = (total_production / theoretical_max * 100) if theoretical_max > 0 else 0
            
            return {
                "period_days": days,
                "weekly_trend": weekly_trend,
                "performance": {
                    "capacity_factor": round(capacity_factor, 2),
                    "total_production_kwh": total_production,
                    "days_operated": days_operated,
                    "average_daily_production": total_production / days_operated if days_operated > 0 else 0
                }
            }
    finally:
        conn.close()


# =========================
# MACHINE LEARNING ENDPOINTS
# =========================

@app.post("/api/ml/train")
async def train_model(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """XGBoost modelini eğit"""
    # Token verify
    token = credentials.credentials
    token_data = verify_token(token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # Veritabanından veri çek
            cur.execute("""
                SELECT 
                    EXTRACT(HOUR FROM timestamp) as hour,
                    EXTRACT(DOW FROM timestamp) as day_of_week,
                    EXTRACT(MONTH FROM timestamp) as month,
                    value,
                    LAG(value, 1) OVER (ORDER BY timestamp) as lag_1,
                    LAG(value, 24) OVER (ORDER BY timestamp) as lag_24
                FROM measurements
                WHERE quality_flag = 'normal'
                ORDER BY timestamp
            """)
            
            rows = cur.fetchall()
            
            if len(rows) < 100:
                raise HTTPException(status_code=400, detail="Yeterli veri yok (min 100 kayıt)")
            
            # DataFrame oluştur
            df = pd.DataFrame(rows, columns=['hour', 'day_of_week', 'month', 'value', 'lag_1', 'lag_24'])
            df = df.dropna()
            
            # Feature'lar ve target
            X = df[['hour', 'day_of_week', 'month', 'lag_1', 'lag_24']]
            y = df['value']
            
            # Train/test split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Scaling
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # XGBoost model
            model = xgb.XGBRegressor(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=42
            )
            
            model.fit(X_train_scaled, y_train)
            
            # Predictions
            y_pred = model.predict(X_test_scaled)
            
            # Metrics
            mae = mean_absolute_error(y_test, y_pred)
            mse = mean_squared_error(y_test, y_pred)
            rmse = np.sqrt(mse)
            r2 = r2_score(y_test, y_pred)
            
            # Model kaydet
            model.save_model(MODEL_PATH)
            joblib.dump(scaler, SCALER_PATH)
            
            return {
                "status": "success",
                "metrics": {
                    "mae": float(mae),
                    "mse": float(mse),
                    "rmse": float(rmse),
                    "r2": float(r2)
                },
                "training_samples": len(X_train),
                "test_samples": len(X_test),
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.post("/api/ml/predict")
async def predict_energy(
    hours_ahead: int = 24,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Enerji üretim tahmini yap"""
    # Token verify
    token = credentials.credentials
    token_data = verify_token(token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    conn = get_conn()
    try:
        # Model yüklü mü kontrol et
        if not os.path.exists(MODEL_PATH):
            raise HTTPException(status_code=404, detail="Model henüz eğitilmemiş")
        
        # Model ve scaler yükle
        model = xgb.XGBRegressor()
        model.load_model(MODEL_PATH)
        scaler = joblib.load(SCALER_PATH)
        
        with conn.cursor() as cur:
            # Son veriyi çek
            cur.execute("""
                SELECT value, timestamp
                FROM measurements
                WHERE quality_flag = 'normal'
                ORDER BY timestamp DESC
                LIMIT 24
            """)
            
            rows = cur.fetchall()
            
            if len(rows) < 24:
                raise HTTPException(status_code=400, detail="Yeterli geçmiş veri yok")
            
            df = pd.DataFrame(rows, columns=['value', 'timestamp'])
            
            predictions = []
            now = datetime.now()
            
            for i in range(hours_ahead):
                future_time = now + timedelta(hours=i)
                
                features = pd.DataFrame({
                    'hour': [future_time.hour],
                    'day_of_week': [future_time.weekday()],
                    'month': [future_time.month],
                    'lag_1': [df['value'].iloc[0]],
                    'lag_24': [df['value'].iloc[23] if len(df) >= 24 else df['value'].iloc[-1]]
                })
                
                features_scaled = scaler.transform(features)
                prediction = model.predict(features_scaled)[0]
                
                predictions.append({
                    "timestamp": future_time.isoformat(),
                    "predicted_value": float(max(0, prediction))
                })
            
            return {
                "status": "success",
                "predictions": predictions,
                "hours_ahead": hours_ahead
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.get("/api/ml/metrics")
async def get_model_metrics(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Model metriklerini getir"""
    # Token verify
    token = credentials.credentials
    token_data = verify_token(token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    try:
        if not os.path.exists(MODEL_PATH):
            return {"status": "no_model", "message": "Model henüz eğitilmemiş"}
        
        # Model dosya bilgisi
        model_info = os.stat(MODEL_PATH)
        
        return {
            "status": "trained",
            "model_size": model_info.st_size,
            "last_trained": datetime.fromtimestamp(model_info.st_mtime).isoformat(),
            "model_type": "XGBoost"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

@app.get("/api/plants")
def get_plants():
    """Tüm santral listesini getir"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT plant_id, COUNT(*) as record_count
                FROM measurements
                GROUP BY plant_id
                ORDER BY plant_id
            """)
            
            rows = cur.fetchall()
            
            return [
                {
                    "plant_id": row[0],
                    "record_count": int(row[1])
                }
                for row in rows
            ]
    finally:
        conn.close()