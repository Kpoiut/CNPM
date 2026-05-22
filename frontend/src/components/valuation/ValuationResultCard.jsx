import React from 'react';
import { icon } from '../../components/ui/icons';

/**
 * ValuationResultCard — Hiển thị kết quả định giá 3 lớp
 *
 * Hiển thị:
 * 1. Market Valuation: fair_value, quick_sale, listing, range
 * 2. Adjustment Ledger: từng factor với delta_pct, delta_vnd, confidence
 * 3. Confidence Evidence: grade, evidence tier, warnings
 * 4. Fit Suitability: persona_fit, feng_shui, family_layout
 */

const formatVnd = (v) => {
  if (!v) return '—';
  return new Intl.NumberFormat('vi-VN', {
    style: 'currency', currency: 'VND', maximumFractionDigits: 0,
  }).format(v);
};

const formatPct = (v) => {
  if (v == null) return '—';
  const sign = v >= 0 ? '+' : '';
  return `${sign}${(v * 100).toFixed(1)}%`;
};

const CONFIDENCE_GRADE_COLORS = {
  A: { bg: '#06d6a015', border: '#06d6a030', text: '#06d6a0' },
  B: { bg: '#0099ff15', border: '#0099ff30', text: '#0099ff' },
  C: { bg: '#f59e0b15', border: '#f59e0b30', text: '#f59e0b' },
  D: { bg: '#ef233c15', border: '#ef233c30', text: '#ef233c' },
};

const FACTOR_GROUP_LABELS = {
  L1_LEGAL: 'Pháp lý',
  L2_GEOMETRY: 'Hình dạng',
  L3_ACCESS: 'Tiếp cận',
  L4_ENVIRONMENT: 'Môi trường',
  L5_BUILDING: 'Công trình',
  L6_VIEW_ORIENTATION: 'View & Hướng',
  F1_FENG_SHUI: 'Phong thủy',
  F2_SPIRITUAL: 'Tâm linh',
};

const CONFIDENCE_BAR_COLORS = { A: '#06d6a0', B: '#0099ff', C: '#f59e0b', D: '#ef233c' };

function FactorGroupBadge({ group }) {
  const colorMap = {
    L1_LEGAL: '#f59e0b',
    L2_GEOMETRY: '#3b82f6',
    L3_ACCESS: '#8b5cf6',
    L4_ENVIRONMENT: '#06d6a0',
    L5_BUILDING: '#f97316',
    L6_VIEW_ORIENTATION: '#06b6d4',
    F1_FENG_SHUI: '#a855f7',
    F2_SPIRITUAL: '#ec4899',
  };
  const color = colorMap[group] || 'var(--text-muted)';
  return (
    <span style={{
      padding: '0.2rem 0.5rem', borderRadius: '6px',
      fontSize: '0.68rem', fontWeight: 600,
      background: color + '18',
      color: color,
      border: `1px solid ${color}30`,
      display: 'inline-flex', alignItems: 'center', gap: '4px',
    }}>
      {FACTOR_GROUP_LABELS[group] || group}
    </span>
  );
}

