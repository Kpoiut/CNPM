import React, { useEffect, useMemo, useState } from 'react'
import { ResponsiveContainer, BarChart, Bar, CartesianGrid, XAxis, YAxis, Tooltip } from 'recharts'
import ChartWrapper from '../../components/ui/ChartWrapper'
import { VisualStrip } from '../../components/ui'
import { icon } from '../../components/ui/icons'
import { VISUAL_ASSETS } from '../../constants/visuals'
import { PROPERTY_TYPES } from '../../constants/vnStrings'

const API_BASE = '/api'

const qualityVisuals = [
  {
    src: VISUAL_ASSETS.officeInterior,
    alt: 'Modern office interior with glass walls and walkways',
    kicker: 'Assessment',
    title: 'Kiểm tra dữ liệu',
    caption: 'Đánh giá chất lượng trước khi định giá.',
  },
  {
    src: VISUAL_ASSETS.houseExterior,
    alt: 'Modern house exterior with metal fence and downspout',
    kicker: 'Evidence',
    title: 'Bằng chứng hiện trường',
    caption: 'Đầu vào phải đủ thật để chấm độ tin cậy.',
  },
  {
    src: VISUAL_ASSETS.citySkyline,
    alt: 'Aerial view of a city skyline at night',
    kicker: 'Scope',
    title: 'Phạm vi khu vực',
    caption: 'Soi mức phủ theo thành phố và quận.',
  },
]

