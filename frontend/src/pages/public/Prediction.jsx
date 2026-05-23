import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { icon } from '../../components/ui/icons'
import { PROPERTY_TYPES } from '../../constants/vnStrings'
import LandIntakeForm from '../../components/valuation/LandIntakeForm'
import ApartmentIntakeForm from '../../components/valuation/ApartmentIntakeForm'
import TownhouseIntakeForm from '../../components/valuation/TownhouseIntakeForm'
import VillaIntakeForm from '../../components/valuation/VillaIntakeForm'
import HouseIntakeForm from '../../components/valuation/HouseIntakeForm'
import ValuationResultCard from '../../components/valuation/ValuationResultCard'
import SDEVResultCard from '../../components/valuation/SDEVResultCard'
import PipelineGateTrail from '../../components/valuation/PipelineGateTrail'
import SubEnginePanel from '../../components/valuation/SubEnginePanel'
import { ImpactAnalysisPanel } from '../../components/valuation/ImpactAnalysisPanel'
import { useAuth } from '../../components/auth'
import { predictPipeline, predictSDEV } from '../../api'
import { PredictionHeroBand } from '../../components/prediction/PredictionHeroBand'

// Map frontend property_type → v2 canonical asset_type
const PROPERTY_TO_ASSET = {
  house:      'HOUSE',
  apartment:  'APARTMENT',
  land:       'LAND_URBAN',
  townhouse:  'TOWNHOUSE',
  villa:      'VILLA',
}

const V2_SUPPORTED = new Set(['house', 'apartment', 'land', 'townhouse', 'villa'])

const completenessPct = (value) => {
  if (!value) return 0
  if (typeof value === 'number') return value * 100
  if (typeof value.completeness_pct === 'number') return value.completeness_pct
  return 0
}

const BASE_TABS = [
  { key: 'form',        label: 'Biểu mẫu + Kết quả', abbr: 'BM', iconKey: 'house' },
  { key: 'comparables', label: 'So sánh',            abbr: 'SS', iconKey: 'table' },
  { key: 'pipeline',    label: 'Pipeline',           abbr: 'PL', iconKey: 'flask' },
]

const fmtVnd = (value) => value
  ? new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(value)
  : '—'

