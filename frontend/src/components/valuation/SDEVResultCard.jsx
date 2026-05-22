import React from 'react';
import { icon } from '../ui/icons';

/**
 * SDEVResultCard — Supply-Demand Equilibrium Valuation result
 *
 * Displays the SDEV-M4 output:
 * - Market-acceptable price range (NOT transaction price)
 * - Acceptance score
 * - Confidence level
 * - Bid-ask overlap information
 * - Cluster statistics
 */
const formatVnd = (v) => {
  if (!v) return '—';
  if (v >= 1e9) return `${(v / 1e9).toFixed(2)} tỷ`;
  if (v >= 1e6) return `${(v / 1e6).toFixed(0)} triệu`;
  return new Intl.NumberFormat('vi-VN').format(v);
};

const CONFIDENCE_STYLES = {
  high:   { bg: '#06d6a015', border: '#06d6a030', text: '#06d6a0', label: 'Cao' },
  medium: { bg: '#f59e0b15', border: '#f59e0b30', text: '#f59e0b', label: 'Trung bình' },
  low:    { bg: '#ef233c15', border: '#ef233c30', text: '#ef233c', label: 'Thấp' },
};

const ACCEPTANCE_STYLES = (score) => {
  if (score >= 0.7) return { color: '#06d6a0', label: 'Tốt' };
  if (score >= 0.4) return { color: '#f59e0b', label: 'Trung bình' };
  return { color: '#ef233c', label: 'Thấp' };
};

