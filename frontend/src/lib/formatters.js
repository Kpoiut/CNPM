// Shared formatters and utilities - single source of truth
// Import from here in all pages

export const API_BASE = '/api'
export const V2_BASE = '/api/v2'

// Evidence Tier — E5 is highest reliability, E1 is lowest
export const EVIDENCE_TIERS = {
  E5: { label: 'E5 - Chứng cứ cấp 5 (Rất cao)', color: '#06d6a0', bg: 'rgba(6,214,160,0.08)', weight: 3.0 },
  E4: { label: 'E4 - Chứng cứ cấp 4 (Cao)', color: '#00b4d8', bg: 'rgba(0,180,216,0.08)', weight: 2.0 },
  E3: { label: 'E3 - Chứng cứ cấp 3 (Trung bình)', color: '#38bdf8', bg: 'rgba(56,189,248,0.08)', weight: 1.0 },
  E2: { label: 'E2 - Chứng cứ cấp 2 (Thấp)', color: '#f59e0b', bg: 'rgba(245,158,11,0.08)', weight: 0.5 },
  E1: { label: 'E1 - Chứng cứ cấp 1 (Rất thấp)', color: '#ef233c', bg: 'rgba(239,35,60,0.08)', weight: 0.15 },
}
export const EVIDENCE_TIER_KEYS = ['E5', 'E4', 'E3', 'E2', 'E1']

export const TIER_COLORS = {
  E5: '#06d6a0', E4: '#00b4d8', E3: '#38bdf8', E2: '#f59e0b', E1: '#ef233c',
}
export const EVIDENCE_LABELS = {
  E5: 'E5 - Rất cao', E4: 'E4 - Cao', E3: 'E3 - Trung bình', E2: 'E2 - Thấp', E1: 'E1 - Rất thấp',
}
export const EVIDENCE_WEIGHTS = {
  E5: 3.0, E4: 2.0, E3: 1.0, E2: 0.5, E1: 0.15,
}
export const GRADE_COLORS = {
  A: '#06d6a0', B: '#0099ff', C: '#f59e0b', D: '#ef233c',
}

// Property types
export const PROPERTY_ICONS = {
  house:      'house',
  apartment:  'apartment',
  land:       'land',
  townhouse:  'townhouse',
  villa:      'villa',
}
export const PROPERTY_TYPE_COLORS = {
  house: '#f59e0b', apartment: '#3b82f6', land: '#22c55e',
  townhouse: '#8b5cf6', villa: '#ec4899',
}
export const PIE_CHART_COLORS = [
  '#4f46e5', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#0ea5e9', '#ec4899', '#6366f1',
]

// Price ranges
export const PRICE_RANGES = [
  { name: '< 1 ty',    min: 0,          max: 1e9 },
  { name: '1-2 ty',   min: 1e9,        max: 2e9 },
  { name: '2-3 ty',   min: 2e9,        max: 3e9 },
  { name: '3-5 ty',   min: 3e9,        max: 5e9 },
  { name: '5-10 ty',  min: 5e9,        max: 1e10 },
  { name: '> 10 ty',  min: 1e10,       max: Infinity },
]

// Pagination defaults
export const PAGE_SIZES = {
  default: 20, table: 20, map: 1000,
  dashboard: 2000, recordExplorer: 5000,
  selfCollected: 100, dataSources: 5000,
  dataQuality: 500, researchLab: 50,
}

// Price formatters
function _nf(v) {
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(v)
}

export function formatVnd(v) {
  if (v == null || v === '') return '—'
  const n = Number(v)
  if (isNaN(n)) return '—'
  return _nf(n).replace('₫', '').trim()
}

export function formatVndShort(v) {
  if (v == null || v === '') return '—'
  const n = Number(v)
  if (isNaN(n)) return '—'
  if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B'
  if (n >= 1e6) return (n / 1e6).toFixed(0) + 'M'
  if (n >= 1e3) return (n / 1e3).toFixed(0) + 'K'
  return String(n)
}

export function formatPct(v, decimals = 1) {
  if (v == null) return '—'
  const sign = v >= 0 ? '+' : ''
  return sign + (Number(v) * 100).toFixed(decimals) + '%'
}

// Date formatters
export function formatDate(v) {
  if (!v) return '—'
  const d = new Date(v)
  if (isNaN(d.getTime())) return String(v)
  return new Intl.DateTimeFormat('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' }).format(d)
}

export function formatDateTime(v) {
  if (!v) return '—'
  const d = new Date(v)
  if (isNaN(d.getTime())) return String(v)
  return new Intl.DateTimeFormat('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }).format(d)
}

export function formatRelativeTime(v) {
  if (!v) return '—'
  const d = new Date(v)
  if (isNaN(d.getTime())) return String(v)
  const diff = Date.now() - d.getTime()
  const m = Math.floor(diff / 60000)
  const h = Math.floor(diff / 3600000)
  const d2 = Math.floor(diff / 86400000)
  if (m < 1) return 'vua xong'
  if (m < 60) return m + 'p truoc'
  if (h < 24) return h + 'h truoc'
  if (d2 < 7) return d2 + 'ngay truoc'
  return formatDate(v)
}

// Badge helpers
export function evidenceTierBadge(tier) {
  const t = tier?.toUpperCase()
  if (!t || !EVIDENCE_TIERS[t]) return null
  const cfg = EVIDENCE_TIERS[t]
  return { label: cfg.label, color: cfg.color, bg: cfg.bg }
}

export function confidenceGradeBadge(grade) {
  const g = String(grade).toUpperCase()
  const colors = { A: '#06d6a0', B: '#0099ff', C: '#f59e0b', D: '#ef233c' }
  const bgs   = { A: 'rgba(6,214,160,0.08)', B: 'rgba(0,153,255,0.08)', C: 'rgba(245,158,11,0.08)', D: 'rgba(239,35,60,0.08)' }
  return { color: colors[g] || '#888', bg: bgs[g] || 'rgba(136,136,136,0.08)' }
}
