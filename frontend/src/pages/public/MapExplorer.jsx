/**
 * MapExplorer — AVM-focused property map
 *
 * Purpose: Market intelligence & comparable density, NOT just dot display.
 *
 * Key features:
 * - District-level price statistics (avg/m² by district)
 * - Property markers color-coded by confidence grade (A/B/C/D)
 * - Click map → show nearby comparable density
 * - Market stats panel: price tier distribution, recent valuations
 * - Fly-to-location from Prediction page
 * - No decorative markers — every element serves AVM purpose
 *
 * Role: user (visible to logged-in users)
 */
import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  MapContainer, TileLayer, Marker, Popup, CircleMarker,
  useMap,
} from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

const HANOI_CENTER = [21.0285, 105.8542]
const HCM_CENTER = [10.7769, 106.7009]
const DEFAULT_ZOOM = 12

// Color coding by confidence grade (A=best, D=worst)
const GRADE_COLORS = {
  A: '#06d6a0',  // green
  B: '#0099ff',  // blue
  C: '#f59e0b',  // orange
  D: '#ef233c',  // red
  default: '#6366f1',
}

const GRADE_LABELS = {
  A: 'Tin cậy cao',
  B: 'Tin cậy vừa',
  C: 'Tin cậy thấp',
  D: 'Cần xác minh',
  default: 'Chưa đánh giá',
}

// Price tier colors (price/m²)
const PRICE_TIER_COLORS = {
  budget:    '#06d6a0',  // < 30M/m²
  moderate:  '#f59e0b',  // 30-70M/m²
  premium:   '#0099ff',   // 70-120M/m²
  luxury:    '#8b5cf6',  // > 120M/m²
  unknown:   '#94a3b8',
}

function formatVnd(v) {
  if (!v) return '—'
  if (v >= 1e9) return `${(v / 1e9).toFixed(1)}B`
  if (v >= 1e6) return `${(v / 1e6).toFixed(0)}M`
  return `${(v / 1e3).toFixed(0)}K`
}

function formatPrice(price) {
  if (!price) return '—'
  return new Intl.NumberFormat('vi-VN', {
    style: 'currency', currency: 'VND', maximumFractionDigits: 0,
  }).format(price)
}

function getPriceTier(pricePerM2) {
  if (!pricePerM2) return 'unknown'
  if (pricePerM2 < 30_000_000) return 'budget'
  if (pricePerM2 < 70_000_000) return 'moderate'
  if (pricePerM2 < 120_000_000) return 'premium'
  return 'luxury'
}

