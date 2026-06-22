/**
 * PropertyVisualizer — trực quan hóa sau định giá (theo ĐÚNG loại BĐS).
 *
 *  Tab "Sơ đồ": bản đồ vệ tinh + lô/căn highlight (xanh nước biển), chế độ
 *    "Quy hoạch" nền sáng tô màu sử dụng đất; zoom sâu → nút xem Street View
 *    nhìn từ mặt đường (Google). Tile upscale nên zoom sâu không bị "no data".
 *  Tab "Mô hình 3D": đùn khối 3D TỪ CHÍNH HÌNH THỬA THẬT (polygon OSM) theo số
 *    tầng — giữ vết lồi lõm; xoay bằng kéo chuột.
 *  Dưới: BĐS rao bán thật tương đồng (Chợ Tốt).
 */
import React, { Suspense, lazy, useEffect, useMemo, useRef, useState } from 'react'
import { MapContainer, TileLayer, Polygon, Polyline, CircleMarker, Tooltip, useMap, useMapEvents } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { icon } from '../../components/ui/icons'
import { mapParcel, mapListings, mapZoning } from '../../api'
import './property-visualizer.css'

const PropertyModel3D = lazy(() => import('./PropertyModel3D'))

const TYPE_VI = { land: 'Đất nền', apartment: 'Căn hộ', house: 'Nhà phố', townhouse: 'Nhà liền kề', villa: 'Biệt thự' }
// Danh từ chỉ chính tài sản (đúng loại hình) dùng cho nhãn "… của bạn"
const NOUN = { land: 'Lô đất', apartment: 'Căn hộ', house: 'Căn nhà', townhouse: 'Nhà', villa: 'Biệt thự' }

const SUBJECT_COLOR = '#0ea5e9'      // xanh nước biển
const SUBJECT_FILL = '#7dd3fc'       // xanh nước biển nhạt

const num = (v) => { const n = Number(v); return Number.isFinite(n) ? n : null }
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v))

function deriveSpec(payload = {}, propertyType = 'house') {
  const area = num(payload.area_m2) || num(payload.built_area_m2) || num(payload.land_area_m2) || 60
  const landArea = num(payload.land_area_m2) || num(payload.area_m2) || area
  const floors = clamp(num(payload.floor_count) || (propertyType === 'villa' ? 2 : propertyType === 'townhouse' ? 3 : 1), 1, 14)
  const aptFloor = num(payload.apt_floor)
  const towerFloors = num(payload.total_floor_count)
    || num(payload.total_floors)
    || num(payload.tower_floors)
    || (aptFloor ? Math.max(aptFloor + 5, 18) : 20)
  const bedrooms = num(payload.bedrooms)
  const bathrooms = num(payload.bathrooms)
  const facing = payload.main_facing || payload.door_orientation || payload.balcony_orientation || ''
  const frontage = num(payload.frontage_m)
  const depth = num(payload.depth_max_m) || num(payload.depth_min_m)
  let fwM, fdM
  if (frontage && depth) { fwM = frontage; fdM = depth }
  else {
    const ratios = { land: [1.05, 1.0], apartment: [1, 1], house: [1, 1.1], townhouse: [0.5, 1.9], villa: [1.2, 1] }
    const [rw, rd] = ratios[propertyType] || [1, 1]
    const base = Math.sqrt(Math.max(area, 12) / (rw * rd))
    fwM = base * rw; fdM = base * rd
    if (frontage) { fwM = frontage; fdM = Math.max(4, area / frontage) }
  }
  return {
    propertyType, area, landArea, floors, aptFloor, towerFloors, bedrooms, bathrooms, facing,
    frontageM: Math.round(fwM * 10) / 10, depthM: Math.round(fdM * 10) / 10,
    isLand: propertyType === 'land', isTower: propertyType === 'apartment',
  }
}

