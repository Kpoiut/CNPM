import React from 'react'
import { icon } from '../../components/ui/icons'
import { VISUAL_ASSETS } from '../../constants/visuals'

function About() {
  return (
    <div>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(0, 1.2fr) minmax(280px, 0.8fr)',
        gap: '1rem',
        marginBottom: '1rem',
        padding: '1rem',
        border: '1px solid var(--border)',
        borderRadius: 16,
        background: 'linear-gradient(135deg, rgba(79,70,229,0.08) 0%, rgba(6,182,212,0.05) 100%), var(--bg-card)',
        boxShadow: 'var(--shadow-sm)',
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem', minWidth: 0 }}>
          <div style={{ fontSize: '0.68rem', fontWeight: 800, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--primary-light)' }}>
            Giới thiệu dự án
          </div>
          <h1 className="page-title" style={{ margin: 0 }}>
            Nghiên cứu và xây dựng hệ thống dự đoán giá bất động sản theo khu vực bằng học máy kết hợp dữ liệu IoT từ điện thoại thông minh
          </h1>
          <p className="page-subtitle" style={{ marginTop: 0, maxWidth: '72ch' }}>
            Hệ thống định giá bất động sản tự động (AVM) sử dụng Machine Learning kết hợp dữ liệu IoT từ smartphone.
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {['AVM + IoT', 'Conformal prediction', 'Pilot dữ liệu thật', 'Bằng chứng có provenance'].map(tag => (
              <span key={tag} className="badge badge-primary">{tag}</span>
            ))}
          </div>
        </div>

        <div style={{
          display: 'grid',
          gap: '0.75rem',
          alignContent: 'start',
        }}>
          <div style={{
            position: 'relative',
            overflow: 'hidden',
            minHeight: 210,
            borderRadius: 14,
            border: '1px solid var(--border)',
            background: 'var(--surface-1)',
            boxShadow: 'var(--shadow-md)',
          }}>
            <img
              src={VISUAL_ASSETS.officeInterior}
              alt="Khu làm việc nghiên cứu AVM"
              style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
            />
            <div style={{
              position: 'absolute',
              inset: 'auto 0 0 0',
              padding: '0.85rem',
              background: 'linear-gradient(180deg, rgba(6,10,18,0.02) 0%, rgba(6,10,18,0.75) 100%)',
              color: 'white',
            }}>
              <div style={{ fontSize: '0.62rem', fontWeight: 800, letterSpacing: '0.12em', textTransform: 'uppercase', opacity: 0.8 }}>
                Research workspace
              </div>
              <div style={{ fontSize: '0.9rem', fontWeight: 700, lineHeight: 1.35 }}>
                Từ dữ liệu thực địa đến mô hình định giá có thể giải thích.
              </div>
            </div>
          </div>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
            gap: '0.75rem',
          }}>
            <div style={{ padding: '0.85rem 0.95rem', border: '1px solid var(--border)', borderRadius: 12, background: 'var(--bg-card)' }}>
              <div style={{ fontSize: '0.68rem', fontWeight: 800, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Input</div>
              <div style={{ fontFamily: 'var(--font-display)', fontWeight: 800, color: 'var(--text-primary)', marginTop: 4 }}>Field + IoT</div>
            </div>
            <div style={{ padding: '0.85rem 0.95rem', border: '1px solid var(--border)', borderRadius: 12, background: 'var(--bg-card)' }}>
              <div style={{ fontSize: '0.68rem', fontWeight: 800, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Output</div>
              <div style={{ fontFamily: 'var(--font-display)', fontWeight: 800, color: 'var(--text-primary)', marginTop: 4 }}>Price + band</div>
            </div>
          </div>
        </div>
      </div>

      {/* Key Features */}
      <div className="mb-6">
        <div style={{ fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '1rem' }}>
          Điểm mới / Điểm khác biệt
        </div>
        <div style={{ display: 'grid', gap: '1rem' }}>
          {[
            { iconKey: 'satellite', color: 'var(--info)', bg: 'rgba(14,165,233,0.08)', border: 'rgba(14,165,233,0.2)', title: 'Dữ liệu IoT từ Smartphone', desc: 'Thu thập GPS, độ ồn, thời gian ghi nhận từ điện thoại thông minh để tăng độ chính xác dự đoán' },
            { iconKey: 'map', color: 'var(--success)', bg: 'rgba(16,185,129,0.08)', border: 'rgba(16,185,129,0.2)', title: 'Dữ liệu khu vực', desc: 'Khoảng cách đến chợ, siêu thị, trường học, bệnh viện, đường chính' },
            { iconKey: 'clipboardCheck', color: 'var(--warning)', bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.2)', title: 'Dữ liệu tự thu thập 3–5%', desc: 'Dữ liệu khảo sát thực địa với đầy đủ thông tin nguồn, người thu thập, thời gian' },
            { iconKey: 'shieldCheck', color: 'var(--primary)', bg: 'rgba(79,70,229,0.08)', border: 'rgba(79,70,229,0.2)', title: 'Conformal Prediction', desc: 'Khoảng giá đáng tin cậy với confidence band được hiệu chỉnh bằng conformal calibration' },
          ].map((f, i) => (
            <div key={i} className="card animate-slideUp" style={{
              padding: '1.25rem',
              borderLeft: `4px solid ${f.color}`,
              background: f.bg,
              borderColor: f.border,
              animationDelay: `${i * 60}ms`,
            }}>
              <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
                <div style={{ flexShrink: 0, color: f.color }}>{icon(f.iconKey, 24)}</div>
                <div>
                  <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1rem', fontWeight: 700, color: f.color, marginBottom: '0.4rem' }}>
                    {f.title}
                  </h3>
                  <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.6, margin: 0 }}>
                    {f.desc}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Data Collection */}
      <div className="card mb-6 animate-slideUp" style={{ animationDelay: '240ms' }}>
        <div className="card-header">
          <span className="card-title">Thu thập dữ liệu</span>
        </div>
        <div style={{ display: 'grid', gap: '1.5rem' }}>
          <div>
            <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.75rem' }}>
              Dữ liệu bắt buộc
            </h4>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.25rem' }}>
              {['Loại BĐS', 'Tỉnh / TP', 'Quận / Huyện', 'Phường / Xã', 'Diện tích (m²)', 'Giá (VND)', 'Thời gian ghi nhận', 'Nguồn dữ liệu'].map(t => (
                <span key={t} className="badge badge-primary">{t}</span>
              ))}
            </div>
          </div>
          <div>
            <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.75rem' }}>
              Dữ liệu IoT (Smartphone)
            </h4>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.25rem' }}>
              {['GPS (vĩ độ, kinh độ)', 'Độ ồn môi trường (dB)', 'Nhiệt độ (°C)', 'Độ ẩm (%)', 'Ánh sáng (lux)', 'Độ chính xác GPS (m)', 'Thiết bị sử dụng', 'Thời gian ghi nhận'].map(t => (
                <span key={t} className="badge badge-info">{t}</span>
              ))}
            </div>
          </div>
          <div>
            <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.75rem' }}>
              Dữ liệu tự thu thập
            </h4>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              {['Người nhập liệu', 'Phương thức thu thập', 'Thời gian thu thập', 'Ghi chú xác minh', 'Ảnh chứng minh'].map(t => (
                <span key={t} className="badge badge-success">{t}</span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Baseline vs Improvement */}
      <div className="card mb-6 animate-slideUp" style={{ animationDelay: '300ms' }}>
        <div className="card-header">
          <span className="card-title">Baseline & Cải tiến</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
          <div style={{ padding: '1.25rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)' }}>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Baseline
            </div>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '0.75rem' }}>
              RandomForest với đặc trưng cơ bản: diện tích, phòng ngủ, khu vực.
            </p>
            <span className="badge badge-neutral">California Housing, Flask House Price</span>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-disabled)', marginTop: '0.5rem' }}>MIT / Apache-2.0</div>
          </div>
          <div style={{ padding: '1.25rem', background: 'rgba(79,70,229,0.08)', borderRadius: 'var(--radius-lg)', border: '1px solid rgba(79,70,229,0.2)' }}>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: '0.85rem', fontWeight: 700, color: 'var(--primary-light)', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Cải tiến
            </div>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '0.75rem' }}>
              RandomForest + đặc trưng IoT (GPS, độ ồn, khoảng cách tiện ích, conformal prediction).
            </p>
            <span className="badge badge-primary">+ Đặc trưng IoT smartphone</span>
            <div style={{ fontSize: '0.72rem', color: 'var(--primary-light)', marginTop: '0.5rem' }}>Điểm khác biệt: sử dụng dữ liệu smartphone</div>
          </div>
        </div>
      </div>

      {/* Tech Stack */}
      <div className="card animate-slideUp" style={{ animationDelay: '360ms' }}>
        <div className="card-header">
          <span className="card-title">Công nghệ sử dụng</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem' }}>
          {[
            { name: 'Backend', tech: 'FastAPI', color: 'var(--success)', bg: 'rgba(16,185,129,0.08)', border: 'rgba(16,185,129,0.2)' },
            { name: 'ML', tech: 'scikit-learn', color: 'var(--info)', bg: 'rgba(14,165,233,0.08)', border: 'rgba(14,165,233,0.2)' },
            { name: 'Frontend', tech: 'React', color: 'var(--primary)', bg: 'rgba(79,70,229,0.08)', border: 'rgba(79,70,229,0.2)' },
            { name: 'Database', tech: 'SQLite', color: 'var(--warning)', bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.2)' },
            { name: 'IoT', tech: 'Smartphone', color: 'var(--accent)', bg: 'rgba(16,185,129,0.06)', border: 'rgba(16,185,129,0.15)' },
          ].map((t, i) => (
            <div key={i} style={{
              textAlign: 'center',
              padding: '1.25rem 1rem',
              background: t.bg,
              borderRadius: 'var(--radius-lg)',
              border: `1px solid ${t.border}`,
            }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.4rem' }}>{t.name}</div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '1rem', fontWeight: 700, color: t.color }}>{t.tech}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default About