function DataQuality() {
  const [provinces, setProvinces] = useState([])
  const [districts, setDistricts] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [formData, setFormData] = useState({
    property_type: 'house',
    province_city: '',
    district: '',
    ward: '',
    area_m2: '',
    bedrooms: 0,
    bathrooms: 0,
    floor_count: 1,
    frontage_m: '',
    legal_status: '',
    furnishing: '',
    area_type: 'urban_center',
    gps_lat: '',
    gps_lng: '',
    noise_level: '',
    temperature: '',
    humidity: '',
    light_level: '',
  })

  useEffect(() => { fetchProvinces() }, [])

  useEffect(() => {
    if (formData.province_city) fetchDistricts(formData.province_city)
  }, [formData.province_city])

  const fetchProvinces = async () => {
    try {
      const res = await fetch(`${API_BASE}/provinces`)
      const data = await res.json()
      const list = Array.isArray(data) ? data : (data?.provinces || [])
      setProvinces(list)
      if (list.length > 0) setFormData(prev => ({ ...prev, province_city: list[0].name }))
    } catch (err) { console.error(err) }
  }

  const fetchDistricts = async (province) => {
    try {
      const res = await fetch(`${API_BASE}/provinces/${encodeURIComponent(province)}/districts`)
      const raw = await res.json()
      const list = Array.isArray(raw) ? raw : (raw?.districts || [])
      setDistricts(list.map(d => typeof d === 'string' ? d : d.name))
      if (list.length > 0) setFormData(prev => ({ ...prev, district: typeof list[0] === 'string' ? list[0] : list[0].name }))
    } catch (err) { console.error(err) }
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const payload = {
        ...formData,
        area_m2: parseFloat(formData.area_m2),
        bedrooms: parseInt(formData.bedrooms, 10) || 0,
        bathrooms: parseInt(formData.bathrooms, 10) || 0,
        floor_count: parseInt(formData.floor_count, 10) || 1,
        frontage_m: formData.frontage_m ? parseFloat(formData.frontage_m) : null,
        gps_lat: formData.gps_lat ? parseFloat(formData.gps_lat) : null,
        gps_lng: formData.gps_lng ? parseFloat(formData.gps_lng) : null,
        noise_level: formData.noise_level ? parseFloat(formData.noise_level) : null,
        temperature: formData.temperature ? parseFloat(formData.temperature) : null,
        humidity: formData.humidity ? parseFloat(formData.humidity) : null,
        light_level: formData.light_level ? parseFloat(formData.light_level) : null,
      }
      const res = await fetch(`${API_BASE}/data-quality/evaluate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
      })
      if (!res.ok) throw new Error('Không thể đánh giá độ tin cậy dữ liệu')
      setResult(await res.json())
    } catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }

  const chartData = useMemo(() => {
    if (!result?.assessment?.component_scores) return []
    const scores = result.assessment.component_scores
    return [
      { name: 'Mẫu hỗ trợ', score: scores.support_volume, fill: 'var(--primary)' },
      { name: 'Chất lượng', score: scores.data_quality, fill: 'var(--accent)' },
      { name: 'Đầy đủ', score: scores.data_completeness, fill: 'var(--info)' },
    ]
  }, [result])

  const gradeConfig = (grade) => {
    const map = {
      A: { color: 'var(--success)', bg: 'var(--success-bg)' },
      B: { color: 'var(--info)', bg: 'var(--info-bg)' },
      C: { color: 'var(--warning)', bg: 'var(--warning-bg)' },
      D: { color: 'var(--danger)', bg: 'var(--danger-bg)' },
    }
    return map[grade] || { color: 'var(--text-muted)', bg: 'var(--bg-elevated)' }
  }

  const gradeStyle = result ? gradeConfig(result.assessment.confidence_grade) : {}

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Đánh giá độ tin cậy dữ liệu</h1>
        <p className="page-subtitle">
          Phân hệ riêng để kiểm tra mức độ phù hợp của dữ liệu đầu vào trước khi đưa vào định giá.
        </p>
      </div>

      <VisualStrip
        label="Data quality"
        title="Không gian kiểm tra trực quan"
        description="Mỗi ảnh chỉ đóng vai trò dẫn mắt, còn kết quả vẫn dựa trên các chỉ số hỗ trợ, provenance và độ đầy đủ thật."
        items={qualityVisuals}
      />

      <div className="grid-2" style={{ gridTemplateColumns: '1.1fr 1fr', gap: '1.5rem' }}>
        {/* Left: Form */}
        <div className="card animate-fadeIn">
          <div className="card-header">
            <span className="card-title">Hồ sơ cần đánh giá</span>
          </div>

          <form onSubmit={handleSubmit}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
              <div className="form-group">
                <label className="form-label required">Loại BĐS</label>
                <select name="property_type" className="form-select" value={formData.property_type} onChange={handleChange}>
                  {Object.entries(PROPERTY_TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label required">Diện tích (m²)</label>
                <input type="number" name="area_m2" className="form-input" value={formData.area_m2} onChange={handleChange} min="1" required />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
              <div className="form-group">
                <label className="form-label">Tỉnh / TP</label>
                <select name="province_city" className="form-select" value={formData.province_city} onChange={handleChange}>
                  {provinces.map(p => <option key={p.name} value={p.name}>{p.name}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Quận / Huyện</label>
                <select name="district" className="form-select" value={formData.district} onChange={handleChange}>
                  <option value="">— Chọn quận —</option>
                  {districts.map(d => <option key={d}>{d}</option>)}
                </select>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
              <div className="form-group">
                <label className="form-label">Phường / Xã</label>
                <input type="text" name="ward" className="form-input" value={formData.ward} onChange={handleChange} placeholder="VD: Phường Thanh Xuân" />
              </div>
              <div className="form-group">
                <label className="form-label">Mặt tiền (m)</label>
                <input type="number" name="frontage_m" className="form-input" value={formData.frontage_m} onChange={handleChange} step="0.1" placeholder="VD: 5" />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
              <div className="form-group">
                <label className="form-label">Phòng ngủ</label>
                <input type="number" name="bedrooms" className="form-input" value={formData.bedrooms} onChange={handleChange} min="0" />
              </div>
              <div className="form-group">
                <label className="form-label">Phòng tắm</label>
                <input type="number" name="bathrooms" className="form-input" value={formData.bathrooms} onChange={handleChange} min="0" />
              </div>
              <div className="form-group">
                <label className="form-label">Số tầng</label>
                <input type="number" name="floor_count" className="form-input" value={formData.floor_count} onChange={handleChange} min="1" />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
              <div className="form-group">
                <label className="form-label">Pháp lý</label>
                <input type="text" name="legal_status" className="form-input" value={formData.legal_status} onChange={handleChange} placeholder="VD: Sổ đỏ" />
              </div>
              <div className="form-group">
                <label className="form-label">Nội thất</label>
                <input type="text" name="furnishing" className="form-input" value={formData.furnishing} onChange={handleChange} placeholder="VD: Đầy đủ" />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
              <div className="form-group">
                <label className="form-label">Vĩ độ GPS</label>
                <input type="number" name="gps_lat" className="form-input" value={formData.gps_lat} onChange={handleChange} step="0.0001" placeholder="21.028511" />
              </div>
              <div className="form-group">
                <label className="form-label">Kinh độ GPS</label>
                <input type="number" name="gps_lng" className="form-input" value={formData.gps_lng} onChange={handleChange} step="0.0001" placeholder="105.854202" />
              </div>
            </div>

            {/* IoT Section */}
            <div style={{ padding: '1rem', marginBottom: '1rem', background: 'rgba(14,165,233,0.06)', borderRadius: 'var(--radius-lg)', border: '1px solid rgba(14,165,233,0.15)' }}>
              <div style={{ fontWeight: 600, fontSize: '0.85rem', color: 'var(--info)', marginBottom: '0.875rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                Tín hiệu IoT / Hiện trường
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
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
            </div>

            <button type="submit" className="btn btn-primary btn-full" disabled={loading}>
              {loading ? (
                <><div className="spinner" style={{ width: 16, height: 16 }}></div> Đang đánh giá...</>
              ) : (
                <>Đánh giá độ tin cậy</>
              )}
            </button>
          </form>
        </div>

        {/* Right: Results */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {error && (
            <div className="alert alert-danger animate-scaleIn">
              <span className="alert-icon">{icon('warning', 16)}</span>
              <span>{error}</span>
            </div>
          )}

          {!result && !error && (
            <div className="card empty-state animate-fadeIn">
              <div className="empty-icon">{icon('inbox', 40)}</div>
              <div className="empty-title">Chưa có kết quả</div>
              <div className="empty-desc">
                Điền thông tin bên trái để kiểm tra mức độ tin cậy của dữ liệu định giá.
              </div>
            </div>
          )}

          {result && (
            <div style={{ display: 'grid', gap: '1rem' }}>
              {/* Overall Score */}
              <div className="card animate-slideUp" style={{ borderLeft: '4px solid var(--primary)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
                  <div>
                    <div style={{ fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--primary-light)', marginBottom: '0.4rem' }}>
                      Tổng điểm tin cậy
                    </div>
                    <div style={{ fontFamily: 'var(--font-display)', fontSize: '2.8rem', fontWeight: 800, color: 'var(--text-primary)', lineHeight: 1 }}>
                      {result.assessment.overall_score}/10
                    </div>
                    <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '0.4rem' }}>
                      {result.assessment.recommended_policy}
                    </div>
                  </div>
                  <div style={{
                    minWidth: 110,
                    textAlign: 'center',
                    padding: '0.875rem 1rem',
                    borderRadius: 'var(--radius-xl)',
                    background: gradeStyle.bg,
                    border: `1px solid ${gradeStyle.color}30`,
                  }}>
                    <div style={{ fontSize: '0.72rem', fontWeight: 600, letterSpacing: '0.08em', color: 'var(--text-muted)', marginBottom: '0.2rem' }}>Cấp độ</div>
                    <div style={{ fontFamily: 'var(--font-display)', fontSize: '2.2rem', fontWeight: 800, color: gradeStyle.color }}>
                      {result.assessment.confidence_grade}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: gradeStyle.color }}>{result.assessment.confidence_label}</div>
                  </div>
                </div>
              </div>

              {/* Chart */}
              <div className="card animate-slideUp" style={{ animationDelay: '60ms' }}>
                <div className="card-header">
                  <span className="card-title">Thành phần chấm điểm</span>
                </div>
                <div style={{ height: 240 }}>
                  <ChartWrapper height={240}>
                    <BarChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                      <YAxis domain={[0, 10]} tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                      <Tooltip
                        formatter={(v) => [`${v}/10`, 'Điểm']}
                        contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius)' }}
                      />
                      <Bar dataKey="score" radius={[8, 8, 0, 0]}>
                        {chartData.map((entry, i) => (
                          <rect key={i} fill={entry.fill} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ChartWrapper>
                </div>
              </div>

              {/* Stats grid */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="card animate-slideUp" style={{ animationDelay: '100ms' }}>
                  <div className="card-header">
                    <span className="card-icon" style={{ background: 'var(--info-bg)', color: 'var(--info)' }}>HT</span>
                    Hỗ trợ thị trường
                  </div>
                  <div style={{ display: 'grid', gap: '0.5rem', fontSize: '0.82rem' }}>
                    <div className="flex justify-between items-center">
                      <span className="text-muted">Khu vực:</span>
                      <span className="font-semibold">{result.request_summary?.district || '—'}, {result.matched_province}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-muted">Mẫu cùng quận:</span>
                      <span className="font-semibold">{result.assessment.support_statistics?.district_support_count}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-muted">Mẫu cùng tỉnh:</span>
                      <span className="font-semibold">{result.assessment.support_statistics?.province_support_count}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-muted">Comparables:</span>
                      <span className="font-semibold">{result.assessment.support_statistics?.comparable_count}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-muted">Neff:</span>
                      <span className="font-semibold">{result.assessment.support_statistics?.effective_sample_size}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-muted">Anchor share:</span>
                      <span className="font-semibold">{(result.assessment.support_statistics?.anchor_share * 100).toFixed(1)}%</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-muted">Self-collected:</span>
                      <span className="font-semibold">{result.assessment.support_statistics?.self_collected_support_count}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-muted">IoT support:</span>
                      <span className="font-semibold">{result.assessment.support_statistics?.iot_support_count}</span>
                    </div>
                  </div>
                </div>

                <div className="card animate-slideUp" style={{ animationDelay: '120ms' }}>
                  <div className="card-header">
                    <span className="card-icon" style={{ background: 'var(--primary-50)', color: 'var(--primary)' }}>IN</span>
                    Hồ sơ đầu vào
                  </div>
                  <div style={{ display: 'grid', gap: '0.5rem', fontSize: '0.82rem' }}>
                    <div className="flex justify-between items-center">
                      <span className="text-muted">Điểm đầy đủ:</span>
                      <span className="font-semibold">{result.assessment.input_profile?.score}/10</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-muted">Trường có dữ liệu:</span>
                      <span className="font-semibold">{(result.assessment.input_profile?.ratio * 100).toFixed(1)}%</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-muted">Trường đã cung cấp:</span>
                      <span className="font-semibold">{result.assessment.input_profile?.provided_fields?.length}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-muted">Trường còn thiếu:</span>
                      <span className="font-semibold text-warning">{result.assessment.input_profile?.missing_fields?.length}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-muted">Output mode:</span>
                      <span className="font-semibold">{result.assessment.output_mode || '—'}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Strengths & Warnings */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="card animate-slideUp" style={{ animationDelay: '160ms' }}>
                  <div className="card-header">
                    <span className="card-icon" style={{ background: 'var(--success-bg)', color: 'var(--success)' }}>OK</span>
                    Điểm mạnh
                  </div>
                  <div style={{ display: 'grid', gap: '0.5rem' }}>
                    {(result.assessment.strengths || []).length > 0 ? result.assessment.strengths.map((s, i) => (
                      <div key={i} style={{ padding: '0.6rem 0.75rem', background: 'var(--success-bg)', borderRadius: 'var(--radius)', fontSize: '0.8rem', color: 'var(--success)', borderLeft: '3px solid var(--success)' }}>
                        {s}
                      </div>
                    )) : (
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>Không có điểm mạnh nổi bật.</div>
                    )}
                  </div>
                </div>

                <div className="card animate-slideUp" style={{ animationDelay: '180ms' }}>
                  <div className="card-header">
                    <span className="card-icon" style={{ background: 'var(--danger-bg)', color: 'var(--danger)' }}>AL</span>
                    Cảnh báo
                  </div>
                  <div style={{ display: 'grid', gap: '0.5rem' }}>
                    {(result.assessment.warnings || []).length > 0 ? result.assessment.warnings.map((w, i) => (
                      <div key={i} style={{ padding: '0.6rem 0.75rem', background: 'var(--danger-bg)', borderRadius: 'var(--radius)', fontSize: '0.8rem', color: 'var(--danger)', borderLeft: '3px solid var(--danger)' }}>
                        {w}
                      </div>
                    )) : (
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>Không có cảnh báo.</div>
                    )}
                  </div>
                </div>
              </div>

              {/* Missing fields */}
              <div className="card animate-slideUp" style={{ animationDelay: '200ms' }}>
                <div className="card-header">
                  <span className="card-icon" style={{ background: 'var(--warning-bg)', color: 'var(--warning)' }}>NX</span>
                  Trường cần bổ sung
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  {result.assessment.input_profile?.missing_fields?.length > 0 ? result.assessment.input_profile.missing_fields.map(field => (
                    <span key={field} className="badge badge-warning">{field}</span>
                  )) : (
                    <span className="badge badge-success">✓ Hồ sơ đầu vào đã khá đầy đủ</span>
                  )}
                </div>
              </div>

              {/* Rules applied */}
              <div className="card animate-slideUp" style={{ animationDelay: '220ms' }}>
                <div className="card-header">
                  <span className="card-icon" style={{ background: 'var(--primary-50)', color: 'var(--primary)' }}>RL</span>
                  Luật chặn đang áp dụng
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  {result.assessment.rules_applied?.length > 0 ? result.assessment.rules_applied.map(rule => (
                    <span key={rule} className="badge badge-primary">{rule}</span>
                  )) : (
                    <span className="badge badge-success">Không kích hoạt luật chặn</span>
                  )}
                </div>
              </div>

              {/* Sample records */}
              {(result.assessment.sample_records || []).length > 0 && (
                <div className="card animate-slideUp" style={{ animationDelay: '240ms' }}>
                  <div className="card-header">
                    <span className="card-icon" style={{ background: 'var(--bg-elevated)', color: 'var(--text-muted)' }}>TB</span>
                    Mẫu đối chứng sử dụng để chấm điểm
                  </div>
                  <div className="table-wrapper">
                    <table className="table">
                      <thead>
                        <tr><th>#ID</th><th>Nguồn</th><th>Khu vực</th><th>Giá</th><th>Chất lượng</th><th>Đầy đủ</th><th>Loại nguồn</th></tr>
                      </thead>
                      <tbody>
                        {result.assessment.sample_records.map(item => (
                          <tr key={item.id}>
                            <td className="font-semibold">#{item.id}</td>
                            <td className="text-sm">{item.source_name || '—'}</td>
                            <td className="text-sm">{item.district || '—'}</td>
                            <td className="text-success font-semibold">
                              {item.price ? new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(item.price) : '—'}
                            </td>
                            <td className="font-semibold">{item.quality_score?.toFixed(1)}</td>
                            <td className="font-semibold">{item.completeness_score?.toFixed(1)}</td>
                            <td><span className={`badge ${item.origin === 'self_collected' ? 'badge-success' : 'badge-primary'}`}>{item.origin}</span></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default DataQuality