// ─────────── Sơ đồ (Leaflet) ───────────
const ROAD_COLOR = { MAIN_STREET: '#f59e0b', SECONDARY_STREET: '#fbbf24' }
const ZONE_COLORS = {
  residential: '#fcd34d', commercial: '#fb7185', industrial: '#c4b5fd',
  green: '#86efac', water: '#7dd3fc', public: '#93c5fd',
  cemetery: '#a3a3a3', agriculture: '#d9f99d', construction: '#fdba74', other: '#e5e7eb',
}
const ZONE_LABEL = {
  residential: 'Đất ở', commercial: 'Thương mại - DV', industrial: 'Công nghiệp',
  green: 'Cây xanh - công viên', water: 'Mặt nước', public: 'Công cộng (trường/viện)',
  cemetery: 'Nghĩa trang', agriculture: 'Nông nghiệp', construction: 'Đang xây dựng', other: 'Khác',
}
const PLANNING_TILE_URL = import.meta.env.VITE_PLANNING_TILE_URL || ''

function VisualizerLazyFallback({ label }) {
  return (
    <div style={{ height: 480, display: 'grid', placeItems: 'center', border: '1px solid var(--border)', borderRadius: 6, background: 'var(--surface)' }}>
      <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, color: 'var(--text-muted)', fontSize: '0.82rem' }}>
        {icon('loader', 14)} {label}
      </div>
    </div>
  )
}

function FitBounds({ coordsList }) {
  const map = useMap()
  useEffect(() => {
    const all = coordsList.flat()
    if (!all.length) return
    const lats = all.map(c => c[0]); const lngs = all.map(c => c[1])
    map.fitBounds([[Math.min(...lats), Math.min(...lngs)], [Math.max(...lats), Math.max(...lngs)]], { padding: [70, 70], maxZoom: 20 })
  }, [coordsList, map])
  return null
}

function ZoomWatcher({ onZoom }) {
  const map = useMapEvents({ zoomend: () => onZoom(map.getZoom()) })
  useEffect(() => { onZoom(map.getZoom()) }, []) // eslint-disable-line
  return null
}

// Nạp lớp quy hoạch theo KHUNG NHÌN + poll khi backend đang nạp nền
function ZoningLoader({ onResult, onLoading }) {
  const map = useMap()
  const timer = useRef(null)
  const polls = useRef(0)
  const fetchBounds = async () => {
    const z = map.getZoom()
    if (z < 12) { onResult({ zones: [], note: 'far' }); onLoading?.(false); return }
    const b = map.getBounds()
    onLoading?.(true)
    try {
      const d = await mapZoning({ minLat: b.getSouth(), minLng: b.getWest(), maxLat: b.getNorth(), maxLng: b.getEast() })
      onResult({ zones: d.zones || [], note: d.too_large ? 'large' : '' })
      if (d.pending > 0 && polls.current < 8) {
        polls.current++
        clearTimeout(timer.current)
        timer.current = setTimeout(fetchBounds, 1500)
      } else { polls.current = 0; onLoading?.(false) }
    } catch { onResult({ zones: [], note: 'empty' }); onLoading?.(false) }
  }
  const run = () => { polls.current = 0; clearTimeout(timer.current); timer.current = setTimeout(fetchBounds, 250) }
  useMapEvents({ moveend: run, zoomend: run })
  useEffect(() => { run() }, []) // eslint-disable-line
  return null
}