const toNumber = (value) => {
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

function comparableReasons(comp, input = {}) {
  if (Array.isArray(comp.match_reasons) && comp.match_reasons.length > 0) {
    return comp.match_reasons.slice(0, 4)
  }
  const reasons = []
  const inputDistrict = input?.district
  if (inputDistrict && comp.district === inputDistrict) reasons.push('Cùng quận/huyện')
  if (input?.ward && comp.ward === input.ward) reasons.push('Cùng phường/xã')
  const inputArea = toNumber(input?.area_m2 || input?.land_area_m2)
  const compArea = toNumber(comp.area_m2)
  if (inputArea && compArea) {
    const delta = Math.abs(compArea - inputArea) / inputArea
    if (delta <= 0.1) reasons.push('Diện tích lệch dưới 10%')
    else if (delta <= 0.25) reasons.push('Diện tích cùng biên độ')
  }
  if (comp.similarity_score != null) reasons.push(`Điểm gần giống ${(comp.similarity_score * 100).toFixed(0)}%`)
  if (comp.evidence_tier) reasons.push(`Nguồn ${comp.evidence_tier}`)
  return reasons.slice(0, 3)
}

function ComparableInsight({ comparables, input }) {
  if (!comparables?.length) return null
  const sameDistrict = comparables.filter(c => input?.district && c.district === input.district).length
  const areas = comparables.map(c => c.area_m2).filter(Boolean)
  const avgSimilarity = comparables
    .filter(c => c.similarity_score != null)
    .reduce((sum, c, _, arr) => sum + c.similarity_score / arr.length, 0)
  const top = comparables[0]

  return (
    <div className="prediction-note-band" style={{ marginTop: '1rem', borderColor: 'var(--info-border)' }}>
      <div className="prediction-note-head">
        <span className="stat-icon info">{icon('shieldCheck', 18)}</span>
        <strong>Vì sao các mẫu này được chọn?</strong>
      </div>
      <div className="prediction-note-grid">
        {[
          ['Tổng mẫu đạt ngưỡng gần giống', `${comparables.length} mẫu`],
          ['Cùng khu vực nhập', `${sameDistrict}/${comparables.length}`],
          ['Độ gần giống trung bình', avgSimilarity ? `${(avgSimilarity * 100).toFixed(0)}%` : 'Đang tính theo pipeline'],
          ['Khoảng diện tích mẫu', areas.length ? `${Math.min(...areas).toLocaleString('vi-VN')} - ${Math.max(...areas).toLocaleString('vi-VN')} m²` : 'Chưa đủ diện tích'],
        ].map(([label, value]) => (
          <div key={label} className="prediction-note-stat">
            <div className="prediction-note-stat-label">{label}</div>
            <div className="prediction-note-stat-value">{value}</div>
          </div>
        ))}
      </div>
      <div className="prediction-inline-note" style={{ marginTop: '0.85rem' }}>
        Danh sách này là các comparable pipeline trả về theo mức gần với hồ sơ bạn nhập, ưu tiên cùng quận/huyện, cùng phân khúc diện tích, giá/m² hợp lý và bậc nguồn dữ liệu. <strong>Mức độ tin cậy</strong> phản ánh độ ổn định của dự đoán, trong đó số lượng mẫu gần là yếu tố rất quan trọng. <strong>Độ tin cậy dữ liệu</strong> phản ánh tính minh bạch, bậc nguồn và khả năng truy xuất của từng mẫu.
        {top && (
          <div style={{ marginTop: '0.5rem', color: 'var(--info)' }}>
            Mẫu gần nhất hiện tại: #{top.legacy_id || top.id} · {comparableReasons(top, input).join(' · ') || 'pipeline chọn theo đặc trưng giá và vị trí'}.
          </div>
        )}
      </div>
    </div>
  )
}

function ResultEvidenceSummary({ comparables, input }) {
  if (!comparables?.length) {
    return (
      <div className="alert alert-warning" style={{ fontSize: '0.82rem' }}>
        Chưa tìm thấy mẫu đủ gần với mô tả đã nhập. Giá vẫn có thể được mô hình ước lượng, nhưng mức độ tin cậy dự đoán sẽ thấp và cần bổ sung dữ liệu thực địa.
      </div>
    )
  }
  const avgSimilarity = comparables
    .filter(c => c.similarity_score != null)
    .reduce((sum, c, _, arr) => sum + c.similarity_score / arr.length, 0)
  const sameDistrict = comparables.filter(c => input?.district && c.district === input.district).length
  return (
    <div className="prediction-inline-note">
      Tóm tắt bằng chứng: tìm thấy <strong>{comparables.length}</strong> mẫu đủ gần, trong đó <strong>{sameDistrict}</strong> mẫu cùng khu vực nhập{avgSimilarity ? `, độ gần giống trung bình ${(avgSimilarity * 100).toFixed(0)}%` : ''}. Chi tiết vì sao từng mẫu được chọn nằm trong tab <strong>So sánh</strong>.
    </div>
  )
}

function ConfidenceSampleGate({ evidence, comparables }) {
  const count = evidence?.comparable_count ?? comparables?.length ?? 0
  const target = 800
  const progress = Math.max(0, Math.min(100, (count / target) * 100))
  const grade = evidence?.confidence_grade || 'D'
  const confidence = evidence?.overall_confidence ?? 0
  const sampleScore = evidence?.confidence_stats?.sample_score ?? count / target
  const avgSimilarity = evidence?.confidence_stats?.avg_similarity
  const tierBreakdown = evidence?.comparable_breakdown || evidence?.confidence_stats?.tier_breakdown || {}

  return (
    <div className="prediction-note-band" style={{ borderColor: 'var(--info-border)', marginBottom: '1rem' }}>
      <div className="prediction-note-head">
        <span className="stat-icon info">{icon('shieldCheck', 18)}</span>
        <strong>Mức độ tin cậy dự đoán: chấm theo mẫu gần</strong>
        <span className={`badge ${grade === 'A' ? 'badge-success' : grade === 'B' ? 'badge-primary' : grade === 'C' ? 'badge-warning' : 'badge-danger'}`} style={{ marginLeft: 'auto' }}>
          Grade {grade}
        </span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '1rem', alignItems: 'center' }}>
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            <span>Mẫu gần đạt ngưỡng</span>
            <strong style={{ color: 'var(--text-primary)' }}>{count}/{target}</strong>
          </div>
          <div style={{ marginTop: '0.45rem', height: 10, borderRadius: 999, overflow: 'hidden', background: 'var(--surface-2)', border: '1px solid var(--border)' }}>
            <div style={{
              width: `${progress}%`,
              height: '100%',
              background: progress >= 100 ? 'var(--success)' : progress >= 38 ? 'var(--warning)' : 'var(--danger)',
            }} />
            </div>
          <div className="prediction-inline-note" style={{ marginTop: '0.75rem' }}>
            Đây là <strong>mức độ tin cậy dự đoán</strong>, khác với <strong>độ tin cậy dữ liệu</strong>. Nó cần ít nhưng phải tinh: chỉ các mẫu gần với form nhập mới được tính, và mốc A về số lượng là 800 mẫu gần. Nếu pool chỉ có vài chục mẫu, điểm bị chặn thấp dù dữ liệu có nguồn tốt.
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.65rem' }}>
          {[
            ['Điểm hiện tại', `${(confidence * 100).toFixed(0)}%`],
            ['Sample score', `${Math.min(sampleScore * 100, 100).toFixed(1)}%`],
            ['Similarity TB', avgSimilarity != null ? `${(avgSimilarity * 100).toFixed(0)}%` : 'Đang tính'],
            ['Bậc nguồn', Object.entries(tierBreakdown).map(([k, v]) => `${k}:${v}`).join(' · ') || '—'],
          ].map(([label, value]) => (
            <div key={label} className="prediction-note-stat">
              <div className="prediction-note-stat-label">{label}</div>
              <div className="prediction-note-stat-value">{value}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function PipelineDecisionMap({ pipelineResult }) {
  if (!pipelineResult?.gates?.length) return null
  const rows = [
    ['Đầu vào', 'INTAKE', 'Form đủ bắt buộc thì mới đi tiếp; thiếu field sẽ dừng hoặc cảnh báo.'],
    ['Chuẩn hóa', 'NORMALIZE', 'Đổi lựa chọn tiếng Việt/casual về mã thuật toán, làm sạch số đo.'],
    ['Tìm mẫu', 'COMPARABLE', 'Chọn toàn bộ mẫu đủ gần theo loại tài sản, khu vực, diện tích và nguồn.'],
    ['Định giá', 'VALUATION', 'Tạo baseline, ledger điều chỉnh và khoảng giá thị trường.'],
    ['Giải thích', 'FIT', 'Tách lớp phù hợp và các cảnh báo để người dùng biết phải bổ sung gì.'],
  ]
  const statusByGate = Object.fromEntries(pipelineResult.gates.map(g => [g.gate_name, g.status]))
  return (
    <div className="prediction-note-band" style={{ borderColor: 'var(--success-border)' }}>
      <div className="prediction-note-head">
        <span className="stat-icon success">{icon('activity', 18)}</span>
        <strong>Bản đồ quyết định của pipeline</strong>
      </div>
      <div style={{ display: 'grid', gap: '0.65rem' }}>
        {rows.map(([label, gate, desc], idx) => {
          const status = statusByGate[gate] || 'SKIP'
          const color = status === 'PASS' ? 'var(--success)' : status === 'WARN' ? 'var(--warning)' : status === 'BLOCK' ? 'var(--danger)' : 'var(--text-muted)'
          return (
            <div key={gate} style={{ display: 'grid', gridTemplateColumns: '34px 130px 90px 1fr', gap: '0.75rem', alignItems: 'center', padding: '0.75rem', borderRadius: 8, border: '1px solid var(--border)', background: 'var(--surface-2)' }}>
              <div style={{ width: 26, height: 26, borderRadius: 999, display: 'grid', placeItems: 'center', background: `${color}18`, color, fontWeight: 800 }}>{idx + 1}</div>
              <strong>{label}</strong>
              <span style={{ color, fontWeight: 800, fontSize: '0.76rem' }}>{status}</span>
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.82rem' }}>{desc}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ─── Comparable row renderer (used by Comparables tab) ───────────────────────
function ComparableRow({ comp, input }) {
  const tierColors = {
    E5: { bg: '#06d6a015', border: '#06d6a040', color: '#06d6a0' },
    E4: { bg: '#00b4d815', border: '#00b4d840', color: '#00b4d8' },
    E3: { bg: '#90e0ef15', border: '#90e0ef40', color: '#90e0ef' },
    E2: { bg: '#ffb70315', border: '#ffb70340', color: '#ffb703' },
    E1: { bg: '#ef233c15', border: '#ef233c40', color: '#ef233c' },
  }
  const tierStyle = tierColors[comp.evidence_tier] || tierColors.E3

  return (
    <tr style={{ fontSize: '0.82rem' }}>
      <td><span style={{ fontFamily: 'monospace', color: 'var(--text-muted)' }}>#{comp.legacy_id || comp.id}</span></td>
      <td>
        <span style={{
          padding: '2px 8px', borderRadius: 'var(--radius-full)',
          background: tierStyle.bg, border: `1px solid ${tierStyle.border}`,
          color: tierStyle.color, fontSize: '0.68rem', fontWeight: 700,
        }}>
          {comp.evidence_tier || 'E3'}
        </span>
      </td>
      <td>
        <div className="font-medium">{comp.district || comp.location}</div>
        {comp.ward && <div className="text-xs text-muted">{comp.ward}</div>}
      </td>
      <td>{comp.area_m2 ? `${comp.area_m2.toLocaleString('vi-VN')} m²` : '—'}</td>
      <td className="font-semibold text-success">
        {comp.price_per_m2
          ? new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(comp.price_per_m2) + ' /m²'
          : '—'
        }
      </td>
      <td className="font-semibold">
        {comp.price
          ? new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(comp.price)
          : comp.price_per_m2 && comp.area_m2
            ? new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(comp.price_per_m2 * comp.area_m2)
            : '—'
        }
      </td>
      <td>
        {comp.verification_status && (
          <span className={`badge ${comp.verification_status === 'verified' ? 'badge-success' : 'badge-neutral'}`} style={{ fontSize: '0.65rem' }}>
            {comp.verification_status}
          </span>
        )}
      </td>
      <td>
        {comp.similarity_score != null && (
          <span style={{
            padding: '2px 8px', borderRadius: 'var(--radius)',
            background: comp.similarity_score >= 0.8
              ? 'var(--success-bg)' : comp.similarity_score >= 0.6
              ? 'var(--warning-bg)' : 'var(--danger-bg)',
            color: comp.similarity_score >= 0.8
              ? 'var(--success)' : comp.similarity_score >= 0.6
              ? 'var(--warning)' : 'var(--danger)',
            fontWeight: 700, fontSize: '0.78rem',
          }}>
            {(comp.similarity_score * 100).toFixed(0)}%
          </span>
        )}
        <div style={{ marginTop: comp.similarity_score != null ? 6 : 0, color: 'var(--text-muted)', fontSize: '0.68rem', lineHeight: 1.4 }}>
          {comparableReasons(comp, input).map(reason => (
            <div key={reason}>{reason}</div>
          ))}
        </div>
      </td>
    </tr>
  )
}

// ─── Comparable table (used by Form and Comparables tabs) ───────────────────
function ComparableTable({ comparables, input }) {
  const [page, setPage] = useState(1)
  if (!comparables || comparables.length === 0) return null
  const pageSize = 15
  const totalPages = Math.max(1, Math.ceil(comparables.length / pageSize))
  const safePage = Math.min(page, totalPages)
  const visible = comparables.slice((safePage - 1) * pageSize, safePage * pageSize)
  return (
    <>
      <ComparableInsight comparables={comparables} input={input} />
      <div className="table-wrapper" style={{ marginTop: '1rem' }}>
        <table className="table" style={{ fontSize: '0.82rem' }}>
          <thead>
            <tr>
              <th>ID</th>
              <th>Nguồn</th>
              <th>Vị trí</th>
              <th>Diện tích</th>
              <th>Giá/m²</th>
              <th>Tổng giá</th>
              <th>Trạng thái</th>
              <th>Vì sao gần giống</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((comp, idx) => (
              <ComparableRow key={idx} comp={comp} input={input} />
            ))}
          </tbody>
        </table>
      </div>
      {totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: '0.5rem', marginTop: '0.75rem' }}>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Trang {safePage}/{totalPages}
          </span>
          {Array.from({ length: totalPages }, (_, idx) => idx + 1).slice(0, 8).map(n => (
            <button
              key={n}
              type="button"
              className={`btn btn-sm ${safePage === n ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setPage(n)}
              style={{ minWidth: 34 }}
            >
              {n}
            </button>
          ))}
          {totalPages > 8 && <span className="text-muted">...</span>}
        </div>
      )}
    </>
  )
}

// ─── Market Stats bar (shown in results panel) ────────────────────────────────
function MarketStatsBar({ comparables }) {
  if (!comparables || comparables.length === 0) return null
  const total = comparables.length
  const avg = comparables.reduce((s, c) => s + (c.price_per_m2 || 0), 0) / total
  return (
    <div style={{
      display: 'flex', gap: '1rem', padding: '0.625rem 0.875rem',
      background: 'var(--surface-2)', borderRadius: 'var(--radius)',
      fontSize: '0.75rem', color: 'var(--text-muted)',
    }}>
      <span><strong>{total}</strong> mẫu gần nhất</span>
      <span>|</span>
      <span>Giá/m² trung bình <strong>{fmtVnd(avg)}</strong>/m²</span>
    </div>
  )
}

// ─── Main Prediction component ────────────────────────────────────────────────
function Prediction() {
  const [activeTab, setActiveTab] = useState('form')
  const [propertyType, setPropertyType] = useState('land')
  const [pipelineResult, setPipelineResult] = useState(null)
  const [sdevResult, setSdevResult] = useState(null)
  const [lastPayload, setLastPayload] = useState(null)
  const [loading, setLoading] = useState(false)
  const [sdevLoading, setSdevLoading] = useState(false)
  const [error, setError] = useState(null)
  const { isAdmin } = useAuth()

  const { data: engineInfo } = useQuery({
    queryKey: ['engine-version'],
    queryFn: async () => {
      const res = await fetch('/api/v2/engine/version')
      if (!res.ok) throw new Error('Không lấy được phiên bản engine')
      return res.json()
    },
    staleTime: 10 * 60 * 1000,
  })

  // Dynamic scope from API
  const { data: scopesData } = useQuery({
    queryKey: ['provinces'],
    queryFn: async () => {
      const res = await fetch('/api/provinces')
      if (!res.ok) throw new Error('Không lấy được danh sách tỉnh/thành')
      return res.json()
    },
    staleTime: 10 * 60 * 1000,
  })

  const scopeText = React.useMemo(() => {
    const provinces = scopesData?.provinces || []
    if (!provinces.length) return 'Đang tải scope từ backend'
    const labels = provinces
      .map(scope => {
        const count = scope.actual_record_count ?? scope.districts?.reduce((sum, d) => sum + (d.record_count || d.actual_record_count || 0), 0) ?? 0
        return `${scope.name} (${count} records)`
      })
    return labels.length > 3
      ? `${labels.slice(0, 3).join(' · ')} · +${labels.length - 3} scope khác`
      : labels.join(' · ')
  }, [scopesData])

  // Districts for selected province
  const [selectedProvince, setSelectedProvince] = useState(null)
  const { data: districtsData } = useQuery({
    queryKey: ['districts', selectedProvince],
    queryFn: async () => {
      const res = await fetch(`/api/provinces/${selectedProvince}/districts`)
      if (!res.ok) throw new Error('Không lấy được danh sách quận/huyện')
      return res.json()
    },
    enabled: !!selectedProvince,
  })

  const handlePropertyTypeChange = (type) => {
    setPropertyType(type)
    setPipelineResult(null)
    setSdevResult(null)
    setLastPayload(null)
    setError(null)
  }

  const handleV2Submit = async (payload) => {
    setLoading(true)
    setError(null)
    setPipelineResult(null)
    setSdevResult(null)
    setLastPayload(payload)
    try {
      const data = await predictPipeline(payload)
      setPipelineResult(data)
      if (payload.district && payload.area_m2) {
        setSdevLoading(true)
        try {
          const sdevData = await predictSDEV({
            asset_type: PROPERTY_TO_ASSET[propertyType] || propertyType.toUpperCase(),
            province_city: payload.province_city || payload.province,
            district: payload.district,
            area_m2: parseFloat(payload.area_m2) || 0,
            bedrooms: parseInt(payload.bedrooms) || 2,
          })
          setSdevResult(sdevData)
        } catch (_) { setSdevResult(null) }
        finally { setSdevLoading(false) }
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // v2 valuation data for ValuationResultCard
  const v2Result = pipelineResult?.valuation
    ? {
        market_valuation: pipelineResult.valuation.market_valuation,
        fit_suitability: pipelineResult.valuation.fit_suitability,
        confidence_evidence: pipelineResult.valuation.confidence_evidence,
        sub_engines: pipelineResult.valuation.sub_engines,
      }
    : null

  // v2 comparables — from PipelineResult.top-level comparable_records field
  const comparables = pipelineResult?.comparable_records || []

  return (
    <div>
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Dự đoán giá bất động sản</h1>
          <p className="page-subtitle">Nhập thông tin tài sản để nhận kết quả định giá tự động từ mô hình Machine Learning</p>
        </div>
      </div>

      <PredictionHeroBand
        scopeText={scopeText}
        engineLabel={engineInfo?.button_label}
        isAdmin={isAdmin}
      />

      {/* ── Tabs ── */}
      <div className="flex gap-2 mb-6">
        {BASE_TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`btn btn-sm ${activeTab === t.key ? 'btn-primary' : 'btn-ghost'}`}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
          >
            {icon(t.iconKey, 16)}
            {t.label}
          </button>
        ))}
        {isAdmin && (
          <button
            key="impact"
            onClick={() => setActiveTab('impact')}
            className={`btn btn-sm ${activeTab === 'impact' ? 'btn-primary' : 'btn-ghost'}`}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
          >
            {icon('chart', 16)}
            Tác động
            <span style={{
              padding: '1px 6px',
              background: '#06d6a020',
              color: '#06d6a0',
              borderRadius: '10px',
              fontSize: '0.65rem',
              fontWeight: 700,
            }}>
              Admin
            </span>
          </button>
        )}
      </div>

      {/* ════════════════════════════════════════════════════════════
          TAB: FORM + RESULTS
          Left: intake form | Right: v2 results (no decorative map)
      ════════════════════════════════════════════════════════════ */}
      {activeTab === 'form' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1.15fr 0.85fr', gap: '1.5rem' }}>
          {/* LEFT — Form */}
          <div className="card animate-fadeIn">
            <div className="card-header">
              <span className="stat-icon primary">{icon('house', 20)}</span>
              <span className="card-title">Thông tin bất động sản</span>
            </div>

            <div className="prediction-note-band" style={{ marginBottom: '1rem' }}>
              <div className="prediction-note-head">
                <span className="stat-icon info">{icon('activity', 18)}</span>
                <strong>Luồng làm việc</strong>
              </div>
              <div className="prediction-note-grid prediction-workflow-grid">
                {[
                  ['01', 'Nhập hồ sơ', 'Form thật để kích hoạt pipeline.'],
                  ['02', 'So sánh mẫu', 'Comparable và evidence đi cùng.'],
                  ['03', 'Xem audit', 'Pipeline, sub-engine và tác động.'],
                ].map(([step, title, desc]) => (
                  <div key={title} className="prediction-note-stat">
                    <div className="prediction-note-stat-label">{step}</div>
                    <div className="prediction-note-stat-value" style={{ fontSize: '0.95rem' }}>{title}</div>
                    <div className="prediction-metric-note">{desc}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Property type selector */}
            <div className="form-group mb-4">
              <label className="form-label">Loại bất động sản</label>
              <div className="flex gap-2 flex-wrap">
                {Object.entries(PROPERTY_TYPES).map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => handlePropertyTypeChange(key)}
                    style={{
                      display: 'inline-flex', alignItems: 'center', gap: '0.4rem',
                      padding: '0.5rem 0.875rem', borderRadius: 'var(--radius)',
                      fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer',
                      border: `1px solid ${propertyType === key ? 'var(--primary)' : 'var(--border)'}`,
                      background: propertyType === key ? 'var(--primary-50)' : 'transparent',
                      color: propertyType === key ? 'var(--primary)' : 'var(--text-secondary)',
                      transition: 'all var(--transition)',
                    }}
                  >
                    {icon(key, 15)}
                    {label}
                  </button>
                ))}
              </div>
              {V2_SUPPORTED.has(propertyType) && (
                <div style={{ marginTop: '0.5rem' }}>
                  <span className="badge badge-success" style={{ fontSize: '0.7rem' }}>
                    {engineInfo?.button_label?.replace('Chạy ', '') || 'Valuation Engine v2'} — 3 lớp output
                  </span>
                </div>
              )}
            </div>

            {/* v2 asset-specific forms */}
            {V2_SUPPORTED.has(propertyType) && propertyType === 'land' && (
              <LandIntakeForm onSubmit={handleV2Submit} loading={loading} isAdmin={isAdmin} engineLabel={engineInfo?.button_label} />
            )}
            {V2_SUPPORTED.has(propertyType) && propertyType === 'apartment' && (
              <ApartmentIntakeForm onSubmit={handleV2Submit} loading={loading} isAdmin={isAdmin} engineLabel={engineInfo?.button_label} />
            )}
            {V2_SUPPORTED.has(propertyType) && propertyType === 'townhouse' && (
              <TownhouseIntakeForm onSubmit={handleV2Submit} loading={loading} isAdmin={isAdmin} engineLabel={engineInfo?.button_label} />
            )}
            {V2_SUPPORTED.has(propertyType) && propertyType === 'villa' && (
              <VillaIntakeForm onSubmit={handleV2Submit} loading={loading} isAdmin={isAdmin} engineLabel={engineInfo?.button_label} />
            )}
            {V2_SUPPORTED.has(propertyType) && propertyType === 'house' && (
              <HouseIntakeForm onSubmit={handleV2Submit} loading={loading} isAdmin={isAdmin} engineLabel={engineInfo?.button_label} />
            )}
          </div>

          {/* RIGHT — Results panel */}
          <div>
            {error && (
              <div className="alert alert-danger mb-4">
                <span className="alert-icon">{icon('warning', 16)}</span>
                <span>{error}</span>
              </div>
            )}

            {pipelineResult && (
              <div className="animate-scaleIn" style={{ position: 'sticky', top: '80px', display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>

                {/* Blocked banner */}
                {pipelineResult.final_status === 'BLOCK' && (
                  <div className="alert alert-danger" style={{
                    display: 'flex', alignItems: 'center', gap: '0.5rem',
                    borderLeft: '4px solid var(--danger, #ef233c)',
                  }}>
                    <span className="alert-icon">{icon('error', 20)}</span>
                    <div>
                      <div style={{ fontWeight: 700 }}>Pipeline BLOCKED</div>
                      <div style={{ fontSize: '0.82rem', opacity: 0.85 }}>
                        Tài sản bị chặn tại gate "{pipelineResult.blocked_at_gate}".
                        Cần bổ sung hoặc sửa thông tin trước khi định giá.
                      </div>
                    </div>
                  </div>
                )}

                {/* Valuation Result Card — 3-layer output */}
                {v2Result && (
                  <>
                    <ValuationResultCard result={v2Result} compact />
                    <ResultEvidenceSummary comparables={comparables} input={lastPayload} />
                  </>
                )}

                {/* SDEV */}
                {(sdevResult || sdevLoading) && (
                  <SDEVResultCard sdev={sdevResult} loading={sdevLoading} />
                )}

              </div>
            )}

            {!pipelineResult && !loading && (
              <div className="card" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                <div style={{ marginBottom: '1rem', opacity: 0.55 }}>{icon('house', 44)}</div>
                <p style={{ fontSize: '0.875rem' }}>
                  Nhập thông tin bất động sản và nhấn <strong>Dự đoán</strong> để xem kết quả định giá với đầy đủ độ tin cậy và bằng chứng.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ════════════════════════════════════════════════════════════
          TAB: COMPARABLES — uses v2 pipeline data, not legacy API
      ════════════════════════════════════════════════════════════ */}
      {activeTab === 'comparables' && (
        <div className="card animate-fadeIn">
          <div className="card-header">
            <span className="stat-icon info">{icon('table', 20)}</span>
            <span className="card-title">Bất động sản so sánh</span>
            <span className="badge badge-primary" style={{ marginLeft: 'auto' }}>
              v2 Pipeline
            </span>
          </div>

          {comparables.length > 0 ? (
            <>
              <ConfidenceSampleGate evidence={v2Result?.confidence_evidence} comparables={comparables} />

              {/* Stats row */}
              <div className="prediction-metric-strip">
                <div>
                  <div className="prediction-metric-label">Số comparable</div>
                  <div className="prediction-metric-value">{comparables.length}</div>
                  <div className="prediction-metric-note">Mẫu đủ gần được pipeline trả về.</div>
                </div>
                <div>
                  <div className="prediction-metric-label">Giá trung bình</div>
                  <div className="prediction-metric-value">
                    {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(
                      comparables.reduce((s, c) => s + (c.price_per_m2 || 0), 0) / comparables.length
                    )}/m²
                  </div>
                  <div className="prediction-metric-note">Trung bình giá/m² của pool.</div>
                </div>
                <div>
                  <div className="prediction-metric-label">Trung vị</div>
                  <div className="prediction-metric-value">
                    {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(
                      [...comparables.map(c => c.price_per_m2 || 0)].sort((a, b) => a - b)[Math.floor(comparables.length / 2)]
                    )}/m²
                  </div>
                  <div className="prediction-metric-note">Điểm giữa của pool hiện tại.</div>
                </div>
                <div>
                  <div className="prediction-metric-label">Min — Max</div>
                  <div className="prediction-metric-value" style={{ fontSize: '0.95rem' }}>
                    {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(
                      Math.min(...comparables.map(c => c.price_per_m2 || 0))
                    )} — {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(
                      Math.max(...comparables.map(c => c.price_per_m2 || 0))
                    )}
                  </div>
                  <div className="prediction-metric-note">Dải giá đang quan sát được.</div>
                </div>
              </div>

              <ComparableTable comparables={comparables} input={lastPayload} />
            </>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">{icon('inbox', 40)}</div>
              <div className="empty-title">Chưa có bất động sản so sánh</div>
              <div className="empty-desc">
                {pipelineResult
                  ? 'Pipeline trả về 0 comparable — thử thay đổi thông tin đầu vào hoặc khu vực khác.'
                  : 'Nhập thông tin và nhấn "Dự đoán" để tìm các bất động sản tương tự từ pipeline v2.'
                }
              </div>
            </div>
          )}
        </div>
      )}

      {/* ════════════════════════════════════════════════════════════
          TAB: PIPELINE — 9-gate audit trail + sub-engines
      ════════════════════════════════════════════════════════════ */}
      {activeTab === 'pipeline' && (
        <div className="animate-fadeIn" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {pipelineResult ? (
            <>
              <PipelineGateTrail
                gates={pipelineResult.gates}
                finalStatus={pipelineResult.final_status}
                blockedAt={pipelineResult.blocked_at_gate}
                completeness={pipelineResult.completeness}
                compact
              />
              <div style={{ marginTop: '0.25rem' }}>
                <PipelineDecisionMap pipelineResult={pipelineResult} />
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Completeness: <strong>{completenessPct(pipelineResult.completeness).toFixed(0)}%</strong>
                </span>
                <div style={{ flex: 1, height: 6, background: 'var(--surface-2)', borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{
                    width: `${completenessPct(pipelineResult.completeness).toFixed(0)}%`,
                    height: '100%',
                    background: completenessPct(pipelineResult.completeness) >= 70 ? 'var(--success)' : completenessPct(pipelineResult.completeness) >= 40 ? 'var(--warning)' : 'var(--danger)',
                    borderRadius: 3,
                    transition: 'width 0.5s ease',
                  }} />
                </div>
              </div>
            </>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">{icon('inbox', 40)}</div>
              <div className="empty-title">Chưa có pipeline data</div>
              <div className="empty-desc">Gửi dự đoán để xem pipeline audit trail</div>
            </div>
          )}

          {/* Sub-Engines */}
          {pipelineResult && (
            <SubEnginePanel
              legal={pipelineResult.legal_result}
              geometry={pipelineResult.geometry_result}
              environment={pipelineResult.environment_result}
              compact
            />
          )}

          {/* Blocked details */}
          {pipelineResult?.final_status === 'BLOCK' && (
            <div className="alert alert-danger">
              <span className="alert-icon">{icon('error', 16)}</span>
              <div>
                <div style={{ fontWeight: 700 }}>Pipeline BLOCKED tại "{pipelineResult.blocked_at_gate}"</div>
                <div style={{ fontSize: '0.82rem', marginTop: '0.5rem' }}>
                  Cần bổ sung thông tin hoặc sửa lại dữ liệu đầu vào để pipeline có thể tiếp tục.
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ════════════════════════════════════════════════════════════
          TAB: IMPACT — Admin-only Contextual Comparable-SHAP δ%
      ════════════════════════════════════════════════════════════ */}
      {activeTab === 'impact' && (
        <div className="animate-fadeIn">
          {isAdmin ? (
            pipelineResult ? (
              <ImpactAnalysisPanel
                formData={{
                  ...lastPayload,
                  asset_type: PROPERTY_TO_ASSET[propertyType] || propertyType.toUpperCase(),
                }}
                runId={pipelineResult.pipeline_id}
              />
            ) : (
              <div className="card">
                <div className="empty-state">
                  <div className="empty-icon">{icon('house', 40)}</div>
                  <div className="empty-title">Chưa có kết quả dự đoán</div>
                  <div className="empty-desc">
                    Nhập thông tin và nhấn "Dự đoán" trước để phân tích tác động.
                  </div>
                </div>
              </div>
            )
          ) : (
            <div className="card">
              <div className="empty-state">
                <div className="empty-icon">{icon('shield', 40)}</div>
                <div className="empty-title">Chỉ dành cho Admin</div>
                <div className="empty-desc">
                  Tab "Tác động" chỉ hiển thị cho tài khoản Quản trị viên.
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default Prediction
