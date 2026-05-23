import React from 'react'
import { VISUAL_ASSETS } from '../../constants/visuals'

function PredictionHeroBand({ scopeText, engineLabel, isAdmin = false }) {
  const chips = [
    'Nhập hồ sơ thật',
    'So sánh comparable',
    'Mở pipeline audit',
    ...(isAdmin ? ['Quyền admin thật'] : []),
  ]

  return (
    <section className="prediction-hero-band">
      <div className="prediction-hero-copy">
        <span className="prediction-hero-eyebrow">Prediction workspace</span>
        <h2 className="prediction-hero-title">
          Định giá bất động sản bằng pipeline thật, không phải demo dựng sẵn
        </h2>
        <p className="prediction-hero-description">
          Đây là vùng nhập liệu, so sánh và audit cho cùng một luồng. Người dùng đi từ form đến comparable
          rồi tới pipeline, nên mọi thứ phải đọc như một quy trình đang chạy chứ không phải ảnh chụp tĩnh.
        </p>

        <div className="prediction-hero-points" aria-label="Prediction workflow highlights">
          {chips.map(chip => (
            <span key={chip} className="prediction-hero-chip">{chip}</span>
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
        <article className="prediction-hero-shot">
          <img
            src={VISUAL_ASSETS.houseExterior}
            alt="Modern house exterior used as the property input context"
            loading="eager"
          />
          <div className="prediction-hero-shot-label">
            <span className="prediction-hero-shot-kicker">Tài sản thật</span>
            <strong className="prediction-hero-shot-title">Mẫu đầu vào</strong>
            <span className="prediction-hero-shot-caption">Form, chứng cứ và bối cảnh địa điểm.</span>
          </div>
        </article>

        <div className="prediction-hero-mini-stack">
          <article className="prediction-hero-mini">
            <img
              src={VISUAL_ASSETS.citySkyline}
              alt="City skyline representing the market scope"
              loading="lazy"
            />
            <div className="prediction-hero-mini-label">
              <strong className="prediction-hero-mini-title">Thị trường</strong>
              <span className="prediction-hero-mini-caption">Khu vực và scope.</span>
            </div>
          </article>

          <article className="prediction-hero-mini">
            <img
              src={VISUAL_ASSETS.officeInterior}
              alt="Office control room representing the audit pipeline"
              loading="lazy"
            />
            <div className="prediction-hero-mini-label">
              <strong className="prediction-hero-mini-title">Bàn điều khiển</strong>
              <span className="prediction-hero-mini-caption">Pipeline và audit trail.</span>
            </div>
          </article>
        </div>
      </div>
    </section>
  )
}

export { PredictionHeroBand }
