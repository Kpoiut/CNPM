import React from 'react'
import { VISUAL_ASSETS } from '../../constants/visuals'

function PredictionHeroBand({ scopeText, engineLabel, isAdmin = false }) {
  const visuals = [
    {
      src: VISUAL_ASSETS.houseExterior,
      alt: 'Modern house exterior used as the property input context',
      title: 'Tài sản đầu vào',
      caption: 'Ngữ cảnh hồ sơ và ảnh tham chiếu.',
    },
    {
      src: VISUAL_ASSETS.citySkyline,
      alt: 'City skyline representing the market scope',
      title: 'Phạm vi thị trường',
      caption: 'Khu vực, comparable và mặt bằng giá.',
    },
    {
      src: VISUAL_ASSETS.officeInterior,
      alt: 'Office control room representing the audit pipeline',
      title: 'Bàn điều khiển',
      caption: 'Trace, model version và audit gate.',
    },
  ]

  const trustSignals = [
    'PostgreSQL/PostGIS',
    'Metric gắn model version',
    'Lưu lịch sử định giá',
    ...(isAdmin ? ['Audit đầy đủ'] : []),
  ]

  return (
    <section className="prediction-hero-band">
      <div className="prediction-hero-copy">
        <span className="prediction-hero-eyebrow">Prediction cockpit</span>
        <h2 className="prediction-hero-title">
          Một workspace cho nhập hồ sơ, đối chiếu comparable và kiểm tra model
        </h2>
        <p className="prediction-hero-description">
          Luồng dự đoán giữ form, bản đồ, kết quả, comparable và audit trong cùng một mạch để user thao tác nhanh,
          còn admin vẫn thấy đủ version, scope dữ liệu và tín hiệu vận hành.
        </p>

        <div className="prediction-hero-points" aria-label="Tín hiệu tin cậy của hệ thống">
          {trustSignals.map(signal => (
            <span key={signal} className="prediction-hero-chip">{signal}</span>
          ))}
        </div>

        <div className="prediction-hero-meta">
          <span className="prediction-hero-meta-item">
            <strong>Scope</strong>
            <span>{scopeText || 'Đang tải scope từ backend'}</span>
          </span>
          <span className="prediction-hero-meta-item">
            <strong>Engine</strong>
            <span>{engineLabel || 'Valuation Engine v2'}</span>
          </span>
        </div>
      </div>

      <div className="prediction-hero-media" aria-label="Prediction visual context">
        <div className="prediction-hero-rail-head">
          <span className="prediction-hero-rail-eyebrow">Visual context</span>
          <strong className="prediction-hero-rail-title">Tài sản, thị trường và vận hành trong cùng một ngữ cảnh.</strong>
          <p className="prediction-hero-rail-text">
            Dải ảnh đóng vai trò nhận diện nhanh, phần quyết định vẫn nằm ở dữ liệu và audit bên dưới.
          </p>
        </div>

        <div className="prediction-hero-strip" aria-label="Prediction visual context strip">
          {visuals.map(item => (
            <figure key={item.title} className="prediction-hero-card">
              <div className="prediction-hero-card-media">
                <img src={item.src} alt={item.alt} loading={item.title === 'Tài sản đầu vào' ? 'eager' : 'lazy'} />
              </div>
              <figcaption className="prediction-hero-card-caption">
                <strong>{item.title}</strong>
                <span>{item.caption}</span>
              </figcaption>
            </figure>
          ))}
        </div>
      </div>
    </section>
  )
}

export { PredictionHeroBand }
