import React from 'react'
import { Link } from 'react-router-dom'

import { icon } from '../../components/ui/icons'
import { VISUAL_ASSETS } from '../../constants/visuals'
import './information-pages.css'

const RESULT_SIGNALS = [
  {
    iconKey: 'chart',
    title: 'Khoảng dự đoán',
    body: 'Khoảng thấp–cao thể hiện vùng giá hợp lý. Khoảng càng hẹp thì bất định của hồ sơ càng thấp.',
  },
  {
    iconKey: 'shieldCheck',
    title: 'Confidence grade',
    body: 'Grade A–D tổng hợp độ phủ comparable, độ gần giống, chất lượng nguồn và độ rộng khoảng giá.',
  },
  {
    iconKey: 'table',
    title: 'Comparable',
    body: 'Các tài sản tham chiếu phải cho biết khu vực, diện tích, giá/m², bậc bằng chứng và lý do được chọn.',
  },
]

const EVIDENCE_TIERS = [
  ['E1', 'Thấp', 'Tin đăng hoặc dữ liệu chưa được kiểm chứng đầy đủ', 'Chỉ tham khảo, không dùng làm điểm tựa chính'],
  ['E2', 'Cơ bản', 'Nguồn công khai có dấu vết nhưng còn thiếu thuộc tính', 'Dùng bổ sung khi thiếu mẫu tốt hơn'],
  ['E3', 'Khá', 'Nguồn rõ, trường dữ liệu chính đủ và có thể đối chiếu', 'Có thể tham gia tập comparable'],
  ['E4', 'Cao', 'Bản ghi đã xác minh hoặc có provenance tốt', 'Ưu tiên trong định giá và kiểm định'],
  ['E5', 'Rất cao', 'Giao dịch/đấu giá/chứng cứ chính thức có khả năng truy xuất', 'Bằng chứng chuẩn để hiệu chỉnh và đánh giá'],
]

const READING_STEPS = [
  ['01', 'Đọc khoảng giá trước', 'Không xem giá trung tâm như một con số tuyệt đối.'],
  ['02', 'Kiểm tra grade', 'Grade thấp cần bổ sung hồ sơ hoặc mở rộng bằng chứng.'],
  ['03', 'Đối chiếu comparable', 'Xem mẫu có thực sự gần về vị trí, diện tích và pháp lý hay không.'],
  ['04', 'Đọc cảnh báo', 'Ngập, pháp lý, hẻm, hình học và dữ liệu thiếu có thể thay đổi quyết định.'],
]

export default function TrustCenter() {
  return (
    <div className="info-page">
      <section
        className="info-hero info-hero--trust"
        style={{ '--info-hero-image': `url(${VISUAL_ASSETS.houseExterior})` }}
      >
        <div className="info-hero__content">
          <span className="info-kicker">Độ tin cậy</span>
          <h1>Biết kết quả đáng tin đến đâu trước khi ra quyết định</h1>
          <p>
            Một định giá tốt phải cho biết giá trị, bằng chứng tạo nên giá trị đó và phần bất định còn lại.
          </p>
          <div className="info-hero__actions">
            <Link className="btn btn-primary" to="/">Bắt đầu định giá</Link>
            <a className="btn btn-ghost info-hero__ghost" href="#cach-doc">Cách đọc kết quả</a>
          </div>
        </div>
      </section>

      <section className="info-section" id="cach-doc">
        <header className="info-section__header">
          <span className="info-kicker">Cách đọc kết quả</span>
          <h2>Ba tín hiệu phải xuất hiện cùng nhau</h2>
          <p>Không đánh giá độ tin cậy chỉ bằng một điểm số hoặc số lượng bản ghi tổng.</p>
        </header>
        <div className="info-grid info-grid--3">
          {RESULT_SIGNALS.map(item => (
            <article className="info-panel" key={item.title}>
              <span className="info-panel__icon">{icon(item.iconKey, 22)}</span>
              <h3>{item.title}</h3>
              <p>{item.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="info-section info-section--band">
        <header className="info-section__header">
          <span className="info-kicker">Nguồn dữ liệu</span>
          <h2>Bậc bằng chứng E1–E5</h2>
          <p>Bậc càng cao thể hiện khả năng truy xuất và kiểm chứng tốt hơn, không đơn thuần là dữ liệu mới hơn.</p>
        </header>
        <div className="info-table-wrap">
          <table className="info-table">
            <thead>
              <tr>
                <th>Bậc</th>
                <th>Độ tin cậy dữ liệu</th>
                <th>Ý nghĩa</th>
                <th>Cách sử dụng</th>
              </tr>
            </thead>
            <tbody>
              {EVIDENCE_TIERS.map(([tier, level, meaning, usage]) => (
                <tr key={tier}>
                  <td><span className={`info-tier info-tier--${tier.toLowerCase()}`}>{tier}</span></td>
                  <td><strong>{level}</strong></td>
                  <td>{meaning}</td>
                  <td>{usage}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="info-section">
        <header className="info-section__header">
          <span className="info-kicker">Quy trình quyết định</span>
          <h2>Đọc định giá theo thứ tự</h2>
        </header>
        <ol className="info-steps">
          {READING_STEPS.map(([number, title, body]) => (
            <li key={number}>
              <span>{number}</span>
              <div><h3>{title}</h3><p>{body}</p></div>
            </li>
          ))}
        </ol>
      </section>

      <section className="info-callout info-callout--warning">
        <span className="info-callout__icon">{icon('alertTriangle', 24)}</span>
        <div>
          <h2>Giới hạn cần biết</h2>
          <p>
            AVM không thay thế thẩm định pháp lý, khảo sát hiện trạng hoặc quyết định tín dụng. Hồ sơ thiếu vị trí,
            pháp lý, diện tích hay comparable phù hợp phải được xem là kết quả sơ bộ.
          </p>
        </div>
        <Link className="btn btn-secondary" to="/methodology">Xem phương pháp</Link>
      </section>
    </div>
  )
}
