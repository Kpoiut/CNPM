import React from 'react'
import { VISUAL_ASSETS } from '../../constants/visuals'

function PredictionHeroBand({ scopeText, engineLabel, isAdmin = false }) {
  const visuals = [
    {
      src: VISUAL_ASSETS.houseExterior,
      alt: 'Modern house exterior used as the property input context',
      title: 'Tài sản đầu vào',
      caption: 'Ảnh thật, tách khỏi mô tả để đọc ngay luồng hồ sơ.',
    },
    {
      src: VISUAL_ASSETS.citySkyline,
      alt: 'City skyline representing the market scope',
      title: 'Phạm vi thị trường',
      caption: 'Bối cảnh khu vực và mặt bằng so sánh.',
    },
    {
      src: VISUAL_ASSETS.officeInterior,
      alt: 'Office control room representing the audit pipeline',
      title: 'Bàn điều khiển',
      caption: 'Trace, audit và pipeline cùng chạy trong một rail ngang.',
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
        <span className="prediction-hero-eyebrow">Không gian định giá</span>
        <h2 className="prediction-hero-title">
          Định giá bất động sản bằng pipeline thật, không phải demo dựng sẵn
        </h2>
        <p className="prediction-hero-description">
          Đây là vùng nhập liệu, so sánh và audit cho cùng một luồng. Người dùng đi từ form đến comparable
          rồi tới pipeline, nên mọi thứ phải đọc như một quy trình đang chạy chứ không phải ảnh chụp tĩnh.
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
          <span className="prediction-hero-rail-eyebrow">Dải hình ảnh</span>
          <strong className="prediction-hero-rail-title">Tài sản, thị trường và vận hành trong cùng một ngữ cảnh.</strong>
          <p className="prediction-hero-rail-text">
            Hình ảnh được tách khỏi biểu mẫu để hỗ trợ nhận diện nhanh mà không lặp lại luồng thao tác bên dưới.
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
