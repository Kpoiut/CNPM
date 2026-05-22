import React from 'react';
import { icon } from '../ui/icons';

/**
 * SubEnginePanel — Hiển thị kết quả chi tiết từ sub-engines:
 *   - Legal Assessment (grade, factors, block status)
 *   - Geometry Metrics (area, shape, taper, buildable)
 *   - Environment Assessment (grade, hazards, positives)
 */

const GRADE_COLORS = {
  A: '#06d6a0', B: '#0099ff', C: '#f59e0b', D: '#ef233c', F: '#dc2626',
};

function GradeBadge({ grade, label }) {
  const color = GRADE_COLORS[grade] || '#64748b';
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      padding: '0.75rem', borderRadius: '8px',
      background: `${color}10`, border: `1px solid ${color}30`,
    }}>
      <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginBottom: '0.2rem' }}>{label}</div>
      <div style={{ fontSize: '1.5rem', fontWeight: 800, color }}>{grade || '—'}</div>
    </div>
  );
}

function FactorRow({ icon, label, value, impact, color }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '0.5rem',
      padding: '0.35rem 0', borderBottom: '1px solid var(--border)',
      fontSize: '0.8rem',
    }}>
      <span style={{ width: '20px', textAlign: 'center' }}>{icon}</span>
      <span style={{ flex: 1, color: 'var(--text-secondary)' }}>{label}</span>
      <span style={{ fontWeight: 600, color: color || 'var(--text-primary)' }}>{value}</span>
      {impact != null && (
        <span style={{
          fontFamily: 'monospace', fontSize: '0.75rem', fontWeight: 600,
          color: impact > 0 ? '#06d6a0' : impact < 0 ? '#ef233c' : '#64748b',
        }}>
          {impact > 0 ? '+' : ''}{(impact * 100).toFixed(1)}%
        </span>
      )}
    </div>
  );
}