export default function ValuationResultCard({ result, compact = false }) {
  if (!result) return null;

  const { market_valuation, confidence_evidence, fit_suitability } = result;
  if (!market_valuation) return null;

  const grade = confidence_evidence?.confidence_grade || 'D';
  const gradeColors = CONFIDENCE_GRADE_COLORS[grade] || CONFIDENCE_GRADE_COLORS.D;

  const adjustments = market_valuation.adjustment_ledger || [];

  return (
    <div className="space-y-4">
      {/* Hero price — Market Valuation */}
      <div style={{
        background: 'linear-gradient(135deg, var(--primary), var(--success))',
        borderRadius: 'var(--radius-lg)',
        padding: '2rem',
        textAlign: 'center',
        color: 'white',
      }}>
        <div style={{ fontSize: '0.8rem', opacity: 0.8, marginBottom: '0.5rem' }}>
          Giá trị thị trường thực
        </div>
        <div style={{ fontFamily: 'var(--font-display)', fontSize: '2.5rem', fontWeight: 800 }}>
          {formatVnd(market_valuation.fair_market_value)}
        </div>

        <div style={{
          display: 'flex', justifyContent: 'center', gap: '2rem', marginTop: '1rem', fontSize: '0.85rem', opacity: 0.85
        }}>
          <div>Quick sale<br /><strong>{formatVnd(market_valuation.quick_sale_value)}</strong></div>
          <div>Chào bán<br /><strong>{formatVnd(market_valuation.recommended_listing)}</strong></div>
          <div>Thấp nhất<br /><strong>{formatVnd(market_valuation.expected_range_low)}</strong></div>
          <div>Cao nhất<br /><strong>{formatVnd(market_valuation.expected_range_high)}</strong></div>
          {market_valuation.liquidity_score && (
            <div style={{ borderLeft: '1px solid rgba(255,255,255,0.2)', paddingLeft: '0.75rem' }}>
              Thanh khoản<br /><strong>{market_valuation.liquidity_score}</strong>
            </div>
          )}
          {market_valuation.optimistic_ask > market_valuation.expected_range_high && (
            <div style={{ opacity: 0.6 }}>Lạc quan<br /><strong>{formatVnd(market_valuation.optimistic_ask)}</strong></div>
          )}
        </div>
      </div>

      {compact && (
        <div style={{
          padding: '0.75rem 0.9rem',
          borderRadius: 8,
          border: '1px solid var(--border)',
          background: 'var(--surface-2)',
          color: 'var(--text-secondary)',
          fontSize: '0.82rem',
          lineHeight: 1.55,
        }}>
          Tóm tắt: mức độ tin cậy dự đoán <strong>{((confidence_evidence?.overall_confidence ?? 0) * 100).toFixed(0)}%</strong>, xếp hạng <strong>{confidence_evidence?.confidence_grade || '—'}</strong>, bậc nguồn <strong>{confidence_evidence?.evidence_tier || '—'}</strong>, số mẫu gần dùng được <strong>{confidence_evidence?.comparable_count || 0}</strong>. Chi tiết so sánh, pipeline và tác động nằm ở các tab bên cạnh.
        </div>
      )}

      {/* Confidence band */}
      {!compact && <div className="card">
        <div className="card-header" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          {icon('shieldCheck', 14)} Mức độ tin cậy dự đoán
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.75rem', marginTop: '0.5rem' }}>
          {[
            ['Xếp hạng', confidence_evidence?.confidence_grade || '—'],
            ['Mức độ tin cậy', `${((confidence_evidence?.overall_confidence ?? 0) * 100).toFixed(0)}%`],
            ['Bậc nguồn dữ liệu', confidence_evidence?.evidence_tier || '—'],
            ['Mẫu gần dùng được', confidence_evidence?.comparable_count || 0],
          ].map(([label, value]) => (
            <div key={label} style={{
              padding: '0.75rem', borderRadius: 'var(--radius)', textAlign: 'center',
              background: gradeColors.bg, border: `1px solid ${gradeColors.border}`,
            }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>{label}</div>
              <div style={{ fontSize: '1.2rem', fontWeight: 700, color: gradeColors.text }}>{value}</div>
            </div>
          ))}
        </div>
        <div style={{
          marginTop: '0.8rem',
          padding: '0.75rem 0.9rem',
          borderRadius: 8,
          background: 'var(--surface-2)',
          border: '1px solid var(--border)',
          color: 'var(--text-secondary)',
          fontSize: '0.82rem',
          lineHeight: 1.55,
        }}>
          <strong style={{ color: 'var(--text-primary)' }}>Mức độ tin cậy</strong> đo độ ổn định của giá dự đoán, phụ thuộc mạnh vào số mẫu gần, độ tương đồng khu vực, diện tích và độ phân tán giá. <strong style={{ color: 'var(--text-primary)' }}>Bậc nguồn dữ liệu</strong> đo tính minh bạch và truy xuất nguồn gốc, tức dữ liệu được xác minh tới đâu chứ không chỉ là có bao nhiêu mẫu.
        </div>
        {/* Comparable tier breakdown */}
        {confidence_evidence?.comparable_breakdown && (
          <div style={{ marginTop: '0.75rem' }}>
            <div className="text-xs text-muted">Phân bổ bậc nguồn dữ liệu</div>
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.25rem' }}>
              {Object.entries(confidence_evidence.comparable_breakdown).sort((a, b) => a[0].localeCompare(b[0])).map(([tier, count]) => (
                <span key={tier}
                  style={{
                    padding: '0.2rem 0.5rem', borderRadius: 'var(--radius)',
                    fontSize: '0.75rem', fontWeight: 600,
                    background: { E5: '#06d6a020', E4: '#0099ff20', E3: '#90e0ef20', E2: '#f59e0b20', E1: '#ef233c20' }[tier] || '#88888820',
                    color: { E5: '#06d6a0', E4: '#0099ff', E3: '#0099cc', E2: '#f59e0b', E1: '#ef233c' }[tier] || 'var(--text-secondary)',
                    border: '1px solid',
                  }}>
                  {tier}={count}
                </span>
              ))}
            </div>
          </div>
        )}
        {/* Confidence bar */}
        <div style={{ marginTop: '0.75rem' }}>
          <div style={{
            height: 8, borderRadius: 4, background: 'var(--border)', overflow: 'hidden',
          }}>
            <div style={{
              height: '100%', borderRadius: 4,
              background: CONFIDENCE_BAR_COLORS[grade] || '#888',
              width: `${(confidence_evidence?.overall_confidence || 0) * 100}%`,
              transition: 'width 1s',
            }} />
          </div>
        </div>
      </div>}

      {/* Adjustment Ledger */}
      {!compact && adjustments.length > 0 && (
        <div className="card">
          <div className="card-header">
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              {icon('sliders', 14)} Bảng điều chỉnh giá — {adjustments.length} yếu tố
            </span>
            <span className="text-xs text-muted" style={{ marginLeft: 'auto' }}>
              Lớp định giá thị trường
            </span>
          </div>
          <table className="table" style={{ fontSize: '0.82rem' }}>
            <thead>
              <tr>
                <th>Yếu tố</th>
                <th>Nhóm</th>
                <th style={{ textAlign: 'right' }}>Tác động %</th>
                <th style={{ textAlign: 'right' }}>Tác động VND</th>
                <th style={{ textAlign: 'right' }}>Độ chắc</th>
              </tr>
            </thead>
            <tbody>
              {adjustments.map((adj, i) => (
                <tr key={i}>
                  <td>
                    <span style={{
                      fontFamily: 'monospace', fontWeight: 700, fontSize: '0.78rem',
                      color: adj.direction === 'POSITIVE' ? '#06d6a0' : adj.direction === 'NEGATIVE' ? '#ef233c' : 'var(--text-muted)',
                    }}>
                      {adj.factor_code}
                    </span>
                    <div className="text-xs text-muted" style={{ marginTop: '0.1rem', maxWidth: 200 }}>
                      {adj.rationale}
                    </div>
                  </td>
                  <td>
                    <FactorGroupBadge group={adj.factor_group} />
                  </td>
                  <td style={{ textAlign: 'right', fontWeight: 700,
                    color: adj.direction === 'POSITIVE' ? '#06d6a0' : adj.direction === 'NEGATIVE' ? '#ef233c' : 'var(--text-secondary)' }}>
                    {formatPct(adj.delta_pct)}
                  </td>
                  <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>
                    {formatVnd(adj.delta_vnd).replace('₫', '').trim()}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <span className="badge" style={{
                      background: adj.confidence >= 0.8 ? '#06d6a020' :
                        adj.confidence >= 0.6 ? '#f59e0b20' : '#ef233c20',
                      color: adj.confidence >= 0.8 ? '#06d6a0' :
                        adj.confidence >= 0.6 ? '#f59e0b' : '#ef233c',
                    }}>
                      {(adj.confidence * 100).toFixed(0)}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Fit Suitability Layer */}
      {!compact && fit_suitability && (
        <div className="card" style={{ borderColor: 'var(--warning-border)' }}>
          <div className="card-header" style={{ color: 'var(--warning-dark)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            {icon('sliders', 14)} Độ phù hợp cá nhân — Fit Layer
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem', marginTop: '0.5rem' }}>
            {[
              ['Persona Fit', fit_suitability.persona_fit_score],
              ['Phong thủy', fit_suitability.feng_shui_fit],
              ['Gia đình', fit_suitability.family_layout_fit],
            ].map(([label, score]) => score != null && (
              <div key={label} style={{
                padding: '0.75rem', borderRadius: 'var(--radius)',
                background: 'var(--warning-bg)', border: '1px solid var(--warning-border)',
                textAlign: 'center',
              }}>
                <div className="text-xs text-muted">{label}</div>
                <div style={{ fontSize: '1.3rem', fontWeight: 800 }}>
                  {score != null ? `${(score * 100).toFixed(0)}%` : '—'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Warnings */}
      {!compact && confidence_evidence?.warnings?.length > 0 && (
        <div className="alert alert-warning">
          <span style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem' }}>
            {icon('alertTriangle', 16, '')}
            <div>
              <strong>Cảnh báo:</strong>
              <ul style={{ marginTop: '0.5rem', paddingLeft: '1.25rem' }}>
                {confidence_evidence.warnings.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </div>
          </span>
        </div>
      )}
      {!compact && confidence_evidence?.recommendations?.length > 0 && (
        <div className="alert alert-info">
          <span style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem' }}>
            {icon('sparkles', 16, '')}
            <div>
              <strong>Khuyến nghị:</strong>
              <ul style={{ marginTop: '0.5rem', paddingLeft: '1.25rem' }}>
                {confidence_evidence.recommendations.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            </div>
          </span>
        </div>
      )}
    </div>
  );
}
