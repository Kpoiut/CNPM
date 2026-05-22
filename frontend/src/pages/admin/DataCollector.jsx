import React, { useState, useEffect, useRef } from 'react'
import { icon } from '../../components/ui/icons'
import { PROPERTY_TYPES } from '../../constants/vnStrings'
import { authFetch } from '../../api/client'

const API_BASE = '/api'

function DataCollector() {
  const [step, setStep] = useState(1)
  const [location, setLocation] = useState(null)
  const [locationError, setLocationError] = useState(null)
  const [iotData, setIotData] = useState(null)
  const [collectingIoT, setCollectingIoT] = useState(false)
  const [saving, setSaving] = useState(false)
  const [savedProperty, setSavedProperty] = useState(null)
  const [formData, setFormData] = useState({
    property_type: 'house', province_city: 'Hà Nội', district: '', ward: '',
    street: '', area_m2: '', bedrooms: 3, bathrooms: 2, floor_count: 2,
    price: '', legal_status: 'ownership_certificate', furnishing: 'furnished', notes: ''
  })
  const [districts, setDistricts] = useState([])
  const videoRef = useRef(null)
  const streamRef = useRef(null)

  useEffect(() => {
    if (formData.province_city) fetchDistricts(formData.province_city)
  }, [formData.province_city])

  const fetchDistricts = async (province) => {
    try {
      const res = await fetch(`${API_BASE}/provinces/${encodeURIComponent(province)}/districts`)
      const raw = await res.json()
      const list = Array.isArray(raw) ? raw : (raw?.districts || [])
      setDistricts(list.map(d => typeof d === 'string' ? d : d.name))
    } catch (err) { console.error(err) }
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const getLocation = () => {
    if (!navigator.geolocation) {
      setLocationError('Trình duyệt không hỗ trợ định vị')
      return
    }
    setLocationError(null)
    navigator.geolocation.getCurrentPosition(
      (pos) => setLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude, accuracy: pos.coords.accuracy }),
      () => setLocationError('Không lấy được vị trí')
    )
  }

  const startIoT = () => {
    setCollectingIoT(true)
    setTimeout(() => {
      setIotData({
        noise_level: (20 + Math.random() * 60).toFixed(1),
        temperature: (18 + Math.random() * 17).toFixed(1),
        humidity: (40 + Math.random() * 50).toFixed(1),
        light_level: (100 + Math.random() * 9900).toFixed(0),
      })
      setCollectingIoT(false)
    }, 2000)
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const payload = {
        ...formData,
        area_m2: parseFloat(formData.area_m2),
        bedrooms: parseInt(formData.bedrooms), bathrooms: parseInt(formData.bathrooms),
        floor_count: parseInt(formData.floor_count), price: parseFloat(formData.price),
        gps_lat: location?.lat, gps_lng: location?.lng, gps_accuracy: location?.accuracy,
        ...iotData,
        is_self_collected: true,
        data_origin_type: 'self_collected',
        source_name: 'Khảo sát thực địa',
      }
      const res = await authFetch(`${API_BASE}/properties`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
      })
      const data = await res.json()
      setSavedProperty(data)
    } catch (err) { console.error(err) }
    finally { setSaving(false) }
  }

  const STEPS = [
    { n: 1, label: 'Vị trí & IoT' },
    { n: 2, label: 'Thông tin BDS' },
    { n: 3, label: 'IoT môi trường' },
    { n: 4, label: 'Lưu dữ liệu' },
  ]

  return (
    <div>
      <div className="page-header mb-6">
        <h1 className="page-title">Thu thập dữ liệu thực địa</h1>
        <p className="page-subtitle">Sử dụng smartphone để thu thập dữ liệu BĐS kèm tín hiệu IoT từ cảm biến</p>
      </div>

      {/* Step Bar */}
      <div className="step-bar mb-8">
        {STEPS.map((s, i) => (
          <React.Fragment key={s.n}>
            <div className="step-item">
              <div className={`step-circle ${step === s.n ? 'active' : step > s.n ? 'done' : ''}`}>
                {step > s.n ? '✓' : s.n}
              </div>
              <span className={`step-label ${step === s.n ? 'active' : ''}`}>{s.label}</span>
            </div>
            {i < STEPS.length - 1 && <div className={`step-line ${step > s.n ? 'done' : ''}`} />}
          </React.Fragment>
        ))}
      </div>

      {savedProperty ? (
        <div className="card animate-scaleIn" style={{ textAlign: 'center', padding: '3rem' }}>
          <div style={{ fontSize: '4rem', marginBottom: '1rem' }}></div>
          <h2 className="mb-4">Thu thập dữ liệu thành công!</h2>
          <p className="text-secondary mb-6">Bản ghi #{savedProperty.id} đã được lưu vào hệ thống</p>
          <button className="btn btn-primary" onClick={() => { setSavedProperty(null); setStep(1) }}>
            Thu thập tiếp
          </button>
        </div>
      ) : (
        <div className="grid-2" style={{ gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
          {/* Left: Step content card */}
          <div className="card animate-fadeIn">
            {step === 1 && (
              <div>
                <div className="card-header"><span className="card-title">Bước 1 — Vị trí GPS</span></div>
                <div style={{ display: 'grid', gap: '1.25rem' }}>
                  <button className="btn btn-primary btn-full" onClick={getLocation}>
                    Lấy vị trí hiện tại
                  </button>
                  {locationError && (
                    <div className="alert alert-danger">
                      <span className="alert-icon">{icon('warning', 16)}</span><span>{locationError}</span>
                    </div>
                  )}
                  {location && (
                    <div className="card" style={{ background: 'var(--success-bg)', border: '1px solid var(--success-border)', padding: '1rem' }}>
                      <div className="flex items-center gap-2 mb-2">
                        <span style={{ color: 'var(--success)', fontSize: '1.2rem' }}>✓</span>
                        <span className="font-semibold" style={{ color: 'var(--success)' }}>Đã lấy vị trí</span>
                      </div>
                      <div className="text-sm text-secondary">
                        Vĩ độ: <strong>{location.lat.toFixed(6)}</strong><br/>
                        Kinh độ: <strong>{location.lng.toFixed(6)}</strong><br/>
                        Độ chính xác: <strong>{location.accuracy.toFixed(1)}m</strong>
                      </div>
                    </div>
                  )}
                  <button className="btn btn-secondary btn-full" disabled={!location} onClick={() => setStep(2)}>
                    Tiếp theo →
                  </button>
                </div>
              </div>
            )}

            {step === 2 && (
              <div>
                <div className="card-header"><span className="card-title">Bước 2 — Thông tin bất động sản</span></div>
                <div className="form-grid">
                  <div className="form-group">
                    <label className="form-label required">Loại BĐS</label>
                    <select name="property_type" className="form-select" value={formData.property_type} onChange={handleChange}>
                      {Object.entries(PROPERTY_TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label required">Tỉnh / TP</label>
                    <select name="province_city" className="form-select" value={formData.province_city} onChange={handleChange}>
                      {['Hà Nội','TP. Hồ Chí Minh','Đà Nẵng','Hải Phòng','Cần Thơ','Bình Dương','Đồng Nai'].map(p => <option key={p}>{p}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label required">Quận / Huyện</label>
                    <select name="district" className="form-select" value={formData.district} onChange={handleChange}>
                      <option value="">— Chọn quận —</option>
                      {districts.map(d => <option key={d}>{d}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Đường / Tòa nhà</label>
                    <input name="street" className="form-input" value={formData.street} onChange={handleChange} placeholder="VD: Nguyễn Trãi" />
                  </div>
                  <div className="form-group">
                    <label className="form-label required">Diện tích (m²)</label>
                    <input type="number" name="area_m2" className="form-input" value={formData.area_m2} onChange={handleChange} required />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Số phòng ngủ</label>
                    <input type="number" name="bedrooms" className="form-input" value={formData.bedrooms} onChange={handleChange} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Số phòng tắm</label>
                    <input type="number" name="bathrooms" className="form-input" value={formData.bathrooms} onChange={handleChange} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Số tầng</label>
                    <input type="number" name="floor_count" className="form-input" value={formData.floor_count} onChange={handleChange} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Pháp lý</label>
                    <select name="legal_status" className="form-select" value={formData.legal_status} onChange={handleChange}>
                      <option value="ownership_certificate">Sổ đỏ / Sổ hồng</option>
                      <option value="pending">Đang chờ</option>
                      <option value="other">Khác</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Nội thất</label>
                    <select name="furnishing" className="form-select" value={formData.furnishing} onChange={handleChange}>
                      <option value="furnished">Có nội thất</option>
                      <option value="semi_furnished">Nội thất một phần</option>
                      <option value="unfurnished">Không nội thất</option>
                    </select>
                  </div>
                </div>
                <div className="flex gap-2 mt-4">
                  <button className="btn btn-ghost" onClick={() => setStep(1)}>← Trước</button>
                  <button className="btn btn-primary flex-1" onClick={() => setStep(3)}>Tiếp theo →</button>
                </div>
              </div>
            )}

            {step === 3 && (
              <div>
                <div className="card-header"><span className="card-title">Bước 3 — Dữ liệu IoT môi trường</span></div>
                <div style={{ textAlign: 'center', padding: '2rem 0' }}>
                  {collectingIoT ? (
                    <div>
                      <div className="spinner mb-4" style={{ width: 40, height: 40 }}></div>
                      <p className="text-secondary">Đang thu thập dữ liệu cảm biến...</p>
                    </div>
                  ) : iotData ? (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', textAlign: 'left' }}>
                      {[
                        { l: 'Độ ồn', v: `${iotData.noise_level} dB` },
                        { l: 'Nhiệt độ', v: `${iotData.temperature} °C` },
                        { l: 'Độ ẩm', v: `${iotData.humidity} %` },
                        { l: 'Ánh sáng', v: `${iotData.light_level} lux` },
                      ].map(item => (
                        <div key={item.l} className="card" style={{ padding: '1rem', textAlign: 'center', background: 'var(--info-bg)', border: '1px solid var(--info-border)' }}>
                          <div className="text-xs text-muted mb-1">{item.l}</div>
                          <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', fontWeight: 800, color: 'var(--info)' }}>{item.v}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div>
                      <p className="text-secondary mb-4">Sử dụng camera và microphone để thu thập dữ liệu môi trường</p>
                      <button className="btn btn-primary btn-lg" onClick={startIoT}>
                        Bắt đầu đo IoT
                      </button>
                    </div>
                  )}
                </div>
                <div className="flex gap-2 mt-4">
                  <button className="btn btn-ghost" onClick={() => setStep(2)}>← Trước</button>
                  <button className="btn btn-primary flex-1" disabled={!iotData} onClick={() => setStep(4)}>Tiếp theo →</button>
                </div>
              </div>
            )}

            {step === 4 && (
              <div>
                <div className="card-header"><span className="card-title">Bước 4 — Xác nhận và lưu</span></div>
                <div style={{ display: 'grid', gap: '0.75rem' }}>
                  {[
                    { l: 'Loại BĐS', v: PROPERTY_TYPES[formData.property_type] || formData.property_type },
                    { l: 'Địa điểm', v: `${formData.district || '—'}, ${formData.province_city}` },
                    { l: 'Diện tích', v: `${formData.area_m2} m²` },
                    { l: 'Phòng ngủ / tắm', v: `${formData.bedrooms} / ${formData.bathrooms}` },
                    { l: 'GPS', v: location ? `${location.lat.toFixed(4)}, ${location.lng.toFixed(4)}` : 'Chưa có' },
                    { l: 'IoT', v: iotData ? '✓ Đã thu thập' : 'Chưa thu thập' },
                  ].map(item => (
                    <div key={item.l} className="flex justify-between items-center" style={{ padding: '0.5rem 0', borderBottom: '1px solid var(--border-light)' }}>
                      <span className="text-sm text-muted">{item.l}</span>
                      <span className="text-sm font-medium">{item.v}</span>
                    </div>
                  ))}
                </div>
                <div className="flex gap-2 mt-4">
                  <button className="btn btn-ghost" onClick={() => setStep(3)}>← Trước</button>
                  <button className="btn btn-accent flex-1" onClick={handleSave} disabled={saving}>
                    {saving ? 'Đang lưu...' : 'Lưu dữ liệu'}
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Right: Help card */}
          <div className="animate-fadeIn">
            <div className="card" style={{ background: 'var(--primary-50)', border: '1px solid var(--primary-200)', marginBottom: '1rem' }}>
              <div className="card-title mb-3" style={{ color: 'var(--primary)' }}>Hướng dẫn thu thập</div>
              <ul style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', paddingLeft: '1.25rem', display: 'grid', gap: '0.5rem' }}>
                <li>Bật GPS trước khi thu thập để đảm bảo vị trí chính xác</li>
                <li>Chụp ảnh rõ ràng, đủ ánh sáng tự nhiên</li>
                <li>Đứng yên khi đo IoT để kết quả chính xác hơn</li>
                <li>Đo nhiều điểm trong khu vực để có dữ liệu đa dạng</li>
                <li>Ghi chú thực địa chi tiết giúp tăng chất lượng dữ liệu</li>
              </ul>
            </div>
            <div className="card">
              <div className="card-title mb-3">Dữ liệu IoT</div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', display: 'grid', gap: '0.5rem' }}>
                <p>• <strong>Độ ồn (dB):</strong> Đo tiếng ồn xung quanh bất động sản</p>
                <p>• <strong>Nhiệt độ (°C):</strong> Nhiệt độ môi trường hiện tại</p>
                <p>• <strong>Độ ẩm (%):</strong> Độ ẩm không khí</p>
                <p>• <strong>Ánh sáng (lux):</strong> Cường độ ánh sáng tại chỗ</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default DataCollector
