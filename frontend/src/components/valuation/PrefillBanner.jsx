/**
 * PrefillBanner — hiển thị dữ liệu đã TỰ ĐỘNG điền từ "Định vị thông minh"
 * và các GỢI Ý có sẵn của hệ thống cho quận đã chọn (kiểu OneHousing).
 *
 * - Đọc các key nội bộ trong prefill: _iot, _location, _field_options.
 * - Cho phép click chip phường/đường để điền nhanh (onPick(key, value)).
 * - Không render gì nếu chưa có prefill từ bản đồ.
 */
import React from 'react'
import { icon } from '../../components/ui/icons'

const fmtVnd = (v) => {
  if (!v) return '—'
  if (v >= 1e9) return `${(v / 1e9).toFixed(2)} tỷ`
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)} tr`
  return `${(v / 1e3).toFixed(0)}K`
}

function Chip({ children, onClick, title }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      style={{
        padding: '3px 10px', borderRadius: 999, cursor: 'pointer',
        border: '1px solid var(--border)', background: 'var(--surface)',
        color: 'var(--text-secondary)', fontSize: '0.72rem', fontWeight: 600,
      }}
    >
      {children}
    </button>
  )
}

export default function PrefillBanner({ prefill, onPick }) {
  if (!prefill || !prefill._v) return null
  const iot = prefill._iot
  const loc = prefill._location
  const opts = prefill._field_options

  return (
    <div
      className="prediction-note-band"
      style={{ borderColor: '#06d6a040', background: 'linear-gradient(135deg, #06d6a010, #0099ff10)' }}
    >
      <div className="prediction-note-head">
        <span className="stat-icon success">{icon('map', 18)}</span>
        <strong>Đã tự động điền từ bản đồ</strong>
        {loc?.in_scope === false && (
          <span className="badge badge-warning" style={{ marginLeft: 'auto', fontSize: '0.62rem' }}>
            ⚠ Ngoài 6 quận scope
          </span>
        )}
      </div>

      {loc?.snapped_to_nearest && loc?.snap_message && (
        <div style={{ marginTop: 8, padding: '0.5rem 0.7rem', borderRadius: 8, fontSize: '0.72rem', background: '#f59e0b15', border: '1px solid #f59e0b50', lineHeight: 1.4 }}>
          ⚠ {loc.snap_message}
        </div>
      )}

      {/* Vị trí + IoT chips */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 6 }}>
        {loc?.district && (
          <span className="badge badge-primary" style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: '0.68rem' }}>
            {icon('pin', 12)} {loc.district}{loc.province_city ? `, ${loc.province_city}` : ''}
          </span>
        )}
        {iot && [
          ['Ồn', `${iot.noise_level} dB`],
          ['Nhiệt', `${iot.temperature}°C`],
          ['Ẩm', `${iot.humidity}%`],
          ['Sáng', `${iot.light_level} lux`],
          ['Chất lượng KV', `${iot.area_quality_score}/10`],
        ].map(([k, v]) => (
          <span key={k} style={{
            fontSize: '0.68rem', padding: '2px 8px', borderRadius: 999,
            background: '#06d6a018', color: '#06d6a0', fontWeight: 600,
          }}>
            {k}: {v}
          </span>
        ))}
      </div>

      {/* Gợi ý hệ thống theo quận */}
      {opts && opts.sample_size > 0 && (
        <div style={{ marginTop: 10, fontSize: '0.74rem' }}>
          <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>
            Hệ thống có sẵn cho khu vực này ({opts.sample_size} mẫu thật) — bấm để điền nhanh:
          </div>

          {opts.wards?.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, marginBottom: 6, alignItems: 'center' }}>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>Phường/Xã:</span>
              {opts.wards.slice(0, 8).map(w => (
                <Chip key={w} onClick={() => onPick?.('ward', w)}>{w}</Chip>
              ))}
            </div>
          )}

          {opts.streets?.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, marginBottom: 6, alignItems: 'center' }}>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>Đường/Dự án:</span>
              {opts.streets.slice(0, 8).map(s => (
                <Chip key={s} onClick={() => onPick?.('street_or_project', s)}>{s}</Chip>
              ))}
            </div>
          )}

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, color: 'var(--text-muted)', fontSize: '0.7rem' }}>
            {opts.area_range && (
              <span>Diện tích phổ biến: <strong style={{ color: 'var(--text-primary)' }}>{opts.area_range.min}–{opts.area_range.max} m²</strong> (median {opts.area_range.median})</span>
            )}
            {opts.price_per_m2_range && (
              <span>Giá/m² khu vực: <strong style={{ color: 'var(--primary)' }}>{fmtVnd(opts.price_per_m2_range.min)}–{fmtVnd(opts.price_per_m2_range.max)}</strong></span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
