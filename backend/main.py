"""
FastAPI Backend for Akfen Energy Dashboard
"""

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import sys
import os

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
    "*"  # Tüm originler
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


security = HTTPBearer()


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
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)  # 0.0.0.0 = tüm network