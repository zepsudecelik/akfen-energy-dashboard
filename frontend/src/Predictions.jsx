import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { TrendingUp, Zap, Brain, Calendar } from 'lucide-react'
import './DataUpload.css'

const API_URL = 'http://localhost:8000/api'

function Predictions() {
  const [predictions, setPredictions] = useState([])
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(false)
  const [training, setTraining] = useState(false)
  const [hoursAhead, setHoursAhead] = useState(24)

  useEffect(() => {
    fetchMetrics()
    fetchPredictions()
  }, [])

  const fetchMetrics = async () => {
    try {
      const response = await fetch(`${API_URL}/ml/metrics`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      const data = await response.json()
      setMetrics(data)
    } catch (error) {
      console.error('Error:', error)
    }
  }

  const fetchPredictions = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${API_URL}/ml/predict?hours_ahead=${hoursAhead}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      const data = await response.json()
      setPredictions(data.predictions || [])
    } catch (error) {
      console.error('Error:', error)
    } finally {
      setLoading(false)
    }
  }

  const trainModel = async () => {
    setTraining(true)
    try {
      const response = await fetch(`${API_URL}/ml/train`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      const data = await response.json()
      setMetrics(data)
      alert('Model başarıyla eğitildi!')
      fetchPredictions()
    } catch (error) {
      alert('Hata: ' + error.message)
    } finally {
      setTraining(false)
    }
  }

  const chartData = predictions.map(p => ({
    time: new Date(p.timestamp).toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' }),
    value: p.predicted_value
  }))

  return (
    <div className="upload-container">
      <div className="upload-header">
        <h1>🤖 Enerji Üretim Tahminleri</h1>
        <p>XGBoost ile makine öğrenmesi tabanlı tahmin</p>
      </div>

      <div className="summary-cards" style={{marginBottom: '2rem'}}>
        <div className="report-card">
          <div className="report-card-icon" style={{color: '#4ade80'}}>
            <Brain size={24} />
          </div>
          <div className="report-card-content">
            <p className="report-card-title">Model Durumu</p>
            <p className="report-card-value" style={{color: '#4ade80'}}>
              {metrics?.status === 'trained' ? 'Eğitilmiş' : 'Eğitilmemiş'}
            </p>
            {metrics?.last_trained && (
              <p className="report-card-subtitle">
                {new Date(metrics.last_trained).toLocaleString('tr-TR')}
              </p>
            )}
          </div>
        </div>

        <div className="report-card">
          <div className="report-card-icon" style={{color: '#60a5fa'}}>
            <TrendingUp size={24} />
          </div>
          <div className="report-card-content">
            <p className="report-card-title">Tahmin Süresi</p>
            <p className="report-card-value" style={{color: '#60a5fa'}}>
              {hoursAhead} Saat
            </p>
            <p className="report-card-subtitle">İleriye dönük</p>
          </div>
        </div>
      </div>

      <div className="upload-card">
        <div style={{display: 'flex', gap: '1rem', marginBottom: '2rem'}}>
          <button 
            className="upload-btn" 
            onClick={trainModel}
            disabled={training}
            style={{flex: 1}}
          >
            {training ? 'Eğitiliyor...' : '🧠 Modeli Yeniden Eğit'}
          </button>
          
          <button 
            className="upload-btn" 
            onClick={fetchPredictions}
            disabled={loading}
            style={{flex: 1, background: 'linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%)'}}
          >
            {loading ? 'Yükleniyor...' : '📊 Tahminleri Yenile'}
          </button>
        </div>

        {predictions.length > 0 && (
          <>
            <div style={{marginBottom: '2rem'}}>
              <h3 style={{color: '#f1f5f9', marginBottom: '1rem'}}>📈 Tahmin Grafiği</h3>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis 
                    dataKey="time" 
                    stroke="#9ca3af"
                    angle={-45}
                    textAnchor="end"
                    height={80}
                  />
                  <YAxis stroke="#9ca3af" />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1f2937', border: 'none' }}
                    formatter={(value) => [`${value.toFixed(2)} kWh`, 'Tahmin']}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="value" 
                    stroke="#4ade80" 
                    strokeWidth={3}
                    dot={{ fill: '#4ade80', r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div>
              <h3 style={{color: '#f1f5f9', marginBottom: '1rem'}}>📋 Detaylı Tahminler</h3>
              <div className="data-table">
                <table>
                  <thead>
                    <tr>
                      <th>Tarih & Saat</th>
                      <th>Tahmin (kWh)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {predictions.map((p, idx) => (
                      <tr key={idx}>
                        <td>{new Date(p.timestamp).toLocaleString('tr-TR')}</td>
                        <td>{p.predicted_value.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default Predictions