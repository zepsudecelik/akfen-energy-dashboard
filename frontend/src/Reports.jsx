import { useState, useEffect, useCallback } from 'react'
import { 
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, 
  Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import { 
  Calendar, TrendingUp, Download, BarChart3, FileText, 
  ArrowUp, ArrowDown, Minus 
} from 'lucide-react'
import jsPDF from 'jspdf'
import autoTable from 'jspdf-autotable'
import './Reports.css'

const API_URL = 'http://localhost:8000/api';

function Reports() {
  const [period, setPeriod] = useState('weekly')
  const [reportData, setReportData] = useState(null)
  const [comparisonData, setComparisonData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [customDates, setCustomDates] = useState({
    start: '',
    end: ''
  })

  const fetchComparison = useCallback(async () => {
    const now = new Date()
    const thisWeekStart = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
    const lastWeekStart = new Date(now.getTime() - 14 * 24 * 60 * 60 * 1000)
    const lastWeekEnd = thisWeekStart

    try {
      const params = new URLSearchParams({
        period1_start: lastWeekStart.toISOString(),
        period1_end: lastWeekEnd.toISOString(),
        period2_start: thisWeekStart.toISOString(),
        period2_end: now.toISOString()
      })

      const response = await fetch(`${API_URL}/reports/comparison?${params}`)
      const data = await response.json()
      setComparisonData(data)
    } catch (error) {
      console.error('Error fetching comparison:', error)
    }
  }, [])

  const fetchReport = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ period })
      if (period === 'custom' && customDates.start && customDates.end) {
        params.append('start_date', customDates.start)
        params.append('end_date', customDates.end)
      }

      const response = await fetch(`${API_URL}/reports/summary?${params}`)
      const data = await response.json()
      setReportData(data)

      // SADECE haftalık için comparison getir
      if (period === 'weekly' && data.summary.total_records > 0) {
        fetchComparison()
      } else {
        setComparisonData(null)
      }
    } catch (error) {
      console.error('Error fetching report:', error)
    } finally {
      setLoading(false)
    }
  }, [period, customDates, fetchComparison])

  useEffect(() => {
    if (period !== 'custom') {
      fetchReport()
    }
  }, [period, fetchReport])

  const handleCustomDateSubmit = () => {
    if (customDates.start && customDates.end) {
      fetchReport()
    }
  }

  const downloadReport = () => {
    const doc = new jsPDF()
    
    doc.setFontSize(20)
    doc.text('Akfen Enerji Uretim Raporu', 14, 20)
    
    doc.setFontSize(12)
    const periodText = period === 'weekly' ? 'Haftalik' : period === 'monthly' ? 'Aylik' : 'Ozel Tarih'
    doc.text(`Donem: ${periodText}`, 14, 30)
    doc.text(`Tarih Araligi: ${new Date(reportData.period.start).toLocaleDateString('tr-TR')} - ${new Date(reportData.period.end).toLocaleDateString('tr-TR')}`, 14, 37)
    
    doc.setFontSize(14)
    doc.text('Ozet Istatistikler', 14, 50)
    
    doc.setFontSize(10)
    doc.text(`Toplam Uretim: ${reportData.summary.total_production_mwh.toFixed(2)} MWh`, 14, 60)
    doc.text(`Ortalama Uretim: ${reportData.summary.average_production.toFixed(1)} kWh`, 14, 67)
    doc.text(`Veri Kalitesi: ${reportData.summary.data_quality.toFixed(1)}%`, 14, 74)
    doc.text(`En Yuksek Gun: ${(reportData.peak_day.production / 1000).toFixed(1)} MWh`, 14, 81)
    
    doc.setFontSize(14)
    doc.text('Gunluk Uretim Detaylari', 14, 95)
    
    const tableData = reportData.daily_breakdown.map(day => [
      new Date(day.date).toLocaleDateString('tr-TR'),
      day.total.toFixed(1),
      day.average.toFixed(1),
      day.max.toFixed(1),
      day.data_points.toString()
    ])
    
    autoTable(doc, {
      startY: 100,
      head: [['Tarih', 'Toplam (kWh)', 'Ortalama (kWh)', 'Max (kWh)', 'Veri Noktasi']],
      body: tableData,
      theme: 'grid',
      styles: { fontSize: 8 },
      headStyles: { fillColor: [74, 222, 128] }
    })
    
    doc.save(`akfen-rapor-${period}-${new Date().toISOString().split('T')[0]}.pdf`)
  }

  if (loading) {
    return (
      <div className="loading">
        <BarChart3 className="spin" size={48} />
        <p>Rapor hazırlanıyor...</p>
      </div>
    )
  }

  if (!reportData) {
    return (
      <div className="loading">
        <BarChart3 size={48} />
        <p>Rapor yüklenemedi</p>
      </div>
    )
  }

  return (
    <div className="reports-container">
      <div className="reports-header">
        <div>
          <h1>📊 Üretim Raporları</h1>
          <p>Detaylı analiz ve performans metrikleri</p>
        </div>
        <button className="download-btn" onClick={downloadReport}>
          <Download size={20} />
          Raporu İndir (PDF)
        </button>
      </div>

      <div className="period-selector">
        <button 
          className={period === 'weekly' ? 'active' : ''}
          onClick={() => setPeriod('weekly')}
        >
          <Calendar size={18} />
          Haftalık
        </button>
        <button 
          className={period === 'monthly' ? 'active' : ''}
          onClick={() => setPeriod('monthly')}
        >
          <Calendar size={18} />
          Aylık
        </button>
        <button 
          className={period === 'custom' ? 'active' : ''}
          onClick={() => setPeriod('custom')}
        >
          <Calendar size={18} />
          Özel Tarih
        </button>
      </div>

      {period === 'custom' && (
        <div className="custom-date-picker">
          <input 
            type="date" 
            value={customDates.start}
            onChange={(e) => setCustomDates({...customDates, start: e.target.value})}
          />
          <span>-</span>
          <input 
            type="date" 
            value={customDates.end}
            onChange={(e) => setCustomDates({...customDates, end: e.target.value})}
          />
          <button onClick={handleCustomDateSubmit}>Rapor Oluştur</button>
        </div>
      )}

      {reportData.summary.total_records === 0 && (
        <div className="chart-card" style={{textAlign: 'center', padding: '3rem'}}>
          <BarChart3 size={48} style={{margin: '0 auto 1rem', color: '#64748b'}} />
          <p style={{fontSize: '1.25rem', marginBottom: '0.5rem'}}>Bu tarih aralığında veri bulunamadı</p>
          <p style={{color: '#64748b', fontSize: '0.875rem'}}>
            Lütfen farklı bir tarih aralığı seçin (örn: 2025-04-01 / 2025-04-30)
          </p>
        </div>
      )}

      {reportData.summary.total_records > 0 && (
        <>
          <div className="summary-cards">
            <ReportCard
              title="Toplam Üretim"
              value={`${reportData.summary.total_production_mwh.toFixed(2)} MWh`}
              subtitle={`${reportData.period.days} gün`}
              icon={<TrendingUp />}
              color="#4ade80"
            />
            <ReportCard
              title="Ortalama Üretim"
              value={`${reportData.summary.average_production.toFixed(1)} kWh`}
              subtitle="Saatlik ortalama"
              icon={<BarChart3 />}
              color="#60a5fa"
            />
            <ReportCard
              title="Veri Kalitesi"
              value={`${reportData.summary.data_quality.toFixed(1)}%`}
              subtitle={`${reportData.summary.outliers_count} anomali`}
              icon={<FileText />}
              color="#fbbf24"
            />
            <ReportCard
              title="En Yüksek Gün"
              value={`${(reportData.peak_day.production / 1000).toFixed(1)} MWh`}
              subtitle={reportData.peak_day.date ? new Date(reportData.peak_day.date).toLocaleDateString('tr-TR') : 'N/A'}
              icon={<ArrowUp />}
              color="#f472b6"
            />
          </div>

          {comparisonData && (
            <div className="comparison-card">
              <h3>📈 Bu Hafta vs Geçen Hafta</h3>
              <div className="comparison-grid">
                <div className="comparison-item">
                  <span>Toplam Üretim</span>
                  <div className="comparison-value">
                    <span>{(comparisonData.period2.total_production / 1000).toFixed(1)} MWh</span>
                    <TrendIcon change={comparisonData.comparison.total_change_percent} />
                  </div>
                </div>
                <div className="comparison-item">
                  <span>Ortalama Üretim</span>
                  <div className="comparison-value">
                    <span>{comparisonData.period2.average_production.toFixed(1)} kWh</span>
                    <TrendIcon change={comparisonData.comparison.average_change_percent} />
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="chart-card">
            <h3>Günlük Üretim Dağılımı</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={reportData.daily_breakdown}>
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
                  formatter={(value) => [`${value.toFixed(1)} kWh`, 'Toplam']}
                />
                <Bar dataKey="total" fill="#4ade80" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="chart-card">
            <h3>Saatlik Üretim Modeli</h3>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={reportData.hourly_pattern}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  dataKey="hour" 
                  tickFormatter={(value) => `${value}:00`}
                  stroke="#9ca3af"
                />
                <YAxis stroke="#9ca3af" />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1f2937', border: 'none' }}
                  formatter={(value) => [`${value.toFixed(1)} kWh`, 'Ortalama']}
                />
                <Line 
                  type="monotone" 
                  dataKey="average" 
                  stroke="#60a5fa" 
                  strokeWidth={3}
                  dot={{ fill: '#60a5fa', r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="chart-card">
            <h3>Detaylı Veri Tablosu</h3>
            <div className="data-table">
              <table>
                <thead>
                  <tr>
                    <th>Tarih</th>
                    <th>Toplam (kWh)</th>
                    <th>Ortalama (kWh)</th>
                    <th>Max (kWh)</th>
                    <th>Veri Noktası</th>
                  </tr>
                </thead>
                <tbody>
                  {reportData.daily_breakdown.map((day, idx) => (
                    <tr key={idx}>
                      <td>{new Date(day.date).toLocaleDateString('tr-TR')}</td>
                      <td>{day.total.toFixed(1)}</td>
                      <td>{day.average.toFixed(1)}</td>
                      <td>{day.max.toFixed(1)}</td>
                      <td>{day.data_points}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function ReportCard({ title, value, subtitle, icon, color }) {
  return (
    <div className="report-card">
      <div className="report-card-icon" style={{ color }}>
        {icon}
      </div>
      <div className="report-card-content">
        <p className="report-card-title">{title}</p>
        <p className="report-card-value" style={{ color }}>{value}</p>
        <p className="report-card-subtitle">{subtitle}</p>
      </div>
    </div>
  )
}

function TrendIcon({ change }) {
  if (change > 0) {
    return (
      <span className="trend-up">
        <ArrowUp size={16} />
        {change.toFixed(1)}%
      </span>
    )
  } else if (change < 0) {
    return (
      <span className="trend-down">
        <ArrowDown size={16} />
        {Math.abs(change).toFixed(1)}%
      </span>
    )
  } else {
    return (
      <span className="trend-neutral">
        <Minus size={16} />
        0%
      </span>
    )
  }
}

export default Reports