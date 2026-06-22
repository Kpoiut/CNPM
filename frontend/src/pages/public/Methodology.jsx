import React from 'react'
import { Link } from 'react-router-dom'

const STEPS = [
  ['01', 'Chuẩn hóa đầu vào', 'Vị trí, loại tài sản và thuộc tính được kiểm tra trước khi chạy mô hình.'],
  ['02', 'Tìm bằng chứng', 'Hệ thống chọn các bất động sản so sánh phù hợp về vị trí, diện tích và đặc điểm.'],
  ['03', 'Ước lượng có phiên bản', 'Kết quả gắn với phiên bản mô hình đang phục vụ, không trộn với benchmark lịch sử.'],
  ['04', 'Giải thích bất định', 'Khoảng giá, cảnh báo và mức tin cậy được trình bày cạnh kết quả.'],
]

export default function Methodology() {
  return (
    <section className="container" style={{ paddingBlock: 'clamp(2rem, 6vw, 5rem)' }}>
      <div className="page-header" style={{ maxWidth: 760 }}>
        <span className="badge badge-primary">Phương pháp</span>
        <h1>Từ dữ liệu tài sản đến kết quả có thể kiểm tra</h1>
        <p>Quy trình được chia thành các bước rõ ràng để người dùng hiểu kết quả thay vì phải tin vào một hộp đen.</p>
      </div>
      <div className="grid grid-2" style={{ marginTop: '2rem' }}>
        {STEPS.map(([number, title, body]) => (
          <article className="card" key={number}>
            <span style={{ color: 'var(--primary)', fontWeight: 800 }}>{number}</span>
            <h3>{title}</h3>
            <p style={{ color: 'var(--text-secondary)' }}>{body}</p>
          </article>
        ))}
      </div>
      <Link className="btn btn-primary" style={{ marginTop: '2rem' }} to="/">Thử định giá</Link>
    </section>
  )
}