export default function SubEnginePanel({ legal, geometry, environment }) {
  const hasAny = legal || geometry || environment;
  if (!hasAny) return null;

  return (
    <div style={{ display: 'grid', gap: '1rem' }}>

      {/* Legal Assessment */}
      {legal && (
        <div className="card">
          <div className="card-header" style={{ borderBottom: '1px solid var(--border, #e5e7eb)' }}>
            <span>{icon('shieldCheck', 16)}</span>
            <span style={{ fontWeight: 700, fontSize: '0.85rem', marginLeft: '0.5rem' }}>
              Đánh giá pháp lý
            </span>
            {legal.is_blocked && (
              <span style={{
                marginLeft: 'auto', padding: '0.15rem 0.5rem', borderRadius: '4px',
                background: '#ef233c15', border: '1px solid #ef233c30', color: '#ef233c',
                fontSize: '0.72rem', fontWeight: 700,
              }}>
                BLOCKED
              </span>
            )}
          </div>
          <div style={{ padding: '0.75rem 1rem' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem', marginBottom: '0.75rem' }}>
              <GradeBadge grade={legal.legal_risk_grade} label="Rủi ro" />
              <GradeBadge grade={legal.ownership_grade} label="Quyền sở hữu" />
              <div style={{
                display: 'flex', flexDirection: 'column', alignItems: 'center',
                padding: '0.75rem', borderRadius: '8px',
                background: legal.compound_risk ? '#ef233c10' : '#06d6a010',
                border: `1px solid ${legal.compound_risk ? '#ef233c30' : '#06d6a030'}`,
              }}>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginBottom: '0.2rem' }}>Rủi ro tổng hợp</div>
                <div style={{
                  fontSize: '1rem', fontWeight: 700,
                  color: legal.compound_risk ? '#ef233c' : '#06d6a0',
                }}>
                  {legal.compound_risk ? 'CÓ' : 'KHÔNG'}
                </div>
              </div>
            </div>
            {legal.factors?.map((f, i) => (
              <FactorRow
                key={i}
                icon=""
                label={f.factor_code?.replace(/_/g, ' ') || `Factor ${i + 1}`}
                value={f.rationale || ''}
                impact={f.impact_pct}
              />
            ))}
          </div>
        </div>
      )}

      {/* Geometry Metrics */}
      {geometry && (
        <div className="card">
          <div className="card-header" style={{ borderBottom: '1px solid var(--border, #e5e7eb)' }}>
            <span>{icon('layoutGrid', 16)}</span>
            <span style={{ fontWeight: 700, fontSize: '0.85rem', marginLeft: '0.5rem' }}>
              Phân tích hình học
            </span>
          </div>
          <div style={{ padding: '0.75rem 1rem' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.5rem', marginBottom: '0.75rem' }}>
              {[
                ['Diện tích', `${geometry.computed_area_m2?.toFixed(1) || '—'} m²`],
                ['Xây được', `${geometry.buildable_area_m2?.toFixed(1) || '—'} m²`],
                ['Vuông vắn', `${((geometry.squareness_score || 0) * 100).toFixed(0)}%`],
                ['Loại', geometry.taper_type || '—'],
              ].map(([label, value]) => (
                <div key={label} style={{
                  textAlign: 'center', padding: '0.5rem', borderRadius: '6px',
                  background: 'var(--bg-surface)', border: '1px solid var(--border)',
                }}>
                  <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>{label}</div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 700 }}>{value}</div>
                </div>
              ))}
            </div>
            <FactorRow icon="" label="Nở hậu score" value={geometry.nö_hậu_score?.toFixed(2) || '0'} />
            <FactorRow icon="" label="Thóp hậu score" value={geometry.thóp_hậu_score?.toFixed(2) || '0'} />
            {geometry.has_neck && (
              <FactorRow icon="" label="Có chai (neck)" value={`${geometry.neck_width_m?.toFixed(1)}m`} color="#ef233c" />
            )}
          </div>
        </div>
      )}

      {/* Environment Assessment */}
      {environment && (
        <div className="card">
          <div className="card-header" style={{ borderBottom: '1px solid var(--border, #e5e7eb)' }}>
            <span>{icon('tree', 16)}</span>
            <span style={{ fontWeight: 700, fontSize: '0.85rem', marginLeft: '0.5rem' }}>
              Đánh giá môi trường
            </span>
          </div>
          <div style={{ padding: '0.75rem 1rem' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem', marginBottom: '0.75rem' }}>
              <GradeBadge grade={environment.risk_grade} label="Rủi ro" />
              <div style={{
                display: 'flex', flexDirection: 'column', alignItems: 'center',
                padding: '0.75rem', borderRadius: '8px', background: 'var(--bg-surface)', border: '1px solid var(--border)',
              }}>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginBottom: '0.2rem' }}>Rủi ro</div>
                <div style={{ fontSize: '1.2rem', fontWeight: 800 }}>{environment.hazard_count || 0}</div>
              </div>
              <div style={{
                display: 'flex', flexDirection: 'column', alignItems: 'center',
                padding: '0.75rem', borderRadius: '8px', background: 'var(--bg-surface)', border: '1px solid var(--border)',
              }}>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginBottom: '0.2rem' }}>Tác động ròng</div>
                <div style={{
                  fontSize: '1rem', fontWeight: 700,
                  color: (environment.net_impact_pct || 0) >= 0 ? '#06d6a0' : '#ef233c',
                }}>
                  {environment.net_impact_pct != null ?
                    `${(environment.net_impact_pct * 100).toFixed(1)}%` : '—'
                  }
                </div>
              </div>
            </div>
            {environment.hazards?.map((h, i) => (
              <FactorRow
                key={i}
                icon=""
                label={h.hazard_code?.replace(/_/g, ' ') || `Hazard ${i + 1}`}
                value={h.explanation || ''}
                impact={h.impact_pct}
              />
            ))}
            {environment.positive_factors?.map((h, i) => (
              <FactorRow
                key={`p${i}`}
                icon=""
                label={h.hazard_code?.replace(/_/g, ' ') || `Positive ${i + 1}`}
                value={h.explanation || ''}
                impact={h.impact_pct}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
