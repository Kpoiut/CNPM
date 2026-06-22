/**
 * MapLocationPicker — "Định vị thông minh"
 *
 * Trải nghiệm chọn vị trí kiểu Google Maps nhưng dùng OpenStreetMap + Nominatim
 * (qua backend), KHÔNG cần Google Maps API key.
 *
 * Luồng:
 *  1. Người dùng chọn LOẠI HÌNH BĐS (đặc tính cố định — quyết định form đích).
 *  2. Tìm địa chỉ hoặc click/kéo marker trên bản đồ.
 *  3. Backend trả: địa chỉ + BĐS gần + giá/m² khu vực + HỒ SƠ IoT tự sinh.
 *  4. Bảng dữ liệu dạng dashboard (sửa được) hiện ngay dưới bản đồ.
 *  5. Bấm "Chạy Valuation Engine v2.0.0" → dự đoán luôn + chuyển dữ liệu sang form.
 */
import React, { useState, useEffect, useCallback, useRef } from 'react'
import {
  MapContainer, TileLayer, Marker, useMap, useMapEvents,
} from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import markerIcon2xUrl from 'leaflet/dist/images/marker-icon-2x.png'
import markerIconUrl from 'leaflet/dist/images/marker-icon.png'
import markerShadowUrl from 'leaflet/dist/images/marker-shadow.png'
import { icon } from '../../components/ui/icons'
import { PROPERTY_TYPES } from '../../constants/vnStrings'
import { mapSearch, mapLocationContext, mapEnrich } from '../../api'

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2xUrl,
  iconUrl: markerIconUrl,
  shadowUrl: markerShadowUrl,
})

const HANOI = [21.0285, 105.8542]
const HCM = [10.7769, 106.7009]

// Khoá map trong khung 2 thành phố — không thể kéo sang khu vực khác
const CITY = {
  hanoi: { center: HANOI, bounds: [[20.90, 105.70], [21.15, 105.95]], zoom: 12, label: 'Hà Nội' },
  hcm: { center: HCM, bounds: [[10.66, 106.55], [10.92, 106.83]], zoom: 12, label: 'TP. Hồ Chí Minh' },
}