function ParcelMap({ lat, lng, data, loading, error, noun }) {
  const [mode, setMode] = useState('satellite') // 'satellite' | 'zoning'
  const [vzones, setVzones] = useState([])
  const [zNote, setZNote] = useState('')
  const [zLoading, setZLoading] = useState(false)
  const zacc = useRef(new Map())

  const subject = data?.subject
  const buildings = data?.buildings || []
  const roads = data?.roads || []
  const zonesPresent = useMemo(() => [...new Set(vzones.map(z => z.zone))], [vzones])
  const subjectCenter = useMemo(() => {
    if (subject && subject.length) return [subject.reduce((s, c) => s + c[0], 0) / subject.length, subject.reduce((s, c) => s + c[1], 0) / subject.length]
    return [lat, lng]
  }, [subject, lat, lng])
  const focusBounds = useMemo(() => (subject && subject.length ? [subject] : [[[lat - 0.0004, lng - 0.0004], [lat + 0.0004, lng + 0.0004]]]), [subject, lat, lng])

  useEffect(() => { zacc.current = new Map(); setVzones([]) }, [lat, lng])

  // Tích lũy vùng theo từng khung nhìn → phủ dần toàn thành phố, không nhấp nháy
  const onZones = ({ zones, note }) => {
    setZNote(note || '')
    if (zones && zones.length) {
      const m = zacc.current
      for (const z of zones) {
        const k = z.zone + ':' + (z.coords[0] ? z.coords[0].join(',') : Math.random())
        if (!m.has(k)) m.set(k, z)
      }
      if (m.size > 1800) { const ks = [...m.keys()].slice(0, m.size - 1800); ks.forEach(k => m.delete(k)) }
      setVzones([...m.values()])
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
          {[['satellite', 'satellite', 'Vệ tinh'], ['zoning', 'layers', 'Quy hoạch']].map(([k, ic, lbl]) => (
            <button key={k} type="button" onClick={() => setMode(k)}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 5, padding: '0.3rem 0.8rem', border: 'none', cursor: 'pointer', fontSize: '0.74rem', fontWeight: 700, background: mode === k ? 'var(--primary)' : 'transparent', color: mode === k ? '#fff' : 'var(--text-secondary)' }}>
              {icon(ic, 13, '', mode === k ? '#fff' : undefined)} {lbl}
            </button>
          ))}
        </div>
        {mode === 'zoning' && zLoading && <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: '0.7rem', color: 'var(--text-muted)' }}>{icon('loader', 12)} Đang tải quy hoạch…</span>}
        <span style={{ marginLeft: 'auto', display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: '0.7rem', color: 'var(--text-muted)' }}>
          <span style={{ width: 12, height: 12, borderRadius: 3, background: SUBJECT_FILL, border: `2px solid ${SUBJECT_COLOR}`, display: 'inline-block' }} /> {noun} của bạn
        </span>
      </div>

      <div style={{ width: '100%', height: 500, borderRadius: 14, overflow: 'hidden', border: '1px solid var(--border)', position: 'relative', background: '#0b1a2b' }}>
        {loading ? (
          <div style={{ display: 'grid', placeItems: 'center', height: '100%', color: '#94a3b8', fontSize: '0.82rem' }}>Đang dựng sơ đồ từ OpenStreetMap…</div>
        ) : error ? (
          <div style={{ display: 'grid', placeItems: 'center', height: '100%', color: '#94a3b8', fontSize: '0.82rem' }}>Chưa lấy được hình học khu đất (OSM).</div>
        ) : (
          <MapContainer
            center={[lat, lng]}
            zoom={18}
            style={{ height: '100%', width: '100%', background: mode === 'zoning' ? '#eef2f6' : '#0b1a2b' }}
            attributionControl={false}
            maxZoom={22}
            zoomAnimation={false}
            fadeAnimation={false}
            markerZoomAnimation={false}
          >
            {mode === 'satellite' ? (
              <TileLayer key="sat" url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" maxZoom={21} maxNativeZoom={19} />
            ) : (
              <TileLayer key="light" url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png" subdomains="abcd" maxZoom={21} maxNativeZoom={20} />
            )}
            {PLANNING_TILE_URL && mode === 'zoning' && <TileLayer url={PLANNING_TILE_URL} opacity={0.6} maxZoom={22} />}
            {mode === 'zoning' && vzones.map((z, i) => (
              <Polygon key={`z${i}`} positions={z.coords} pathOptions={{ color: 'rgba(30,41,59,0.55)', weight: 1, fillColor: ZONE_COLORS[z.zone] || ZONE_COLORS.other, fillOpacity: 0.6 }} />
            ))}
            {mode === 'zoning' && <ZoningLoader onResult={onZones} onLoading={setZLoading} />}
            {roads.map((r, i) => (
              <Polyline key={`r${i}`} positions={r.coords} pathOptions={{ color: mode === 'zoning' ? '#64748b' : (ROAD_COLOR[r.cls] || '#cbd5e1'), weight: r.cls === 'MAIN_STREET' ? 4 : 2, opacity: 0.65 }} />
            ))}
            {mode === 'satellite' && buildings.map((b, i) => (
              <Polygon key={`b${i}`} positions={b} pathOptions={{ color: '#475569', weight: 1, fillColor: '#94a3b8', fillOpacity: 0.16 }} />
            ))}
            {subject && (
              <>
                <Polygon positions={subject} pathOptions={{ color: '#ffffff', weight: 7, fill: false, opacity: 0.95 }} />
                <Polygon positions={subject} pathOptions={{ color: SUBJECT_COLOR, weight: 3, fillColor: SUBJECT_FILL, fillOpacity: 0.55 }} />
              </>
            )}
            <CircleMarker center={subjectCenter} radius={9} pathOptions={{ color: '#ffffff', weight: 3, fillColor: SUBJECT_COLOR, fillOpacity: 1 }}>
              <Tooltip permanent direction="top" offset={[0, -8]} className="pp-lot-label">{icon('pin', 11, '', '#fff')} {noun} của bạn</Tooltip>
            </CircleMarker>
            <FitBounds coordsList={focusBounds} />
          </MapContainer>
        )}
      </div>

      {mode === 'zoning' && (
        <div style={{ marginTop: 7 }}>
          {zonesPresent.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 4 }}>
              {zonesPresent.map(z => (
                <span key={z} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: '0.66rem', color: 'var(--text-secondary)' }}>
                  <span style={{ width: 12, height: 12, borderRadius: 2, background: ZONE_COLORS[z] || ZONE_COLORS.other, border: '1px solid rgba(0,0,0,0.25)' }} />
                  {ZONE_LABEL[z] || z}
                </span>
              ))}
            </div>
          )}
          {zNote === 'far' && <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: '0.7rem', color: 'var(--warning)' }}>{icon('search', 12)} Phóng to (zoom ≥ 12) để hiện màu quy hoạch; kéo bản đồ để phủ dần toàn thành phố.</div>}
          {zNote === 'large' && <div style={{ fontSize: '0.7rem', color: 'var(--warning)' }}>Khu vực quá rộng — phóng to thêm để tải lớp quy hoạch.</div>}
          <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', marginTop: 3 }}>
            Kéo/zoom để phủ dần quy hoạch <strong>toàn Hà Nội / TP.HCM</strong> (đã xem tới đâu giữ màu tới đó). Nguồn: OpenStreetMap (ODbL) — tham khảo.
          </div>
        </div>
      )}
    </div>
  )
}

