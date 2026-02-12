import { useState } from 'react'
import { Upload, FileSpreadsheet, CheckCircle, AlertCircle, X } from 'lucide-react'
import * as XLSX from 'xlsx'
import './DataUpload.css'

const API_URL = 'http://localhost:8000/api';

function DataUpload() {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      setFile(selectedFile)
      setError(null)
      setResult(null)
    }
  }

  const handleUpload = async () => {
    if (!file) {
      setError('Lütfen bir dosya seçin')
      return
    }

    setUploading(true)
    setError(null)

    try {
      // Excel dosyasını oku
      const data = await file.arrayBuffer()
      const workbook = XLSX.read(data)
      const worksheet = workbook.Sheets[workbook.SheetNames[0]]
      const jsonData = XLSX.utils.sheet_to_json(worksheet)

      // Backend'e gönder
      const response = await fetch(`${API_URL}/upload-data`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ data: jsonData })
      })

      if (!response.ok) {
        throw new Error('Yükleme başarısız')
      }

      const result = await response.json()
      setResult(result)
      setFile(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="upload-container">
      <div className="upload-header">
        <h1>📤 Veri Yükleme</h1>
        <p>Excel dosyasından enerji üretim verilerini yükleyin</p>
      </div>

      <div className="upload-card">
        <div className="upload-area">
          <FileSpreadsheet size={64} className="upload-icon" />
          <h3>Excel Dosyası Seçin</h3>
          <p>Desteklenen formatlar: .xlsx, .xls, .csv</p>
          
          <input
            type="file"
            accept=".xlsx,.xls,.csv"
            onChange={handleFileChange}
            className="file-input"
            id="file-upload"
          />
          <label htmlFor="file-upload" className="file-label">
            <Upload size={20} />
            Dosya Seç
          </label>

          {file && (
            <div className="selected-file">
              <FileSpreadsheet size={20} />
              <span>{file.name}</span>
              <button onClick={() => setFile(null)} className="remove-file">
                <X size={16} />
              </button>
            </div>
          )}
        </div>

        {file && (
          <button 
            className="upload-btn" 
            onClick={handleUpload}
            disabled={uploading}
          >
            {uploading ? 'Yükleniyor...' : 'Verileri Yükle'}
          </button>
        )}

        {error && (
          <div className="alert alert-error">
            <AlertCircle size={20} />
            <span>{error}</span>
          </div>
        )}

        {result && (
          <div className="alert alert-success">
            <CheckCircle size={20} />
            <div>
              <strong>Başarılı!</strong>
              <p>{result.inserted} kayıt eklendi</p>
            </div>
          </div>
        )}
      </div>

      <div className="upload-info">
        <h3>📋 Excel Formatı</h3>
        <p>Excel dosyanız şu sütunları içermelidir:</p>
        <ul>
          <li><strong>timestamp</strong> - Tarih ve saat (örn: 2025-04-01 10:00:00)</li>
          <li><strong>value</strong> - Üretim değeri (kWh)</li>
          <li><strong>plant_id</strong> (opsiyonel) - Santral ID (varsayılan: AKFEN_MAHSUP)</li>
        </ul>
      </div>
    </div>
  )
}

export default DataUpload