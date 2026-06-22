import React, { useState, useEffect } from 'react'
import { BarChart3, TrendingUp, Target, BarChart, PieChart, Activity } from 'lucide-react'

const API_BASE = '/api'

const good = '#22c55e'
const warn = '#f59e0b'
const bad = '#ef4444'
const blue = '#3b82f6'
const violet = '#8b5cf6'

function cleanFeatureName(name = '') {
  return String(name)
    .replace(/_norm|_feature|_score/g, '')
    .replace(/_/g, ' ')
    .replace(/\bppm\b/gi, 'giá/m²')
    .replace(/\bm2\b/gi, 'm²')
    .trim()
}

function fmtPct(v, digits = 1) {
  return Number.isFinite(Number(v)) ? `${Number(v).toFixed(digits)}%` : '—'
}

function fmtMoney(v) {
  const n = Number(v)
  if (!Number.isFinite(n)) return '—'
  if (Math.abs(n) >= 1e9) return `${(n / 1e9).toFixed(2)} tỷ`
  if (Math.abs(n) >= 1e6) return `${(n / 1e6).toFixed(0)} triệu`
  return n.toLocaleString('vi-VN')
}

function clamp01(v) {
  return Math.max(0, Math.min(1, Number.isFinite(v) ? v : 0))
}

function MiniNote({ children, tone = 'info' }) {
  const color = tone === 'bad' ? bad : tone === 'warn' ? warn : tone === 'good' ? good : blue
  return (
    <div style={{
      border: `1px solid ${color}33`,
      background: `${color}10`,
      color: 'var(--text-secondary)',
      borderRadius: 8,
      padding: '0.55rem 0.7rem',
      fontSize: '0.74rem',
      lineHeight: 1.45,
    }}>
      {children}
    </div>
  )
}

function EmptyChart({ label = 'Không có dữ liệu', height = 220 }) {
  return (
    <div style={{
      height,
      border: '1px dashed var(--border)',
      borderRadius: 8,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: 'var(--text-muted)',
      fontSize: '0.8rem',
    }}>
      {label}
    </div>
  )
}

