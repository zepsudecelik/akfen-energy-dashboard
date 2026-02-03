import { useState } from 'react'
import { Lock, Mail, User, Zap } from 'lucide-react'
import './Login.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
function Login({ onLogin }) {
  const [isRegister, setIsRegister] = useState(false)
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: ''
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const endpoint = isRegister ? '/auth/register' : '/auth/login'
      const payload = isRegister 
        ? formData 
        : { email: formData.email, password: formData.password }

      const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Bir hata oluştu')
      }

      if (isRegister) {
        // Register başarılı, login'e geç
        setIsRegister(false)
        setError('')
        alert('Kayıt başarılı! Şimdi giriş yapabilirsiniz.')
      } else {
        // Login başarılı
        localStorage.setItem('token', data.access_token)
        onLogin(data.access_token)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
  }

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <Zap size={48} className="login-icon" />
          <h1>Akfen Enerji</h1>
          <p>Güneş Enerjisi İzleme Sistemi</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          {isRegister && (
            <div className="form-group">
              <User size={20} />
              <input
                type="text"
                name="full_name"
                placeholder="Ad Soyad"
                value={formData.full_name}
                onChange={handleChange}
                required
              />
            </div>
          )}

          <div className="form-group">
            <Mail size={20} />
            <input
              type="email"
              name="email"
              placeholder="Email"
              value={formData.email}
              onChange={handleChange}
              required
            />
          </div>

          <div className="form-group">
            <Lock size={20} />
            <input
              type="password"
              name="password"
              placeholder="Şifre"
              value={formData.password}
              onChange={handleChange}
              required
              minLength={6}
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <button type="submit" className="login-button" disabled={loading}>
            {loading ? 'Yükleniyor...' : (isRegister ? 'Kayıt Ol' : 'Giriş Yap')}
          </button>

          <div className="toggle-mode">
            {isRegister ? 'Hesabın var mı?' : 'Hesabın yok mu?'}
            <button
              type="button"
              onClick={() => {
                setIsRegister(!isRegister)
                setError('')
              }}
              className="toggle-button"
            >
              {isRegister ? 'Giriş Yap' : 'Kayıt Ol'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default Login