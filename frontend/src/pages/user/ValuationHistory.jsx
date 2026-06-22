import React, { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { listValuationRuns, submitValuationFeedback } from '../../api'
import { icon } from '../../components/ui/icons'

const FEEDBACK_SOURCES = [
  ['sale_contract', 'Hợp đồng mua bán'],
  ['notarized_contract', 'Hợp đồng công chứng'],
  ['bank_appraisal', 'Thẩm định ngân hàng'],
  ['expert_verified', 'Chuyên gia xác minh'],
  ['owner_report', 'Chủ sở hữu báo giá'],
]

function formatVnd(value) {
  if (!value) return 'Chưa có'
  return new Intl.NumberFormat('vi-VN', {
    style: 'currency',
    currency: 'VND',
    maximumFractionDigits: 0,
  }).format(value)
}

function formatDate(value) {
  if (!value) return 'Chưa ghi'
  return new Intl.DateTimeFormat('vi-VN', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(value))
}

function feedbackBadge(status) {
  if (status === 'verified') return ['badge-success', 'Đã duyệt']
  if (status === 'pending_review') return ['badge-warning', 'Chờ duyệt']
  if (status === 'rejected') return ['badge-danger', 'Từ chối']
  return ['badge-neutral', 'Chưa gửi']
}

export default function ValuationHistory() {
  const [searchParams] = useSearchParams()
  const needsSelection = searchParams.get('reason') === 'select-valuation'
  const [runs, setRuns] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeRequestId, setActiveRequestId] = useState('')
  const [feedback, setFeedback] = useState({
    actual_price_vnd: '',
    actual_price_source: 'sale_contract',
    evidence_ref: '',
  })
  const [submitting, setSubmitting] = useState(false)

  const selectedRun = useMemo(
    () => runs.find((item) => item.request_id === activeRequestId),
    [runs, activeRequestId],
  )

  async function loadRuns() {
    setLoading(true)
    setError('')
    try {
      const data = await listValuationRuns(30)
      setRuns(data.runs || [])
    } catch (err) {
      setError(err.message || 'Không tải được lịch sử định giá')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadRuns()
  }, [])

  async function handleFeedbackSubmit(event) {
    event.preventDefault()
    if (!activeRequestId) return
    setSubmitting(true)
    setError('')
    try {
      await submitValuationFeedback(activeRequestId, {
        actual_price_vnd: Number(feedback.actual_price_vnd),
        actual_price_source: feedback.actual_price_source,
        evidence_ref: feedback.evidence_ref.trim(),
      })
      setFeedback({ actual_price_vnd: '', actual_price_source: 'sale_contract', evidence_ref: '' })
      await loadRuns()
    } catch (err) {
      setError(err.message || 'Không gửi được giá thực tế')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="container" style={{ paddingBlock: '2rem' }}>
      <div className="page-header" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
        <div>
          <span className="badge badge-primary">{icon('activity', 14)} Không gian định giá</span>
          <h1>Lịch sử định giá</h1>
          <p>{needsSelection ? 'Chọn một lần định giá để tiếp tục xem bằng chứng.' : 'Theo dõi các lần định giá, feedback giá thật và trạng thái đưa vào training.'}</p>
        </div>
        <div style={{ display: 'flex', gap: '.5rem', flexWrap: 'wrap' }}>
          <button className="btn btn-secondary" type="button" onClick={loadRuns} disabled={loading}>
            {loading ? icon('loader', 16) : icon('refreshCw', 16)} Tải lại
          </button>
          <Link className="btn btn-primary" to="/app/valuations/new">{icon('plus', 16)} Định giá mới</Link>
        </div>
      </div>

      {error && (
        <div className="card" style={{ marginTop: '1rem', borderColor: 'var(--danger-border)', color: 'var(--danger)' }}>
          {icon('warning', 16)} {error}
        </div>
      )}

      {loading ? (
        <div className="card" style={{ marginTop: '1.5rem', display: 'flex', alignItems: 'center', gap: '.75rem' }}>
          {icon('loader', 18)} Đang tải lịch sử định giá...
        </div>
      ) : runs.length === 0 ? (
        <div className="empty-state" style={{ marginTop: '1.5rem' }}>
          <div className="empty-state-icon">{icon('database', 34)}</div>
          <h2>{needsSelection ? 'Chưa có lần định giá để chọn' : 'Chưa có định giá đã lưu'}</h2>
          <p>Dữ liệu lịch sử được lấy từ tài khoản thật trong PostgreSQL. Hệ thống không tạo bản ghi minh họa giả.</p>
          <Link className="btn btn-primary" to="/app/valuations/new">{icon('plus', 16)} Tạo định giá mới</Link>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr)', gap: '1rem', marginTop: '1.5rem' }}>
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div className="table-wrapper">
              <table className="table">
                <thead>
                  <tr>
                    <th>Lần định giá</th>
                    <th>Giá dự đoán</th>
                    <th>Confidence</th>
                    <th>Feedback</th>
                    <th>Training</th>
                    <th>Thao tác</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((run) => {
                    const [badgeClass, badgeText] = feedbackBadge(run.feedback_verification_status)
                    const isActive = run.request_id === activeRequestId
                    return (
                      <tr key={run.request_id} style={isActive ? { background: 'var(--bg-hover)' } : undefined}>
                        <td>
                          <div style={{ display: 'grid', gap: '.2rem' }}>
                            <strong>{run.source_endpoint}</strong>
                            <small style={{ color: 'var(--text-muted)' }}>{run.request_id}</small>
                            <small style={{ color: 'var(--text-muted)' }}>{formatDate(run.created_at)}</small>
                          </div>
                        </td>
                        <td>{formatVnd(run.fair_market_value_vnd)}</td>
                        <td>
                          <span className="badge badge-info">{run.confidence_grade || 'N/A'}</span>
                          <div style={{ marginTop: '.25rem', color: 'var(--text-muted)', fontSize: '.8rem' }}>
                            {run.overall_confidence ? `${Math.round(run.overall_confidence * 100)}%` : 'Chưa có'}
                          </div>
                        </td>
                        <td><span className={`badge ${badgeClass}`}>{badgeText}</span></td>
                        <td>
                          <span className={`badge ${run.training_eligible ? 'badge-success' : 'badge-neutral'}`}>
                            {run.training_eligible ? 'Sẵn sàng' : 'Chưa dùng'}
                          </span>
                        </td>
                        <td>
                          <button className="btn btn-sm btn-secondary" type="button" onClick={() => setActiveRequestId(run.request_id)}>
                            {icon(isActive ? 'check' : 'clipboard', 14)} {needsSelection ? 'Chọn' : 'Feedback'}
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card">
            {selectedRun ? (
              <form onSubmit={handleFeedbackSubmit} style={{ display: 'grid', gap: '1rem' }}>
                <div>
                  <span className="badge badge-neutral">{icon('clipboard', 14)} {selectedRun.request_id}</span>
                  <h2 style={{ margin: '.65rem 0 .25rem', fontSize: '1.25rem' }}>Gửi giá thực tế sau giao dịch</h2>
                  <p style={{ margin: 0, color: 'var(--text-secondary)' }}>
                    Giá này sẽ chờ admin xác minh trước khi được đưa vào training queue.
                  </p>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '.85rem' }}>
                  <label className="login-field" style={{ margin: 0 }}>
                    <span className="login-label">Giá thực tế VND</span>
                    <input
                      className="login-input"
                      type="number"
                      min="100000000"
                      step="1000000"
                      value={feedback.actual_price_vnd}
                      onChange={(event) => setFeedback((prev) => ({ ...prev, actual_price_vnd: event.target.value }))}
                      placeholder="7800000000"
                      required
                    />
                  </label>
                  <label className="login-field" style={{ margin: 0 }}>
                    <span className="login-label">Nguồn giá</span>
                    <select
                      className="login-input"
                      value={feedback.actual_price_source}
                      onChange={(event) => setFeedback((prev) => ({ ...prev, actual_price_source: event.target.value }))}
                    >
                      {FEEDBACK_SOURCES.map(([value, label]) => (
                        <option key={value} value={value}>{label}</option>
                      ))}
                    </select>
                  </label>
                  <label className="login-field" style={{ margin: 0 }}>
                    <span className="login-label">Mã/tài liệu tham chiếu</span>
                    <input
                      className="login-input"
                      value={feedback.evidence_ref}
                      onChange={(event) => setFeedback((prev) => ({ ...prev, evidence_ref: event.target.value }))}
                      placeholder="HDMB-2026-001"
                      minLength={3}
                      maxLength={500}
                      required
                    />
                  </label>
                </div>
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '.65rem', flexWrap: 'wrap' }}>
                  <button className="btn btn-ghost" type="button" onClick={() => setActiveRequestId('')}>
                    {icon('close', 14)} Đóng
                  </button>
                  <button className="btn btn-primary" type="submit" disabled={submitting}>
                    {submitting ? icon('loader', 16) : icon('shieldCheck', 16)} Gửi feedback
                  </button>
                </div>
              </form>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', gap: '.75rem', color: 'var(--text-secondary)' }}>
                {icon('info', 18)} Chọn một dòng trong lịch sử để gửi giá thực tế hoặc tiếp tục luồng bằng chứng.
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  )
}
