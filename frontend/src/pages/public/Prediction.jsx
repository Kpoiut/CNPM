import React, { Suspense, lazy, useState, useEffect, useRef } from 'react'
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
import { useAuth } from '../../components/auth'
import { predictPipeline, predictSDEV, iotAreaSignal } from '../../api'
import { PredictionHeroBand } from '../../components/prediction/PredictionHeroBand'
import { setNovaContext, clearNovaContext } from '../../components/nova/novaBus'
import './prediction-pro.css'

const MapLocationPicker = lazy(() => import('../../components/valuation/MapLocationPicker'))
const PropertyVisualizer = lazy(() => import('../../components/valuation/PropertyVisualizer'))
const ImpactAnalysisPanel = lazy(() =>
  import('../../components/valuation/ImpactAnalysisPanel').then(module => ({ default: module.ImpactAnalysisPanel }))
)

function LazyPanelFallback({ label = 'Đang tải mô-đun...' }) {
  return (
    <div className="prediction-inline-note" style={{ minHeight: 120, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      {label}
    </div>
  )
}

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

// Hai cách bắt đầu (chọn 1 trong 2) — đứng trên nhóm kết quả
const ENTRY_TABS = [
  { key: 'form', label: 'Biểu mẫu', iconKey: 'house' },
  { key: 'map',  label: 'Định vị thông minh', iconKey: 'map' },
]

// Nhóm kết quả — bị KHÓA cho tới khi có kết quả dự đoán
const RESULT_TABS = [
  { key: 'result',      label: 'Kết quả',  iconKey: 'chart' },
  { key: 'comparables', label: 'So sánh',  iconKey: 'table' },
  { key: 'pipeline',    label: 'Pipeline', iconKey: 'flask' },
]
const RESULT_TAB_KEYS = ['result', 'comparables', 'pipeline', 'impact']

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

function modelMetricText(model) {
  return model?.test_mape != null
    ? `${model.stamp} · MAPE ${Number(model.test_mape).toLocaleString('vi-VN', { maximumFractionDigits: 2 })}%`
    : 'Đang tải metric có version'
}

function PredictionReadinessStrip({
  isAdmin,
  scopeText,
  engineLabel,
  modelProvenance,
  pipelineResult,
  loading,
}) {
  const servingModel = modelProvenance?.serving
  const hasResult = Boolean(pipelineResult)
  const items = [
    {
      iconKey: isAdmin ? 'shieldCheck' : 'user',
      label: 'Vai trò',
      value: isAdmin ? 'Admin operations' : 'User workspace',
      note: isAdmin ? 'Mở audit, model và tác động' : 'Dự đoán, giải thích, lịch sử',
    },
    {
      iconKey: 'database',
      label: 'Nguồn dữ liệu',
      value: 'PostgreSQL/PostGIS',
      note: scopeText || 'Đang tải scope từ backend',
    },
    {
      iconKey: 'activity',
      label: 'Model đang phục vụ',
      value: servingModel?.stamp || 'Đang tải',
      note: modelMetricText(servingModel),
    },
    {
      iconKey: loading ? 'loader' : 'clock',
      label: 'Phản hồi',
      value: loading ? 'Pipeline đang chạy' : 'Cached target <200ms',
      note: hasResult ? 'Kết quả đã có thể đối chiếu' : engineLabel || 'Valuation Engine v2',
    },
  ]

  return (
    <section className="pp-readiness-strip" aria-label="Prediction production readiness">
      {items.map(item => (
        <div className="pp-readiness-item" key={item.label}>
          <span className="pp-readiness-icon">{icon(item.iconKey, 17)}</span>
          <span className="pp-readiness-copy">
            <span>{item.label}</span>
            <strong>{item.value}</strong>
            <small>{item.note}</small>
          </span>
        </div>
      ))}
    </section>
  )
}

function PredictionCommandRail({
  isAdmin,
  activeTab,
  propertyType,
  pipelineResult,
  v2Result,
  comparables,
  loading,
  staleLocation,
  repredicting,
  scopeText,
  engineLabel,
  modelProvenance,
}) {
  const hasResult = Boolean(pipelineResult)
  const value = v2Result?.market_valuation?.fair_market_value
  const grade = v2Result?.confidence_evidence?.confidence_grade || pipelineResult?.valuation?.confidence_evidence?.confidence_grade
  const confidence = v2Result?.confidence_evidence?.overall_confidence
  const servingModel = modelProvenance?.serving
  const latestModel = modelProvenance?.latest
  const nextAction = loading
    ? 'Đợi pipeline hoàn tất'
    : !hasResult
      ? 'Nhập hồ sơ rồi bấm Dự đoán'
      : staleLocation
        ? 'Vị trí đã đổi — chạy lại dự đoán'
        : activeTab === 'form'
          ? 'Kiểm tra Kết quả hoặc So sánh'
          : activeTab === 'result'
            ? 'Đối chiếu comparable/pipeline'
            : 'Có thể quay lại form để tinh chỉnh'

  return (
    <aside className="pp-command-rail" aria-label="Prediction workspace status">
      <div className="pp-rail-card pp-rail-card--role">
        <div className="pp-rail-kicker">{isAdmin ? 'Vận hành quản trị' : 'Định giá cá nhân'}</div>
        <div className="pp-rail-title">
          {icon(isAdmin ? 'shieldCheck' : 'user', 18)}
          {isAdmin ? 'Chế độ kiểm soát đầy đủ' : 'Chế độ định giá người dùng'}
        </div>
        <p>
          {isAdmin
            ? 'Có thêm tab Tác động, audit pipeline và thông tin vận hành để kiểm tra mô hình.'
            : 'Tập trung vào nhập hồ sơ, nhận khoảng giá, xem bằng chứng và mức tin cậy.'}
        </p>
      </div>

      <div className="pp-rail-card">
        <div className="pp-rail-kicker">Hành động tiếp theo</div>
        <strong className="pp-rail-action">{nextAction}</strong>
        <div className="pp-step-stack">
          {[
            ['form', '01', 'Hồ sơ'],
            ['result', '02', 'Kết quả'],
            ['comparables', '03', 'So sánh'],
            ['pipeline', '04', 'Audit'],
          ].map(([key, number, label]) => (
            <span
              key={key}
              className={`pp-step-pill ${activeTab === key ? 'is-active' : ''} ${hasResult || key === 'form' ? '' : 'is-locked'}`}
            >
              <b>{number}</b>{label}
            </span>
          ))}
        </div>
      </div>

      <div className="pp-rail-card">
        <div className="pp-rail-kicker">Tóm tắt trực tiếp</div>
        <dl className="pp-rail-metrics">
          <div>
            <dt>Loại tài sản</dt>
            <dd>{PROPERTY_TYPES?.[propertyType] || propertyType}</dd>
          </div>
          <div>
            <dt>Giá ước tính</dt>
            <dd>{value ? fmtVnd(value) : 'Chưa chạy'}</dd>
          </div>
          <div>
            <dt>Comparable</dt>
            <dd>{comparables?.length || 0} mẫu</dd>
          </div>
          <div>
            <dt>Confidence</dt>
            <dd>{grade ? `Grade ${grade}${confidence != null ? ` · ${(confidence * 100).toFixed(0)}%` : ''}` : '—'}</dd>
          </div>
        </dl>
      </div>

      <div className="pp-rail-card pp-rail-card--system">
        <div className="pp-rail-kicker">Thông tin hệ thống</div>
        <div className="pp-system-line">
          <span>{icon('flask', 16)}</span>
          <span>{engineLabel || 'Valuation Engine v2'}</span>
        </div>
        <div className="pp-system-line">
          <span>{icon('database', 16)}</span>
          <span>PostgreSQL/PostGIS source</span>
        </div>
        <div className="pp-system-line">
          <span>{icon('shieldCheck', 16)}</span>
          <span>Model đang phục vụ: {modelMetricText(servingModel)}</span>
        </div>
        <div className="pp-system-line">
          <span>{icon('activity', 16)}</span>
          <span>Chu kỳ train mới nhất: {modelMetricText(latestModel)}</span>
        </div>
        {servingModel?.stamp && latestModel?.stamp && servingModel.stamp !== latestModel.stamp && (
          <small>
            Candidate mới chưa được activate vì metric test chưa tốt hơn model đang phục vụ.
          </small>
        )}
        <small>{scopeText}</small>
        {repredicting && <span className="pp-rail-sync">{icon('loader', 14)} Đang cập nhật live estimate</span>}
      </div>
    </aside>
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
  const [prefill, setPrefill] = useState(null)
  const [iotSignal, setIotSignal] = useState(null)
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

  const { data: modelComparison } = useQuery({
    queryKey: ['model-metric-provenance'],
    queryFn: async () => {
      const res = await fetch('/api/v2/explain/model-compare')
      if (!res.ok) throw new Error('Không lấy được metric theo model version')
      return res.json()
    },
    staleTime: 5 * 60 * 1000,
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

  // Map picker → set loại hình + prefill rồi chuyển sang biểu mẫu để người dùng hoàn tất
  const handleMapConfirm = ({ propertyType: nextType, prefill: nextPrefill }) => {
    if (nextType && nextType !== propertyType) {
      setPropertyType(nextType)
      setPipelineResult(null)
      setSdevResult(null)
      setLastPayload(null)
      setError(null)
    }
    setPrefill(nextPrefill)
    setActiveTab('form')
  }

  // Map picker → DỰ ĐOÁN LUÔN: giữ data ở form + chạy pipeline + sang kết quả
  const handleMapPredict = ({ propertyType: nextType, prefill: nextPrefill }) => {
    if (nextType && nextType !== propertyType) setPropertyType(nextType)
    setPrefill(nextPrefill)
    const assetType = PROPERTY_TO_ASSET[nextType] || nextType.toUpperCase()
    const clean = Object.fromEntries(
      Object.entries(nextPrefill || {}).filter(([k, v]) => !k.startsWith('_') && v !== '' && v != null)
    )
    runPrediction({ asset_type: assetType, ...clean })
  }

  // Xóa hết: reset form + kết quả (remount form qua resetKey)
  const [resetKey, setResetKey] = useState(0)
  const [formPhotos, setFormPhotos] = useState([])
  const clearAll = () => {
    setPrefill(null)
    setPipelineResult(null)
    setSdevResult(null)
    setLastPayload(null)
    setError(null)
    setFormPhotos([])
    setResetKey(k => k + 1)
  }
  const onFormUpload = (e) => {
    const files = Array.from(e.target.files || []).slice(0, 6)
    setFormPhotos(prev => [...prev, ...files.map(f => ({ name: f.name, url: URL.createObjectURL(f) }))].slice(0, 6))
  }

  // Khóa nhóm kết quả: nếu chưa có dự đoán mà đang ở tab kết quả → quay về biểu mẫu
  useEffect(() => {
    if (RESULT_TAB_KEYS.includes(activeTab) && !pipelineResult && !loading) {
      setActiveTab('form')
    }
  }, [activeTab, pipelineResult, loading])

  // Kích thước nút nhóm kết quả: admin +50%, user +100% (thiếu nút Tác động)
  const resultScale = isAdmin ? 1.5 : 2.0
  const resultTabs = isAdmin
    ? [...RESULT_TABS, { key: 'impact', label: 'Tác động', iconKey: 'chart' }]
    : RESULT_TABS

  const liveTimerRef = useRef(null)
  const lastLocSigRef = useRef(null)
  const [repredicting, setRepredicting] = useState(false)
  const [staleLocation, setStaleLocation] = useState(false)

  const locSig = (p) => [p?.province_city, p?.district, p?.ward, p?.latitude, p?.longitude, p?.street_or_project].join('|')

  const runPrediction = async (payload, { silent = false } = {}) => {
    if (silent) { setRepredicting(true) }
    else { setLoading(true); setError(null); setPipelineResult(null); setSdevResult(null) }

    let enriched = payload
    if (!silent) {
      const lat = parseFloat(payload.latitude)
      const lng = parseFloat(payload.longitude)
      const hasIot = payload.noise_level != null && payload.noise_level !== ''
      if (!hasIot && Number.isFinite(lat) && Number.isFinite(lng)) {
        try {
          const signal = await iotAreaSignal({ lat, lng })
          const r = signal?.readings || {}
          enriched = {
            ...payload,
            ...(r.noise_level != null ? { noise_level: r.noise_level } : {}),
            ...(r.temperature != null ? { temperature: r.temperature } : {}),
            ...(r.humidity != null ? { humidity: r.humidity } : {}),
            iot_signal_source: signal?.sensor_source,
            iot_node_count: signal?.node_count,
          }
          setIotSignal(signal)
        } catch (_) { /* không chặn dự đoán nếu tín hiệu lỗi */ }
      }
    }
    setLastPayload(enriched)

    try {
      const data = await predictPipeline(enriched)
      setPipelineResult(data)
      lastLocSigRef.current = locSig(enriched)
      setStaleLocation(false)
      if (!silent) setActiveTab('result')
      if (!silent && enriched.district && enriched.area_m2) {
        setSdevLoading(true)
        try {
          const sdevData = await predictSDEV({
            asset_type: PROPERTY_TO_ASSET[propertyType] || propertyType.toUpperCase(),
            province_city: enriched.province_city || enriched.province,
            district: enriched.district,
            area_m2: parseFloat(enriched.area_m2) || 0,
            bedrooms: parseInt(enriched.bedrooms) || 2,
          })
          setSdevResult(sdevData)
        } catch (_) { setSdevResult(null) }
        finally { setSdevLoading(false) }
      }
    } catch (err) {
      if (!silent) setError(err.message)
    } finally {
      if (silent) setRepredicting(false); else setLoading(false)
    }
  }

  const handleV2Submit = (payload) => runPrediction(payload, { silent: false })

  // Tự cập nhật giá khi đổi field SỐ; ĐÓNG BĂNG khi đổi VỊ TRÍ (quận/phường/tọa độ) → cần bấm dự đoán lại
  const handleLiveChange = (payload) => {
    if (!pipelineResult) return
    if (locSig(payload) !== lastLocSigRef.current) { setStaleLocation(true); return }
    clearTimeout(liveTimerRef.current)
    liveTimerRef.current = setTimeout(() => runPrediction(payload, { silent: true }), 650)
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

  // Grade hiển thị ở thanh kết quả
  const resultGrade = v2Result?.confidence_evidence?.confidence_grade
  const resultConf = v2Result?.confidence_evidence?.overall_confidence ?? 0
  const GRADE_COLORS = { A: '#06d6a0', B: '#0099ff', C: '#f59e0b', D: '#ef233c' }
  const resultGradeColor = GRADE_COLORS[resultGrade] || '#888'

  // Publish kết quả định giá hiện tại cho trợ lý Nova (tương tác sâu: "giải thích kết quả này")
  useEffect(() => {
    const mv = v2Result?.market_valuation
    if (!mv) { clearNovaContext(['current_valuation']); return }
    const topFactors = (mv.adjustments || mv.top_factors || [])
      .slice?.(0, 5)
      .map(a => a?.label || a?.name || a?.factor_code || a)
      .filter(Boolean)
    setNovaContext({
      current_valuation: {
        fair_value: mv.fair_market_value,
        fair_value_text: fmtVnd(mv.fair_market_value),
        range_low: mv.expected_range_low,
        range_high: mv.expected_range_high,
        property_type: PROPERTY_TYPES?.[propertyType] || propertyType,
        district: lastPayload?.district,
        area: lastPayload?.area_m2,
        confidence_grade: resultGrade,
        confidence: resultConf ? `${(resultConf * 100).toFixed(0)}%` : undefined,
        top_factors: topFactors,
      },
    })
    return () => clearNovaContext(['current_valuation'])
  }, [v2Result, propertyType, lastPayload, resultGrade, resultConf])

  return (
    <div className="pred-pro">
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

      <PredictionReadinessStrip
        isAdmin={isAdmin}
        scopeText={scopeText}
        engineLabel={engineInfo?.button_label}
        modelProvenance={modelComparison?.metric_provenance}
        pipelineResult={pipelineResult}
        loading={loading || repredicting}
      />

      {/* Hero giá trị — cập nhật trực tiếp khi đổi thông số (ẩn ở tab Kết quả) */}
      {v2Result?.market_valuation && activeTab !== 'result' && (
        <div className="pp-hero" style={{ margin: '1rem 0 1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14, flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: 220 }}>
              <div className="pp-hero-label">Giá trị thị trường ước tính</div>
              <div className="pp-hero-price">{fmtVnd(v2Result.market_valuation.fair_market_value)}</div>
              <div className="pp-hero-sub">
                {PROPERTY_TYPES?.[propertyType] || propertyType}
                {lastPayload?.district ? ` · ${lastPayload.district}` : ''}
                {lastPayload?.area_m2 ? ` · ${lastPayload.area_m2} m²` : ''}
                {(v2Result.market_valuation.expected_range_low && v2Result.market_valuation.expected_range_high)
                  ? ` · khoảng ${fmtVnd(v2Result.market_valuation.expected_range_low)} – ${fmtVnd(v2Result.market_valuation.expected_range_high)}` : ''}
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'flex-end' }}>
              <span className="pp-hero-chip">
                <span className="pp-live-dot" />
                {repredicting ? 'Đang cập nhật giá...' : staleLocation ? 'Cần dự đoán lại' : 'Cập nhật trực tiếp'}
              </span>
              {iotSignal?.node_count > 0 && (
                <span className="pp-hero-chip" style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>{icon('radio', 13)} {iotSignal.node_count} cảm biến IoT</span>
              )}
              {pipelineResult?.valuation?.confidence_evidence?.confidence_grade && (
                <span className="pp-hero-chip">Độ tin cậy {pipelineResult.valuation.confidence_evidence.confidence_grade}</span>
              )}
            </div>
          </div>
        </div>
      )}


      {/* ── Tabs: cách nhập (trái) · kết quả khóa tới khi dự đoán (phải) ── */}
      <div className="pp-tabs" style={{ display: 'flex', alignItems: 'stretch', gap: '0.6rem', flexWrap: 'wrap', marginBottom: '1.5rem' }}>
        {ENTRY_TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`btn ${activeTab === t.key ? 'btn-primary' : 'btn-ghost'}`}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.45rem', padding: '0.65rem 1.2rem', fontSize: '0.92rem', fontWeight: 700 }}
          >
            {icon(t.iconKey, 18)}
            {t.label}
          </button>
        ))}

        <div style={{ width: 1, background: 'var(--border)', margin: '0 0.2rem' }} />

        {resultTabs.map(t => {
          const locked = !pipelineResult
          const active = activeTab === t.key
          return (
            <button
              key={t.key}
              onClick={() => { if (!locked) setActiveTab(t.key) }}
              disabled={locked}
              title={locked ? 'Cần dự đoán xong mới mở khóa' : ''}
              className={`btn ${active ? 'btn-primary' : 'btn-ghost'}`}
              style={{
                flex: '1 1 0', minWidth: 130, justifyContent: 'center',
                display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
                padding: `${(0.5 * resultScale).toFixed(2)}rem ${(0.9 * resultScale).toFixed(2)}rem`,
                fontSize: `${Math.min(0.82 + (resultScale - 1) * 0.4, 1.1).toFixed(2)}rem`,
                fontWeight: 700,
                opacity: locked ? 0.45 : 1,
                cursor: locked ? 'not-allowed' : 'pointer',
              }}
            >
              {icon(t.iconKey, Math.round(16 * resultScale / 1.5))}
              {t.label}
              {t.key === 'impact' && (
                <span className="pp-tab-admin-badge">
                  Admin
                </span>
              )}
              {locked && <span className="pp-tab-lock">{icon('lock', 12)}</span>}
            </button>
          )
        })}
      </div>

      <div className="pp-workspace">
        <PredictionCommandRail
          isAdmin={isAdmin}
          activeTab={activeTab}
          propertyType={propertyType}
          pipelineResult={pipelineResult}
          v2Result={v2Result}
          comparables={comparables}
          loading={loading}
          staleLocation={staleLocation}
          repredicting={repredicting}
          scopeText={scopeText}
          engineLabel={engineInfo?.button_label}
          modelProvenance={modelComparison?.metric_provenance}
        />

        <main className="pp-workspace-main">

      {/* ════════════════════════════════════════════════════════════
          TAB: MAP — Định vị thông minh (chọn vị trí → tự điền form)
      ════════════════════════════════════════════════════════════ */}
      {activeTab === 'map' && (
        <Suspense fallback={<LazyPanelFallback label="Đang tải bản đồ định vị..." />}>
          <MapLocationPicker
            propertyType={propertyType}
            onPropertyTypeChange={handlePropertyTypeChange}
            onConfirm={handleMapConfirm}
            onPredict={handleMapPredict}
          />
        </Suspense>
      )}

      {/* ════════════════════════════════════════════════════════════
          TAB: FORM + RESULTS
          Left: intake form | Right: v2 results (no decorative map)
      ════════════════════════════════════════════════════════════ */}
      {activeTab === 'form' && (
        <div>
          {/* Form (full width) */}
          <div className="card animate-fadeIn">
            <div className="card-header">
              <span className="stat-icon primary">{icon('house', 20)}</span>
              <span className="card-title">Thông tin bất động sản</span>
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
                <button
                  type="button"
                  onClick={clearAll}
                  title="Xóa toàn bộ thông tin đã nhập"
                  style={{
                    marginLeft: 'auto', display: 'inline-flex', alignItems: 'center', gap: '0.4rem',
                    padding: '0.5rem 0.875rem', borderRadius: 'var(--radius)',
                    fontSize: '0.8rem', fontWeight: 700, cursor: 'pointer',
                    border: '1px solid var(--danger, #ef233c)', background: 'transparent',
                    color: 'var(--danger, #ef233c)',
                  }}
                >
                  Xóa hết
                </button>
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
              <LandIntakeForm key={`land-${resetKey}`} onSubmit={handleV2Submit} loading={loading} isAdmin={isAdmin} engineLabel={engineInfo?.button_label} prefill={prefill} onLiveChange={handleLiveChange} />
            )}
            {V2_SUPPORTED.has(propertyType) && propertyType === 'apartment' && (
              <ApartmentIntakeForm key={`apartment-${resetKey}`} onSubmit={handleV2Submit} loading={loading} isAdmin={isAdmin} engineLabel={engineInfo?.button_label} prefill={prefill} onLiveChange={handleLiveChange} />
            )}
            {V2_SUPPORTED.has(propertyType) && propertyType === 'townhouse' && (
              <TownhouseIntakeForm key={`townhouse-${resetKey}`} onSubmit={handleV2Submit} loading={loading} isAdmin={isAdmin} engineLabel={engineInfo?.button_label} prefill={prefill} onLiveChange={handleLiveChange} />
            )}
            {V2_SUPPORTED.has(propertyType) && propertyType === 'villa' && (
              <VillaIntakeForm key={`villa-${resetKey}`} onSubmit={handleV2Submit} loading={loading} isAdmin={isAdmin} engineLabel={engineInfo?.button_label} prefill={prefill} onLiveChange={handleLiveChange} />
            )}
            {V2_SUPPORTED.has(propertyType) && propertyType === 'house' && (
              <HouseIntakeForm key={`house-${resetKey}`} onSubmit={handleV2Submit} loading={loading} isAdmin={isAdmin} engineLabel={engineInfo?.button_label} prefill={prefill} onLiveChange={handleLiveChange} />
            )}

            {/* Ảnh BĐS (tùy chọn) — tham chiếu trực quan, không bắt buộc */}
            <div style={{ marginTop: '1rem', padding: '0.75rem 0.9rem', border: '1px dashed var(--border)', borderRadius: 'var(--radius)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: '0.8rem', fontWeight: 700, color: 'var(--primary)', cursor: 'pointer' }}>
                  {icon('plus', 14)} Tải ảnh bất động sản (tùy chọn)
                  <input type="file" accept="image/*" multiple onChange={onFormUpload} style={{ display: 'none' }} />
                </label>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Ảnh dùng để tham chiếu trực quan, không bắt buộc và không thay đổi giá dự đoán.</span>
              </div>
              {formPhotos.length > 0 && (
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
                  {formPhotos.map((p, i) => (
                    <div key={i} style={{ position: 'relative' }}>
                      <img src={p.url} alt={p.name} style={{ width: 56, height: 56, borderRadius: 8, objectFit: 'cover', border: '1px solid var(--border)' }} />
                      <button type="button" onClick={() => setFormPhotos(ph => ph.filter((_, j) => j !== i))}
                        style={{ position: 'absolute', top: -6, right: -6, width: 18, height: 18, borderRadius: '50%', border: 'none', background: 'var(--danger, #ef233c)', color: '#fff', cursor: 'pointer', fontSize: 11, lineHeight: '18px', padding: 0 }}>×</button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ════════════════════════════════════════════════════════════
          TAB: RESULT — trang kết quả riêng (full-width)
      ════════════════════════════════════════════════════════════ */}
      {activeTab === 'result' && (
        <div className="animate-fadeIn">
          <div>
            {error && (
              <div className="alert alert-danger mb-4">
                <span className="alert-icon">{icon('warning', 16)}</span>
                <span>{error}</span>
              </div>
            )}

            {pipelineResult && (
              <div className="animate-scaleIn" style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>

                {/* Thanh tóm tắt + hành động */}
                <div className="pp-result-bar">
                  <div style={{ minWidth: 0 }}>
                    <div className="pp-result-title">Kết quả định giá</div>
                    <div className="pp-result-chips">
                      <span className="pp-result-chip">{PROPERTY_TYPES?.[propertyType] || propertyType}</span>
                      {lastPayload?.district && <span className="pp-result-chip">{lastPayload.district}</span>}
                      {lastPayload?.ward && <span className="pp-result-chip">{lastPayload.ward}</span>}
                      {(lastPayload?.area_m2 || lastPayload?.land_area_m2) && (
                        <span className="pp-result-chip">{lastPayload.area_m2 || lastPayload.land_area_m2} m²</span>
                      )}
                    </div>
                  </div>
                  <div className="pp-result-actions">
                    {resultGrade && (
                      <span className="pp-grade-pill" style={{ background: `${resultGradeColor}18`, color: resultGradeColor, border: `1px solid ${resultGradeColor}40` }}>
                        {icon('shieldCheck', 14)} Độ tin cậy {resultGrade} · {(resultConf * 100).toFixed(0)}%
                      </span>
                    )}
                    <button className="btn btn-ghost btn-sm" onClick={() => setActiveTab('form')}>← Sửa biểu mẫu</button>
                    <button className="btn btn-primary btn-sm" disabled={repredicting || loading} onClick={() => lastPayload && runPrediction(lastPayload)}>
                      {repredicting ? 'Đang tính...' : 'Định giá lại'}
                    </button>
                  </div>
                </div>

                {/* Trạng thái cập nhật giá trực tiếp */}
                {repredicting && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '0.5rem 0.75rem', borderRadius: 8, background: 'var(--primary-50)', border: '1px solid var(--primary-200)', fontSize: '0.78rem', color: 'var(--primary)' }}>
                    <span className="spinner" style={{ width: 14, height: 14 }} />
                    Đang cập nhật giá theo thay đổi...
                  </div>
                )}
                {staleLocation && !repredicting && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '0.5rem 0.75rem', borderRadius: 8, background: '#f59e0b15', border: '1px solid #f59e0b50', fontSize: '0.78rem' }}>
                    <span>{icon('pin', 14)}</span>
                    <span>Bạn đã đổi <strong>vị trí/khu vực</strong> — giá hiện tại không còn đúng. Bấm <strong>Dự đoán</strong> để cập nhật.</span>
                  </div>
                )}

                {/* Tín hiệu IoT khu vực đã phát khi dự đoán */}
                {iotSignal && (
                  <div style={{
                    padding: '0.6rem 0.8rem', borderRadius: 10, fontSize: '0.76rem',
                    background: iotSignal.node_count > 0 ? '#06d6a012' : '#f59e0b12',
                    border: `1px solid ${iotSignal.node_count > 0 ? '#06d6a040' : '#f59e0b40'}`,
                  }}>
                    <strong style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>{icon('radio', 14)} Tín hiệu IoT khu vực</strong>{' '}
                    {iotSignal.node_count > 0
                      ? `— thu từ ${iotSignal.node_count} node cảm biến (gần nhất ${iotSignal.nearest_node_m}m). Ồn ${iotSignal.readings?.noise_level ?? '—'}dB · ${iotSignal.readings?.temperature ?? '—'}°C · ${iotSignal.readings?.humidity ?? '—'}%`
                      : '— không có node trong vùng, dùng ước lượng theo quận.'}
                  </div>
                )}

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

                {/* Valuation Result Card — 3-layer output (đầy đủ) */}
                {v2Result && <ValuationResultCard result={v2Result} />}

                {/* SDEV — đẩy lên trên để trực quan hóa cung-cầu */}
                {(sdevResult || sdevLoading) && (
                  <SDEVResultCard sdev={sdevResult} loading={sdevLoading} />
                )}

                {v2Result && (
                  <ResultEvidenceSummary comparables={comparables} input={lastPayload} />
                )}

                {/* Trực quan hóa (full-width) */}
                {v2Result && lastPayload && (
                  <Suspense fallback={<LazyPanelFallback label="Đang tải trực quan hóa tài sản..." />}>
                    <PropertyVisualizer payload={lastPayload} propertyType={propertyType} userPhotos={formPhotos} />
                  </Suspense>
                )}

              </div>
            )}

            {loading && !pipelineResult && (
              <div className="card" style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-muted)' }}>
                <span className="spinner" style={{ width: 26, height: 26, display: 'inline-block' }} />
                <p style={{ marginTop: '0.75rem', fontSize: '0.9rem' }}>Đang chạy Valuation Engine v2...</p>
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
              <Suspense fallback={<LazyPanelFallback label="Đang tải phân tích tác động..." />}>
                <ImpactAnalysisPanel
                  formData={{
                    ...lastPayload,
                    asset_type: PROPERTY_TO_ASSET[propertyType] || propertyType.toUpperCase(),
                  }}
                  runId={pipelineResult.pipeline_id}
                />
              </Suspense>
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
        </main>
      </div>
    </div>
  )
}

export default Prediction
