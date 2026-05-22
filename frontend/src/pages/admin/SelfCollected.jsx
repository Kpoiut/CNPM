import React, { useState, useEffect, useMemo, useCallback } from 'react'
import { icon } from '../../components/ui/icons'
import { PROPERTY_TYPES } from '../../constants/vnStrings'
import { authFetch } from '../../api/client'
import ChartContainer from '../../components/ui/ChartContainer'
import { ResponsiveContainer, BarChart, Bar, Cell } from 'recharts'

const API_BASE = '/api'
const PAGE_SIZE = 20

const COLLECTION_METHODS_LABELS = {
  field_survey:                    'Khảo sát thực địa',
  smartphone_sensor_capture:        'Cảm biến smartphone',
  google_form_verified:            'Phiếu khảo sát',
  app_user_submission:             'Người dùng gửi app',
  manual_verified_from_public_listing: 'Xác minh tay',
  // legacy keys
  field_visit:                     'Khảo sát thực địa',
  survey_form:                     'Phiếu khảo sát',
  smartphone_sensor:               'Cảm biến smartphone',
  user_input:                      'Người dùng nhập',
}

const TIER_COLORS = {
  E5: { bg: 'rgba(6,214,160,0.15)',  color: '#06d6a0', border: '#06d6a0' },  // E5 = HIGHEST confidence
  E4: { bg: 'rgba(0,180,216,0.15)',  color: '#00b4d8', border: '#00b4d8' },
  E3: { bg: 'rgba(56,189,248,0.15)', color: '#38bdf8', border: '#38bdf8' },
  E2: { bg: 'rgba(245,158,11,0.15)', color: '#f59e0b', border: '#f59e0b' },
  E1: { bg: 'rgba(239,35,60,0.15)',  color: '#ef233c', border: '#ef233c' },  // E1 = LOWEST confidence
}

const TIER_LABELS = {
  E5: 'E5 — Đầy đủ nhất',
  E4: 'E4 — Nhiều bằng chứng',
  E3: 'E3 — Một phần',
  E2: 'E2 — Có nguồn',
  E1: 'E1 — Ít bằng chứng nhất',
}

const VERIFY_LABELS = {
  verified:   'Đã xác minh',
  pending:    'Chờ xác minh',
  unverified: 'Chưa xác minh',
  rejected:   'Từ chối',
}

function formatPrice(price) {
  if (!price) return '—'
  return new Intl.NumberFormat('vi-VN', {
    style: 'currency', currency: 'VND', maximumFractionDigits: 0
  }).format(price)
}

function formatDate(d) {
  if (!d) return '—'
  try { return new Date(d).toLocaleString('vi-VN', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' }) }
  catch { return d }
}

// ── IoT Gauge mini-component ──────────────────────────────────────────────────
function IoTGauge({ value, max, unit, label, color }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3, minWidth: 56 }}>
      <div style={{ position: 'relative', width: 40, height: 40 }}>
        <svg viewBox="0 0 36 36" style={{ width: '100%', height: '100%', transform: 'rotate(-90deg)' }}>
          <circle cx="18" cy="18" r="15" fill="none" stroke="var(--border)" strokeWidth="3" />
          <circle
            cx="18" cy="18" r="15" fill="none" stroke={color} strokeWidth="3"
            strokeDasharray={`${pct} 100`}
            strokeDashoffset="0"
            strokeLinecap="round"
          />
        </svg>
        <div style={{
          position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
          justifyContent: 'center', fontSize: '0.55rem', fontWeight: 700,
          color, transform: 'none',
        }}>{value ?? '—'}</div>
      </div>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', fontWeight: 600 }}>{label}</div>
        <div style={{ fontSize: '0.58rem', color: 'var(--text-muted)' }}>{unit}</div>
      </div>
    </div>
  )
}

// ── IoT mini bar chart ───────────────────────────────────────────────────────
function IoTMiniChart({ record }) {
  const data = [
    { name: 'Độ ồn', v: record.noise_level, max: 100, color: '#f59e0b', unit: 'dB' },
    { name: 'Nhiệt', v: record.temperature, max: 50, color: '#ef4444', unit: '°C' },
    { name: 'Độ ẩm', v: record.humidity, max: 100, color: '#3b82f6', unit: '%' },
    { name: 'Ánh sáng', v: record.light_level, max: 1000, color: '#fcd34d', unit: 'lux' },
  ].filter(d => d.v != null)

  if (!data.length) return null

  return (
    <ChartContainer height={80}>
      <ResponsiveContainer width="100%" height={80}>
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 30, left: 0, bottom: 0 }}>
          <Bar dataKey="v" radius={[0, 3, 3, 0]}>
            {data.map((d, i) => <Cell key={i} fill={d.color} fillOpacity={0.8} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartContainer>
  )
}