export default function SDEVResultCard({ sdev, loading }) {
  if (loading) {
    return (
      <div className="card" style={{ borderColor: '#7c3aed30', background: '#7c3aed08' }}>
        <div className="card-header" style={{ color: '#7c3aed', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          SDEV — Supply-Demand Equilibrium Valuation
        </div>
        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
          Đang chạy SDEV...
        </div>
      </div>
    );
  }

  if (!sdev) return null;

  if (sdev.status === 'NO_ESTIMATE') {
    return (
      <div className="card" style={{ borderColor: '#ef233c30', background: '#ef233c08' }}>
        <div className="card-header" style={{ color: '#ef233c', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          SDEV — Không đủ dữ liệu
        </div>
        <div style={{ padding: '1rem' }}>
          <div style={{ color: '#ef233c', fontWeight: 600, marginBottom: '0.5rem' }}>
            Không thể ước lượng
          </div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Lý do: {sdev.reason || 'Dữ liệu không đủ để định giá'}
          </div>
          <div style={{
            marginTop: '0.75rem', padding: '0.75rem',
            background: '#ef233c15', borderRadius: 'var(--radius)',
            fontSize: '0.8rem', color: 'var(--text-secondary)',
            display: 'flex', alignItems: 'flex-start', gap: '0.4rem',
          }}>
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{flexShrink:0,marginTop:'2px'}}><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
            Cần thêm dữ liệu comparable listings hoặc buyer requirements trong khu vực này.
          </div>
        </div>
      </div>
    );
  }

  const {
    estimated_mid_price,
    acceptable_low,
    acceptable_high,
    price_per_m2,
    acceptance_score,
    confidence_level,
    ask_bid_overlap_score,
    cluster,
    demand_coverage_ratio,
    main_drivers,
    disclaimer,
    model,
  } = sdev;

  const confStyle = CONFIDENCE_STYLES[confidence_level] || CONFIDENCE_STYLES.low;
  const acceptStyle = ACCEPTANCE_STYLES(acceptance_score);
  const range_pct = acceptable_high > acceptable_low
    ? ((acceptable_high - acceptable_low) / acceptable_low * 100).toFixed(0)
    : '0';

  return (
    <div className="card" style={{ borderColor: '#7c3aed30', background: '#7c3aed05' }}>
      {/* Header */}
      <div className="card-header" style={{ color: '#7c3aed', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
        <span>SDEV — Supply-Demand Equilibrium Valuation</span>
        <span className="text-xs text-muted" style={{ marginLeft: 'auto', opacity: 0.7 }}>
          {model}
        </span>
      </div>

      {/* Disclaimer */}
      <div style={{
        padding: '0.5rem 0.75rem',
        background: '#f59e0b12',
        borderBottom: '1px solid #f59e0b20',
        fontSize: '0.72rem',
        color: '#f59e0b',
      }}>
        <span style={{ display: 'inline-flex', verticalAlign: 'middle', marginRight: 6 }}>{icon('warning', 14)}</span>
        {disclaimer || 'Đây là vùng giá ước lượng, KHÔNG phải giá giao dịch thực tế.'}
      </div>

      {/* Hero price range */}
      <div style={{ padding: '1.25rem 1.5rem' }}>
        <div style={{ textAlign: 'center', marginBottom: '1rem' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
            Vùng giá chấp nhận thị trường
          </div>
          <div style={{
            fontFamily: 'var(--font-display)',
            fontSize: '2rem',
            fontWeight: 800,
            color: '#7c3aed',
            letterSpacing: '-0.02em',
          }}>
            {formatVnd(acceptable_low)} — {formatVnd(acceptable_high)}
          </div>
          <div style={{
            fontSize: '0.8rem',
            color: 'var(--text-secondary)',
            marginTop: '0.25rem',
          }}>
            Giá trung vị: <strong style={{ color: '#7c3aed' }}>{formatVnd(estimated_mid_price)}</strong>
            {' '}| Rộng: ±{range_pct}%
          </div>
        </div>

        {/* Metrics grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '0.75rem',
          marginBottom: '1rem',
        }}>
          {/* Acceptance score */}
          <div style={{
            padding: '0.75rem',
            borderRadius: 'var(--radius)',
            background: `${acceptStyle.color}12`,
            border: `1px solid ${acceptStyle.color}25`,
            textAlign: 'center',
          }}>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
              Điểm chấp nhận
            </div>
            <div style={{ fontSize: '1.4rem', fontWeight: 700, color: acceptStyle.color }}>
              {(acceptance_score * 100).toFixed(0)}%
            </div>
            <div style={{ fontSize: '0.65rem', color: acceptStyle.color, marginTop: '0.15rem' }}>
              {acceptStyle.label}
            </div>
          </div>

          {/* Confidence */}
          <div style={{
            padding: '0.75rem',
            borderRadius: 'var(--radius)',
            background: confStyle.bg,
            border: `1px solid ${confStyle.border}`,
            textAlign: 'center',
          }}>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
              Độ tin cậy
            </div>
            <div style={{ fontSize: '1.4rem', fontWeight: 700, color: confStyle.text }}>
              {confStyle.label}
            </div>
          </div>

          {/* Overlap */}
          <div style={{
            padding: '0.75rem',
            borderRadius: 'var(--radius)',
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border)',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
              Ask-Bid Overlap
            </div>
            <div style={{
              fontSize: '1.4rem', fontWeight: 700,
              color: ask_bid_overlap_score > 0.3 ? '#06d6a0' : ask_bid_overlap_score > 0 ? '#f59e0b' : '#ef233c'
            }}>
              {(ask_bid_overlap_score * 100).toFixed(0)}%
            </div>
          </div>
        </div>

        {/* Cluster info */}
        {cluster && (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '0.5rem',
            fontSize: '0.75rem',
            padding: '0.75rem',
            background: 'var(--bg-secondary)',
            borderRadius: 'var(--radius)',
            marginBottom: '0.75rem',
          }}>
            <div>
              <span className="text-xs text-muted">Quận: </span>
              <strong>{cluster.district || '—'}</strong>
            </div>
            <div>
              <span className="text-xs text-muted">Diện tích: </span>
              <strong>{cluster.area_band || '—'}</strong>
            </div>
            <div>
              <span className="text-xs text-muted">PN: </span>
              <strong>{cluster.bedrooms || '—'}</strong>
            </div>
            <div>
              <span className="text-xs text-muted">Listings: </span>
              <strong style={{ color: '#7c3aed' }}>{cluster.n_ask_listings || 0}</strong>
            </div>
            <div>
              <span className="text-xs text-muted">Buyer reqs: </span>
              <strong style={{ color: cluster.n_bid_requirements > 0 ? '#06d6a0' : 'var(--text-muted)' }}>
                {cluster.n_bid_requirements || 0}
              </strong>
            </div>
            <div>
              <span className="text-xs text-muted">Coverage: </span>
              <strong>{((demand_coverage_ratio || 0) * 100).toFixed(0)}%</strong>
            </div>
          </div>
        )}

        {/* Price per m² */}
        {price_per_m2 > 0 && (
          <div style={{
            textAlign: 'center',
            fontSize: '0.8rem',
            color: 'var(--text-secondary)',
            marginBottom: '0.5rem',
          }}>
            Giá/m²: <strong>{formatVnd(price_per_m2)}/m²</strong>
          </div>
        )}

        {/* Main drivers */}
        {main_drivers && main_drivers.length > 0 && (
          <div>
            <div className="text-xs text-muted" style={{ marginBottom: '0.35rem' }}>
              Động lực chính
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
              {main_drivers.slice(0, 4).map((d, i) => (
                <span key={i} style={{
                  padding: '0.2rem 0.5rem',
                  background: '#7c3aed10',
                  borderRadius: '999px',
                  fontSize: '0.7rem',
                  color: '#7c3aed',
                  border: '1px solid #7c3aed20',
                }}>
                  {d}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
