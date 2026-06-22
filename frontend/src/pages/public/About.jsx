import React from 'react'
import { Link } from 'react-router-dom'

import { icon } from '../../components/ui/icons'
import './information-pages.css'

const PROJECT_PILLARS = [
  {
    iconKey: 'map',
    title: 'Dữ liệu theo khu vực',
    body: 'Vị trí, tiện ích, môi trường, pháp lý và comparable được chuẩn hóa theo taxonomy thống nhất.',
  },
  {
    iconKey: 'satellite',
    title: 'Tín hiệu IoT',
    body: 'GPS, độ ồn và thông tin thực địa từ smartphone bổ sung ngữ cảnh cho tài sản.',
  },
  {
    iconKey: 'shieldCheck',
    title: 'Định giá có bằng chứng',
    body: 'Khoảng giá, confidence grade, model version và provenance xuất hiện cùng kết quả.',
  },
  {
    iconKey: 'activity',
    title: 'Vòng phản hồi',
    body: 'Lịch sử định giá và giá thực tế đã xác minh có thể trở thành dữ liệu retraining hợp lệ.',
  },
]

const STACK = [
  ['API', 'FastAPI'],
  ['Data', 'PostgreSQL / PostGIS'],
  ['ML', 'scikit-learn'],
  ['UI', 'React'],
  ['MLOps', 'Alembic / Docker / CI'],
]

export default function About() {
  return (
    <div className="info-page about-page">
      <section
        className="about-hero info-hero"
        style={{ '--info-hero-image': 'url(/media/about-avm-city-hero.png)' }}
      >
        <div className="about-hero__content info-hero__content">
          <span className="info-kicker">Real Estate AVM</span>
          <h1>Định giá bất động sản theo khu vực bằng học máy và dữ liệu thực địa</h1>
          <p>
            Hệ thống kết hợp dữ liệu thị trường, IoT từ smartphone và model có phiên bản để tạo khoảng giá có thể giải thích và kiểm tra.
          </p>
          <div className="info-hero__actions">
            <Link className="btn btn-primary" to="/">Bắt đầu định giá</Link>
            <Link className="btn btn-ghost info-hero__ghost" to="/methodology">Xem phương pháp</Link>
          </div>
        </div>
      </section>

      <section className="info-section">
        <header className="info-section__header">
          <span className="info-kicker">Mục tiêu dự án</span>
          <h2>Từ một con số dự đoán thành một quyết định có cơ sở</h2>
          <p>
            AVM tồn tại để rút ngắn thời gian tham chiếu giá nhưng vẫn giữ được nguồn dữ liệu, bất định và dấu vết model cho người dùng lẫn quản trị viên.
          </p>
        </header>
        <div className="info-grid info-grid--4">
          {PROJECT_PILLARS.map(item => (
            <article className="info-panel" key={item.title}>
              <span className="info-panel__icon">{icon(item.iconKey, 22)}</span>
              <h3>{item.title}</h3>
              <p>{item.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="info-section info-section--band about-flow">
        <header className="info-section__header">
          <span className="info-kicker">Luồng giá trị</span>
          <h2>Dữ liệu vào rõ ràng, kết quả ra có thể audit</h2>
        </header>
        <div className="about-flow__track">
          {[
            ['01', 'Thu thập', 'Hồ sơ, thị trường, IoT'],
            ['02', 'Chuẩn hóa', 'Taxonomy, provenance, E1–E5'],
            ['03', 'Định giá', 'Comparable + model + gate'],
            ['04', 'Phản hồi', 'Giá thực, xác minh, retraining'],
          ].map(([number, title, body]) => (
            <div key={number}>
              <span>{number}</span><strong>{title}</strong><small>{body}</small>
            </div>
          ))}
        </div>
      </section>

      <section className="info-section">
        <header className="info-section__header">
          <span className="info-kicker">Nền tảng kỹ thuật</span>
          <h2>Một stack duy nhất cho vận hành production</h2>
        </header>
        <div className="about-stack" aria-label="Công nghệ sử dụng">
          {STACK.map(([label, value]) => (
            <div key={label}><span>{label}</span><strong>{value}</strong></div>
          ))}
        </div>
      </section>
    </div>
  )
}
