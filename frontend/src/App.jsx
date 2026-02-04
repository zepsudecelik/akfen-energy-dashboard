import { useState, useEffect } from 'react'
import { 
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, 
  Tooltip, Legend, ResponsiveContainer 
} from 'recharts'
import { Activity, Zap, TrendingUp, AlertTriangle, Bell, X, LayoutDashboard, FileBarChart } from 'lucide-react'
import './App.css'
import Login from './login.jsx'
import Reports from './Reports.jsx'

const API_URL = 'http://localhost:8000/api';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [currentUser, setCurrentUser] = useState(null)
  const [currentPage, setCurrentPage] = useState('dashboard')
  const [stats, setStats] = useState(null)
  const [hourlyData, setHourlyData] = useState([])
  const [dailyData, setDailyData] = useState([])
  const [anomalies, setAnomalies] = useState([])
  const [loading, setLoading] = useState(true)
  const [alerts, setAlerts] = useState([])
  const [notificationsEnabled, setNotificationsEnabled] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) {
      verifyToken(token)
    } else {
      setLoading(false)
    }
  }, [])

  const verifyToken = async (token) => {
    try {
      const response = await fetch(`${API_URL}/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (response.ok) {
        const userData = await response.json()
        setCurrentUser(userData)
        setIsAuthenticated(true)
        setLoading(false)
      } else {
        localStorage.removeItem('token')
        setLoading(false)
      }
    } catch (error) {
      console.error('Token verification failed:', error)
      localStorage.removeItem('token')
      setLoading(false)
    }
  }

  const handleLogin = (token) => {
    verifyToken(token)
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    setIsAuthenticated(false)
    setCurrentUser(null)
  }

  useEffect(() => {
    if (isAuthenticated) {
      fetchData()
      const interval = setInterval(fetchData, 30000)
      return () => clearInterval(interval)
    }
  }, [isAuthenticated])

  useEffect(() => {
    if ('Notification' in window) {
      if (Notification.permission === 'granted') {
        setNotificationsEnabled(true)
      }
    }
  }, [])

  const requestNotificationPermission = async () => {
    if ('Notification' in window) {
      const permission = await Notification.requestPermission()
      setNotificationsEnabled(permission === 'granted')
    }
  }

  const showNotification = (title, body, type = 'warning') => {
    if (notificationsEnabled) {
      new Notification(title, {
        body: body,
        icon: '⚡',
        badge: type === 'critical' ? '🚨' : '⚠️'
      })
    }
    
    if (type === 'critical') {
      playAlertSound()
    }
  }

  const playAlertSound = () => {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)()
    const oscillator = audioContext.createOscillator()
    const gainNode = audioContext.createGain()
    
    oscillator.connect(gainNode)
    gainNode.connect(audioContext.destination)
    
    oscillator.frequency.value = 800
    oscillator.type = 'sine'
    gainNode.gain.setValueAtTime(0.3, audioContext.currentTime)
    
    oscillator.start(audioContext.currentTime)
    oscillator.stop(audioContext.currentTime + 0.2)
  }

  const checkForAlerts = (anomaliesData, statsData) => {
    const newAlerts = []
    
    if (anomaliesData.length > 5) {
      newAlerts.push({
        id: Date.now(),
        type: 'warning',
        title: 'Yüksek Anomali Sayısı',
        message: `${anomaliesData.length} anomali tespit edildi`,
        timestamp: new Date().toISOString()
      })
      showNotification(
        '⚠️ Yüksek Anomali Sayısı',
        `${anomaliesData.length} anomali tespit edildi`,
        'warning'
      )
    }

    const criticalAnomalies = anomaliesData.filter(a => 
      Math.abs(a.value) > statsData.max_production * 1.5 || a.value < 0
    )
    
    if (criticalAnomalies.length > 0) {
      newAlerts.push({
        id: Date.now() + 1,
        type: 'critical',
        title: '🚨 Kritik Anomali',
        message: `${criticalAnomalies.length} kritik değer tespit edildi`,
        timestamp: new Date().toISOString()
      })
      showNotification(
        '🚨 Kritik Anomali',
        `${criticalAnomalies.length} kritik değer tespit edildi`,
        'critical'
      )
    }

    if (statsData.negatives_count > 0) {
      newAlerts.push({
        id: Date.now() + 2,
        type: 'critical',
        title: '🚨 Negatif Üretim',
        message: `${statsData.negatives_count} negatif değer bulundu`,
        timestamp: new Date().toISOString()
      })
    }

    setAlerts(prev => [...newAlerts, ...prev].slice(0, 10))
  }

  const fetchData = async () => {
    setLoading(true)
    try {
      const [statsRes, hourlyRes, dailyRes, anomaliesRes] = await Promise.all([
        fetch(`${API_URL}/stats`),
        fetch(`${API_URL}/hourly-production?days=7`),
        fetch(`${API_URL}/daily-production?months=1`),
        fetch(`${API_URL}/anomalies?limit=10`)
      ])

      const [statsData, hourlyData, dailyData, anomaliesData] = await Promise.all([
        statsRes.json(),
        hourlyRes.json(),
        dailyRes.json(),
        anomaliesRes.json()
      ])

      setStats(statsData)
      setHourlyData(hourlyData)
      setDailyData(dailyData)
      setAnomalies(anomaliesData)

      checkForAlerts(anomaliesData, statsData)
    } catch (error) {
      console.error('Error:', error)
    } finally {
      setLoading(false)
    }
  }

  const dismissAlert = (alertId) => {
    setAlerts(prev => prev.filter(a => a.id !== alertId))
  }

  if (!isAuthenticated) {
    return <Login onLogin={handleLogin} />
  }

  if (loading || !stats) {
    return (
      <div className="loading">
        <Activity className="spin" size={48} />
        <p>Yükleniyor...</p>
      </div>
    )
  }

  return (
    <div className="dashboard">
      <header className="header">
        <div className="header-content">
          <Zap size={32} />
          <h1>Akfen Enerji İzleme Sistemi</h1>
          
          <div className="nav-buttons">
            <button 
              className={`nav-btn ${currentPage === 'dashboard' ? 'active' : ''}`}
              onClick={() => setCurrentPage('dashboard')}
            >
              <LayoutDashboard size={20} />
              Dashboard
            </button>
            <button 
              className={`nav-btn ${currentPage === 'reports' ? 'active' : ''}`}
              onClick={() => setCurrentPage('reports')}
            >
              <FileBarChart size={20} />
              Raporlar
            </button>
          </div>

          {currentUser && <span className="user-name">Hoşgeldin, {currentUser.full_name}</span>}
          <button 
            className={`notification-btn ${notificationsEnabled ? 'enabled' : ''}`}
            onClick={requestNotificationPermission}
            title="Bildirimleri Aç"
          >
            <Bell size={20} />
            {notificationsEnabled && <span className="notification-badge">ON</span>}
          </button>
          <button className="logout-btn" onClick={handleLogout}>
            Çıkış
          </button>
        </div>
      </header>

      {currentPage === 'dashboard' ? (
        <>
          {alerts.length > 0 && (
            <div className="alerts-container">
              {alerts.map(alert => (
                <div key={alert.id} className={`alert alert-${alert.type}`}>
                  <div className="alert-content">
                    <AlertTriangle size={20} />
                    <div>
                      <h4>{alert.title}</h4>
                      <p>{alert.message}</p>
                      <span className="alert-time">
                        {new Date(alert.timestamp).toLocaleTimeString('tr-TR')}
                      </span>
                    </div>
                  </div>
                  <button 
                    className="alert-close"
                    onClick={() => dismissAlert(alert.id)}
                  >
                    <X size={16} />
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="stats-grid">
            <StatCard
              icon={<Activity size={24} />}
              title="Toplam Üretim"
              value={`${(stats.total_production / 1000).toFixed(1)} MWh`}
              color="#4ade80"
            />
            <StatCard
              icon={<TrendingUp size={24} />}
              title="Ortalama"
              value={`${stats.average_production.toFixed(1)} kWh`}
              color="#60a5fa"
            />
            <StatCard
              icon={<Zap size={24} />}
              title="Max Üretim"
              value={`${stats.max_production.toFixed(1)} kWh`}
              color="#fbbf24"
            />
            <StatCard
              icon={<AlertTriangle size={24} />}
              title="Anomaliler"
              value={stats.outliers_count + stats.negatives_count}
              color="#f87171"
              alert={stats.outliers_count + stats.negatives_count > 5}
            />
          </div>

          <div className="charts-grid">
            <div className="chart-card">
              <h2>Saatlik Üretim (Son 7 Gün)</h2>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={hourlyData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis 
                    dataKey="timestamp" 
                    tickFormatter={(value) => new Date(value).toLocaleDateString('tr-TR', { 
                      month: 'short', 
                      day: 'numeric'
                    })}
                    stroke="#9ca3af"
                  />
                  <YAxis stroke="#9ca3af" />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1f2937', border: 'none' }}
                  />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="avg" 
                    stroke="#4ade80" 
                    strokeWidth={2}
                    dot={false}
                    name="Ortalama (kWh)"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="chart-card">
              <h2>Günlük Toplam (Son 30 Gün)</h2>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={dailyData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis 
                    dataKey="date" 
                    tickFormatter={(value) => new Date(value).toLocaleDateString('tr-TR', { 
                      month: 'short', 
                      day: 'numeric' 
                    })}
                    stroke="#9ca3af"
                  />
                  <YAxis stroke="#9ca3af" />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1f2937', border: 'none' }}
                  />
                  <Legend />
                  <Bar 
                    dataKey="total" 
                    fill="#60a5fa" 
                    name="Toplam (kWh)"
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {anomalies.length > 0 && (
            <div className="chart-card">
              <h2>Son Anomaliler</h2>
              <table>
                <thead>
                  <tr>
                    <th>Zaman</th>
                    <th>Değer</th>
                    <th>Durum</th>
                  </tr>
                </thead>
                <tbody>
                  {anomalies.map((a, idx) => (
                    <tr key={idx}>
                      <td>{new Date(a.timestamp).toLocaleString('tr-TR')}</td>
                      <td>{a.value.toFixed(2)} kWh</td>
                      <td>
                        <span className={`badge badge-${a.quality_flag}`}>
                          {a.quality_flag}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      ) : (
        <Reports />
      )}
    </div>
  )
}

function StatCard({ icon, title, value, color, alert }) {
  return (
    <div className={`stat-card ${alert ? 'stat-card-alert' : ''}`}>
      <div className="stat-icon" style={{ color }}>
        {icon}
      </div>
      <div className="stat-content">
        <p className="stat-title">{title}</p>
        <p className="stat-value" style={{ color }}>{value}</p>
      </div>
      {alert && <div className="pulse-dot"></div>}
    </div>
  )
}

export default App