// ─────────── Mô hình 3D đùn từ hình thửa THẬT (SVG) ───────────
function buildShapeMeters(data) {
  // Trả về danh sách điểm (mét) tâm tại (0,0). Ưu tiên polygon thật từ OSM.
  if (data?.subject && data.subject.length >= 3) {
    const pts = data.subject
    const lat0 = pts.reduce((s, c) => s + c[0], 0) / pts.length
    const lng0 = pts.reduce((s, c) => s + c[1], 0) / pts.length
    const mLat = 111320, mLng = 111320 * Math.cos(lat0 * Math.PI / 180)
    return pts.map(([la, ln]) => [(ln - lng0) * mLng, (la - lat0) * mLat])
  }
  return []
}

// ─────────── Ảnh THỰC TẾ tại đúng vị trí (Google, keyless iframe) ───────────
function PropertyImagery({ lat, lng, noun }) {
  const [view, setView] = useState('street')
  const [isLoaded, setIsLoaded] = useState(false)
  const sv = `https://www.google.com/maps?layer=c&cbll=${lat},${lng}&cbp=11,0,0,0,0&output=svembed`
  const sat = `https://maps.google.com/maps?q=${lat},${lng}&t=k&z=20&output=embed`
  const openUrl = view === 'street'
    ? `https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${lat},${lng}`
    : `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
          {[['street', 'street', 'Mặt đường'], ['sat', 'satellite', 'Từ trên cao']].map(([k, ic, lbl]) => (
            <button key={k} type="button" onClick={() => setView(k)}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 5, padding: '0.3rem 0.8rem', border: 'none', cursor: 'pointer', fontSize: '0.74rem', fontWeight: 700, background: view === k ? 'var(--primary)' : 'transparent', color: view === k ? '#fff' : 'var(--text-secondary)' }}>
              {icon(ic, 13, '', view === k ? '#fff' : undefined)} {lbl}
            </button>
          ))}
        </div>
        <a href={openUrl} target="_blank" rel="noreferrer" style={{ marginLeft: 'auto', fontSize: '0.72rem', color: 'var(--primary)', fontWeight: 700, textDecoration: 'none' }}>Mở Google Maps →</a>
      </div>
      <div style={{ width: '100%', height: 360, borderRadius: 6, overflow: 'hidden', border: '1px solid var(--border)', background: 'var(--surface-2)' }}>
        {isLoaded ? (
          <iframe key={view} title="property-imagery" src={view === 'street' ? sv : sat}
            width="100%" height="100%" style={{ border: 0, display: 'block' }} loading="lazy" referrerPolicy="no-referrer-when-downgrade" allow="fullscreen" allowFullScreen />
        ) : (
          <div style={{ height: '100%', display: 'grid', placeItems: 'center', padding: '1rem', textAlign: 'center' }}>
            <div>
              <div style={{ marginBottom: 8 }}>{icon('camera', 28)}</div>
              <div style={{ color: 'var(--text-primary)', fontSize: '0.82rem', fontWeight: 700 }}>Ảnh vị trí từ Google Maps</div>
              <p style={{ margin: '0.35rem auto 0.75rem', maxWidth: 460, color: 'var(--text-muted)', fontSize: '0.72rem', lineHeight: 1.5 }}>
                Chỉ kết nối Google Maps khi bạn chủ động mở để giảm request bên thứ ba và giữ trang phản hồi nhanh.
              </p>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setIsLoaded(true)}>
                {icon('eye', 13)} Cho phép tải Google Maps
              </button>
            </div>
          </div>
        )}
      </div>
      <div style={{ fontSize: '0.66rem', color: 'var(--text-muted)', marginTop: 5 }}>
        Ảnh thực tế tại đúng tọa độ {noun.toLowerCase()} bạn định giá (Google Street View / vệ tinh). Nếu khu vực chưa có Street View, hãy chuyển sang "Từ trên cao".
      </div>
    </div>
  )
}

// ─────────── BĐS tương đồng THẬT (Chợ Tốt) ───────────
function SimilarListings({ payload, propertyType }) {
  const [listings, setListings] = useState([])
  const [photos, setPhotos] = useState([])
  const [loading, setLoading] = useState(true)
  const place = [payload?.district, payload?.province_city].filter(Boolean).join(', ')
  const area = num(payload?.area_m2) || num(payload?.land_area_m2) || num(payload?.built_area_m2)

  useEffect(() => {
    let cancelled = false
    setLoading(true); setListings([]); setPhotos([])
    const asset = { land: 'LAND_URBAN', apartment: 'APARTMENT', townhouse: 'TOWNHOUSE', house: 'HOUSE', villa: 'VILLA' }[propertyType] || 'HOUSE'
    ;(async () => {
      try {
        const d = await mapListings({ propertyType, provinceCity: payload?.province_city, district: payload?.district, areaM2: area })
        if (!cancelled && d?.listings?.length) { setListings(d.listings); setLoading(false); return }
      } catch { /* fallback */ }
      try {
        const r = await fetch(`/api/v2/reference-photos?property_type=${asset}&limit=8`)
        const dd = await r.json()
        if (!cancelled) setPhotos((dd.photos || []).map(p => ({ url: p.url, caption: p.caption_vi || '' })))
      } catch { /* ignore */ }
      if (!cancelled) setLoading(false)
    })()
    return () => { cancelled = true }
  }, [propertyType, payload?.district, payload?.province_city, area])

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
          Tin rao thật cùng loại: <strong style={{ color: 'var(--text-secondary)' }}>{TYPE_VI[propertyType] || propertyType}{place ? ` · ${place}` : ''}{area ? ` · ~${Math.round(area)} m²` : ''}</strong>
        </span>
        {listings.length > 0 && <span style={{ marginLeft: 'auto', fontSize: '0.68rem', color: 'var(--text-muted)' }}>Nguồn: Chợ Tốt / Nhà Tốt</span>}
      </div>
      {loading ? (
        <div style={{ height: 150, display: 'grid', placeItems: 'center', color: 'var(--text-muted)', fontSize: '0.82rem', border: '1px solid var(--border)', borderRadius: 10 }}>Đang lấy tin rao bán thật tương đồng…</div>
      ) : listings.length > 0 ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 10 }}>
          {listings.map((l, i) => (
            <a key={i} href={l.url} target="_blank" rel="noreferrer" style={{ display: 'flex', flexDirection: 'column', borderRadius: 10, overflow: 'hidden', border: '1px solid var(--border)', background: 'var(--surface)', textDecoration: 'none', color: 'inherit' }}>
              <div style={{ height: 110, background: 'var(--surface-2)' }}>
                <img src={l.image} alt={l.title || 'listing'} loading="lazy" onError={(e) => { e.target.style.opacity = 0.2 }} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              </div>
              <div style={{ padding: '7px 9px', display: 'flex', flexDirection: 'column', gap: 3 }}>
                <div style={{ fontWeight: 800, fontSize: '0.84rem', color: 'var(--primary)' }}>{l.price || '—'}</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{l.area ? `${l.area} m²` : ''}{l.rooms ? ` · ${l.rooms}PN` : ''}{l.toilets ? ` · ${l.toilets}WC` : ''}</div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-primary)', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden', lineHeight: 1.3 }}>{l.title}</div>
                <div style={{ fontSize: '0.64rem', color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: 3 }}>{icon('pin', 11)} {l.location || place}</div>
              </div>
            </a>
          ))}
        </div>
      ) : photos.length > 0 ? (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: 8 }}>
            {photos.map((p, i) => (
              <div key={i} style={{ borderRadius: 8, overflow: 'hidden', border: '1px solid var(--border)', height: 96 }}>
                <img src={p.url} alt={p.caption} loading="lazy" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              </div>
            ))}
          </div>
          <div style={{ fontSize: '0.64rem', color: 'var(--text-muted)', marginTop: 6 }}>Chưa lấy được tin rao thật — đang hiển thị ảnh tham chiếu đúng loại hình.</div>
        </>
      ) : (
        <div style={{ height: 120, display: 'grid', placeItems: 'center', color: 'var(--text-muted)', fontSize: '0.82rem', border: '1px solid var(--border)', borderRadius: 10 }}>Không tìm thấy tin tương đồng.</div>
      )}
    </div>
  )
}

export default function PropertyVisualizer({ payload, propertyType, userPhotos = [] }) {
  const spec = useMemo(() => deriveSpec(payload, propertyType), [payload, propertyType])
  const lat = num(payload?.latitude)
  const lng = num(payload?.longitude)
  const hasCoords = lat != null && lng != null
  const noun = NOUN[propertyType] || 'Tài sản'
  const [tab, setTab] = useState(hasCoords ? 'map' : '3d')
  const [parcel, setParcel] = useState(null)
  const [pLoading, setPLoading] = useState(false)
  const [pError, setPError] = useState(false)

  useEffect(() => {
    if (!hasCoords) return
    let cancel = false
    setPLoading(true); setPError(false); setParcel(null)
    mapParcel({ lat, lng })
      .then(d => { if (!cancel) { setParcel(d); setPLoading(false) } })
      .catch(() => { if (!cancel) { setPError(true); setPLoading(false) } })
    return () => { cancel = true }
  }, [lat, lng, hasCoords])

  const chips = [
    spec.isLand ? `${Math.round(spec.landArea)} m² đất` : `${Math.round(spec.area)} m² sàn`,
    !spec.isLand && (spec.isTower ? (spec.aptFloor ? `Tầng ${spec.aptFloor}` : null) : `${spec.floors} tầng`),
    spec.bedrooms ? `${spec.bedrooms} PN` : null,
    spec.bathrooms ? `${spec.bathrooms} WC` : null,
    spec.facing ? `Hướng ${spec.facing}` : null,
  ].filter(Boolean)

  const modelMeters = useMemo(() => {
    if (tab !== '3d') return []
    const pts = buildShapeMeters(parcel)
    const mx = pts.reduce((s, p) => s + p[0], 0) / pts.length
    const my = pts.reduce((s, p) => s + p[1], 0) / pts.length
    return pts.map(([x, y]) => [x - mx, y - my])
  }, [tab, parcel, spec])
  const modelRealShape = !!(parcel?.subject && parcel.subject.length >= 3)

  return (
    <section className="property-visualizer">
      <header className="property-visualizer__header">
        <h3 className="property-visualizer__title">
          {icon('map', 16)}
          Trực quan hóa — {TYPE_VI[propertyType] || 'bất động sản'}
        </h3>
      </header>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, margin: '0.4rem 0 0.7rem' }}>
        {chips.map(c => (
          <span key={c} style={{ fontSize: '0.7rem', fontWeight: 600, padding: '2px 9px', borderRadius: 999, background: 'var(--primary-50)', color: 'var(--primary)', border: '1px solid var(--border)' }}>{c}</span>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
        {[['map', 'map', 'Sơ đồ', hasCoords], ['3d', 'cube', 'Mô hình 3D', true]].map(([k, ic, lbl, on]) => (
          <button key={k} type="button" disabled={!on} onClick={() => setTab(k)}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '0.4rem 0.8rem', borderRadius: 8, cursor: on ? 'pointer' : 'not-allowed', fontSize: '0.76rem', fontWeight: 700, opacity: on ? 1 : 0.4, border: `1px solid ${tab === k ? 'var(--primary)' : 'var(--border)'}`, background: tab === k ? 'var(--primary-50)' : 'transparent', color: tab === k ? 'var(--primary)' : 'var(--text-secondary)' }}>
            {icon(ic, 14)} {lbl}
          </button>
        ))}
      </div>

      {tab === 'map' && hasCoords
        ? <ParcelMap lat={lat} lng={lng} data={parcel} loading={pLoading} error={pError} noun={noun} />
        : (
          <Suspense fallback={<VisualizerLazyFallback label="Đang tải mô hình 3D..." />}>
            <PropertyModel3D meters={modelMeters} realShape={modelRealShape} spec={spec} noun={noun} />
          </Suspense>
        )}

      <div style={{ marginTop: '1rem' }}>
        <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
          {icon('camera', 14)} Ảnh thực tế {noun.toLowerCase()} của bạn
        </div>
        {hasCoords ? (
          <PropertyImagery lat={lat} lng={lng} noun={noun} />
        ) : (
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', padding: '1rem', border: '1px dashed var(--border)', borderRadius: 10 }}>Cần tọa độ (định vị trên bản đồ) để hiển thị ảnh thực tế.</div>
        )}
        {userPhotos.length > 0 && (
          <div style={{ marginTop: 10 }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 4 }}>Ảnh bạn đã tải lên:</div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {userPhotos.map((p, i) => (
                <img key={i} src={p.url} alt={p.name || 'user'} style={{ width: 64, height: 64, borderRadius: 8, objectFit: 'cover', border: `2px solid ${SUBJECT_COLOR}` }} />
              ))}
            </div>
          </div>
        )}
      </div>

      <div style={{ marginTop: '1.1rem' }}>
        <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
          {icon('globe', 14)} Tin rao bán tương tự (tham khảo giá khu vực)
        </div>
        <SimilarListings payload={payload} propertyType={propertyType} />
      </div>
    </section>
  )
}
