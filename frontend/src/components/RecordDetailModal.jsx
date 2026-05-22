import React from 'react'
import { PROPERTY_TYPES, VERIFICATION_STATUS } from '../constants/vnStrings'

function formatPrice(price) {
  if (!price) return '—'
  return new Intl.NumberFormat('vi-VN', {
    style: 'currency',
    currency: 'VND',
    maximumFractionDigits: 0
  }).format(price)
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  try {
    return new Date(dateStr).toLocaleString('vi-VN')
  } catch {
    return dateStr
  }
}

function truthyEntries(flags = {}) {
  return Object.entries(flags).filter(([, value]) => Boolean(value))
}

function RecordDetailModal({ open, record, onClose }) {
  if (!open || !record) return null

  const traceScore = Math.max(0, Math.min(10, record.trace_profile?.trace_completeness_score || 0))
  const primaryImage = record.image_url || record.image_urls?.[0]
  const gallery = record.image_urls || []
  const sourceLink = record.source_url || record.source_access_link || record.trace_profile?.source_access_link
  const verificationLabel = VERIFICATION_STATUS[record.verification_status] || record.verification_status || '—'

  const gradeColor = (grade) => {
    if (grade === 'verified') return 'var(--success)'
    if (grade === 'pending') return 'var(--warning)'
    if (grade === 'rejected') return 'var(--danger)'
    return 'var(--text-muted)'
  }

  const flagLabel = (key) => {
    const labels = {
      has_gps: 'GPS', has_coordinates: 'GPS', has_price: 'Giá', has_area: 'Diện tích',
      has_bedrooms: 'Phòng ngủ', has_bathrooms: 'Phòng tắm', has_source_link: 'Link nguồn',
      has_iot: 'IoT', has_image: 'Hình ảnh', has_floor: 'Số tầng',
      has_legal: 'Pháp lý', has_verification: 'Xác minh',
    }
    return labels[key] || key.replaceAll('_', ' ')
  }

  return (
    <div className="data-modal-overlay" onClick={onClose}>
      <div className="data-modal-panel animate-scaleIn" onClick={(e) => e.stopPropagation()}>
        <div className="data-modal-header">
          <div>
            <div className="eyebrow">Hồ sơ bản ghi</div>
            <h2>Bản ghi #{record.id}</h2>
            <div className="modal-chip-row">
              <span className={`badge ${record.data_origin_type === 'self_collected' ? 'badge-success' : 'badge-primary'}`}>
                {record.data_origin_type === 'self_collected' ? 'Tự thu thập' : 'Nguồn bên ngoài'}
              </span>
              <span className={`badge`} style={{
                background: `${gradeColor(record.verification_status)}20`,
                border: `1px solid ${gradeColor(record.verification_status)}50`,
                color: gradeColor(record.verification_status)
              }}>
                {verificationLabel}
              </span>
            </div>
          </div>
          <button className="modal-close" onClick={onClose}>Đóng</button>
        </div>

        <div className="record-detail-shell">
          <section className="record-hero-panel animate-fadeIn">
            <div className="record-hero-copy">
              <div className="hero-kicker">Tóm tắt định danh</div>
              <h3>{PROPERTY_TYPES[record.property_type] || record.property_type}</h3>
              <p>
                {record.street_or_project || '—'}, {record.ward || '—'}, {record.district || '—'}, {record.province_city || '—'}
              </p>
              <div className="hero-stat-grid">
                <div className="hero-stat-card">
                  <span>Giá</span>
                  <strong>{formatPrice(record.price)}</strong>
                </div>
                <div className="hero-stat-card">
                  <span>Diện tích</span>
                  <strong>{record.area_m2 ? `${record.area_m2} m²` : '—'}</strong>
                </div>
                <div className="hero-stat-card">
                  <span>Giá / m²</span>
                  <strong>{record.price_per_m2 ? formatPrice(record.price_per_m2) : '—'}</strong>
                </div>
                <div className="hero-stat-card">
                  <span>Phòng ngủ / tắm</span>
                  <strong>{record.bedrooms ?? 0} / {record.bathrooms ?? 0}</strong>
                </div>
              </div>
            </div>

            <div className="record-hero-image">
              {primaryImage ? (
                <img src={primaryImage} alt={`Bản ghi ${record.id}`} onError={(e) => { e.currentTarget.style.display = 'none' }} />
              ) : (
                <div className="record-image-placeholder">Không có hình ảnh</div>
              )}
            </div>
          </section>

          <section className="detail-grid-two">
            <div className="detail-card animate-slideUp">
              <div className="detail-card-header">Truy vết dữ liệu</div>
              <div className="trace-score-row">
                <div>
                  <div className="trace-score-value">{traceScore.toFixed(1)}</div>
                  <div className="trace-score-label">Độ đầy đủ truy vết /10</div>
                </div>
                <div className="trace-meter">
                  <div className="trace-meter-fill" style={{ width: `${traceScore * 10}%` }}></div>
                </div>
              </div>
              <div className="trace-flag-grid">
                {Object.entries(record.trace_profile?.flags || {}).map(([key, value]) => (
                  <div key={key} className={`trace-flag ${value ? 'ok' : 'miss'}`}>
                    <span>{value ? '✓' : '—'}</span>
                    <strong>{flagLabel(key)}</strong>
                  </div>
                ))}
              </div>
            </div>

            <div className="detail-card animate-slideUp" style={{ animationDelay: '80ms' }}>
              <div className="detail-card-header">Nguồn và xác thực</div>
              <div className="detail-line"><span>Nguồn</span><strong>{record.source_name || '—'}</strong></div>
              <div className="detail-line"><span>Tiêu đề nguồn</span><strong>{record.source_page_title || '—'}</strong></div>
              <div className="detail-line"><span>Trạng thái</span><strong>{verificationLabel}</strong></div>
              <div className="detail-line"><span>Thu thập bởi</span><strong>{record.collected_by || '—'}</strong></div>
              <div className="detail-line"><span>Phương thức thu</span><strong>{record.collection_method || '—'}</strong></div>
              <div className="detail-action-row">
                {sourceLink && (
                  <a className="btn btn-primary btn-sm" href={sourceLink} target="_blank" rel="noopener noreferrer">
                    Mở link nguồn
                  </a>
                )}
                {record.source_screenshot_path && (
                  <a className="btn btn-secondary btn-sm" href={record.source_screenshot_path} target="_blank" rel="noopener noreferrer">
                    Xem ảnh chứng minh
                  </a>
                )}
              </div>
              <div className="detail-note-box">
                {record.verification_note || record.field_note || record.field_notes || 'Chưa có ghi chú bổ sung.'}
              </div>
            </div>
          </section>

          <section className="detail-grid-two">
            <div className="detail-card animate-slideUp" style={{ animationDelay: '120ms' }}>
              <div className="detail-card-header">Thông tin vị trí và tài sản</div>
              <div className="detail-key-grid">
                <div><span>Loại BĐS</span><strong>{PROPERTY_TYPES[record.property_type] || record.property_type}</strong></div>
                <div><span>Loại khu vực</span><strong>{record.area_type || '—'}</strong></div>
                <div><span>Pháp lý</span><strong>{record.legal_status || '—'}</strong></div>
                <div><span>Nội thất</span><strong>{record.furnishing || '—'}</strong></div>
                <div><span>Số tầng</span><strong>{record.floor_count || '—'}</strong></div>
                <div><span>Mặt tiền</span><strong>{record.frontage_m ? `${record.frontage_m} m` : '—'}</strong></div>
                <div><span>Lat / Lng</span><strong>{record.latitude || '—'}, {record.longitude || '—'}</strong></div>
                <div><span>GPS field</span><strong>{record.gps_lat || '—'}, {record.gps_lng || '—'}</strong></div>
              </div>
            </div>

            <div className="detail-card animate-slideUp" style={{ animationDelay: '160ms' }}>
              <div className="detail-card-header">Dữ liệu IoT & môi trường</div>
              <div className="detail-key-grid">
                <div><span>Độ ồn</span><strong>{record.noise_level != null ? `${record.noise_level} dB` : '—'}</strong></div>
                <div><span>Nhiệt độ</span><strong>{record.temperature != null ? `${record.temperature} °C` : '—'}</strong></div>
                <div><span>Độ ẩm</span><strong>{record.humidity != null ? `${record.humidity} %` : '—'}</strong></div>
                <div><span>Ánh sáng</span><strong>{record.light_level != null ? `${record.light_level} lux` : '—'}</strong></div>
                <div><span>GPS accuracy</span><strong>{record.gps_accuracy != null ? `${record.gps_accuracy} m` : '—'}</strong></div>
                <div><span>Thiết bị</span><strong>{record.phone_device || '—'}</strong></div>
                <div><span>OS / App</span><strong>{record.os_version || '—'} / {record.app_version || '—'}</strong></div>
                <div><span>Điểm khu vực</span><strong>{record.area_quality_score != null ? record.area_quality_score : '—'}</strong></div>
              </div>
            </div>
          </section>

          <section className="detail-card animate-slideUp" style={{ animationDelay: '200ms' }}>
            <div className="detail-card-header">Timeline xử lý bản ghi</div>
            <div className="timeline-grid">
              <div><span>Listing</span><strong>{formatDate(record.timeline?.listed_at)}</strong></div>
              <div><span>Lấy từ nguồn</span><strong>{formatDate(record.timeline?.source_collected_at)}</strong></div>
              <div><span>Thu thập nội bộ</span><strong>{formatDate(record.timeline?.collected_at)}</strong></div>
              <div><span>Xác minh</span><strong>{formatDate(record.timeline?.verified_at)}</strong></div>
              <div><span>Capture IoT</span><strong>{formatDate(record.timeline?.capture_time)}</strong></div>
              <div><span>Cập nhật</span><strong>{formatDate(record.timeline?.updated_at)}</strong></div>
            </div>
          </section>

          {gallery.length > 1 && (
            <section className="detail-card animate-slideUp" style={{ animationDelay: '240ms' }}>
              <div className="detail-card-header">Thư viện hình ảnh</div>
              <div className="gallery-grid">
                {gallery.map((image, index) => (
                  <img
                    key={`${record.id}-${index}`}
                    src={image}
                    alt={`Gallery ${index + 1}`}
                    className="gallery-thumb"
                    onError={(e) => { e.currentTarget.style.display = 'none' }}
                  />
                ))}
              </div>
            </section>
          )}

          {/* Provenance Chain */}
          <section className="detail-card animate-slideUp" style={{ animationDelay: '280ms' }}>
            <div className="detail-card-header">Provenance Chain</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 8 }}>
              SHA256 hash chain — tampered records sẽ hiển thị cảnh báo
            </div>
            {record.provenance_chain && record.provenance_chain.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {record.provenance_chain.map((step, i) => (
                  <React.Fragment key={i}>
                    {i > 0 && (
                      <div style={{ textAlign: 'center', color: 'var(--border-color)', fontSize: '0.65rem', padding: '1px 0' }}>
                        ↓ chain #{i + 1}
                      </div>
                    )}
                    <div style={{
                      border: '1px solid var(--border)', borderRadius: 8,
                      background: 'var(--surface-2)', overflow: 'hidden',
                    }}>
                      <div style={{
                        padding: '6px 12px', background: 'var(--bg-elevated)',
                        borderBottom: '1px solid var(--border)', display: 'flex', gap: 8, alignItems: 'center',
                      }}>
                        <span style={{ fontWeight: 700, color: '#7c3aed', fontSize: '0.75rem' }}>{step.step?.toUpperCase()}</span>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{step.actor}</span>
                        <span style={{ marginLeft: 'auto', fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                          {step.timestamp ? new Date(step.timestamp).toLocaleString('vi-VN') : '—'}
                        </span>
                      </div>
                      <div style={{ padding: '8px 12px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4, fontSize: '0.75rem' }}>
                        {step.source && <div><span style={{ color: 'var(--text-muted)' }}>Source: </span><strong>{step.source}</strong></div>}
                        {step.input_hash && <div><span style={{ color: 'var(--text-muted)' }}>Hash: </span><code style={{ fontSize: '0.68rem' }}>{step.input_hash.slice(0, 16)}...</code></div>}
                        {step.verify_url && (
                          <div style={{ gridColumn: '1/-1' }}>
                            <a href={step.verify_url} target="_blank" rel="noopener noreferrer" style={{ color: '#7c3aed', fontSize: '0.75rem' }}>
                              Verify Online
                            </a>
                          </div>
                        )}
                      </div>
                    </div>
                  </React.Fragment>
                ))}
              </div>
            ) : (
              <div style={{ padding: '16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.82rem' }}>
                Không có provenance chain cho bản ghi này
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  )
}

export default RecordDetailModal
