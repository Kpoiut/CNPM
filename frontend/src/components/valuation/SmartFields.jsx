/**
 * SmartFields — field tái sử dụng, kiểu OneHousing/Grab.
 *
 * - Combobox (SelectField): ô có thể TÌM KIẾM + chọn 1 chạm (không phải gõ tay).
 * - NumberField: gõ tự do HOẶC bấm chọn nhanh từ dropdown gợi ý.
 * - TextField: gõ tự do + dropdown gợi ý.
 * - Tất cả đều memo hoá (bỏ qua prop hàm) → chỉ field đổi mới render lại,
 *   loại bỏ giật lag khi form có nhiều trường.
 */
import React, { useState, useRef, useEffect, useLayoutEffect, useMemo, memo } from 'react'
import { createPortal } from 'react-dom'
import { icon } from '../../components/ui/icons'

function normOptions(options = []) {
  if (Array.isArray(options)) return options.map(o => (Array.isArray(o) ? o : [o, o]))
  return Object.entries(options)
}

// So sánh props bỏ qua hàm → onChange/onPick đổi ref mỗi render không gây re-render
function sameProps(prev, next) {
  const keys = new Set([...Object.keys(prev), ...Object.keys(next)])
  for (const k of keys) {
    if (typeof prev[k] === 'function' && typeof next[k] === 'function') continue
    if (prev[k] !== next[k]) return false
  }
  return true
}

function useOutsideClose(open, setOpen, refs) {
  useEffect(() => {
    if (!open) return undefined
    const h = (e) => {
      for (const r of refs) { if (r.current && r.current.contains(e.target)) return }
      setOpen(false)
    }
    document.addEventListener('mousedown', h)
    return () => document.removeEventListener('mousedown', h)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, setOpen])
}

/**
 * Dropdown rendered qua portal + position:fixed neo theo ô input.
 * → Thoát mọi `overflow:hidden` của .card và mọi stacking-context của các
 *   section bên dưới, nên danh sách gợi ý KHÔNG còn bị che / cắt cụt.
 *   Tự lật lên trên khi không đủ chỗ phía dưới.
 */
function PortalDropdown({ anchorRef, popRef, maxHeight = 240, children }) {
  const [rect, setRect] = useState(() => anchorRef.current?.getBoundingClientRect() || null)
  useLayoutEffect(() => {
    const el = anchorRef.current
    if (!el) return undefined
    const update = () => setRect(el.getBoundingClientRect())
    update()
    window.addEventListener('scroll', update, true)
    window.addEventListener('resize', update)
    return () => {
      window.removeEventListener('scroll', update, true)
      window.removeEventListener('resize', update)
    }
  }, [anchorRef])
  if (!rect) return null
  const spaceBelow = window.innerHeight - rect.bottom
  const openUp = spaceBelow < maxHeight + 24 && rect.top > spaceBelow
  const style = {
    position: 'fixed', left: rect.left, width: rect.width, zIndex: 9999,
    background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8,
    boxShadow: '0 12px 34px rgba(0,0,0,0.35)', overflow: 'hidden',
    ...(openUp
      ? { bottom: Math.max(8, window.innerHeight - rect.top + 4) }
      : { top: rect.bottom + 4 }),
  }
  return createPortal(
    <div ref={popRef} className="pp-dropdown" style={style}>{children}</div>,
    document.body,
  )
}

function OptionRow({ active, children, onClick }) {
  return (
    <button
      type="button"
      className="pp-opt"
      onMouseDown={(e) => { e.preventDefault(); onClick() }}
      style={{
        display: 'block', width: '100%', textAlign: 'left', padding: '0.45rem 0.7rem',
        border: 'none', borderBottom: '1px solid var(--border)', cursor: 'pointer',
        fontSize: '0.82rem', background: active ? 'var(--primary-50)' : 'transparent',
        color: active ? 'var(--primary)' : 'var(--text-primary)', fontWeight: active ? 700 : 500,
      }}
    >
      {children}
    </button>
  )
}

