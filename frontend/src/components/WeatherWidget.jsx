import { useState, useEffect } from 'react'
import { Cloud, Droplets, Wind, Thermometer } from 'lucide-react'

const API_URL = 'http://localhost:8000/api'

function WeatherWidget({ plantId }) {
  // Santral - Şehir eşleştirmesi
  const plantCityMap = {
    'YAYSUN_LISANSLI': 'Kayseri',
    'MT_DOGAL': 'Gaziantep',
    'IOTA_M._FIRINCI': 'Adana',
    'O._ENGIL208': 'Konya',
    'O._ERCIS': 'Van',
    'PSI_ENGIL207': 'Konya',
    'AKFEN_MAHSUP': 'Ankara'
  }
  
  const city = plantCityMap[plantId] || 'Ankara'
  
  const [weather, setWeather] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchWeather()
    const interval = setInterval(fetchWeather, 600000)
    return () => clearInterval(interval)
  }, [city])

  const fetchWeather = async () => {
    try {
      const response = await fetch(`${API_URL}/weather?city=${city}`)
      const data = await response.json()
      setWeather(data)
    } catch (error) {
      console.error('Weather fetch error:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="weather-widget">
        <p>Hava durumu yükleniyor...</p>
      </div>
    )
  }

  if (!weather) {
    return null
  }

  return (
    <div className="weather-widget">
      <div className="weather-header">
        <h3>🌤️ {weather.city}</h3>
        <img 
          src={`https://openweathermap.org/img/wn/${weather.icon}@2x.png`}
          alt={weather.description}
          className="weather-icon"
        />
      </div>
      
      <div className="weather-main">
        <div className="weather-temp">
          {weather.temperature}°C
        </div>
        <p className="weather-desc">{weather.description}</p>
      </div>

      <div className="weather-details">
        <div className="weather-detail">
          <Thermometer size={18} />
          <span>Hissedilen: {weather.feels_like}°C</span>
        </div>
        <div className="weather-detail">
          <Droplets size={18} />
          <span>Nem: {weather.humidity}%</span>
        </div>
        <div className="weather-detail">
          <Wind size={18} />
          <span>Rüzgar: {weather.wind_speed} m/s</span>
        </div>
        <div className="weather-detail">
          <Cloud size={18} />
          <span>Bulutluluk: {weather.clouds}%</span>
        </div>
      </div>
    </div>
  )
}

export default WeatherWidget