function FeatureImportanceChart({ data, topN = 15, height = 300, showLabels = false }) {
  if (!data?.length) return <EmptyChart height={height} label="Chưa có dữ liệu SHAP importance" />
  const rows = data.slice(0, topN).map(item => ({
    name: cleanFeatureName(item.feature),
    raw: item.feature,
    value: Math.abs(Number(item.importance || 0)),
  }))
  const max = Math.max(...rows.map(r => r.value), 1)
  return (
    <div style={{ minHeight: height, display: 'grid', gap: 7 }}>
      {rows.map((row, idx) => {
        const pct = clamp01(row.value / max)
        return (
          <div key={row.raw || idx} style={{ display: 'grid', gridTemplateColumns: showLabels ? '180px 1fr 74px' : '130px 1fr 64px', gap: 10, alignItems: 'center' }}>
            <div title={row.raw} style={{ color: 'var(--text-secondary)', fontSize: '0.73rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {row.name || `Feature ${idx + 1}`}
            </div>
            <div style={{ height: 10, background: 'rgba(59,130,246,0.12)', borderRadius: 999, overflow: 'hidden' }}>
              <div style={{
                width: `${Math.max(4, pct * 100)}%`,
                height: '100%',
                borderRadius: 999,
                background: idx < 3 ? 'linear-gradient(90deg,#38bdf8,#22c55e)' : 'linear-gradient(90deg,#60a5fa,#3b82f6)',
              }} />
            </div>
            <div style={{ color: idx < 3 ? good : 'var(--text-muted)', fontSize: '0.7rem', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
              {row.value.toExponential(2)}
            </div>
          </div>
        )
      })}
      <MiniNote tone="info">
        Thanh dài hơn nghĩa là biến có ảnh hưởng mạnh hơn tới dự đoán. Top 3 nên được đọc trước khi xem residual.
      </MiniNote>
    </div>
  )
}

function CalibrationChart({ data, height = 300, showDetails = false }) {
  if (!data?.length) return <EmptyChart height={height} label="Chưa có dữ liệu calibration" />
  return (
    <div style={{ minHeight: height, display: 'grid', gap: 10 }}>
      {data.map((b, idx) => {
        const predicted = Number(b.predicted_coverage_pct || 0)
        const actual = Number(b.actual_coverage_pct || 0)
        const gap = actual - predicted
        const tone = Math.abs(gap) <= 5 ? good : Math.abs(gap) <= 15 ? warn : bad
        return (
          <div key={b.band || idx} style={{ border: '1px solid var(--border)', borderRadius: 8, padding: '0.7rem', background: 'rgba(15,23,42,0.18)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, marginBottom: 7 }}>
              <strong style={{ color: 'var(--text-primary)', fontSize: '0.78rem' }}>Band {b.band}</strong>
              <span style={{ color: tone, fontSize: '0.72rem', fontWeight: 700 }}>
                Lệch {gap >= 0 ? '+' : ''}{gap.toFixed(1)}%
              </span>
            </div>
            <div style={{ display: 'grid', gap: 6 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '82px 1fr 48px', gap: 8, alignItems: 'center' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Dự kiến</span>
                <div style={{ height: 8, background: 'rgba(59,130,246,0.12)', borderRadius: 999 }}>
                  <div style={{ width: `${Math.min(100, predicted)}%`, height: '100%', borderRadius: 999, background: blue }} />
                </div>
                <span style={{ fontSize: '0.7rem', textAlign: 'right' }}>{fmtPct(predicted)}</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '82px 1fr 48px', gap: 8, alignItems: 'center' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Thực tế</span>
                <div style={{ height: 8, background: 'rgba(34,197,94,0.12)', borderRadius: 999 }}>
                  <div style={{ width: `${Math.min(100, actual)}%`, height: '100%', borderRadius: 999, background: good }} />
                </div>
                <span style={{ fontSize: '0.7rem', textAlign: 'right' }}>{fmtPct(actual)}</span>
              </div>
            </div>
            {showDetails && (
              <div style={{ marginTop: 8, color: 'var(--text-muted)', fontSize: '0.68rem', display: 'flex', gap: 14, flexWrap: 'wrap' }}>
                <span>Mẫu: {b.n_samples ?? '—'}</span>
                <span>Độ rộng khoảng: {fmtMoney(b.mean_interval_width)}</span>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function ModelComparisonChart({ data, height = 300, showAllMetrics = false }) {
  if (!data?.length) return <EmptyChart height={height} label="Chưa có dữ liệu so sánh model" />
  const rows = data.map(m => ({
    name: String(m.model_name || 'Model').replace(/ReliabilityAwareGradientBoosting/g, 'ReliabilityGB').replace(/QualityWeightedRandomForest/g, 'QW-RF').replace(/ConfidenceWeightedXGBoost/g, 'CW-XGB'),
    mape: Number(m.mape_pct || 0),
    r2: Number(m.r2 || 0),
    mae: Number(m.mae_vnd || 0),
    n: m.n_test,
    isServing: Boolean(m.is_serving),
    isLatest: Boolean(m.is_latest),
    isBestVerified: Boolean(m.is_best_verified),
  }))
  const maxMape = Math.max(...rows.map(r => r.mape), 1)
  return (
    <div style={{ minHeight: height, display: 'grid', gap: 10 }}>
      {rows.map((r, idx) => {
        const tone = r.mape < 15 ? good : r.mape < 25 ? warn : bad
        const badges = [
          r.isServing ? 'Serving' : null,
          r.isLatest ? 'Latest' : null,
          r.isBestVerified ? 'Best MAPE' : null,
        ].filter(Boolean)
        return (
          <div key={idx} style={{ display: 'grid', gridTemplateColumns: showAllMetrics ? '190px 1fr 170px' : '150px 1fr 62px', gap: 10, alignItems: 'center' }}>
            <div title={r.name} style={{ color: 'var(--text-secondary)', fontSize: '0.73rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              <span>{r.name}</span>
              {badges.length > 0 && (
                <span style={{ marginLeft: 6, color: r.isServing ? good : 'var(--text-muted)', fontWeight: 800 }}>
                  {badges.join(' · ')}
                </span>
              )}
            </div>
            <div style={{ height: 28, background: 'rgba(239,68,68,0.1)', borderRadius: 6, overflow: 'hidden', position: 'relative' }}>
              <div style={{ width: `${Math.max(4, (r.mape / maxMape) * 100)}%`, height: '100%', background: tone, opacity: 0.78 }} />
              <span style={{ position: 'absolute', left: 8, top: 5, fontSize: '0.68rem', color: '#fff', fontWeight: 700 }}>MAPE {fmtPct(r.mape)}</span>
            </div>
            {showAllMetrics ? (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.68rem', display: 'grid', gap: 2 }}>
                <span>R²: {(r.r2 || 0).toFixed(3)}</span>
                <span>MAE: {fmtMoney(r.mae)}</span>
                <span>n={r.n ?? '—'}</span>
              </div>
            ) : (
              <div style={{ color: tone, fontSize: '0.7rem', fontWeight: 700, textAlign: 'right' }}>{fmtPct(r.mape)}</div>
            )}
          </div>
        )
      })}
      <MiniNote tone={rows[0]?.mape > 25 ? 'bad' : 'info'}>
        MAPE thấp hơn là tốt hơn. Badge Serving là model đang được pin để phục vụ production; Latest là lần retrain mới nhất; Best MAPE là snapshot thấp nhất theo metadata.
      </MiniNote>
    </div>
  )
}

function ResidualAnalysisChart({ data, height = 300, fullScatter = false }) {
  const points = data?.scatter_sample || []
  if (!points.length) return <EmptyChart height={height} label="Chưa có residual sample" />
  if (fullScatter) {
    const sample = points.slice(0, 220)
    const maxActual = Math.max(...sample.map(p => Number(p.actual_price || 0)), 1)
    const maxPred = Math.max(...sample.map(p => Number(p.predicted_price || 0)), 1)
    return (
      <div style={{ minHeight: height }}>
        <svg viewBox="0 0 640 340" width="100%" height={height - 30} role="img" aria-label="Actual vs predicted scatter" style={{ background: 'rgba(15,23,42,0.16)', borderRadius: 8 }}>
          <line x1="48" y1="300" x2="612" y2="300" stroke="#334155" />
          <line x1="48" y1="28" x2="48" y2="300" stroke="#334155" />
          <line x1="48" y1="300" x2="612" y2="28" stroke={violet} strokeDasharray="5 5" opacity="0.75" />
          {sample.map((p, idx) => {
            const x = 48 + clamp01(Number(p.actual_price || 0) / maxActual) * 564
            const y = 300 - clamp01(Number(p.predicted_price || 0) / maxPred) * 272
            const abs = Math.abs(Number(p.residual_pct || 0))
            const fill = abs < 15 ? good : abs < 30 ? warn : bad
            return <circle key={idx} cx={x} cy={y} r={abs > 50 ? 4 : 3} fill={fill} opacity="0.7" />
          })}
          <text x="48" y="326" fill="#94a3b8" fontSize="12">Actual</text>
          <text x="14" y="28" fill="#94a3b8" fontSize="12">Pred</text>
        </svg>
        <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <span style={{ color: good }}>● Sai số thấp</span><span style={{ color: warn }}>● Cần xem lại</span><span style={{ color: bad }}>● Outlier</span>
        </div>
      </div>
    )
  }
  const sorted = points.slice().sort((a, b) => Math.abs(Number(b.residual_pct || 0)) - Math.abs(Number(a.residual_pct || 0))).slice(0, 14)
  const max = Math.max(...sorted.map(p => Math.abs(Number(p.residual_pct || 0))), 1)
  return (
    <div style={{ minHeight: height, display: 'grid', gap: 7 }}>
      {sorted.map((p, idx) => {
        const residual = Number(p.residual_pct || 0)
        const abs = Math.abs(residual)
        const tone = abs < 15 ? good : abs < 30 ? warn : bad
        return (
          <div key={p.id || idx} style={{ display: 'grid', gridTemplateColumns: '90px 1fr 74px', gap: 9, alignItems: 'center' }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>#{p.id} {p.district}</div>
            <div style={{ height: 10, borderRadius: 999, background: 'rgba(148,163,184,0.12)', overflow: 'hidden' }}>
              <div style={{ width: `${Math.max(4, (abs / max) * 100)}%`, height: '100%', background: tone, borderRadius: 999 }} />
            </div>
            <div style={{ color: tone, fontSize: '0.7rem', fontWeight: 700, textAlign: 'right' }}>{residual > 0 ? '+' : ''}{fmtPct(residual)}</div>
          </div>
        )
      })}
      <MiniNote tone="warn">Danh sách này ưu tiên các mẫu sai số lớn để dễ nhìn nguyên nhân, không phải bảng raw toàn bộ.</MiniNote>
    </div>
  )
}

function PredictionDistributionChart({ data, height = 300 }) {
  const points = data?.scatter_sample || []
  if (!points.length) return <EmptyChart height={height} label="Chưa có phân phối lỗi" />
  const residuals = points.map(p => Number(p.residual_pct || 0)).sort((a, b) => a - b)
  const edges = [-100, -50, -30, -20, -10, -5, 5, 10, 20, 30, 50, 100]
  const bins = edges.slice(0, -1).map((edge, i) => {
    const next = edges[i + 1]
    return { label: `${edge}%–${next}%`, mid: (edge + next) / 2, count: residuals.filter(r => r >= edge && r < next).length }
  })
  bins.push({ label: '>=100%', mid: 120, count: residuals.filter(r => r >= 100).length })
  const max = Math.max(...bins.map(b => b.count), 1)
  const median = residuals[Math.floor(residuals.length / 2)]
  const mean = residuals.reduce((a, b) => a + b, 0) / residuals.length
  return (
    <div style={{ minHeight: height, display: 'grid', gap: 10 }}>
      <div style={{ display: 'flex', gap: 16, color: 'var(--text-muted)', fontSize: '0.72rem', flexWrap: 'wrap' }}>
        <span>Median: <strong style={{ color: 'var(--text-primary)' }}>{fmtPct(median)}</strong></span>
        <span>Mean: <strong style={{ color: 'var(--text-primary)' }}>{fmtPct(mean)}</strong></span>
        <span>Mẫu: <strong style={{ color: 'var(--text-primary)' }}>{residuals.length}</strong></span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${bins.length}, minmax(26px, 1fr))`, gap: 6, alignItems: 'end', height: Math.max(160, height - 95) }}>
        {bins.map((b, idx) => {
          const tone = Math.abs(b.mid) <= 5 ? good : Math.abs(b.mid) <= 20 ? warn : bad
          return (
            <div key={idx} title={`${b.label}: ${b.count}`} style={{ display: 'grid', alignItems: 'end', height: '100%' }}>
              <div style={{ minHeight: 3, height: `${Math.max(3, (b.count / max) * 100)}%`, background: tone, borderRadius: '5px 5px 0 0', opacity: 0.76 }} />
            </div>
          )
        })}
      </div>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', color: 'var(--text-muted)', fontSize: '0.66rem' }}>
        <span style={{ color: good }}>■ ±5% tốt</span><span style={{ color: warn }}>■ ±5–20% chấp nhận</span><span style={{ color: bad }}>■ &gt;±20% lỗi cao</span>
      </div>
    </div>
  )
}

function SHAPBeeswarmChart({ data, height = 220 }) {
  if (!data?.length) return <EmptyChart height={height} label="Chưa có beeswarm SHAP" />
  const rows = data.slice(0, 15).map((f, idx) => {
    const vals = (f.shap_values || []).map(Number).filter(Number.isFinite)
    const min = vals.length ? Math.min(...vals) : 0
    const max = vals.length ? Math.max(...vals) : 0
    const avg = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0
    return { id: f.feature || idx, name: cleanFeatureName(f.feature), min, max, avg }
  })
  const span = Math.max(...rows.map(r => Math.max(Math.abs(r.min), Math.abs(r.max))), 1)
  return (
    <div style={{ minHeight: height, display: 'grid', gap: 8 }}>
      {rows.map(r => {
        const left = 50 + (r.min / span) * 45
        const right = 50 + (r.max / span) * 45
        const avg = 50 + (r.avg / span) * 45
        return (
          <div key={r.id} style={{ display: 'grid', gridTemplateColumns: '155px 1fr 58px', gap: 10, alignItems: 'center' }}>
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.7rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.name}</div>
            <div style={{ height: 18, position: 'relative', background: 'linear-gradient(90deg,rgba(59,130,246,.08),rgba(148,163,184,.12),rgba(239,68,68,.08))', borderRadius: 999 }}>
              <div style={{ position: 'absolute', left: '50%', top: 2, bottom: 2, width: 1, background: '#64748b' }} />
              <div style={{ position: 'absolute', left: `${Math.min(left, right)}%`, width: `${Math.max(2, Math.abs(right - left))}%`, top: 7, height: 4, background: violet, borderRadius: 999 }} />
              <div style={{ position: 'absolute', left: `${avg}%`, top: 4, width: 10, height: 10, marginLeft: -5, borderRadius: '50%', background: r.avg >= 0 ? bad : blue }} />
            </div>
            <div style={{ color: r.avg >= 0 ? bad : blue, fontSize: '0.68rem', textAlign: 'right' }}>{r.avg.toFixed(3)}</div>
          </div>
        )
      })}
      <MiniNote tone="info">Điểm đỏ kéo giá lên, điểm xanh kéo giá xuống; đường tím là khoảng dao động SHAP của từng biến.</MiniNote>
    </div>
  )
}

function SHAPWaterfallChart({ data, height = 400 }) {
  if (!data?.steps?.length) return <EmptyChart height={height} label="Nhập Property ID để xem waterfall" />
  const rows = data.steps.slice(0, 16).map(step => ({
    name: cleanFeatureName(step.feature),
    contribution: Number(step.contribution || 0),
    value: step.value,
  }))
  const max = Math.max(...rows.map(r => Math.abs(r.contribution)), 1)
  return (
    <div style={{ minHeight: height, display: 'grid', gap: 9 }}>
      <div style={{ display: 'flex', gap: 16, color: 'var(--text-muted)', fontSize: '0.72rem', flexWrap: 'wrap' }}>
        <span>Base: <strong style={{ color: 'var(--text-primary)' }}>{fmtMoney(data.base_value)}</strong></span>
        <span>Dự đoán: <strong style={{ color: 'var(--primary)' }}>{data.predicted_price_vnd || fmtMoney(data.final_value)}</strong></span>
      </div>
      {rows.map((r, idx) => {
        const tone = r.contribution >= 0 ? good : bad
        return (
          <div key={`${r.name}-${idx}`} style={{ display: 'grid', gridTemplateColumns: '160px 1fr 96px', gap: 10, alignItems: 'center' }}>
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.72rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.name}</div>
            <div style={{ height: 12, background: 'rgba(148,163,184,0.12)', borderRadius: 999, overflow: 'hidden' }}>
              <div style={{ width: `${Math.max(4, (Math.abs(r.contribution) / max) * 100)}%`, height: '100%', marginLeft: r.contribution < 0 ? 'auto' : 0, background: tone, borderRadius: 999 }} />
            </div>
            <div style={{ color: tone, textAlign: 'right', fontSize: '0.7rem', fontWeight: 700 }}>
              {r.contribution >= 0 ? '+' : ''}{fmtMoney(r.contribution)}
            </div>
          </div>
        )
      })}
    </div>
  )
}

function MetricCard({ label, value, unit, color, sublabel }) {
  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius)',
      padding: '0.875rem 1rem',
      display: 'flex',
      flexDirection: 'column',
      gap: '0.2rem',
    }}>
      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {label}
      </span>
      <span style={{ fontSize: '1.4rem', fontWeight: 700, color: color || 'var(--text-primary)', lineHeight: 1.2 }}>
        {value ?? '—'}
      </span>
      {unit && <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{unit}</span>}
      {sublabel && <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)', opacity: 0.7 }}>{sublabel}</span>}
    </div>
  )
}

function LoadingPanel({ height = 300 }) {
  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius)',
      height,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    }}>
      <div className="spinner" style={{ width: 32, height: 32 }} />
    </div>
  )
}

function ErrorPanel({ message }) {
  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius)',
      height: 300,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      flexDirection: 'column',
      gap: '0.5rem',
      color: 'var(--text-muted)',
      fontSize: '0.875rem',
    }}>
      <Activity size={24} style={{ opacity: 0.5 }} />
      <span>{message || 'No data available'}</span>
    </div>
  )
}

export default function ExplainabilityDashboard() {
  const [globalData, setGlobalData] = useState(null)
  const [residualsData, setResidualsData] = useState(null)
  const [calibrationData, setCalibrationData] = useState(null)
  const [modelCompareData, setModelCompareData] = useState(null)
  const [selectedProperty, setSelectedProperty] = useState(null)
  const [waterfallData, setWaterfallData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('overview')
  const [modelVersion, setModelVersion] = useState('—')

  useEffect(() => {
    const loadData = async () => {
      const requests = await Promise.allSettled([
        fetch(`${API_BASE}/v2/explain/global`),
        fetch(`${API_BASE}/v2/explain/residuals`),
        fetch(`${API_BASE}/v2/explain/calibration`),
        fetch(`${API_BASE}/v2/explain/model-compare`),
      ])
      const [globalRes, residualsRes, calibRes, compareRes] = requests.map(result =>
        result.status === 'fulfilled' ? result.value : null
      )

      if (globalRes?.ok) {
        const g = await globalRes.json()
        setGlobalData(g)
        setModelVersion(g.model_version?.slice(0, 16) || '—')
      }
      if (residualsRes?.ok) setResidualsData(await residualsRes.json())
      if (calibRes?.ok) setCalibrationData(await calibRes.json())
      if (compareRes?.ok) setModelCompareData(await compareRes.json())
      setLoading(false)
    }
    loadData()
  }, [])

  const loadWaterfall = async (propertyId) => {
    try {
      const res = await fetch(`${API_BASE}/v2/explain/prediction/${propertyId}`)
      if (res.ok) {
        const data = await res.json()
        setWaterfallData(data)
        setSelectedProperty(propertyId)
      }
    } catch (e) {
      console.error('Waterfall load error:', e)
    }
  }

  if (loading) {
    return (
      <div style={{ padding: '2rem', maxWidth: 1400, margin: '0 auto' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
          {[...Array(6)].map((_, i) => <LoadingPanel key={i} height={80} />)}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
          {[...Array(6)].map((_, i) => <LoadingPanel key={i} />)}
        </div>
      </div>
    )
  }

  const officialTestMape = residualsData?.official_test_mape_pct
  const officialTestMae = residualsData?.official_test_mae_vnd
  const officialTestR2 = residualsData?.official_test_r2
  const officialTestN = residualsData?.official_test_n
  const mape = residualsData?.live_residual_mape_pct ?? residualsData?.overall_mape_pct
  const mapeRaw = residualsData?.raw_mape_pct             // Raw MAPE (all records — debug only)
  const wape = residualsData?.overall_wape_pct            // WAPE
  const mdape = residualsData?.overall_mdape_pct          // MdAPE
  const nOfficial = residualsData?.n_official
  const nRaw = residualsData?.raw_n
  const nOutliers = residualsData?.n_outliers
  const priceBins = residualsData?.price_bins || []

  return (
    <div style={{ padding: '1.5rem', maxWidth: 1600, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
          <BarChart3 size={24} style={{ color: 'var(--primary)' }} />
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, margin: 0 }}>
            Model Explainability Center
          </h1>
          <span style={{
            background: 'var(--primary-bg)',
            color: 'var(--primary)',
            padding: '0.2rem 0.6rem',
            borderRadius: '20px',
            fontSize: '0.75rem',
            fontFamily: 'monospace',
          }}>
            v{modelVersion}
          </span>
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', margin: 0 }}>
          SHAP Transparency Report — Feature attribution, calibration, and model performance analysis
        </p>
      </div>

      {/* Metrics Strip */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem', marginBottom: '1.5rem' }}>
        <MetricCard label="Official Test MAPE" value={officialTestMape ? `${officialTestMape.toFixed(1)}%` : '—'} sublabel={`holdout · n=${officialTestN || '—'}`} color={officialTestMape < 20 ? '#22c55e' : officialTestMape < 30 ? '#f59e0b' : '#ef4444'} />
        <MetricCard label="Live DB MAPE" value={mape ? `${mape.toFixed(1)}%` : '—'} sublabel={`current DB ≥500M · n=${nOfficial}`} color="#38bdf8" />
        <MetricCard label="WAPE" value={wape ? `${wape.toFixed(1)}%` : '—'} sublabel="weighted" color={wape < 15 ? '#22c55e' : wape < 25 ? '#f59e0b' : '#ef4444'} />
        <MetricCard label="MdAPE" value={mdape ? `${mdape.toFixed(1)}%` : '—'} sublabel="median" color={mdape < 10 ? '#22c55e' : mdape < 20 ? '#f59e0b' : '#ef4444'} />
        <MetricCard label="Official Test R2" value={officialTestR2 ? officialTestR2.toFixed(3) : '—'} color={officialTestR2 > 0.7 ? '#22c55e' : '#f59e0b'} />
        <MetricCard label="Official Test MAE" value={officialTestMae ? `${(officialTestMae / 1e9).toFixed(2)}B` : '—'} unit="VND" />
        <MetricCard label="MAPE (Raw)" value={mapeRaw ? `${mapeRaw.toFixed(1)}%` : '—'} sublabel={`all n=${nRaw} · debug`} color="#64748b" />
      </div>

      {/* Tab Navigation */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', borderBottom: '1px solid var(--border)', paddingBottom: '0.5rem' }}>
        {['overview', 'shap', 'residuals', 'calibration'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '0.4rem 1rem',
              borderRadius: 'var(--radius)',
              border: 'none',
              cursor: 'pointer',
              fontSize: '0.8rem',
              fontWeight: activeTab === tab ? 600 : 400,
              background: activeTab === tab ? 'var(--primary-bg)' : 'transparent',
              color: activeTab === tab ? 'var(--primary)' : 'var(--text-secondary)',
              transition: 'all 150ms',
            }}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <TrendingUp size={16} style={{ color: 'var(--primary)' }} />
                <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: 0 }}>Feature Importance</h3>
              </div>
              {!globalData ? <ErrorPanel message="SHAP data not available" />
                : <FeatureImportanceChart data={globalData.feature_importance} topN={15} height={350} />}
            </div>

            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <Target size={16} style={{ color: 'var(--primary)' }} />
                <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: 0 }}>Calibration by Band</h3>
              </div>
              {!calibrationData ? <ErrorPanel message="Calibration data not available" />
                : <CalibrationChart data={calibrationData.bands} height={350} />}
            </div>

            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <BarChart size={16} style={{ color: 'var(--primary)' }} />
                <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: 0 }}>Model MAPE Comparison</h3>
              </div>
              {!modelCompareData ? <ErrorPanel message="Model compare data not available" />
                : <ModelComparisonChart data={modelCompareData.models} height={350} />}
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <Activity size={16} style={{ color: 'var(--primary)' }} />
                <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: 0 }}>Residual Distribution</h3>
              </div>
              {!residualsData ? <ErrorPanel message="Residuals not available" />
                : <ResidualAnalysisChart data={residualsData} height={280} />}
            </div>

            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <PieChart size={16} style={{ color: 'var(--primary)' }} />
                <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: 0 }}>Prediction Error Distribution</h3>
              </div>
              {!residualsData ? <ErrorPanel message="Residuals not available" />
                : <PredictionDistributionChart data={residualsData} height={280} />}
            </div>
          </div>

          {/* Beeswarm */}
          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <BarChart3 size={16} style={{ color: 'var(--primary)' }} />
              <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: 0 }}>SHAP Beeswarm — Top 15 Features</h3>
            </div>
            {!globalData ? <ErrorPanel message="SHAP data not available" height={200} />
              : <SHAPBeeswarmChart data={globalData.beeswarm_data} height={220} />}
          </div>
        </>
      )}

      {/* SHAP Tab */}
      {activeTab === 'shap' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '1rem' }}>
            <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: '0 0 1rem' }}>Global Feature Importance</h3>
            {!globalData ? <ErrorPanel message="SHAP data not available" />
              : <FeatureImportanceChart data={globalData.feature_importance} topN={20} height={500} showLabels />}
          </div>
          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '1rem' }}>
            <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: '0 0 1rem' }}>Single Prediction Waterfall</h3>
            <div style={{ marginBottom: '1rem' }}>
              <input
                type="number"
                placeholder="Property ID"
                onKeyDown={e => { if (e.key === 'Enter') loadWaterfall(Number(e.target.value)) }}
                style={{
                  width: '100%',
                  padding: '0.5rem 0.75rem',
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius)',
                  color: 'var(--text-primary)',
                  fontSize: '0.875rem',
                  boxSizing: 'border-box',
                }}
              />
            </div>
            {!waterfallData ? (
              <div style={{ height: 450, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                Enter a property ID and press Enter to see SHAP waterfall
              </div>
            ) : (
              <SHAPWaterfallChart data={waterfallData} height={450} />
            )}
          </div>
        </div>
      )}

      {/* Residuals Tab */}
      {activeTab === 'residuals' && (
        <>
          {/* Methodology note */}
          <div style={{
            background: 'rgba(79,70,229,0.05)',
            border: '1px solid rgba(79,70,229,0.15)',
            borderRadius: 'var(--radius)',
            padding: '0.75rem 1rem',
            marginBottom: '1rem',
            fontSize: '0.78rem',
            color: 'var(--text-secondary)',
            lineHeight: 1.6,
          }}>
            <strong style={{ color: 'var(--primary)' }}>Metric Methodology:</strong>{' '}
            <strong>Official Test MAPE</strong> = holdout-test metric stored in active model metadata.{' '}
            <strong>Live DB MAPE</strong> = recomputed diagnostics on current PostgreSQL records with actual_price ≥ 500M.{' '}
            <strong>Raw MAPE</strong> = all records (debug only).{' '}
            <strong>WAPE</strong> = sum(|error|) / sum(actual).{' '}
            <strong>MdAPE</strong> = median(|error|/actual).{' '}
            <strong>Outliers</strong> (|error| &gt; 50%) are shown separately — NOT excluded from Live DB MAPE.
          </div>

          {/* Outlier alert */}
          {nOutliers > 0 && (
            <div style={{
              background: 'rgba(239,35,60,0.06)',
              border: '1px solid rgba(239,35,60,0.2)',
              borderRadius: 'var(--radius)',
              padding: '0.6rem 1rem',
              marginBottom: '1rem',
              fontSize: '0.78rem',
              color: '#ef233c',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}>
              <span style={{ fontSize: '1rem' }}>⚠</span>
              {nOutliers} high-residual cases (|error| &gt; 50%) — displayed in table below.
            </div>
          )}

          {/* Scatter + Histogram */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '1rem' }}>
              <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: '0 0 1rem' }}>Actual vs Predicted</h3>
              {!residualsData ? <ErrorPanel message="Residuals not available" />
                : <ResidualAnalysisChart data={residualsData} height={380} fullScatter />}
            </div>
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '1rem' }}>
              <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: '0 0 1rem' }}>Error Histogram</h3>
              {!residualsData ? <ErrorPanel message="Residuals not available" />
                : <PredictionDistributionChart data={residualsData} height={380} />}
            </div>
          </div>

          {/* Segmented MAPE by price bin */}
          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '1rem', marginBottom: '1rem' }}>
            <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: '0 0 0.75rem' }}>MAPE by Price Segment</h3>
            {!residualsData ? <ErrorPanel message="—" /> : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '0.75rem' }}>
                {priceBins.map((bin, i) => {
                  const mapeValue = Number(bin.mape_pct)
                  const tone = !Number.isFinite(mapeValue) ? 'var(--text-muted)' : mapeValue < 15 ? good : mapeValue < 25 ? warn : bad
                  const label = !Number.isFinite(mapeValue) ? 'Chưa đủ mẫu' : mapeValue < 15 ? 'Ổn định' : mapeValue < 25 ? 'Cần theo dõi' : 'Rủi ro cao'
                  return (
                    <div key={i} style={{
                      border: `1px solid ${tone}33`,
                      background: `${tone}0f`,
                      borderRadius: 8,
                      padding: '0.75rem',
                      opacity: bin.count === 0 ? 0.55 : 1,
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, marginBottom: 8 }}>
                        <strong style={{ color: 'var(--text-primary)', fontSize: '0.8rem' }}>{bin.label}</strong>
                        <span style={{ color: tone, fontSize: '0.68rem', fontWeight: 800 }}>{label}</span>
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                        <span>Mẫu: <b style={{ color: 'var(--text-primary)' }}>{bin.count}</b></span>
                        <span>MAPE: <b style={{ color: tone }}>{bin.mape_pct != null ? fmtPct(bin.mape_pct) : '—'}</b></span>
                        <span>WAPE: <b>{bin.wape_pct != null ? fmtPct(bin.wape_pct) : '—'}</b></span>
                        <span>MdAPE: <b>{bin.median_ape_pct != null ? fmtPct(bin.median_ape_pct) : '—'}</b></span>
                      </div>
                      <div style={{ height: 7, background: 'rgba(148,163,184,0.16)', borderRadius: 999, marginTop: 10, overflow: 'hidden' }}>
                        <div style={{ width: `${Math.min(100, Math.max(4, mapeValue || 0))}%`, height: '100%', background: tone, borderRadius: 999 }} />
                      </div>
                      <div style={{ marginTop: 6, color: 'var(--text-muted)', fontSize: '0.68rem' }}>
                        MAE {bin.mae_vnd != null ? fmtMoney(bin.mae_vnd) : '—'}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Outliers table */}
          {residualsData?.outliers?.length > 0 && (
            <div style={{ background: 'var(--surface)', border: '1px solid rgba(239,35,60,0.2)', borderRadius: 'var(--radius)', padding: '1rem', marginBottom: '1rem' }}>
              <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: '0 0 0.75rem', color: '#ef233c' }}>
                High Residual Cases ({nOutliers}) — NOT excluded from Official MAPE
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '0.75rem' }}>
                {residualsData.outliers.map(o => {
                  const residual = Number(o.residual_pct || 0)
                  const direction = residual > 0 ? 'Dự đoán thấp hơn thực tế' : 'Dự đoán cao hơn thực tế'
                  return (
                    <div key={o.id} style={{ border: '1px solid rgba(239,68,68,0.25)', background: 'rgba(239,68,68,0.07)', borderRadius: 8, padding: '0.75rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, marginBottom: 8 }}>
                        <strong style={{ color: 'var(--primary)', fontFamily: 'monospace' }}>#{o.id}</strong>
                        <span style={{ color: bad, fontWeight: 800, fontSize: '0.75rem' }}>{residual > 0 ? '+' : ''}{fmtPct(residual)}</span>
                      </div>
                      <div style={{ color: 'var(--text-primary)', fontSize: '0.78rem', fontWeight: 700, marginBottom: 3 }}>
                        {o.district || 'Không rõ khu vực'} · {o.property_type || 'BĐS'}
                      </div>
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.7rem', marginBottom: 8 }}>{direction}</div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                        <span>Thực tế: <b>{fmtMoney(o.actual_price)}</b></span>
                        <span>Dự đoán: <b>{fmtMoney(o.predicted_price)}</b></span>
                        <span>Sai lệch: <b style={{ color: bad }}>{fmtMoney(o.error_vnd)}</b></span>
                        <span>Mức: <b style={{ color: bad }}>Outlier</b></span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </>
      )}

      {/* Calibration Tab */}
      {activeTab === 'calibration' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '1rem' }}>
            <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: '0 0 1rem' }}>ICP by Confidence Band</h3>
            {!calibrationData ? <ErrorPanel message="Calibration data not available" />
              : <CalibrationChart data={calibrationData.bands} height={400} showDetails />}
          </div>
          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '1rem' }}>
            <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: '0 0 1rem' }}>Model Performance Across Versions</h3>
            {!modelCompareData ? <ErrorPanel message="Model compare data not available" />
              : <ModelComparisonChart data={modelCompareData.models} height={400} showAllMetrics />}
          </div>
        </div>
      )}

      {/* Footer */}
      <div style={{ marginTop: '2rem', padding: '1rem', borderTop: '1px solid var(--border)', color: 'var(--text-muted)', fontSize: '0.75rem', display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
        <span>Model Explainability Center — SHAP-based transparency report</span>
        <span>Model: {modelVersion} | Generated: {new Date().toLocaleString('vi-VN')}</span>
      </div>
    </div>
  )
}