/** Combobox tìm kiếm — phần CHỌN kiểu OneHousing */
export const SelectField = memo(function SelectField({ label, value, onChange, options, required, placeholder = '— Chọn —', hint, span }) {
  const opts = useMemo(() => normOptions(options), [options])
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const groupRef = useRef(null)
  const anchorRef = useRef(null)
  const popRef = useRef(null)
  useOutsideClose(open, setOpen, [groupRef, popRef])
  const selected = opts.find(o => String(o[0]) === String(value))
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return opts
    return opts.filter(([c, l]) => String(l).toLowerCase().includes(q) || String(c).toLowerCase().includes(q))
  }, [opts, query])

  return (
    <div className={`form-group ${span ? 'span-2' : ''}`} style={{ position: 'relative' }} ref={groupRef}>
      {label && <label className={`form-label ${required ? 'required' : ''}`}>{label}{required ? ' *' : ''}</label>}
      <div style={{ position: 'relative' }} ref={anchorRef}>
        <input
          className="form-input"
          value={open ? query : (selected ? selected[1] : '')}
          placeholder={placeholder}
          onChange={e => { if (open) setQuery(e.target.value) }}
          onFocus={() => { setOpen(true); setQuery('') }}
          onClick={() => setOpen(true)}
          style={{ cursor: 'pointer', paddingRight: 26 }}
          autoComplete="off"
        />
        <span onMouseDown={(e) => { e.preventDefault(); setOpen(o => !o) }}
          style={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', cursor: 'pointer', pointerEvents: 'auto' }}>
          {icon('chevronDown', 14)}
        </span>
      </div>
      {open && (
        <PortalDropdown anchorRef={anchorRef} popRef={popRef} maxHeight={220}>
          <div style={{ maxHeight: 220, overflowY: 'auto' }}>
            {filtered.length === 0 && <div style={{ padding: '0.5rem 0.7rem', fontSize: '0.78rem', color: 'var(--text-muted)' }}>Không có lựa chọn khớp</div>}
            {filtered.map(([code, lbl]) => (
              <OptionRow key={code} active={String(code) === String(value)} onClick={() => { onChange(code); setOpen(false); setQuery('') }}>
                {lbl}
              </OptionRow>
            ))}
          </div>
        </PortalDropdown>
      )}
      {hint && <div className="text-xs text-muted" style={{ marginTop: 2 }}>{hint}</div>}
    </div>
  )
}, sameProps)