const fmtVnd = (v) => {
  if (!v) return '—'
  if (v >= 1e9) return `${(v / 1e9).toFixed(2)} tỷ`
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)} tr`
  return `${(v / 1e3).toFixed(0)}K`
}

const fmtDist = (m) => (m == null ? '—' : m >= 1000 ? `${(m / 1000).toFixed(1)} km` : `${m} m`)

function pinIcon() {
  return L.divIcon({
    className: '',
    html: `<div style="transform:translate(-50%,-100%);font-size:30px;line-height:1;filter:drop-shadow(0 2px 4px rgba(0,0,0,.4))">📍</div>`,
    iconSize: [30, 30], iconAnchor: [0, 0],
  })
}

function ClickHandler({ onPick }) {
  useMapEvents({
    click(e) { onPick(e.latlng.lat, e.latlng.lng) },
  })
  return null
}

function CityLock({ city }) {
  const map = useMap()
  useEffect(() => {
    const c = CITY[city]
    if (!c) return
    map.setMaxBounds(c.bounds)
    map.options.maxBoundsViscosity = 1.0
    map.setMinZoom(11)
    map.flyToBounds(c.bounds, { duration: 0.6 })
  }, [city, map])
  return null
}

function FlyTo({ center, zoom }) {
  const map = useMap()
  useEffect(() => {
    if (center) map.flyTo(center, zoom || map.getZoom(), { duration: 0.8 })
  }, [center, zoom, map])
  return null
}

// ── UI nhỏ tái dùng cho dashboard kết quả ──────────────────────────────────
function StatTile({ iconKey, label, value, sub, accent = 'var(--primary)' }) {
  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: '0.75rem 0.85rem', display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-muted)', fontSize: '0.66rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.3 }}>
        <span style={{ color: accent, display: 'inline-flex' }}>{icon(iconKey, 13)}</span>{label}
      </div>
      <div style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-primary)', lineHeight: 1.2 }}>{value}</div>
      {sub && <div style={{ fontSize: '0.66rem', color: 'var(--text-muted)' }}>{sub}</div>}
    </div>
  )
}

function InfoPanel({ iconKey, title, action, children }) {
  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: '0.9rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
        <span style={{ color: 'var(--primary)', display: 'inline-flex' }}>{icon(iconKey, 15)}</span>
        <strong style={{ fontSize: '0.8rem' }}>{title}</strong>
        {action && <div style={{ marginLeft: 'auto' }}>{action}</div>}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>{children}</div>
    </div>
  )
}

function KV({ label, value }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, fontSize: '0.76rem' }}>
      <span style={{ color: 'var(--text-muted)' }}>{label}</span>
      <span style={{ color: 'var(--text-primary)', fontWeight: 600, textAlign: 'right' }}>{value}</span>
    </div>
  )
}

function EditField({ label, value, onChange, options, listId }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>{label}</span>
      <input
        className="form-input"
        value={value || ''}
        onChange={e => onChange(e.target.value)}
        list={options?.length ? listId : undefined}
        style={{ padding: '0.4rem 0.55rem', fontSize: '0.8rem' }}
      />
      {options?.length > 0 && (
        <datalist id={listId}>
          {options.map(o => <option key={o} value={o} />)}
        </datalist>
      )}
    </div>
  )
}

export default function MapLocationPicker({ propertyType, onPropertyTypeChange, onConfirm, onPredict }) {
  const [city, setCity] = useState('hanoi')
  const [coords, setCoords] = useState(null)            // {lat, lng}
  const [flyCenter, setFlyCenter] = useState(null)
  const [context, setContext] = useState(null)
  const [loading, setLoading] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [searching, setSearching] = useState(false)
  const [edit, setEdit] = useState(false)
  const [draft, setDraft] = useState({})
  const [photos, setPhotos] = useState([])             // ảnh tải lên (tùy chọn)
  const [enrich, setEnrich] = useState(null)           // dữ liệu OSM (lazy)
  const [enrichLoading, setEnrichLoading] = useState(false)
  const reqIdRef = useRef(0)
  const enrichIdRef = useRef(0)

  // Lấy context (địa chỉ + IoT + BĐS gần) khi đổi tọa độ / loại hình
  useEffect(() => {
    if (!coords) return
    const id = ++reqIdRef.current
    setLoading(true)
    setEnrich(null)
    mapLocationContext({ lat: coords.lat, lng: coords.lng, propertyType })
      .then(data => { if (id === reqIdRef.current) setContext(data) })
      .catch(() => { if (id === reqIdRef.current) setContext(null) })
      .finally(() => { if (id === reqIdRef.current) setLoading(false) })
  }, [coords, propertyType])

  // Làm giàu OSM (lazy) — chạy nền sau khi có context, không chặn dashboard
  useEffect(() => {
    if (!coords) return
    const id = ++enrichIdRef.current
    setEnrichLoading(true)
    mapEnrich({ lat: coords.lat, lng: coords.lng, propertyType })
      .then(data => {
        if (id !== enrichIdRef.current) return
        setEnrich(data)
        // tự điền diện tích vào ô sửa nếu đang trống
        if (data?.prefill?.area_m2) {
          setDraft(d => (d.area_m2 ? d : { ...d, area_m2: data.prefill.area_m2 }))
        }
      })
      .catch(() => { if (id === enrichIdRef.current) setEnrich(null) })
      .finally(() => { if (id === enrichIdRef.current) setEnrichLoading(false) })
  }, [coords, propertyType])

  // Seed bản nháp (sửa được) từ context
  useEffect(() => {
    if (!context) return
    const p = context.prefill || {}
    const l = context.location || {}
    const median = context.field_options?.area_range?.median
    setDraft({
      province_city: l.province_city || p.province_city || '',
      district: l.district || p.district || '',
      ward: l.ward || p.ward || '',
      street_or_project: p.street_or_project || l.road || '',
      area_m2: p.area_m2 || p.land_area_m2 || (median ? String(median) : ''),
    })
    setEdit(false)
  }, [context])

  const handlePick = useCallback((lat, lng) => {
    setCoords({ lat, lng })
  }, [])

  const handleSearch = async (e) => {
    e?.preventDefault()
    if (searchText.trim().length < 2) return
    setSearching(true)
    try {
      const data = await mapSearch(searchText.trim())
      setSearchResults(data.results || [])
    } catch {
      setSearchResults([])
    } finally {
      setSearching(false)
    }
  }

  const selectSearchResult = (r) => {
    setSearchResults([])
    setSearchText(r.name || r.display_name)
    setCoords({ lat: r.latitude, lng: r.longitude })
    setFlyCenter([r.latitude, r.longitude])
  }

  const useMyLocation = () => {
    if (!navigator.geolocation) return
    navigator.geolocation.getCurrentPosition(
      pos => {
        const { latitude, longitude } = pos.coords
        setCoords({ lat: latitude, lng: longitude })
        setFlyCenter([latitude, longitude])
      },
      () => {},
      { enableHighAccuracy: true, timeout: 8000 },
    )
  }

  const onUploadPhotos = (e) => {
    const files = Array.from(e.target.files || []).slice(0, 6)
    const next = files.map(f => ({ name: f.name, url: URL.createObjectURL(f), file: f }))
    setPhotos(prev => [...prev, ...next].slice(0, 6))
  }

  const loc = context?.location
  const iot = context?.iot
  const nearby = context?.nearby
  const fieldOpts = context?.field_options
  const canConfirm = !!coords && !!context && !loading
  const finalType = context?.suggested_property_type || propertyType
  const typeLabel = PROPERTY_TYPES?.[finalType] || finalType

  const buildPrefill = () => ({
    ...context.prefill,
    ...(enrich?.prefill || {}),
    province_city: draft.province_city,
    district: draft.district,
    ward: draft.ward,
    street_or_project: draft.street_or_project,
    ...(draft.area_m2 ? { area_m2: draft.area_m2, land_area_m2: draft.area_m2 } : {}),
    _v: Date.now(),
    _iot: context.iot,
    _location: context.location,
    _field_options: context.field_options,
    _amenities: enrich?.amenities,
    _photos: photos.map(p => p.name),
  })

  const doPredict = () => {
    if (!context) return
    onPredict?.({ propertyType: finalType, prefill: buildPrefill(), context, photos })
  }

  const doConfirm = () => {
    if (!context) return
    onConfirm?.({ propertyType: finalType, prefill: buildPrefill(), context })
  }

  return (
    <div className="card animate-fadeIn" style={{ overflow: 'hidden' }}>
      <div className="card-header">
        <span className="stat-icon primary">{icon('map', 20)}</span>
        <span className="card-title">Định vị thông minh — chọn vị trí trên bản đồ</span>
        <span className="badge badge-success" style={{ marginLeft: 'auto', fontSize: '0.7rem' }}>
          OpenStreetMap · IoT tự động
        </span>
      </div>

      {/* Bước 1: chọn loại hình (đặc tính cố định) */}
      <div className="prediction-note-band" style={{ marginBottom: '1rem' }}>
        <div className="prediction-note-head">
          <span className="stat-icon info">{icon('house', 18)}</span>
          <strong>Chọn loại hình bất động sản</strong>
          <span className="text-xs text-muted" style={{ marginLeft: 'auto' }}>không đổi sau khi định giá</span>
        </div>
        <div className="flex gap-2 flex-wrap" style={{ marginTop: '0.5rem' }}>
          {Object.entries(PROPERTY_TYPES).map(([key, label]) => (
            <button
              key={key}
              type="button"
              onClick={() => onPropertyTypeChange?.(key)}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: '0.4rem',
                padding: '0.55rem 1rem', borderRadius: 'var(--radius)',
                fontSize: '0.85rem', fontWeight: 600, cursor: 'pointer',
                border: `1px solid ${propertyType === key ? 'var(--primary)' : 'var(--border)'}`,
                background: propertyType === key ? 'var(--primary-50)' : 'transparent',
                color: propertyType === key ? 'var(--primary)' : 'var(--text-secondary)',
                transition: 'all var(--transition)',
              }}
            >
              {icon(key, 16)}
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Tìm kiếm + bản đồ full-width; kết quả hiển thị bên dưới */}
      <div>
        <div>
          <form onSubmit={handleSearch} style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.6rem' }}>
            <input
              className="form-input"
              placeholder="Tìm địa chỉ, dự án (VD: Vinhomes, Cầu Giấy, Phú Mỹ Hưng)..."
              value={searchText}
              onChange={e => setSearchText(e.target.value)}
              style={{ flex: 1 }}
            />
            <button type="submit" className="btn btn-primary btn-sm" disabled={searching}>
              {searching ? '...' : 'Tìm'}
            </button>
            <button type="button" className="btn btn-ghost btn-sm" onClick={useMyLocation} title="Dùng vị trí hiện tại">
              {icon('map', 14)} GPS
            </button>
          </form>

          {searchResults.length > 0 && (
            <div style={{
              border: '1px solid var(--border)', borderRadius: 8, marginBottom: '0.6rem',
              maxHeight: 180, overflowY: 'auto', background: 'var(--surface)',
            }}>
              {searchResults.map((r, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => selectSearchResult(r)}
                  style={{
                    display: 'block', width: '100%', textAlign: 'left', padding: '0.5rem 0.75rem',
                    border: 'none', borderBottom: '1px solid var(--border)', background: 'transparent',
                    cursor: 'pointer', fontSize: '0.8rem', color: 'var(--text-primary)',
                  }}
                >
                  <strong>{r.name}</strong>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{r.display_name}</div>
                </button>
              ))}
            </div>
          )}

          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem', alignItems: 'center' }}>
            <div style={{ display: 'flex', border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
              {Object.entries(CITY).map(([key, c]) => (
                <button key={key} type="button" onClick={() => setCity(key)}
                  style={{
                    padding: '0.4rem 0.9rem', border: 'none', cursor: 'pointer', fontSize: '0.78rem', fontWeight: 700,
                    background: city === key ? 'var(--primary)' : 'transparent',
                    color: city === key ? '#fff' : 'var(--text-secondary)',
                  }}>
                  {c.label}
                </button>
              ))}
            </div>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: '0.7rem', color: 'var(--text-muted)', marginLeft: 'auto' }}>
              {icon('lock', 12)} Khoá trong {CITY[city].label} · click/kéo marker để chọn
            </span>
          </div>

          <div style={{ height: 460, borderRadius: 10, overflow: 'hidden', border: '1px solid var(--border)' }}>
            <MapContainer
              center={CITY.hanoi.center} zoom={12} style={{ width: '100%', height: '100%' }}
              maxBounds={CITY.hanoi.bounds} maxBoundsViscosity={1.0} minZoom={11}
            >
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution="© OpenStreetMap"
              />
              <ClickHandler onPick={handlePick} />
              <CityLock city={city} />
              <FlyTo center={flyCenter} zoom={16} />
              {coords && (
                <Marker
                  position={[coords.lat, coords.lng]}
                  icon={pinIcon()}
                  draggable
                  eventHandlers={{
                    dragend: (e) => {
                      const m = e.target.getLatLng()
                      handlePick(m.lat, m.lng)
                    },
                  }}
                />
              )}
            </MapContainer>
          </div>
        </div>

        {/* ════ Dashboard kết quả (sửa được) ════ */}
        <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
          {!coords && (
            <div style={{
              padding: '1.5rem 1rem', textAlign: 'center', color: 'var(--text-muted)',
              border: '1px dashed var(--border)', borderRadius: 10, fontSize: '0.82rem',
            }}>
              {icon('map', 32)}
              <p style={{ marginTop: '0.5rem' }}>Chọn một điểm trên bản đồ để xem địa chỉ, dữ liệu IoT và BĐS lân cận.</p>
            </div>
          )}

          {loading && (
            <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.82rem' }}>
              <span className="spinner" style={{ width: 20, height: 20, display: 'inline-block', verticalAlign: 'middle' }} />
              {' '}Đang phân tích vị trí...
            </div>
          )}

          {loc && !loading && (
            <>
              {/* Header vị trí */}
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, background: 'linear-gradient(135deg, var(--primary-50), transparent)', border: '1px solid var(--border)', borderRadius: 12, padding: '0.9rem 1rem' }}>
                <span style={{ color: 'var(--primary)', marginTop: 2 }}>{icon('map', 22)}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: '0.66rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.3 }}>Vị trí đã chọn</div>
                  <div style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--text-primary)', lineHeight: 1.3 }}>
                    {[draft.ward, draft.district, draft.province_city].filter(Boolean).join(', ') || loc.display_name}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 2 }}>
                    Tọa độ: {Number(loc.latitude).toFixed(6)}, {Number(loc.longitude).toFixed(6)} · {typeLabel}
                  </div>
                  <div style={{ marginTop: 6 }}>
                    {loc.in_scope ? (
                      <span className="badge badge-success" style={{ fontSize: '0.66rem' }}>✓ Trong vùng dữ liệu ML</span>
                    ) : (
                      <span className="badge badge-warning" style={{ fontSize: '0.66rem' }}>⚠ Ngoài scope — gán quận gần nhất: {loc.district}</span>
                    )}
                  </div>
                </div>
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => setEdit(e => !e)} style={{ flexShrink: 0 }}>
                  {icon('settings', 14)} {edit ? 'Xong' : 'Chỉnh sửa thông tin'}
                </button>
              </div>

              {loc.snapped_to_nearest && loc.snap_message && (
                <div style={{ padding: '0.5rem 0.7rem', borderRadius: 8, fontSize: '0.72rem', background: '#f59e0b15', border: '1px solid #f59e0b50', color: 'var(--text-primary)', lineHeight: 1.4 }}>
                  ⚠ {loc.snap_message}
                </div>
              )}

              {/* Hàng số liệu nhanh */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '0.6rem' }}>
                <StatTile iconKey="chart" label="Giá/m² khu vực"
                  value={nearby?.summary?.avg_price_per_m2 ? `${fmtVnd(nearby.summary.avg_price_per_m2)}/m²` : '—'}
                  sub={nearby?.summary?.min_price_per_m2 ? `${fmtVnd(nearby.summary.min_price_per_m2)} – ${fmtVnd(nearby.summary.max_price_per_m2)}` : 'Chưa đủ dữ liệu'} />
                <StatTile iconKey="shieldCheck" label="Chất lượng KV" accent="#06d6a0"
                  value={iot?.area_quality_score != null ? `${iot.area_quality_score}/10` : '—'}
                  sub={iot?.estimated ? 'IoT ước lượng' : 'IoT tín hiệu thật'} />
                <StatTile iconKey="activity" label="Nhiệt độ" accent="#f59e0b"
                  value={iot?.temperature != null ? `${iot.temperature}°C` : '—'}
                  sub={iot?.humidity != null ? `Độ ẩm ${iot.humidity}%` : ''} />
                <StatTile iconKey="radio" label="Độ ồn" accent="#0099ff"
                  value={iot?.noise_level != null ? `${iot.noise_level} dB` : '—'}
                  sub={iot?.noise_desc ? String(iot.noise_desc).slice(0, 24) : ''} />
                <StatTile iconKey="table" label="Diện tích phổ biến"
                  value={fieldOpts?.area_range ? `${fieldOpts.area_range.min}–${fieldOpts.area_range.max} m²` : '—'}
                  sub={fieldOpts?.sample_size ? `${fieldOpts.sample_size} mẫu khu vực` : ''} />
              </div>

              {/* Hàng panel chi tiết */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '0.75rem' }}>
                {/* Thông tin vị trí — SỬA ĐƯỢC */}
                <InfoPanel iconKey="map" title="Thông tin vị trí"
                  action={<span className="text-xs text-muted">{edit ? 'đang sửa' : ''}</span>}>
                  {edit ? (
                    <>
                      <EditField label="Tỉnh / TP" value={draft.province_city} onChange={v => setDraft(d => ({ ...d, province_city: v }))} />
                      <EditField label="Quận / Huyện" value={draft.district} onChange={v => setDraft(d => ({ ...d, district: v }))} />
                      <EditField label="Phường / Xã" value={draft.ward} onChange={v => setDraft(d => ({ ...d, ward: v }))} listId="ward-opts" options={fieldOpts?.wards} />
                      <EditField label="Đường / Dự án" value={draft.street_or_project} onChange={v => setDraft(d => ({ ...d, street_or_project: v }))} listId="street-opts" options={fieldOpts?.streets} />
                      <EditField label="Diện tích (m²)" value={draft.area_m2} onChange={v => setDraft(d => ({ ...d, area_m2: v }))} />
                    </>
                  ) : (
                    <>
                      <KV label="Tỉnh / TP" value={draft.province_city || '—'} />
                      <KV label="Quận / Huyện" value={draft.district || '—'} />
                      <KV label="Phường / Xã" value={draft.ward || '—'} />
                      <KV label="Đường / Dự án" value={draft.street_or_project || '—'} />
                      <KV label="Loại hình" value={typeLabel} />
                      <KV label="Diện tích" value={draft.area_m2 ? `${draft.area_m2} m²` : '—'} />
                    </>
                  )}
                </InfoPanel>

                {/* Thông số khu vực (IoT) */}
                <InfoPanel iconKey="activity" title="Thông số khu vực (IoT)"
                  action={<span className="badge" style={{ fontSize: '0.6rem', background: iot?.estimated ? '#f59e0b20' : '#06d6a020', color: iot?.estimated ? '#f59e0b' : '#06d6a0' }}>{iot?.estimated ? 'ước lượng' : 'thật'}</span>}>
                  <KV label="Độ ồn" value={iot?.noise_level != null ? `${iot.noise_level} dB` : '—'} />
                  <KV label="Nhiệt độ" value={iot?.temperature != null ? `${iot.temperature}°C` : '—'} />
                  <KV label="Độ ẩm" value={iot?.humidity != null ? `${iot.humidity}%` : '—'} />
                  <KV label="Ánh sáng" value={iot?.light_level != null ? `${iot.light_level} lux` : '—'} />
                  <KV label="Chất lượng KV" value={iot?.area_quality_score != null ? `${iot.area_quality_score}/10` : '—'} />
                  <KV label="Sai số GPS" value={iot?.gps_accuracy != null ? `±${iot.gps_accuracy} m` : '—'} />
                </InfoPanel>

                {/* Tham khảo khu vực */}
                <InfoPanel iconKey="chart" title={`Tham khảo khu vực${nearby?.summary?.count ? ` (${nearby.summary.count} BĐS)` : ''}`}>
                  {nearby?.summary?.avg_price_per_m2 ? (
                    <>
                      <KV label="Giá/m² TB" value={`${fmtVnd(nearby.summary.avg_price_per_m2)}/m²`} />
                      <KV label="Khoảng giá" value={`${fmtVnd(nearby.summary.min_price_per_m2)} – ${fmtVnd(nearby.summary.max_price_per_m2)}`} />
                      <KV label="Gần nhất cách" value={nearby.summary.nearest_distance_m != null ? `${nearby.summary.nearest_distance_m} m` : '—'} />
                    </>
                  ) : (
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Chưa có BĐS cùng loại gần điểm này trong dữ liệu.</div>
                  )}
                </InfoPanel>

                {/* Tiện ích & môi trường (OSM) */}
                <InfoPanel iconKey="globe" title="Tiện ích & môi trường (OSM)"
                  action={enrichLoading ? <span className="text-xs text-muted">đang lấy…</span> : null}>
                  {enrich?.amenities && Object.keys(enrich.amenities).length > 0 ? (
                    <>
                      <KV label={<span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>{icon('school', 13)} Trường học</span>} value={fmtDist(enrich.amenities.school)} />
                      <KV label={<span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>{icon('hospital', 13)} Bệnh viện</span>} value={fmtDist(enrich.amenities.hospital)} />
                      <KV label={<span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>{icon('market', 13)} Chợ / Siêu thị</span>} value={fmtDist(enrich.amenities.market)} />
                      <KV label={<span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>{icon('park', 13)} Công viên</span>} value={fmtDist(enrich.amenities.park)} />
                      <KV label={<span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>{icon('bus', 13)} Trạm xe buýt</span>} value={fmtDist(enrich.amenities.bus)} />
                      <KV label={<span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>{icon('church', 13)} Nghĩa trang</span>} value={fmtDist(enrich.amenities.cemetery)} />
                      <KV label={<span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>{icon('water', 13)} Sông / mặt nước</span>} value={fmtDist(enrich.amenities.water)} />
                      {enrich?.parcel?.road_class && (
                        <KV label={<span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>{icon('navigation', 13)} Hạng đường</span>} value={`${enrich.parcel.road_class}${enrich.parcel.road_width_m ? ` · ${enrich.parcel.road_width_m}m` : ''}`} />
                      )}
                    </>
                  ) : enrichLoading ? (
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Đang lấy dữ liệu tiện ích từ OpenStreetMap…</div>
                  ) : (
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Chưa lấy được dữ liệu OSM — chọn lại điểm để thử lại.</div>
                  )}
                </InfoPanel>

                {/* Hệ thống có sẵn + ảnh tải lên */}
                <InfoPanel iconKey="database" title="Dữ liệu hệ thống & ảnh">
                  {fieldOpts?.wards?.length > 0 && (
                    <div style={{ fontSize: '0.72rem' }}>
                      <span style={{ color: 'var(--text-muted)' }}>Phường phổ biến: </span>{fieldOpts.wards.slice(0, 4).join(' · ')}
                    </div>
                  )}
                  {fieldOpts?.sample_size > 0 && <KV label="Số mẫu khu vực" value={`${fieldOpts.sample_size}`} />}
                  <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: '0.74rem', color: 'var(--primary)', cursor: 'pointer', fontWeight: 600, marginTop: 4 }}>
                    {icon('plus', 13)} Tải ảnh BĐS (tùy chọn)
                    <input type="file" accept="image/*" multiple onChange={onUploadPhotos} style={{ display: 'none' }} />
                  </label>
                  {photos.length > 0 && (
                    <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', marginTop: 2 }}>
                      {photos.map((p, i) => (
                        <img key={i} src={p.url} alt={p.name} style={{ width: 42, height: 42, borderRadius: 6, objectFit: 'cover', border: '1px solid var(--border)' }} />
                      ))}
                    </div>
                  )}
                  <div style={{ fontSize: '0.64rem', color: 'var(--text-muted)' }}>Ảnh giúp tham chiếu trực quan; không bắt buộc.</div>
                </InfoPanel>
              </div>

              {context?.prefill?._template_from_nearest && (
                <div style={{ fontSize: '0.7rem', color: 'var(--warning)', lineHeight: 1.4 }}>
                  ⓘ Một số thông số (diện tích, số tầng, pháp lý) được sao chép từ BĐS gần nhất làm mẫu khởi tạo — bấm "Chỉnh sửa thông tin" để chỉnh lại cho đúng tài sản của bạn.
                </div>
              )}

              {/* Diện tích — BẮT BUỘC để pipeline không bị chặn ở gate INTAKE */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', padding: '0.6rem 0.85rem', border: `1px solid ${draft.area_m2 ? 'var(--border)' : 'var(--danger, #ef233c)'}`, borderRadius: 10, background: 'var(--surface)' }}>
                <label style={{ fontSize: '0.82rem', fontWeight: 700 }}>Diện tích (m²) <span style={{ color: 'var(--danger, #ef233c)' }}>*</span></label>
                <input
                  className="form-input" type="number" min="1" step="0.1"
                  value={draft.area_m2 || ''}
                  onChange={e => setDraft(d => ({ ...d, area_m2: e.target.value }))}
                  style={{ width: 130 }} placeholder="VD: 80"
                />
                <span style={{ fontSize: '0.72rem', color: draft.area_m2 ? 'var(--text-muted)' : 'var(--danger, #ef233c)' }}>
                  {draft.area_m2 ? 'Có thể chỉnh lại cho đúng tài sản của bạn.' : 'Bắt buộc — nhập diện tích để định giá.'}
                </span>
              </div>

              {/* CTA — dự đoán luôn */}
              <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  className="btn btn-primary btn-lg"
                  disabled={!canConfirm || !draft.area_m2}
                  onClick={doPredict}
                  style={{ flex: '2 1 240px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}
                >
                  {icon('flask', 18)} Chạy Valuation Engine v2.0.0
                </button>
                <button
                  type="button"
                  className="btn btn-ghost btn-lg"
                  disabled={!canConfirm}
                  onClick={doConfirm}
                  style={{ flex: '1 1 160px' }}
                >
                  Chỉ điền form →
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.75rem', lineHeight: 1.4 }}>
        {context?.disclaimer || 'BĐS gần chỉ là dữ liệu tham khảo khu vực. Giá cuối cùng do model dự đoán dựa trên thông tin bạn xác nhận trong biểu mẫu.'}
      </div>
    </div>
  )
}
