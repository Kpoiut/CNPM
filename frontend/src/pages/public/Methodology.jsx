import React from 'react'
import { Link } from 'react-router-dom'

import { icon } from '../../components/ui/icons'
import { VISUAL_ASSETS } from '../../constants/visuals'
import './information-pages.css'

const PIPELINE = [
  ['01', 'Tiếp nhận hồ sơ', 'Kiểm tra loại tài sản, vị trí, diện tích và các trường bắt buộc.'],
  ['02', 'Chuẩn hóa dữ liệu', 'Đưa địa danh, đơn vị, pháp lý và thuộc tính về taxonomy thống nhất.'],
  ['03', 'Tìm comparable', 'Lọc mẫu gần theo khu vực, loại tài sản, diện tích, giá/m² và chất lượng bằng chứng.'],
  ['04', 'Ước lượng giá', 'Kết hợp model đang phục vụ với baseline comparable và các hệ số điều chỉnh có dấu vết.'],
  ['05', 'Conformal prediction', 'Hiệu chỉnh khoảng dự đoán để thể hiện bất định thay vì chỉ trả một điểm giá.'],
  ['06', 'Lưu lineage', 'Gắn request, account, model version, latency, input và phản hồi thực tế cho audit/retraining.'],
]

const METRICS = [
  ['MAPE', 'Sai số phần trăm tuyệt đối trung bình', 'So sánh tương đối giữa các model trên cùng holdout set.'],
  ['MAE', 'Sai số tuyệt đối trung bình theo VND', 'Cho biết mức lệch tiền tệ điển hình, phải gắn đúng đơn vị giá.'],
  ['R²', 'Mức biến thiên được model giải thích', 'Dùng bổ sung; không thay thế kiểm tra sai số và drift.'],
  ['Coverage', 'Tỷ lệ giá thực nằm trong khoảng dự đoán', 'Kiểm tra chất lượng Conformal prediction và độ rộng khoảng.'],
]

const GOVERNANCE = [
  {
    iconKey: 'database',
    title: 'Dataset có phiên bản',
    body: 'Mỗi lần train lưu snapshot, profile E1–E5, train/validation/holdout và checksum để tái lập kết quả.',
  },
  {
    iconKey: 'experiment',
    title: 'Candidate tách khỏi serving',
    body: 'Model mới chỉ là candidate cho tới khi vượt release gate trên cùng holdout và kiểm tra drift.',
  },
  {
    iconKey: 'shieldCheck',
    title: 'Không tự động promote',
    body: 'MAPE/MAE kém hơn, lineage thiếu hoặc dữ liệu lỗi sẽ chặn activate dù quá trình train hoàn tất.',
  },
]

export default function Methodology() {
  return (
    <div className="info-page">
      <section
        className="info-hero info-hero--method"
        style={{ '--info-hero-image': `url(${VISUAL_ASSETS.citySkyline})` }}
      >
        <div className="info-hero__content">
          <span className="info-kicker">Phương pháp</span>
          <h1>Từ hồ sơ bất động sản đến kết quả có thể kiểm tra</h1>
          <p>Pipeline tách rõ dữ liệu, bằng chứng, model và kiểm soát phát hành để tránh một “hộp đen” khó truy vết.</p>
          <div className="info-hero__actions">
            <Link className="btn btn-primary" to="/">Thử định giá</Link>
            <a className="btn btn-ghost info-hero__ghost" href="#pipeline">Xem luồng định giá</a>
          </div>
        </div>
      </section>

      <section className="info-section" id="pipeline">
        <header className="info-section__header">
          <span className="info-kicker">Luồng định giá</span>
          <h2>Sáu bước có gate và lineage</h2>
          <p>Mỗi bước có thể pass, cảnh báo hoặc chặn; lỗi đầu vào không được âm thầm đi tiếp.</p>
        </header>
        <ol className="method-pipeline">
          {PIPELINE.map(([number, title, body]) => (
            <li key={number}>
              <span className="method-pipeline__number">{number}</span>
              <div><h3>{title}</h3><p>{body}</p></div>
            </li>
          ))}
        </ol>
      </section>

      <section className="info-section info-section--band">
        <header className="info-section__header">
          <span className="info-kicker">Đánh giá model</span>
          <h2>Metric chỉ có nghĩa khi gắn đúng version và holdout</h2>
        </header>
        <div className="info-table-wrap">
          <table className="info-table">
            <thead><tr><th>Metric</th><th>Đo điều gì</th><th>Cách dùng trong AVM</th></tr></thead>
            <tbody>
              {METRICS.map(([name, meaning, usage]) => (
                <tr key={name}><td><strong>{name}</strong></td><td>{meaning}</td><td>{usage}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="info-section">
        <header className="info-section__header">
          <span className="info-kicker">Model governance</span>
          <h2>Train xong chưa đồng nghĩa được phục vụ</h2>
        </header>
        <div className="info-grid info-grid--3">
          {GOVERNANCE.map(item => (
            <article className="info-panel" key={item.title}>
              <span className="info-panel__icon">{icon(item.iconKey, 22)}</span>
              <h3>{item.title}</h3>
              <p>{item.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="info-callout">
        <span className="info-callout__icon">{icon('activity', 24)}</span>
        <div>
          <h2>Kết quả luôn gắn với model đang phục vụ</h2>
          <p>Candidate mới và model production không được trộn metric. Dashboard admin chịu trách nhiệm hiển thị version, trạng thái và bằng chứng release hiện hành.</p>
        </div>
        <Link className="btn btn-secondary" to="/trust">Đọc độ tin cậy</Link>
      </section>
    </div>
  )
}