/** Số — gõ tự do HOẶC bấm chọn nhanh từ dropdown gợi ý */
export const NumberField = memo(function NumberField({ label, value, onChange, required, placeholder, min, max, step = 'any', span, hint, suggestions }) {
  const [open, setOpen] = useState(false)
  const groupRef = useRef(null)
  const anchorRef = useRef(null)
  const popRef = useRef(null)
  useOutsideClose(open, setOpen, [groupRef, popRef])
  const hasSug = Array.isArray(suggestions) && suggestions.length > 0
  return (
    <div className={`form-group ${span ? 'span-2' : ''}`} style={{ position: 'relative' }} ref={groupRef}>
      {label && <label className={`form-label ${required ? 'required' : ''}`}>{label}{required ? ' *' : ''}</label>}
      <div style={{ position: 'relative' }} ref={anchorRef}>
        <input
          type="number" className="form-input"
          value={value} onChange={e => onChange(e.target.value)}
          required={required} placeholder={placeholder} min={min} max={max} step={step}
          style={hasSug ? { paddingRight: 26 } : undefined}
        />
        {hasSug && (
          <span onMouseDown={(e) => { e.preventDefault(); setOpen(o => !o) }}
            style={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', cursor: 'pointer' }}>
            {icon('chevronDown', 14)}
          </span>
        )}
      </div>
      {open && hasSug && (
        <PortalDropdown anchorRef={anchorRef} popRef={popRef} maxHeight={200}>
          <div style={{ maxHeight: 200, overflowY: 'auto' }}>
            {suggestions.map(s => (
              <OptionRow key={s} active={String(s) === String(value)} onClick={() => { onChange(String(s)); setOpen(false) }}>
                {s}
              </OptionRow>
            ))}
          </div>
        </PortalDropdown>
      )}
      {hint && <div className="text-xs text-muted" style={{ marginTop: 2 }}>{hint}</div>}
    </div>
  )
}, sameProps)

/** Text tự do (phường/đường) — gõ + dropdown gợi ý */
export const TextField = memo(function TextField({ label, value, onChange, placeholder, options, required, span }) {
  const opts = useMemo(() => (options ? normOptions(options) : []), [options])
  const [open, setOpen] = useState(false)
  const groupRef = useRef(null)
  const anchorRef = useRef(null)
  const popRef = useRef(null)
  useOutsideClose(open, setOpen, [groupRef, popRef])
  const filtered = useMemo(() => {
    const q = String(value || '').trim().toLowerCase()
    if (!q) return opts
    return opts.filter(([, l]) => String(l).toLowerCase().includes(q))
  }, [opts, value])
  return (
    <div className={`form-group ${span ? 'span-2' : ''}`} style={{ position: 'relative' }} ref={groupRef}>
      {label && <label className={`form-label ${required ? 'required' : ''}`}>{label}{required ? ' *' : ''}</label>}
      <div style={{ position: 'relative' }} ref={anchorRef}>
        <input
          className="form-input" value={value} onChange={e => onChange(e.target.value)}
          onFocus={() => setOpen(true)} placeholder={placeholder} required={required}
          style={opts.length ? { paddingRight: 26 } : undefined} autoComplete="off"
        />
        {opts.length > 0 && (
          <span onMouseDown={(e) => { e.preventDefault(); setOpen(o => !o) }}
            style={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', cursor: 'pointer' }}>
            {icon('chevronDown', 14)}
          </span>
        )}
      </div>
      {open && filtered.length > 0 && (
        <PortalDropdown anchorRef={anchorRef} popRef={popRef} maxHeight={200}>
          <div style={{ maxHeight: 200, overflowY: 'auto' }}>
            {filtered.map(([code, lbl]) => (
              <OptionRow key={code} active={false} onClick={() => { onChange(lbl); setOpen(false) }}>{lbl}</OptionRow>
            ))}
          </div>
        </PortalDropdown>
      )}
    </div>
  )
}, sameProps)

/** Nhóm nút phân đoạn — tập lựa chọn nhỏ */
export const SegmentedField = memo(function SegmentedField({ label, value, onChange, options, hint, span }) {
  const opts = useMemo(() => normOptions(options), [options])
  return (
    <div className={`form-group ${span ? 'span-2' : ''}`}>
      {label && <label className="form-label">{label}</label>}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {opts.map(([code, lbl]) => {
          const active = String(value) === String(code)
          return (
            <button key={code} type="button" onClick={() => onChange(code)}
              className="pp-seg"
              style={{
                padding: '0.4rem 0.7rem', borderRadius: 'var(--radius)', cursor: 'pointer',
                fontSize: '0.78rem', fontWeight: 600,
                border: `1px solid ${active ? 'var(--primary)' : 'var(--border)'}`,
                background: active ? 'var(--primary-50)' : 'transparent',
                color: active ? 'var(--primary)' : 'var(--text-secondary)',
              }}>
              {lbl}
            </button>
          )
        })}
      </div>
      {hint && <div className="text-xs text-muted" style={{ marginTop: 2 }}>{hint}</div>}
    </div>
  )
}, sameProps)

export const CheckField = memo(function CheckField({ label, checked, onChange }) {
  return (
    <div className="form-group">
      <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
        <input type="checkbox" checked={!!checked} onChange={e => onChange(e.target.checked)} />
        {label}
      </label>
    </div>
  )
}, sameProps)

export const SliderField = memo(function SliderField({ label, value, onChange, min = 0, max = 1, step = 0.05, format, span }) {
  return (
    <div className={`form-group ${span ? 'span-2' : ''}`}>
      {label && <label className="form-label">{label}</label>}
      <input type="range" min={min} max={max} step={step} value={value || 0} onChange={e => onChange(e.target.value)} style={{ width: '100%' }} />
      <div className="text-xs text-muted text-right">{format ? format(value) : value}</div>
    </div>
  )
}, sameProps)

/** Section gập/mở — gom trường nâng cao, mặc định thu gọn */
export function CollapsibleSection({ title, badge, hint, defaultOpen = false, accent, grid = true, children }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="card pp-section" style={{ overflow: 'visible', ...(accent ? { borderColor: accent } : {}) }}>
      <button
        type="button" onClick={() => setOpen(o => !o)}
        style={{ width: '100%', background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, textAlign: 'left', padding: 0, color: 'var(--text-primary)' }}
      >
        <span style={{ display: 'inline-flex', transform: open ? 'rotate(0deg)' : 'rotate(-90deg)', transition: 'transform .15s' }}>
          {icon('chevronDown', 16)}
        </span>
        <span style={{ fontWeight: 700, fontSize: '0.92rem' }}>{title}</span>
        {badge && <span className="badge" style={{ fontSize: '0.62rem', background: 'var(--surface-2)', color: 'var(--text-muted)' }}>{badge}</span>}
        {hint && <span className="text-xs text-muted" style={{ marginLeft: 'auto' }}>{hint}</span>}
        {!open && !hint && <span className="text-xs text-muted" style={{ marginLeft: 'auto' }}>Bấm để mở</span>}
      </button>
      {open && (grid ? <div className="form-grid" style={{ marginTop: '0.75rem' }}>{children}</div> : <div style={{ marginTop: '0.75rem' }}>{children}</div>)}
    </div>
  )
}

export function OpenSection({ title, hint, accent, grid = true, children }) {
  return (
    <div className="card pp-section" style={{ overflow: 'visible', ...(accent ? { borderColor: accent } : {}) }}>
      <div className="card-header">
        <span>{title}</span>
        {hint && <span className="text-xs text-muted" style={{ marginLeft: 'auto' }}>{hint}</span>}
      </div>
      {grid ? <div className="form-grid">{children}</div> : children}
    </div>
  )
}

/** Trạng thái IoT tự điền theo địa chỉ */
export function IotAutoNote({ data }) {
  if (!data) return null
  const live = data.tier === 'live_area'
  const isDb = data.tier === 'db_ward' || data.tier === 'db_district'
  const color = live ? '#06d6a0' : isDb ? '#0099ff' : '#f59e0b'
  const r = data.readings || {}
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', padding: '0.5rem 0.75rem', borderRadius: 8, fontSize: '0.74rem', background: `${color}12`, border: `1px solid ${color}40` }}>
      <span style={{ color, fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 5 }}>{icon('radio', 13, '', color)} IoT tự điền</span>
      <span style={{ color: 'var(--text-muted)' }}>{data.tier_label}</span>
      {data.node_count > 0 && <span style={{ color: 'var(--text-muted)' }}>· {data.node_count} node{data.nearest_node_m != null ? ` · gần nhất ${data.nearest_node_m}m` : ''}</span>}
      {data.geocoded && <span style={{ color, fontWeight: 600 }}>· đã tự điền tọa độ</span>}
      <span style={{ marginLeft: 'auto', color: 'var(--text-secondary)' }}>
        {r.noise_level != null ? `Ồn ${r.noise_level}dB` : ''}{r.temperature != null ? ` · ${r.temperature}°C` : ''}{r.humidity != null ? ` · ${r.humidity}%` : ''}
      </span>
    </div>
  )
}

/** Thanh hoàn thiện hồ sơ */
export const FormProgress = memo(function FormProgress({ form, ignore = [] }) {
  const keys = Object.keys(form).filter(k => !ignore.includes(k) && k !== 'asset_type' && k !== 'asset_subtype')
  const filled = keys.filter(k => {
    const v = form[k]
    if (typeof v === 'boolean') return true
    return v !== '' && v != null
  }).length
  const total = keys.length || 1
  const pct = Math.round((filled / total) * 100)
  const color = pct >= 75 ? 'var(--success)' : pct >= 45 ? 'var(--warning)' : 'var(--danger)'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '0.5rem 0.75rem', background: 'var(--surface-2)', borderRadius: 8 }}>
      <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
        Hồ sơ: <strong style={{ color: 'var(--text-primary)' }}>{filled}/{total}</strong> trường
      </span>
      <div style={{ flex: 1, height: 7, background: 'var(--surface)', borderRadius: 999, overflow: 'hidden', border: '1px solid var(--border)' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, transition: 'width .3s' }} />
      </div>
      <span style={{ fontSize: '0.72rem', fontWeight: 700, color }}>{pct}%</span>
    </div>
  )
})