// ── Expandable detail row ────────────────────────────────────────────────────
function RecordDetailPanel({ record }) {
  const hasIot = record.noise_level != null || record.temperature != null || record.humidity != null || record.light_level != null
  const hasGps = record.gps_lat != null || record.latitude != null
  const primaryImage = record.image_url || record.image_urls?.[0]
  const gallery = record.image_urls || []

  const collectionMethodLabels = COLLECTION_METHODS_LABELS

  return (
    <div style={{
      background: 'var(--surface-2)',
      borderTop: '1px solid var(--border)',
      borderBottom: '1px solid var(--border)',
      padding: '1.25rem 1.5rem',
      animation: 'slideDown 200ms ease-out',
    }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>

        {/* Left: IoT data */}
        <div>
          <div style={{
            fontSize: '0.78rem', fontWeight: 700, color: 'var(--primary)',
            marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: 6,
          }}>
            {icon('satellite', 14)} Dữ liệu cảm biến & môi trường
          </div>

          {hasIot ? (
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: '0.75rem' }}>
              {record.noise_level != null && (
                <IoTGauge value={record.noise_level} max={100} unit="dB" label="Độ ồn" color="#f59e0b" />
              )}
              {record.temperature != null && (
                <IoTGauge value={record.temperature} max={50} unit="°C" label="Nhiệt độ" color="#ef4444" />
              )}
              {record.humidity != null && (
                <IoTGauge value={record.humidity} max={100} unit="%" label="Độ ẩm" color="#3b82f6" />
              )}
              {record.light_level != null && (
                <IoTGauge value={record.light_level > 1000 ? 1000 : record.light_level} max={1000} unit="lux" label="Ánh sáng" color="#fcd34d" />
              )}
            </div>
          ) : (
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', padding: '0.5rem', background: 'var(--bg-elevated)', borderRadius: 8, textAlign: 'center' }}>
              Không có dữ liệu cảm biến
            </div>
          )}

          {hasIot && (
            <div style={{ marginBottom: '0.5rem' }}>
              <IoTMiniChart record={record} />
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: '0.75rem', marginTop: '0.5rem' }}>
            <div style={{ background: 'var(--bg-elevated)', borderRadius: 6, padding: '5px 8px' }}>
              <span style={{ color: 'var(--text-muted)' }}>Thiết bị</span>
              <div style={{ fontWeight: 600 }}>{record.phone_device || '—'}</div>
            </div>
            <div style={{ background: 'var(--bg-elevated)', borderRadius: 6, padding: '5px 8px' }}>
              <span style={{ color: 'var(--text-muted)' }}>Điểm khu vực</span>
              <div style={{ fontWeight: 600 }}>{record.area_quality_score != null ? `${record.area_quality_score}/10` : '—'}</div>
            </div>
            <div style={{ background: 'var(--bg-elevated)', borderRadius: 6, padding: '5px 8px' }}>
              <span style={{ color: 'var(--text-muted)' }}>GPS accuracy</span>
              <div style={{ fontWeight: 600 }}>{record.gps_accuracy != null ? `${record.gps_accuracy} m` : '—'}</div>
            </div>
            <div style={{ background: 'var(--bg-elevated)', borderRadius: 6, padding: '5px 8px' }}>
              <span style={{ color: 'var(--text-muted)' }}>OS / App</span>
              <div style={{ fontWeight: 600 }}>{record.os_version || '—'} / {record.app_version || '—'}</div>
            </div>
          </div>

          {record.field_notes && (
            <div style={{
              marginTop: '0.75rem', background: 'rgba(245,158,11,0.06)',
              border: '1px solid rgba(245,158,11,0.18)', borderRadius: 8,
              padding: '0.5rem 0.75rem', fontSize: '0.75rem',
            }}>
              <div style={{ fontWeight: 700, color: 'var(--warning)', marginBottom: 3 }}>Ghi chú thực địa</div>
              <div style={{ color: 'var(--text-secondary)', lineHeight: 1.5 }}>{record.field_notes}</div>
            </div>
          )}
        </div>

        {/* Right: Collection + location + proof */}
        <div>
          <div style={{
            fontSize: '0.78rem', fontWeight: 700, color: 'var(--info)',
            marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: 6,
          }}>
            {icon('flaskConical', 14)} Chứng minh & truy vết
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: '0.78rem' }}>
            <div style={{ background: 'var(--bg-elevated)', borderRadius: 6, padding: '6px 10px', display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Phương thức</span>
              <strong>{collectionMethodLabels[record.collection_method] || record.collection_method || '—'}</strong>
            </div>
            <div style={{ background: 'var(--bg-elevated)', borderRadius: 6, padding: '6px 10px', display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Người thu thập</span>
              <strong style={{ color: 'var(--primary)' }}>{record.collected_by || '—'}</strong>
            </div>
            <div style={{ background: 'var(--bg-elevated)', borderRadius: 6, padding: '6px 10px', display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Thời gian thu thập</span>
              <strong>{formatDate(record.captured_at || record.collected_at)}</strong>
            </div>
            <div style={{ background: 'var(--bg-elevated)', borderRadius: 6, padding: '6px 10px', display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Xác minh bởi</span>
              <strong>{record.verified_by || '—'}</strong>
            </div>

            {record.gps_lat != null && (
              <div style={{ background: 'var(--bg-elevated)', borderRadius: 6, padding: '6px 10px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                  <span style={{ color: 'var(--text-muted)' }}>GPS từ thực địa</span>
                  <a
                    href={`https://www.google.com/maps?q=${record.gps_lat},${record.gps_lng}`}
                    target="_blank" rel="noopener noreferrer"
                    style={{ color: 'var(--primary)', fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: 3 }}
                  >
                    {icon('map', 12)} Xem bản đồ
                  </a>
                </div>
                <div style={{ fontFamily: 'monospace', fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                  {record.gps_lat?.toFixed(6)}, {record.gps_lng?.toFixed(6)}
                </div>
              </div>
            )}

            {record.latitude != null && (
              <div style={{ background: 'var(--bg-elevated)', borderRadius: 6, padding: '6px 10px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                  <span style={{ color: 'var(--text-muted)' }}>Lat / Lng (tài sản)</span>
                  <a
                    href={`https://www.google.com/maps?q=${record.latitude},${record.longitude}`}
                    target="_blank" rel="noopener noreferrer"
                    style={{ color: 'var(--primary)', fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: 3 }}
                  >
                    {icon('map', 12)} Xem bản đồ
                  </a>
                </div>
                <div style={{ fontFamily: 'monospace', fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                  {record.latitude?.toFixed(6)}, {record.longitude?.toFixed(6)}
                </div>
              </div>
            )}

            {record.verification_note && (
              <div style={{
                background: 'rgba(6,214,160,0.06)',
                border: '1px solid rgba(6,214,160,0.18)', borderRadius: 6,
                padding: '6px 10px',
              }}>
                <div style={{ fontWeight: 700, color: 'var(--success)', marginBottom: 2 }}>Ghi chú xác minh</div>
                <div style={{ color: 'var(--text-secondary)', lineHeight: 1.45 }}>{record.verification_note}</div>
              </div>
            )}

            {record.source_screenshot_path && (
              <div style={{
                background: 'var(--bg-elevated)', borderRadius: 6, padding: '6px 10px',
              }}>
                <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>Ảnh chứng minh</div>
                <a
                  href={record.source_screenshot_path}
                  target="_blank" rel="noopener noreferrer"
                  className="btn btn-sm"
                  style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}
                >
                  {icon('image', 12)} Xem ảnh chứng minh
                </a>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Photo gallery */}
      {(primaryImage || gallery.length > 0) && (
        <div style={{ marginTop: '1.25rem' }}>
          <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
            Hình ảnh hiện trường ({gallery.length || 1})
          </div>
          <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 4 }}>
            {primaryImage && (
              <img
                src={primaryImage}
                alt="Ảnh hiện trường"
                style={{
                  width: 120, height: 90, objectFit: 'cover', borderRadius: 8,
                  border: '1px solid var(--border)', cursor: 'pointer', flexShrink: 0,
                }}
                onClick={() => window.open(primaryImage, '_blank')}
              />
            )}
            {gallery.slice(1).map((img, i) => (
              <img
                key={i}
                src={img}
                alt={`Ảnh ${i + 2}`}
                style={{
                  width: 120, height: 90, objectFit: 'cover', borderRadius: 8,
                  border: '1px solid var(--border)', cursor: 'pointer', flexShrink: 0,
                }}
                onClick={() => window.open(img, '_blank')}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main component ───────────────────────────────────────────────────────────
export default function SelfCollected() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [expandedId, setExpandedId] = useState(null)
  const [filters, setFilters] = useState({ search: '', method: '', has_iot: '' })
  const [page, setPage] = useState(1)

  const getMethodLabel = useCallback((m) => COLLECTION_METHODS_LABELS[m] || m || '—', [])
  const [formData, setFormData] = useState({
    property_type: 'house', province_city: 'Hà Nội', district: '', ward: '',
    area_m2: '', bedrooms: '', bathrooms: '', floor_count: 1, price: '',
    gps_lat: '', gps_lng: '', gps_accuracy: '', noise_level: '', light_level: '',
    temperature: '', humidity: '', phone_device: '', area_quality_score: '',
    field_notes: '', collection_method: 'field_visit', collected_by: '', verification_note: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [message, setMessage] = useState(null)

  useEffect(() => { fetchData() }, [])
  useEffect(() => { setPage(1) }, [filters])

  const fetchData = async () => {
    setLoading(true)
    try {
      const res = await authFetch(`${API_BASE}/properties?limit=2000&self_collected=true`)
      const result = await res.json()
      const rows = Array.isArray(result) ? result : []
      setData(rows.filter(r => r.data_origin_type === 'self_collected' || r.collection_method || r.collected_by))
    } catch (err) { console.error(err) }
    finally { setLoading(false) }
  }

  const filteredData = useMemo(() => {
    return data.filter(r => {
      const search = filters.search.trim().toLowerCase()
      const hasIot = r.noise_level != null || r.temperature != null || r.humidity != null
      if (search) {
        const haystack = [r.id, r.district, r.ward, r.province_city, r.collected_by, r.source_name].filter(Boolean).join(' ').toLowerCase()
        if (!haystack.includes(search)) return false
      }
      if (filters.method && r.collection_method !== filters.method) return false
      if (filters.has_iot === 'yes' && !hasIot) return false
      if (filters.has_iot === 'no' && hasIot) return false
      return true
    })
  }, [data, filters])

  const paginatedData = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE
    return filteredData.slice(start, start + PAGE_SIZE)
  }, [filteredData, page])

  const totalPages = useMemo(() => Math.max(1, Math.ceil(filteredData.length / PAGE_SIZE)), [filteredData])

  const stats = useMemo(() => ({
    total: filteredData.length,
    withIot: filteredData.filter(r => r.noise_level != null || r.temperature != null || r.humidity != null).length,
    withGps: filteredData.filter(r => r.gps_lat != null).length,
    withPhotos: filteredData.filter(r => r.image_url || r.image_urls?.length).length,
    verified: filteredData.filter(r => r.verification_status === 'verified').length,
  }), [filteredData])

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    setMessage(null)
    try {
      const payload = {
        ...formData,
        is_self_collected: true,
        data_origin_type: 'self_collected',
        source_name: 'Khảo sát thực địa',
        area_m2: parseFloat(formData.area_m2) || null,
        bedrooms: parseInt(formData.bedrooms) || 0,
        bathrooms: parseInt(formData.bathrooms) || 0,
        floor_count: parseInt(formData.floor_count) || 1,
        price: parseFloat(formData.price) || null,
        gps_lat: formData.gps_lat ? parseFloat(formData.gps_lat) : null,
        gps_lng: formData.gps_lng ? parseFloat(formData.gps_lng) : null,
        gps_accuracy: formData.gps_accuracy ? parseFloat(formData.gps_accuracy) : null,
        noise_level: formData.noise_level ? parseFloat(formData.noise_level) : null,
        light_level: formData.light_level ? parseFloat(formData.light_level) : null,
        temperature: formData.temperature ? parseFloat(formData.temperature) : null,
        humidity: formData.humidity ? parseFloat(formData.humidity) : null,
        area_quality_score: formData.area_quality_score ? parseFloat(formData.area_quality_score) : null,
        legal_status: 'ownership_certificate',
        furnishing: 'furnished',
        captured_at: new Date().toISOString(),
      }
      const res = await authFetch(`${API_BASE}/properties`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
      })
      if (!res.ok) throw new Error('Không thể tạo bản ghi')
      setMessage({ type: 'success', text: 'Thêm dữ liệu tự thu thập thành công!' })
      setShowForm(false)
      fetchData()
      setFormData({
        property_type: 'house', province_city: 'Hà Nội', district: '', ward: '',
        area_m2: '', bedrooms: '', bathrooms: '', floor_count: 1, price: '',
        gps_lat: '', gps_lng: '', gps_accuracy: '', noise_level: '', light_level: '',
        temperature: '', humidity: '', phone_device: '', area_quality_score: '',
        field_notes: '', collection_method: 'field_visit', collected_by: '', verification_note: '',
      })
    } catch (err) {
      setMessage({ type: 'error', text: err.message })
    } finally { setSubmitting(false) }
  }

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '4rem', gap: 12 }}>
      <div className="spinner" style={{ width: 36, height: 36 }} />
      <p style={{ color: 'var(--text-muted)' }}>Đang tải dữ liệu tự thu thập...</p>
    </div>
  )

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div className="page-header-row">
          <div>
            <h1 className="page-title">Dữ liệu tự thu thập</h1>
            <p className="page-subtitle">Bản ghi khảo sát thực địa — có đầy đủ IoT, GPS, hình ảnh & chứng minh nguồn gốc</p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 5,
              padding: '4px 10px', borderRadius: 20,
              background: 'rgba(6,214,160,0.1)', border: '1px solid rgba(6,214,160,0.25)',
              fontSize: '0.78rem', color: 'var(--success)', fontWeight: 700,
            }}>
              <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--success)', boxShadow: '0 0 4px var(--success)' }} />
              TỰ THU THẬP
            </div>
            <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
              {showForm ? '✕ Đóng' : '+ Khảo sát mới'}
            </button>
          </div>
        </div>
      </div>

      {message && (
        <div className={`alert alert-${message.type === 'success' ? 'success' : 'danger'} mb-6 animate-scaleIn`}>
          <span>{message.text}</span>
        </div>
      )}

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
        {[
          { label: 'Tổng bản ghi', value: stats.total, color: 'var(--primary)', icon: 'database' },
          { label: 'Có dữ liệu IoT', value: stats.withIot, color: '#f59e0b', icon: 'satellite' },
          { label: 'Có GPS thực địa', value: stats.withGps, color: 'var(--success)', icon: 'map' },
          { label: 'Có hình ảnh', value: stats.withPhotos, color: '#7c3aed', icon: 'image' },
          { label: 'Đã xác minh', value: stats.verified, color: '#06d6a0', icon: 'check' },
        ].map((s, i) => (
          <div key={i} className="stat-card animate-slideUp">
            <div style={{
              width: 36, height: 36, borderRadius: 10,
              background: `${s.color}18`, display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: s.color,
            }}>
              {icon(s.icon, 18)}
            </div>
            <div>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, color: s.color }}>{s.value}</div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 2 }}>{s.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Form */}
      {showForm && (
        <div className="card mb-6 animate-slideUp">
          <div className="card-header">
            <span className="card-title">Thu thập dữ liệu khảo sát thực địa</span>
          </div>
          <form onSubmit={handleSubmit}>
            {/* Thông tin BĐS */}
            <div style={{ marginBottom: '1.25rem', padding: '1rem', background: 'rgba(79,70,229,0.05)', borderRadius: 12, border: '1px solid rgba(79,70,229,0.12)' }}>
              <div style={{ fontWeight: 700, fontSize: '0.82rem', color: '#a78bfa', marginBottom: '0.875rem', display: 'flex', alignItems: 'center', gap: 6 }}>
                {icon('house', 14)} Thông tin bất động sản
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1rem' }}>
                <div className="form-group">
                  <label className="form-label required">Loại BĐS</label>
                  <select name="property_type" className="form-select" value={formData.property_type} onChange={handleChange}>
                    {Object.entries(PROPERTY_TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label required">Tỉnh / TP</label>
                  <input name="province_city" className="form-input" value={formData.province_city} onChange={handleChange} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Quận / Huyện</label>
                  <input name="district" className="form-input" value={formData.district} onChange={handleChange} placeholder="VD: Quận Cầu Giấy" />
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1rem' }}>
                <div className="form-group">
                  <label className="form-label required">Diện tích (m²)</label>
                  <input type="number" name="area_m2" className="form-input" value={formData.area_m2} onChange={handleChange} placeholder="80" required />
                </div>
                <div className="form-group">
                  <label className="form-label">Phòng ngủ</label>
                  <input type="number" name="bedrooms" className="form-input" value={formData.bedrooms} onChange={handleChange} min="0" />
                </div>
                <div className="form-group">
                  <label className="form-label">Phòng tắm</label>
                  <input type="number" name="bathrooms" className="form-input" value={formData.bathrooms} onChange={handleChange} min="0" />
                </div>
                <div className="form-group">
                  <label className="form-label">Giá (VND)</label>
                  <input type="number" name="price" className="form-input" value={formData.price} onChange={handleChange} placeholder="3000000000" />
                </div>
              </div>
            </div>

            {/* IoT data */}
            <div style={{ marginBottom: '1.25rem', padding: '1rem', background: 'rgba(245,158,11,0.05)', borderRadius: 12, border: '1px solid rgba(245,158,11,0.12)' }}>
              <div style={{ fontWeight: 700, fontSize: '0.82rem', color: '#f59e0b', marginBottom: '0.875rem', display: 'flex', alignItems: 'center', gap: 6 }}>
                {icon('satellite', 14)} Dữ liệu cảm biến & môi trường
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1rem' }}>
                <div className="form-group">
                  <label className="form-label">Vĩ độ GPS</label>
                  <input type="number" name="gps_lat" className="form-input" value={formData.gps_lat} onChange={handleChange} step="0.0000001" placeholder="21.028511" />
                </div>
                <div className="form-group">
                  <label className="form-label">Kinh độ GPS</label>
                  <input type="number" name="gps_lng" className="form-input" value={formData.gps_lng} onChange={handleChange} step="0.0000001" placeholder="105.854202" />
                </div>
                <div className="form-group">
                  <label className="form-label">Độ chính xác GPS (m)</label>
                  <input type="number" name="gps_accuracy" className="form-input" value={formData.gps_accuracy} onChange={handleChange} step="0.1" placeholder="5" />
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1rem' }}>
                <div className="form-group">
                  <label className="form-label">Độ ồn (dB)</label>
                  <input type="number" name="noise_level" className="form-input" value={formData.noise_level} onChange={handleChange} step="0.1" placeholder="45" />
                </div>
                <div className="form-group">
                  <label className="form-label">Nhiệt độ (°C)</label>
                  <input type="number" name="temperature" className="form-input" value={formData.temperature} onChange={handleChange} step="0.1" placeholder="28" />
                </div>
                <div className="form-group">
                  <label className="form-label">Độ ẩm (%)</label>
                  <input type="number" name="humidity" className="form-input" value={formData.humidity} onChange={handleChange} step="0.1" placeholder="70" />
                </div>
                <div className="form-group">
                  <label className="form-label">Ánh sáng (lux)</label>
                  <input type="number" name="light_level" className="form-input" value={formData.light_level} onChange={handleChange} step="1" placeholder="500" />
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="form-group">
                  <label className="form-label">Thiết bị</label>
                  <input name="phone_device" className="form-input" value={formData.phone_device} onChange={handleChange} placeholder="iPhone 14 Pro" />
                </div>
                <div className="form-group">
                  <label className="form-label">Điểm chất lượng (1–10)</label>
                  <input type="number" name="area_quality_score" className="form-input" value={formData.area_quality_score} onChange={handleChange} step="0.1" min="1" max="10" placeholder="8" />
                </div>
              </div>
              <div style={{ marginTop: '0.75rem' }}>
                <div className="form-group">
                  <label className="form-label">Ghi chú thực địa</label>
                  <textarea name="field_notes" className="form-input form-textarea" value={formData.field_notes} onChange={handleChange} rows="2" placeholder="Mô tả khu vực, điều kiện xung quanh..." />
                </div>
              </div>
            </div>

            {/* Collection info */}
            <div style={{ marginBottom: '1.25rem', padding: '1rem', background: 'rgba(14,165,233,0.05)', borderRadius: 12, border: '1px solid rgba(14,165,233,0.12)' }}>
              <div style={{ fontWeight: 700, fontSize: '0.82rem', color: '#0ea5e9', marginBottom: '0.875rem', display: 'flex', alignItems: 'center', gap: 6 }}>
                {icon('flaskConical', 14)} Chứng minh & xác minh
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
                <div className="form-group">
                  <label className="form-label">Phương thức thu thập</label>
                  <select name="collection_method" className="form-select" value={formData.collection_method} onChange={handleChange}>
                    <option value="field_visit">Khảo sát thực địa</option>
                    <option value="survey_form">Phiếu khảo sát</option>
                    <option value="smartphone_sensor">Cảm biến smartphone</option>
                    <option value="user_input">Người dùng nhập</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label required">Người thu thập</label>
                  <input name="collected_by" className="form-input" value={formData.collected_by} onChange={handleChange} placeholder="Nguyễn Văn A" required />
                </div>
                <div className="form-group">
                  <label className="form-label">Ghi chú xác minh</label>
                  <input name="verification_note" className="form-input" value={formData.verification_note} onChange={handleChange} placeholder="Đã xác minh bằng..." />
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 10 }}>
              <button type="button" className="btn btn-ghost" onClick={() => setShowForm(false)}>Hủy</button>
              <button type="submit" className="btn btn-primary flex-1" disabled={submitting}>
                {submitting ? (
                  <><div className="spinner" style={{ width: 14, height: 14 }} /> Đang lưu...</>
                ) : (
                  <>Lưu bản ghi khảo sát</>
                )}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Filters */}
      <div className="card mb-4 animate-fadeIn">
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div className="form-group" style={{ flex: 1, minWidth: 180 }}>
            <label className="form-label">Tìm kiếm</label>
            <input type="text" className="form-input" value={filters.search}
              placeholder="ID, quận, người thu thập..."
              onChange={e => setFilters(f => ({ ...f, search: e.target.value }))} />
          </div>
          <div className="form-group" style={{ minWidth: 160 }}>
            <label className="form-label">Phương thức</label>
            <select className="form-select" value={filters.method}
              onChange={e => setFilters(f => ({ ...f, method: e.target.value }))}>
              <option value="">Tất cả</option>
              <option value="field_survey">Khảo sát thực địa</option>
              <option value="smartphone_sensor_capture">Cảm biến smartphone</option>
              <option value="google_form_verified">Phiếu khảo sát</option>
              <option value="app_user_submission">Người dùng gửi app</option>
            </select>
          </div>
          <div className="form-group" style={{ minWidth: 120 }}>
            <label className="form-label">Dữ liệu IoT</label>
            <select className="form-select" value={filters.has_iot}
              onChange={e => setFilters(f => ({ ...f, has_iot: e.target.value }))}>
              <option value="">Tất cả</option>
              <option value="yes">Có IoT</option>
              <option value="no">Không có IoT</option>
            </select>
          </div>
          <button className="btn btn-ghost btn-sm" onClick={() => setFilters({ search: '', method: '', has_iot: '' })}>
            Đặt lại
          </button>
          <span style={{ marginLeft: 'auto', fontSize: '0.78rem', color: 'var(--text-muted)', alignSelf: 'center' }}>
            {filteredData.length > PAGE_SIZE
              ? `${(page - 1) * PAGE_SIZE + 1}–${Math.min(page * PAGE_SIZE, filteredData.length)} / ${filteredData.length} bản ghi`
              : `${filteredData.length} bản ghi`}
          </span>
        </div>
      </div>

      {/* Table with expandable rows */}
      <div className="card animate-fadeIn">
        {filteredData.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center' }}>
            <div style={{ color: 'var(--text-muted)', marginBottom: 8 }}>{icon('inbox', 40)}</div>
            <div style={{ fontWeight: 700, color: 'var(--text-muted)' }}>Chưa có dữ liệu tự thu thập</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 4 }}>Nhấn "Khảo sát mới" để bắt đầu.</div>
          </div>
        ) : (
          <div>
            <table className="table">
              <thead>
                <tr>
                  <th style={{ width: 32 }} />
                  <th>#ID</th>
                  <th>Tài sản</th>
                  <th>Vị trí</th>
                  <th>Giá</th>
                  <th>Cảm biến</th>
                  <th>GPS</th>
                  <th>Người thu thập</th>
                  <th>Thời gian</th>
                  <th>Evidence</th>
                </tr>
              </thead>
              <tbody>
                {paginatedData.map((item) => {
                  const hasIot = item.noise_level != null || item.temperature != null || item.humidity != null || item.light_level != null
                  const hasGps = item.gps_lat != null
                  const hasPhotos = Boolean(item.image_url || item.image_urls?.length)
                  const hasNotes = Boolean(item.field_notes)
                  const isExpanded = expandedId === item.id
                  const tier = item.evidence_tier || 'E3'
                  const tierStyle = TIER_COLORS[tier] || TIER_COLORS.E3
                  const verifyStatus = item.verification_status || 'unverified'

                  return (
                    <React.Fragment key={item.id}>
                      <tr
                        style={{
                          cursor: 'pointer',
                          background: isExpanded ? 'rgba(6,214,160,0.03)' : 'transparent',
                          transition: 'background 150ms',
                        }}
                        onClick={() => setExpandedId(isExpanded ? null : item.id)}
                      >
                        <td>
                          <span style={{
                            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                            width: 22, height: 22, borderRadius: 6,
                            background: isExpanded ? 'rgba(6,214,160,0.15)' : 'var(--bg-elevated)',
                            color: isExpanded ? 'var(--success)' : 'var(--text-muted)',
                            transition: 'all 150ms',
                            fontSize: '0.8rem',
                          }}>
                            {isExpanded ? '−' : '+'}
                          </span>
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <span style={{
                              display: 'inline-block', width: 6, height: 6, borderRadius: '50%',
                              background: hasIot && hasGps ? 'var(--success)' : hasIot ? '#f59e0b' : hasGps ? 'var(--info)' : 'var(--text-muted)',
                              boxShadow: hasIot || hasGps ? `0 0 4px currentColor` : 'none',
                            }} />
                            <span className="font-semibold">#{item.id}</span>
                          </div>
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <span style={{ color: 'var(--primary)' }}>{icon('house', 14)}</span>
                            <div>
                              <div className="font-medium text-sm">{PROPERTY_TYPES[item.property_type] || item.property_type}</div>
                              <div className="text-xs text-muted">{item.area_m2} m²</div>
                            </div>
                          </div>
                        </td>
                        <td>
                          <div className="text-sm">{item.district || '—'}</div>
                          <div className="text-xs text-muted">{item.province_city || '—'}</div>
                        </td>
                        <td>
                          <div className="font-semibold text-success text-sm">{formatPrice(item.price)}</div>
                          {item.price_per_m2 && (
                            <div className="text-xs text-muted">{formatPrice(item.price_per_m2)}/m²</div>
                          )}
                        </td>
                        <td>
                          {hasIot ? (
                            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                              {item.noise_level != null && (
                                <span style={{ fontSize: '0.65rem', padding: '1px 5px', borderRadius: 4, background: 'rgba(245,158,11,0.12)', color: '#f59e0b', fontWeight: 600 }}>
                                  {item.noise_level} dB
                                </span>
                              )}
                              {item.temperature != null && (
                                <span style={{ fontSize: '0.65rem', padding: '1px 5px', borderRadius: 4, background: 'rgba(239,68,68,0.1)', color: '#ef4444', fontWeight: 600 }}>
                                  {item.temperature}°C
                                </span>
                              )}
                              {item.humidity != null && (
                                <span style={{ fontSize: '0.65rem', padding: '1px 5px', borderRadius: 4, background: 'rgba(59,130,246,0.1)', color: '#3b82f6', fontWeight: 600 }}>
                                  {item.humidity}%
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="badge badge-neutral">—</span>
                          )}
                        </td>
                        <td>
                          {hasGps ? (
                            <span className="badge badge-success" style={{ fontSize: '0.68rem' }}>
                              {item.gps_lat?.toFixed(4)}, {item.gps_lng?.toFixed(4)}
                            </span>
                          ) : (
                            <span className="badge badge-neutral">—</span>
                          )}
                        </td>
                        <td>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                            <span className="text-sm" style={{ color: 'var(--primary)' }}>{item.collected_by || '—'}</span>
                            <span className="text-xs" style={{ color: '#a78bfa', fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                              {getMethodLabel(item.collection_method)}
                            </span>
                          </div>
                        </td>
                        <td>
                          <span className="text-xs text-muted">{formatDate(item.captured_at || item.collected_at)}</span>
                        </td>
                        <td>
                          {/* Evidence badges */}
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 3, minWidth: 110 }}>
                            {/* Evidence tier */}
                            <span style={{
                              fontSize: '0.62rem', fontWeight: 700,
                              background: tierStyle.bg, color: tierStyle.color,
                              border: `1px solid ${tierStyle.border}40`,
                              borderRadius: 4, padding: '1px 5px',
                              display: 'inline-block', width: 'fit-content',
                              letterSpacing: '0.02em',
                            }}>
                              {tier}
                            </span>
                            {/* Evidence indicators */}
                            <div style={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                              {hasIot && (
                                <span title="Có IoT" style={{ fontSize: '0.6rem', color: '#f59e0b', fontWeight: 700 }}>✓</span>
                              )}
                              {hasGps && (
                                <span title="Có GPS" style={{ fontSize: '0.6rem', color: '#00b4d8', fontWeight: 700 }}>✓</span>
                              )}
                              {hasPhotos && (
                                <span title="Có ảnh" style={{ fontSize: '0.6rem', color: '#7c3aed', fontWeight: 700 }}>✓</span>
                              )}
                              {hasNotes && (
                                <span title="Có ghi chú" style={{ fontSize: '0.6rem', color: '#06d6a0', fontWeight: 700 }}>✓</span>
                              )}
                            </div>
                            {/* Verification */}
                            <span style={{
                              fontSize: '0.6rem',
                              color: verifyStatus === 'verified' ? '#06d6a0'
                                      : verifyStatus === 'pending' ? '#f59e0b'
                                      : 'var(--text-muted)',
                              fontWeight: 600,
                            }}>
                              {VERIFY_LABELS[verifyStatus] || verifyStatus}
                            </span>
                          </div>
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr>
                          <td colSpan={10} style={{ padding: 0 }}>
                            <RecordDetailPanel record={item} />
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  )
                })}
              </tbody>
            </table>

            {/* Pagination footer */}
            {totalPages > 1 && (
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                gap: '0.5rem', padding: '1rem', borderTop: '1px solid var(--border)',
              }}>
                <button
                  className="btn btn-ghost btn-sm"
                  disabled={page === 1}
                  onClick={() => setPage(p => p - 1)}
                  style={{ display: 'flex', alignItems: 'center', gap: 4 }}
                >
                  {icon('chevronLeft', 14)} Trước
                </button>
                <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map(p => (
                    <button
                      key={p}
                      onClick={() => setPage(p)}
                      style={{
                        width: 30, height: 30, borderRadius: 6,
                        border: p === page ? '1px solid var(--primary)' : '1px solid var(--border)',
                        background: p === page ? 'rgba(79,70,229,0.12)' : 'transparent',
                        color: p === page ? 'var(--primary)' : 'var(--text-muted)',
                        fontSize: '0.78rem', fontWeight: 600, cursor: 'pointer',
                        transition: 'all 150ms',
                      }}
                    >
                      {p}
                    </button>
                  ))}
                </div>
                <button
                  className="btn btn-ghost btn-sm"
                  disabled={page === totalPages}
                  onClick={() => setPage(p => p + 1)}
                  style={{ display: 'flex', alignItems: 'center', gap: 4 }}
                >
                  Sau {icon('chevronRight', 14)}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