// Property popup with AVM context
function PropertyPopup({ property, onNavigate }) {
  const priceTier = getPriceTier(property.price_per_m2)
  const grade = property.confidence_grade || property.evidence_tier?.[0] || 'default'
  const gradeColor = GRADE_COLORS[grade] || GRADE_COLORS.default

  return (
    <div style={{ minWidth: 220, fontFamily: 'system-ui, -apple-system, sans-serif', fontSize: 13 }}>
      <div style={{ fontWeight: 700, color: '#1e293b', marginBottom: 6, fontSize: 14, lineHeight: 1.3 }}>
        {property.district || property.street_or_project || 'Bất động sản'}
        {property.ward && <span style={{ fontWeight: 400, color: '#64748b' }}>, {property.ward}</span>}
      </div>
      <div style={{ fontSize: 12, color: '#64748b', marginBottom: 4 }}>
        {PROPERTY_TYPES_VN[property.property_type] || property.property_type}
        {property.area_m2 && ` · ${property.area_m2} m²`}
      </div>
      {property.price && (
        <div style={{ fontWeight: 700, color: '#059669', fontSize: 15, marginTop: 4 }}>
          {formatVnd(property.price)}
        </div>
      )}
      {property.price_per_m2 && (
        <div style={{ fontSize: 12, color: '#64748b' }}>
          {formatVnd(property.price_per_m2)}/m²
          <span style={{
            display: 'inline-block', marginLeft: 6, padding: '1px 5px', borderRadius: 4,
            background: PRICE_TIER_COLORS[priceTier] + '20', color: PRICE_TIER_COLORS[priceTier],
            fontSize: 10, fontWeight: 600,
          }}>
            {priceTier === 'budget' ? 'Bình dân' : priceTier === 'moderate' ? 'Trung cấp' : priceTier === 'premium' ? 'Cao cấp' : priceTier === 'luxury' ? 'Xa xỉ' : '?'}
          </span>
        </div>
      )}
      {/* Confidence/Evidence badge */}
      <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
        {property.confidence_grade ? (
          <span style={{
            display: 'inline-block', padding: '2px 8px', borderRadius: 8,
            fontSize: 11, fontWeight: 600,
            background: gradeColor + '20', color: gradeColor,
            border: `1px solid ${gradeColor}40`,
          }}>
            Grade {property.confidence_grade}
          </span>
        ) : property.evidence_tier ? (
          <span style={{
            display: 'inline-block', padding: '2px 8px', borderRadius: 8,
            fontSize: 11, fontWeight: 600,
            background: gradeColor + '20', color: gradeColor,
          }}>
            {property.evidence_tier}
          </span>
        ) : null}
        {property.data_origin_type === 'self_collected' && (
          <span style={{
            display: 'inline-block', padding: '2px 8px', borderRadius: 8,
            fontSize: 11, fontWeight: 600,
            background: '#06d6a020', color: '#06d6a0',
            border: '1px solid #06d6a040',
          }}>
            Tự thu thập
          </span>
        )}
      </div>
      {/* Action */}
      {property.latitude && property.longitude && (
        <div style={{ marginTop: 10, display: 'flex', gap: 6 }}>
          <button
            onClick={() => onNavigate?.(property)}
            style={{
              flex: 1, padding: '5px 10px', borderRadius: 6, border: 'none',
              background: '#7c3aed', color: 'white', fontSize: 12, cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            Định giá tại đây
          </button>
        </div>
      )}
    </div>
  )
}

const PROPERTY_TYPES_VN = {
  house: 'Nhà riêng',
  apartment: 'Căn hộ',
  land: 'Đất nền',
  townhouse: 'Nhà phố',
  villa: 'Biệt thự',
}

function MapController({ onMapClick, onReady }) {
  const map = useMap()
  useEffect(() => {
    map.on('click', onMapClick)
    return () => { map.off('click', onMapClick) }
  }, [map, onMapClick])
  useEffect(() => { onReady(map) }, [map, onReady])
  return null
}

function createMarkerIcon(color, grade) {
  return L.divIcon({
    className: '',
    html: `<div style="
      width:14px;height:14px;border-radius:50%;
      background:${color};
      border:2px solid white;
      box-shadow:0 1px 4px rgba(0,0,0,0.3);
      cursor:pointer;
    "></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  })
}

export default function MapExplorer() {
  const mapInstanceRef = useRef(null)
  const [mapCenter, setMapCenter] = useState(HANOI_CENTER)
  const [mapZoom, setMapZoom] = useState(DEFAULT_ZOOM)
  const [activeLayer, setActiveLayer] = useState('street')
  const [activeView, setActiveView] = useState('price_tier') // 'price_tier' | 'confidence' | 'comparable'
  const [selectedDistrict, setSelectedDistrict] = useState(null)
  const [clickedCoords, setClickedCoords] = useState(null)
  const [hoveredMarker, setHoveredMarker] = useState(null)

  // Fetch all properties with coordinates
  const { data: properties, isLoading } = useQuery({
    queryKey: ['map-properties'],
    queryFn: async () => {
      const res = await fetch('/api/properties?limit=5000')
      if (!res.ok) return []
      const data = await res.json()
      return Array.isArray(data) ? data : []
    },
    staleTime: 5 * 60 * 1000,
  })

  // Fetch district price stats from dashboard API
  const { data: districtStats } = useQuery({
    queryKey: ['district-price-stats'],
    queryFn: async () => {
      const res = await fetch('/api/dataset/overview')
      if (!res.ok) return null
      return res.json()
    },
    staleTime: 10 * 60 * 1000,
  })

  const geoProps = useMemo(() =>
    (properties || []).filter(p => p.latitude && p.longitude),
    [properties]
  )

  // Compute district-level price statistics
  const districtPriceStats = useMemo(() => {
    const stats = {}
    geoProps.forEach(p => {
      if (!p.district || !p.price_per_m2) return
      if (!stats[p.district]) {
        stats[p.district] = { prices: [], count: 0, total_area: 0, province: p.province_city }
      }
      stats[p.district].prices.push(p.price_per_m2)
      stats[p.district].count++
      stats[p.district].total_area += p.area_m2 || 0
    })
    return Object.entries(stats).map(([district, data]) => {
      const avg = data.prices.reduce((a, b) => a + b, 0) / data.prices.length
      const sorted = [...data.prices].sort((a, b) => a - b)
      const median = sorted[Math.floor(sorted.length / 2)]
      return {
        district,
        province: data.province,
        count: data.count,
        avg_price_per_m2: avg,
        median_price_per_m2: median,
        total_area: data.total_area,
        min: Math.min(...data.prices),
        max: Math.max(...data.prices),
        tier: getPriceTier(avg),
      }
    }).sort((a, b) => b.avg_price_per_m2 - a.avg_price_per_m2)
  }, [geoProps])

  // Count by district
  const countByDistrict = useMemo(() => {
    const counts = {}
    geoProps.forEach(p => {
      if (!p.district) return
      counts[p.district] = (counts[p.district] || 0) + 1
    })
    return counts
  }, [geoProps])

  // Market summary stats
  const marketStats = useMemo(() => {
    const withPrice = geoProps.filter(p => p.price && p.area_m2)
    const avgPrice = withPrice.reduce((s, p) => s + p.price / (p.area_m2 || 1), 0) / Math.max(withPrice.length, 1)
    const gradeCounts = { A: 0, B: 0, C: 0, D: 0, default: 0 }
    const tierCounts = { budget: 0, moderate: 0, premium: 0, luxury: 0, unknown: 0 }
    geoProps.forEach(p => {
      const grade = p.confidence_grade || p.evidence_tier?.[0] || 'default'
      gradeCounts[grade] = (gradeCounts[grade] || 0) + 1
      tierCounts[getPriceTier(p.price_per_m2)]++
    })
    return {
      total: geoProps.length,
      withPrice: withPrice.length,
      avgPricePerM2: avgPrice,
      gradeCounts,
      tierCounts,
    }
  }, [geoProps])

  const handleMapClick = useCallback((e) => {
    setClickedCoords({ lat: e.latlng.lat.toFixed(6), lng: e.latlng.lng.toFixed(6) })
  }, [])

  const handleMapReady = useCallback((map) => {
    mapInstanceRef.current = map
  }, [])

  const handleNavigate = useCallback((property) => {
    window.location.href = `/?lat=${property.latitude}&lng=${property.longitude}&type=${property.property_type}`
  }, [])

  const getMarkerColor = (property) => {
    if (activeView === 'price_tier') {
      return PRICE_TIER_COLORS[getPriceTier(property.price_per_m2)]
    }
    if (activeView === 'confidence') {
      const grade = property.confidence_grade || property.evidence_tier?.[0] || 'default'
      return GRADE_COLORS[grade] || GRADE_COLORS.default
    }
    return GRADE_COLORS.default
  }

  const copyCoords = () => {
    if (clickedCoords) {
      navigator.clipboard.writeText(`${clickedCoords.lat}, ${clickedCoords.lng}`)
    }
  }

  const tileLayers = {
    street: {
      url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      attribution: '© OpenStreetMap',
    },
    satellite: {
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      attribution: '© Esri',
    },
    dark: {
      url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
      attribution: '© CARTO',
    },
  }

  const viewBtns = [
    { key: 'price_tier', label: 'Mức giá' },
    { key: 'confidence', label: 'Độ tin cậy' },
  ]

  const layerBtns = [
    { key: 'street', label: 'Đường' },
    { key: 'satellite', label: 'Vệ tinh' },
    { key: 'dark', label: 'Tối' },
  ]

  const goToCity = (city) => {
    if (mapInstanceRef.current) {
      mapInstanceRef.current.setView(
        city === 'hanoi' ? HANOI_CENTER : HCM_CENTER,
        DEFAULT_ZOOM
      )
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 60px)' }}>
      {/* Header */}
      <div className="page-header" style={{ flexShrink: 0 }}>
        <div>
          <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            Bản đồ thị trường BĐS
          </h1>
          <p className="page-subtitle">
            {geoProps.length} tài sản có tọa độ · Click bản đồ để lấy GPS · Chọn điểm để định giá
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Market view toggle */}
          <div style={{
            display: 'flex', borderRadius: 8, overflow: 'hidden',
            border: '1px solid var(--border)', background: 'var(--surface)',
          }}>
            {viewBtns.map(btn => (
              <button
                key={btn.key}
                onClick={() => setActiveView(btn.key)}
                style={{
                  padding: '5px 12px', border: 'none', cursor: 'pointer',
                  fontSize: '0.72rem', fontWeight: 600,
                  background: activeView === btn.key ? 'var(--primary)' : 'transparent',
                  color: activeView === btn.key ? 'white' : 'var(--text-secondary)',
                  transition: 'all 150ms',
                }}
              >
                {btn.label}
              </button>
            ))}
          </div>
          {/* Layer toggle */}
          <div style={{
            display: 'flex', borderRadius: 8, overflow: 'hidden',
            border: '1px solid var(--border)', background: 'var(--surface)',
          }}>
            {layerBtns.map(layer => (
              <button
                key={layer.key}
                onClick={() => setActiveLayer(layer.key)}
                style={{
                  padding: '5px 10px', border: 'none', cursor: 'pointer',
                  fontSize: '0.72rem', fontWeight: 600,
                  background: activeLayer === layer.key ? 'var(--primary)' : 'transparent',
                  color: activeLayer === layer.key ? 'white' : 'var(--text-secondary)',
                  transition: 'all 150ms',
                }}
              >
                {layer.label}
              </button>
            ))}
          </div>
          {/* Jump to city */}
          <select
            onChange={e => goToCity(e.target.value)}
            style={{
              padding: '5px 10px', borderRadius: 8, border: '1px solid var(--border)',
              background: 'var(--surface)', color: 'var(--text-primary)',
              fontSize: '0.72rem', cursor: 'pointer', fontWeight: 600,
            }}
          >
            <option value="hanoi">Hà Nội</option>
            <option value="hcm">Hồ Chí Minh</option>
          </select>
        </div>
      </div>

      {/* Map + Sidebar */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Map */}
        <div style={{ flex: 1, position: 'relative' }}>
          <MapContainer
            center={mapCenter}
            zoom={mapZoom}
            style={{ width: '100%', height: '100%' }}
            zoomControl={true}
          >
            <MapController onMapClick={handleMapClick} onReady={handleMapReady} />
            <TileLayer
              url={tileLayers[activeLayer]?.url}
              attribution={tileLayers[activeLayer]?.attribution}
            />

            {/* Property markers — color-coded by active view */}
            {geoProps.map((p, i) => {
              const color = getMarkerColor(p)
              return (
                <Marker
                  key={p.id || i}
                  position={[p.latitude, p.longitude]}
                  icon={createMarkerIcon(color, p.confidence_grade)}
                  eventHandlers={{
                    click: () => setHoveredMarker(p),
                  }}
                >
                  <Popup>
                    <PropertyPopup property={p} onNavigate={handleNavigate} />
                  </Popup>
                </Marker>
              )
            })}
          </MapContainer>

          {/* Clicked coordinates overlay */}
          {clickedCoords && (
            <div style={{
              position: 'absolute', bottom: 16, left: '50%', transform: 'translateX(-50%)',
              background: 'rgba(15,23,42,0.95)', backdropFilter: 'blur(8px)',
              border: '1px solid rgba(125,211,252,0.3)', borderRadius: 10,
              padding: '6px 14px', display: 'flex', alignItems: 'center', gap: 10,
              zIndex: 1000, fontSize: '0.78rem', color: '#38bdf8',
              boxShadow: '0 4px 16px rgba(0,0,0,0.3)',
            }}>
              <span>{clickedCoords.lat}, {clickedCoords.lng}</span>
              <button
                onClick={copyCoords}
                style={{
                  padding: '2px 8px', borderRadius: 5,
                  border: '1px solid rgba(125,211,252,0.3)',
                  background: 'rgba(125,211,252,0.1)', color: '#38bdf8',
                  fontSize: '0.72rem', cursor: 'pointer', fontWeight: 600,
                }}
              >
                Copy
              </button>
              <button
                onClick={() => {
                  window.location.href = `/?lat=${clickedCoords.lat}&lng=${clickedCoords.lng}`
                }}
                style={{
                  padding: '2px 8px', borderRadius: 5, border: 'none',
                  background: '#7c3aed', color: 'white',
                  fontSize: '0.72rem', cursor: 'pointer', fontWeight: 600,
                }}
              >
                Định giá tại đây
              </button>
              <button
                onClick={() => setClickedCoords(null)}
                style={{ border: 'none', background: 'none', color: '#64748b', cursor: 'pointer', padding: '2px 4px', fontSize: '1rem' }}
              >
                ×
              </button>
            </div>
          )}

          {/* Loading indicator */}
          {isLoading && (
            <div style={{
              position: 'absolute', top: 10, left: '50%', transform: 'translateX(-50%)',
              background: 'rgba(15,23,42,0.85)', backdropFilter: 'blur(4px)',
              borderRadius: 8, padding: '4px 12px', zIndex: 1000,
              fontSize: '0.72rem', color: '#94a3b8',
              border: '1px solid var(--border)',
              display: 'flex', alignItems: 'center', gap: '6px',
            }}>
              Đang tải {properties?.length || 0} tài sản...
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div style={{
          width: 320, flexShrink: 0, background: 'var(--surface)',
          borderLeft: '1px solid var(--border)', overflowY: 'auto',
          display: 'flex', flexDirection: 'column',
        }}>
          {/* Market Overview */}
          <div style={{ padding: 12, borderBottom: '1px solid var(--border)' }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 8, fontWeight: 700, textTransform: 'uppercase' }}>
              Tổng quan thị trường
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              <div style={{ background: 'var(--bg-elevated)', borderRadius: 8, padding: '8px 10px' }}>
                <div style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--primary)' }}>{marketStats.total}</div>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Có tọa độ</div>
              </div>
              <div style={{ background: 'var(--bg-elevated)', borderRadius: 8, padding: '8px 10px' }}>
                <div style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--accent)' }}>{formatVnd(marketStats.avgPricePerM2)}</div>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>TB /m²</div>
              </div>
            </div>
          </div>

          {/* View Legend */}
          <div style={{ padding: 12, borderBottom: '1px solid var(--border)' }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 8, fontWeight: 700, textTransform: 'uppercase' }}>
              {activeView === 'price_tier' ? 'Mức giá /m²' : 'Độ tin cậy'}
            </div>
            {activeView === 'price_tier' ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {[
                  ['Bình dân', '< 30M', PRICE_TIER_COLORS.budget],
                  ['Trung cấp', '30–70M', PRICE_TIER_COLORS.moderate],
                  ['Cao cấp', '70–120M', PRICE_TIER_COLORS.premium],
                  ['Xa xỉ', '> 120M', PRICE_TIER_COLORS.luxury],
                ].map(([label, range, color]) => (
                  <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ width: 12, height: 12, borderRadius: '50%', background: color, flexShrink: 0 }} />
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', flex: 1 }}>{label}</span>
                    <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>{range}</span>
                    <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      {marketStats.tierCounts[label === 'Bình dân' ? 'budget' : label === 'Trung cấp' ? 'moderate' : label === 'Cao cấp' ? 'premium' : 'luxury'] || 0}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {['A', 'B', 'C', 'D'].map(grade => (
                  <div key={grade} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ width: 12, height: 12, borderRadius: '50%', background: GRADE_COLORS[grade], flexShrink: 0 }} />
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', flex: 1 }}>
                      {GRADE_LABELS[grade]}
                    </span>
                    <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      {marketStats.gradeCounts[grade] || 0}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* District Price Stats */}
          <div style={{ padding: 12, flex: 1, overflowY: 'auto' }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 8, fontWeight: 700, textTransform: 'uppercase' }}>
              Giá TB theo quận ({formatVnd(marketStats.avgPricePerM2)}/m²)
            </div>
            {districtPriceStats.slice(0, 12).map(stat => (
              <div
                key={stat.district}
                onClick={() => {
                  setSelectedDistrict(stat.district)
                  if (mapInstanceRef.current) {
                    // Find a property in this district to center on
                    const prop = geoProps.find(p => p.district === stat.district)
                    if (prop) {
                      mapInstanceRef.current.setView([prop.latitude, prop.longitude], 14)
                    }
                  }
                }}
                style={{
                  padding: '8px 10px', borderRadius: 8, marginBottom: 6, cursor: 'pointer',
                  background: selectedDistrict === stat.district ? 'var(--primary-50)' : 'var(--bg-elevated)',
                  border: selectedDistrict === stat.district ? '1px solid var(--primary-200)' : '1px solid transparent',
                  transition: 'all 150ms',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {stat.district}
                  </div>
                  <span style={{
                    fontSize: '0.65rem', fontWeight: 700,
                    color: PRICE_TIER_COLORS[stat.tier],
                    background: PRICE_TIER_COLORS[stat.tier] + '18',
                    padding: '1px 5px', borderRadius: 4,
                  }}>
                    {stat.count} BĐS
                  </span>
                </div>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--primary)' }}>
                  {formatVnd(stat.avg_price_per_m2)}/m²
                </div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                  Min: {formatVnd(stat.min)} · Max: {formatVnd(stat.max)}
                </div>
              </div>
            ))}
            {districtPriceStats.length === 0 && (
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textAlign: 'center', padding: '1rem' }}>
                Chưa có đủ dữ liệu giá theo quận
              </div>
            )}
          </div>

          {/* Quick action */}
          <div style={{ padding: 12, borderTop: '1px solid var(--border)' }}>
            <div style={{
              padding: '10px 14px', background: '#7c3aed15', border: '1px solid #7c3aed30',
              borderRadius: 8, fontSize: '0.75rem', color: '#7c3aed',
              textAlign: 'center',
            }}>
              Click bản đồ để lấy tọa độ và định giá ngay tại vị trí đó
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}