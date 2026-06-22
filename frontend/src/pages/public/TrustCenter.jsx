import React from 'react'
import { Link } from 'react-router-dom'

const TRUST_ITEMS = [
  ['Khoảng giá, không chỉ một con số', 'Kết quả luôn đi cùng khoảng ước lượng và mức độ tin cậy để tránh cảm giác chính xác giả.'],
  ['Có dấu vết mô hình', 'Chỉ số đánh giá phải gắn với phiên bản mô hình, tập dữ liệu, cỡ mẫu và thời điểm đo.'],
  ['Có bằng chứng so sánh', 'Bất động sản tham chiếu, vị trí và chất lượng dữ liệu được tách khỏi kết quả trung tâm.'],
]

export default function TrustCenter() {
  return (
    <section className="container" style={{ paddingBlock: 'clamp(2rem, 6vw, 5rem)' }}>
      <div className="page-header" style={{ maxWidth: 760 }}>
        <span className="badge badge-primary">Độ tin cậy</span>
        <h1>Biết kết quả đáng tin đến đâu trước khi ra quyết định</h1>
        <p>Mỗi định giá cần trả lời ba câu hỏi: giá bao nhiêu, dựa trên bằng chứng nào và còn bất định ở đâu.</p>
      </div>
      <div className="grid grid-3" style={{ marginTop: '2rem' }}>
        {TRUST_ITEMS.map(([title, body]) => (
          <article className="card" key={title}>
            <h3>{title}</h3>
            <p style={{ color: 'var(--text-secondary)' }}>{body}</p>
          </article>
        ))}
      </div>
      <div style={{ marginTop: '2rem', display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <Link className="btn btn-primary" to="/">Bắt đầu định giá</Link>
        <Link className="btn btn-ghost" to="/methodology">Xem phương pháp</Link>
      </div>
    </section>
  )
}
