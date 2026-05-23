import React, { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { icon } from '../../components/ui/icons'
import { VISUAL_ASSETS } from '../../constants/visuals'

const API_BASE = '/api'

// ─── Format helpers ───────────────────────────────────────────────────────────
const fmtVND = (n) => {
  if (!n) return ''
  return Math.round(n / 1e9 * 100) / 100 + ' tỷ'
}

const fmtBudget = (val) => {
  if (!val) return ''
  return Math.round(val / 1e9 * 100) / 100 + ' tỷ'
}

const formatBudget = (val) => {
  if (!val) return ''
  return Math.round(val / 1e9 * 100) / 100
}

// ─── Constants ────────────────────────────────────────────────────────────────
const DISTRICTS = [
  { value: 'Quận Cầu Giấy', label: 'Quận Cầu Giấy', note: 'Cao cấp, gần ĐH Quốc gia' },
  { value: 'Quận Thanh Xuân', label: 'Quận Thanh Xuân', note: 'Trung cấp, khu mới phát triển' },
  { value: 'Quận Đống Đa', label: 'Quận Đống Đa', note: 'Trung tâm, hạ tầng đồng bộ' },
]
const PROPERTY_TYPES = [
  { value: 'apartment', label: 'Căn hộ chung cư', iconKey: 'apartment' },
  { value: 'house', label: 'Nhà riêng', iconKey: 'house' },
  { value: 'townhouse', label: 'Nhà phố liền kề', iconKey: 'townhouse' },
  { value: 'land', label: 'Đất nền', iconKey: 'land' },
]
const BEDROOM_OPTIONS = [
  { value: '1', label: '1 PN' },
  { value: '2', label: '2 PN' },
  { value: '3', label: '3 PN' },
  { value: '4', label: '4 PN' },
  { value: '5', label: '5+ PN' },
]
const LEGAL_OPTIONS = [
  { value: 'ownership_certificate', label: 'Sổ đỏ / Sổ hồng (Chủ quyền)' },
  { value: 'land_use_right', label: 'Hợp đồng mua bán (Quyền sử dụng)' },
  { value: 'any', label: 'Không yêu cầu' },
]
const URGENCY_OPTIONS = [
  { value: 'urgent', label: 'Gấp (dưới 1 tháng)', color: '#ef233c' },
  { value: 'normal', label: 'Bình thường (1-3 tháng)', color: '#f59e0b' },
  { value: 'flexible', label: 'Thong thả (3-6 tháng)', color: '#06b6d4' },
]

// ─── Validation ──────────────────────────────────────────────────────────────
function validate(data) {
  const errs = {}
  if (!data.district) errs.district = 'Vui lòng chọn quận'
  if (!data.property_type) errs.property_type = 'Vui lòng chọn loại bất động sản'
  const minB = parseFloat(data.min_budget)
  const maxB = parseFloat(data.max_budget)
  if (!minB || minB < 0.5) errs.min_budget = 'Ngân sách tối thiểu phải từ 500 triệu'
  if (!maxB || maxB < 0.5) errs.max_budget = 'Ngân sách tối đa phải từ 500 triệu'
  if (minB && maxB && maxB < minB) errs.max_budget = 'Ngân sách tối đa phải >= ngân sách tối thiểu'
  if (minB && maxB && maxB / minB > 3) errs.max_budget = 'Khoảng min-max không nên chênh quá 3 lần'
  const minA = parseFloat(data.min_area)
  const maxA = parseFloat(data.max_area)
  if (minA && maxA && maxA < minA) errs.max_area = 'Diện tích tối đa phải >= diện tích tối thiểu'
  return errs
}

// ─── API ─────────────────────────────────────────────────────────────────────
async function submitBuyerRequirement(data) {
  const payload = {
    property_type: data.property_type || 'apartment',
    province_city: 'Hà Nội',
    district: data.district,
    ward: data.ward || null,
    min_area: data.min_area ? parseFloat(data.min_area) : null,
    max_area: data.max_area ? parseFloat(data.max_area) : null,
    min_budget: Math.round(parseFloat(data.min_budget) * 1e9),
    max_budget: Math.round(parseFloat(data.max_budget) * 1e9),
    bedrooms: data.bedrooms ? parseInt(data.bedrooms) : null,
    legal_requirement: data.legal_requirement || 'any',
    urgency: data.urgency || 'normal',
    source_type: 'survey',
    notes: data.notes || null,
  }

  const res = await fetch(`${API_BASE}/research/buyer-requirement`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Lỗi không xác định' }))
    throw new Error(err.detail || res.statusText)
  }
  return res.json()
}

async function fetchStats() {
  const res = await fetch(`${API_BASE}/research/evaluation-summary`)
  if (!res.ok) return null
  return res.json()
}

// ─── Step 1: Requirements Form ─────────────────────────────────────────────
function RequirementsForm({ data, errors, onChange }) {
  return (
    <>
      <div className="survey-form-section-title">
        <span>01</span>
        <div>
          <strong>Nhu cầu cốt lõi</strong>
          <p>Chọn loại tài sản, khu vực, ngân sách và quy mô mong muốn.</p>
        </div>
      </div>

      {/* Property type */}
      <div className="form-group">
        <label className="form-label">Loại bất động sản *</label>
        <div className="flex gap-2 flex-wrap">
          {PROPERTY_TYPES.map(pt => (
            <button
              key={pt.value}
              type="button"
              onClick={() => onChange('property_type', pt.value)}
              style={{
                flex: '1 1 120px',
                padding: '0.75rem',
                border: `2px solid ${data.property_type === pt.value ? 'var(--primary)' : 'var(--border)'}`,
                borderRadius: 10,
                background: data.property_type === pt.value ? 'var(--primary-50)' : 'transparent',
                color: data.property_type === pt.value ? 'var(--primary)' : 'var(--text-secondary)',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.85rem',
                textAlign: 'center',
                transition: 'all 150ms',
              }}
            >
              <div style={{ marginBottom: '0.35rem' }}>{icon(pt.iconKey, 18)}</div>
              <div style={{ fontWeight: 600, fontSize: '0.8rem' }}>{pt.label}</div>
            </button>
          ))}
        </div>
        {errors.property_type && <div className="form-error">{errors.property_type}</div>}
      </div>

      {/* District */}
      <div className="form-group">
        <label className="form-label">Quận mong muốn *</label>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem' }}>
          { DISTRICTS.map(d => (
            <button
              key={d.value}
              type="button"
              onClick={() => onChange('district', d.value)}
              style={{
                padding: '0.75rem',
                border: `2px solid ${data.district === d.value ? 'var(--primary)' : 'var(--border)'}`,
                borderRadius: 10,
                background: data.district === d.value ? 'var(--primary-50)' : 'transparent',
                color: data.district === d.value ? 'var(--primary)' : 'var(--text-secondary)',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.85rem',
                textAlign: 'center',
              }}
            >
              <div style={{ fontWeight: 700, marginBottom: 2 }}>{d.label}</div>
              <div style={{ fontSize: '0.7rem', fontWeight: 400, opacity: 0.7 }}>{d.note}</div>
            </button>
          ))}
        </div>
        {errors.district && <div className="form-error">{errors.district}</div>}
      </div>

      {/* Budget range */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <div className="form-group">
          <label className="form-label">Ngân sách tối thiểu (tỷ VND) *</label>
          <input
            type="number"
            className={`form-input ${errors.min_budget ? 'error' : ''}`}
            value={data.min_budget || ''}
            onChange={e => onChange('min_budget', e.target.value)}
            placeholder="VD: 3.5"
            min="0.5"
            max="50"
            step="0.1"
          />
          {data.min_budget && <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>≈ {fmtVND(parseFloat(data.min_budget) * 1e9)}</div>}
          {errors.min_budget && <div className="form-error">{errors.min_budget}</div>}
        </div>
        <div className="form-group">
          <label className="form-label">Ngân sách tối đa (tỷ VND) *</label>
          <input
            type="number"
            className={`form-input ${errors.max_budget ? 'error' : ''}`}
            value={data.max_budget || ''}
            onChange={e => onChange('max_budget', e.target.value)}
            placeholder="VD: 6.5"
            min="0.5"
            max="50"
            step="0.1"
          />
          {data.max_budget && <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>≈ {fmtVND(parseFloat(data.max_budget) * 1e9)}</div>}
          {errors.max_budget && <div className="form-error">{errors.max_budget}</div>}
        </div>
      </div>

      {/* Budget visualization */}
      {data.min_budget && data.max_budget && !errors.min_budget && !errors.max_budget && (
        <div style={{
          background: 'var(--success-bg)',
          border: '1px solid var(--success-border)',
          borderRadius: 10,
          padding: '0.75rem 1rem',
          marginBottom: '1rem',
        }}>
          <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--success)', marginBottom: 4 }}>
            Khoảng ngân sách: {data.min_budget} – {data.max_budget} tỷ VND
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ flex: 1, height: 8, background: 'var(--success-border)', borderRadius: 4 }}>
              <div style={{
                width: '100%',
                height: '100%',
                background: 'var(--success)',
                borderRadius: 4,
              }} />
            </div>
          </div>
        </div>
      )}

      {/* Area range */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <div className="form-group">
          <label className="form-label">Diện tích tối thiểu (m²)</label>
          <input
            type="number"
            className="form-input"
            value={data.min_area || ''}
            onChange={e => onChange('min_area', e.target.value)}
            placeholder="VD: 50"
            min="20"
            max="300"
            step="5"
          />
          {errors.max_area && <div className="form-error">{errors.max_area}</div>}
        </div>
        <div className="form-group">
          <label className="form-label">Diện tích tối đa (m²)</label>
          <input
            type="number"
            className="form-input"
            value={data.max_area || ''}
            onChange={e => onChange('max_area', e.target.value)}
            placeholder="VD: 90"
            min="20"
            max="300"
            step="5"
          />
        </div>
      </div>

      {/* Bedrooms */}
      <div className="form-group">
        <label className="form-label">Số phòng ngủ mong muốn</label>
        <div className="flex gap-2">
          {BEDROOM_OPTIONS.map(opt => (
            <button
              key={opt.value}
              type="button"
              onClick={() => onChange('bedrooms', opt.value === data.bedrooms ? '' : opt.value)}
              className={`btn btn-sm ${data.bedrooms === opt.value ? 'btn-primary' : 'btn-ghost'}`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
    </>
  )
}

// ─── Step 2: Legal + Urgency ─────────────────────────────────────────────────
function LegalUrgencyForm({ data, errors, onChange }) {
  return (
    <>
      <div className="survey-form-section-title">
        <span>02</span>
        <div>
          <strong>Pháp lý và thời hạn</strong>
          <p>Điều kiện mua và mức độ khẩn cấp của yêu cầu.</p>
        </div>
      </div>

      <div className="form-group">
        <label className="form-label">Yêu cầu pháp lý</label>
        <div className="flex flex-col gap-2">
          {LEGAL_OPTIONS.map(opt => (
            <label
              key={opt.value}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '0.75rem',
                border: `2px solid ${data.legal_requirement === opt.value ? 'var(--primary)' : 'var(--border)'}`,
                borderRadius: 10,
                cursor: 'pointer',
                background: data.legal_requirement === opt.value ? 'var(--primary-50)' : 'transparent',
                transition: 'all 150ms',
              }}
            >
              <input
                type="radio"
                name="legal_requirement"
                value={opt.value}
                checked={data.legal_requirement === opt.value}
                onChange={() => onChange('legal_requirement', opt.value)}
                style={{ accentColor: 'var(--primary)' }}
              />
              <span style={{ fontSize: '0.88rem', fontWeight: data.legal_requirement === opt.value ? 600 : 400 }}>
                {opt.label}
              </span>
            </label>
          ))}
        </div>
      </div>

      <div className="form-group">
        <label className="form-label">Thời hạn tìm mua</label>
        <div className="flex gap-2">
          {URGENCY_OPTIONS.map(opt => (
            <button
              key={opt.value}
              type="button"
              onClick={() => onChange('urgency', opt.value)}
              style={{
                flex: 1,
                padding: '0.75rem',
                border: `2px solid ${data.urgency === opt.value ? opt.color : 'var(--border)'}`,
                borderRadius: 10,
                background: data.urgency === opt.value ? opt.color + '20' : 'transparent',
                color: data.urgency === opt.value ? opt.color : 'var(--text-secondary)',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.82rem',
                transition: 'all 150ms',
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      <div className="form-group">
        <label className="form-label">Ghi chú thêm (tùy chọn)</label>
        <textarea
          className="form-input"
          value={data.notes || ''}
          onChange={e => onChange('notes', e.target.value)}
          placeholder="VD: Cần gần trường học, thích view công viên, ưu tiên tầng cao..."
          rows={3}
          style={{ resize: 'vertical', minHeight: 80 }}
        />
      </div>
    </>
  )
}

// ─── Success Screen ──────────────────────────────────────────────────────────
function SuccessScreen({ result, onReset }) {
  return (
    <div style={{ textAlign: 'center', padding: '3rem 1rem' }}>
      <div style={{ fontSize: '3rem', marginBottom: '1rem' }} />
      <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem', color: 'var(--success)' }}>
        Cảm ơn bạn!
      </h2>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem', maxWidth: 480, margin: '0 auto 2rem' }}>
        Yêu cầu tìm mua của bạn đã được ghi nhận. Dữ liệu sẽ được dùng để cải thiện mô hình ước lượng vùng giá chấp nhận thị trường BĐS Hà Nội.
      </p>

      <div className="card" style={{ textAlign: 'left', maxWidth: 400, margin: '0 auto 2rem' }}>
        <div className="card-header">
          <span className="card-title">Tóm tắt yêu cầu</span>
        </div>
        <div style={{ padding: '1rem', display: 'grid', gap: '0.75rem' }}>
          <div className="flex justify-between">
            <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Quận</span>
            <span style={{ fontWeight: 600 }}>{result.district}</span>
          </div>
          <div className="flex justify-between">
            <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Ngân sách</span>
            <span style={{ fontWeight: 600, color: 'var(--success)' }}>{result.budget_range_b} tỷ</span>
          </div>
          <div className="flex justify-between">
            <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>ID</span>
            <span style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>#{result.id}</span>
          </div>
        </div>
      </div>

      <div style={{
        background: 'var(--info-bg)',
        border: '1px solid var(--info-border)',
        borderRadius: 10,
        padding: '1rem',
        maxWidth: 480,
        margin: '0 auto 2rem',
        fontSize: '0.82rem',
        color: 'var(--info)',
        lineHeight: 1.6,
      }}>
        <strong>Nghiên cứu này:</strong> Dữ liệu của bạn giúp xây dựng mô hình SDEV (Supply-Demand Equilibrium Valuation) — ước lượng vùng giá chấp nhận thị trường từ tín hiệu cung-cầu.
        Kết quả không phải tư vấn đầu tư.
      </div>

      <button
        onClick={onReset}
        className="btn btn-primary"
        style={{ padding: '0.75rem 2rem' }}
      >
        Điền yêu cầu mới
      </button>
    </div>
  )
}

// ─── Main Component ──────────────────────────────────────────────────────────
export default function BuyerSurvey() {
  const [step, setStep] = useState(1)
  const [submitted, setSubmitted] = useState(false)
  const [submitResult, setSubmitResult] = useState(null)
  const [errors, setErrors] = useState({})

  const [formData, setFormData] = useState({
    property_type: 'apartment',
    district: '',
    min_budget: '',
    max_budget: '',
    min_area: '',
    max_area: '',
    bedrooms: '',
    legal_requirement: 'any',
    urgency: 'normal',
    notes: '',
    ward: '',
  })

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    if (errors[field]) setErrors(prev => ({ ...prev, [field]: '' }))
  }

  const handleNext = () => {
    const step1Errors = validate(formData)
    if (Object.keys(step1Errors).length > 0) {
      setErrors(step1Errors)
      return
    }
    setErrors({})
    setStep(2)
  }

  const mutation = useMutation({
    mutationFn: submitBuyerRequirement,
    onSuccess: (data) => {
      setSubmitResult(data)
      setSubmitted(true)
    },
  })

  const handleSubmit = () => {
    const allErrors = validate(formData)
    if (Object.keys(allErrors).length > 0) {
      setErrors(allErrors)
      setStep(1)
      return
    }
    mutation.mutate(formData)
  }

  const handleReset = () => {
    setFormData({
      property_type: 'apartment',
      district: '',
      min_budget: '',
      max_budget: '',
      min_area: '',
      max_area: '',
      bedrooms: '',
      legal_requirement: 'any',
      urgency: 'normal',
      notes: '',
      ward: '',
    })
    setErrors({})
    setStep(1)
    setSubmitted(false)
    setSubmitResult(null)
  }

  // ── Stats query ──────────────────────────────────────────────────────────
  const { data: stats } = useQuery({
    queryKey: ['evaluation-summary'],
    queryFn: fetchStats,
    staleTime: 60 * 1000,
  })

  if (submitted) {
    return (
      <div>
        <div className="survey-hero animate-fadeIn">
          <div className="survey-hero-copy">
            <div className="survey-hero-eyebrow">Buyer demand study</div>
            <h1 className="survey-hero-title">Khảo sát nhu cầu tìm mua BĐS</h1>
            <p className="survey-hero-description">Cảm ơn bạn đã tham gia nghiên cứu!</p>
          </div>
        </div>
        <SuccessScreen result={submitResult} onReset={handleReset} />
      </div>
    )
  }

  return (
    <div>
      <div className="survey-hero animate-fadeIn">
        <div className="survey-hero-copy">
          <div className="survey-hero-eyebrow">Buyer demand study</div>
          <h1 className="survey-hero-title">Khảo sát nhu cầu tìm mua BĐS</h1>
          <p className="survey-hero-description">
            Giúp nghiên cứu ước lượng vùng giá chấp nhận thị trường bằng tín hiệu cung-cầu.
            Mẫu của bạn trở thành tín hiệu thật cho mô hình, không phải dữ liệu demo.
          </p>
          <div className="survey-hero-points">
            <span className="survey-hero-chip">2 bước</span>
            <span className="survey-hero-chip">Pilot 3 quận Hà Nội</span>
            <span className="survey-hero-chip">Ẩn danh / có thể bổ sung</span>
          </div>
        </div>

        <div className="survey-hero-media">
          <div className="survey-hero-shot">
            <img src={VISUAL_ASSETS.houseExterior} alt="Bất động sản thực dùng cho khảo sát nhu cầu" />
            <div className="survey-hero-shot-label">
              <span className="survey-hero-shot-kicker">Demand input</span>
              <strong>Dữ liệu khảo sát tác động trực tiếp đến mô hình cầu</strong>
              <span className="survey-hero-mini-caption">Giá, diện tích, khu vực và thời hạn mua được lưu như tín hiệu thật.</span>
            </div>
          </div>
          <div className="survey-hero-mini-stack">
            <div className="survey-hero-metric">
              <span>{stats?.buyer_requirements?.total_active || 0}</span>
              <strong>Yêu cầu đã thu thập</strong>
            </div>
            <div className="survey-hero-metric">
              <span>{stats?.expert_evaluation?.completed || 0}/{stats?.expert_evaluation?.total_properties || 50}</span>
              <strong>Expert đánh giá xong</strong>
            </div>
            <div className="survey-hero-metric">
              <span>{stats?.buyer_requirements?.target || 200}</span>
              <strong>Mục tiêu thu thập</strong>
            </div>
          </div>
        </div>
      </div>

      <div className="survey-context-strip">
        <strong>Nghiên cứu SDEV</strong>
        <span>Dữ liệu của bạn được dùng để xây dựng tín hiệu cầu cho mô hình ước lượng vùng giá chấp nhận. Kết quả chỉ dùng cho nghiên cứu khoa học, không phải tư vấn đầu tư.</span>
      </div>

      {/* Step indicator */}
      <div className="survey-step-rail" style={{
        display: 'flex',
        gap: '0.5rem',
        marginBottom: '1.5rem',
        alignItems: 'center',
      }}>
        {[1, 2].map(s => (
          <React.Fragment key={s}>
            <div style={{
              width: 32,
              height: 32,
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 700,
              fontSize: '0.85rem',
              background: step >= s ? 'var(--primary)' : 'var(--border)',
              color: step >= s ? 'white' : 'var(--text-muted)',
              transition: 'all 200ms',
            }}>
              {step > s ? '✓' : s}
            </div>
            <div style={{
              flex: s === 1 ? 'none' : 1,
              height: 2,
              background: s < 2 && step > 1 ? 'var(--primary)' : 'var(--border)',
              transition: 'all 200ms',
            }} />
          </React.Fragment>
        ))}
        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginLeft: 8 }}>
          Bước {step}/2: {step === 1 ? 'Nhu cầu cơ bản' : 'Pháp lý & Thời hạn'}
        </span>
      </div>

      {/* Form card */}
      <div className="card animate-fadeIn survey-form-card">
        <div className="card-header">
          <span className="stat-icon primary">{icon('home', 18)}</span>
          <span className="card-title">
            {step === 1 ? 'Nhu cầu tìm mua của bạn' : 'Yêu cầu bổ sung'}
          </span>
          {step === 1 && (
            <span className="badge badge-neutral" style={{ marginLeft: 'auto', fontSize: '0.7rem' }}>
              1/2 bước
            </span>
          )}
        </div>

        <div style={{ padding: '1.5rem' }}>
          {step === 1 ? (
            <RequirementsForm data={formData} errors={errors} onChange={handleChange} />
          ) : (
            <LegalUrgencyForm data={formData} errors={errors} onChange={handleChange} />
          )}

          {/* Navigation */}
          <div className="flex gap-2" style={{ marginTop: '1.5rem', justifyContent: 'space-between' }}>
            {step > 1 ? (
              <button
                onClick={() => setStep(1)}
                className="btn btn-ghost"
              >
                ← Quay lại
              </button>
            ) : <div />}

            {step === 1 ? (
              <button
                onClick={handleNext}
                className="btn btn-primary"
                style={{ padding: '0.75rem 2rem' }}
              >
                Tiếp tục →
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={mutation.isPending}
                className="btn btn-primary"
                style={{ padding: '0.75rem 2rem' }}
              >
                {mutation.isPending ? (
                  <><span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} /> Đang gửi...</>
                ) : (
                  <>{icon('checkCircle', 16)} Gửi yêu cầu</>
                )}
              </button>
            )}
          </div>

          {/* Error */}
          {mutation.isError && (
            <div className="alert alert-danger mt-4">
              <span className="alert-icon">{icon('warning', 16)}</span>
              <span>{mutation.error.message}</span>
            </div>
          )}
        </div>
      </div>

      {/* Privacy note */}
      <div style={{
        marginTop: '1rem',
        padding: '0.875rem 1rem',
        background: 'var(--bg-elevated)',
        borderRadius: 10,
        fontSize: '0.78rem',
        color: 'var(--text-muted)',
        lineHeight: 1.6,
      }}>
        <strong>Quyền riêng tư:</strong> Dữ liệu của bạn được lưu trữ ẩn danh, chỉ dùng cho nghiên cứu.
        Không chia sẻ cho bên thứ ba. Xem chi tiết trong paper/pilot_paper.md.
      </div>
    </div>
  )
}
