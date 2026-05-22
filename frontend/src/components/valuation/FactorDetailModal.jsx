import React from 'react';

/**
 * FactorDetailModal — shows detailed breakdown for a single factor.
 * Triggered by clicking a bar in ContributionChart.
 */
export function FactorDetailModal({ factor, onClose }) {
  if (!factor) return null;

  const directionColor = factor.direction === 'POSITIVE' ? '#10b981'
    : factor.direction === 'NEGATIVE' ? '#ef4444'
    : '#94a3b8';

  const directionLabel = factor.direction === 'POSITIVE' ? 'Tích cực'
    : factor.direction === 'NEGATIVE' ? 'Tiêu cực'
    : 'Trung tính';

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        background: 'rgba(0,0,0,0.6)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '1rem',
      }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div style={{
        background: 'var(--card-bg)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        padding: '1.5rem',
        maxWidth: '520px',
        width: '100%',
        boxShadow: '0 20px 60px rgba(0,0,0,0.4)',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.1rem' }}>{factor.field_label}</h3>
            <span style={{
              display: 'inline-block',
              marginTop: '0.3rem',
              padding: '2px 10px',
              borderRadius: 'var(--radius-full)',
              fontSize: '0.72rem',
              fontWeight: 600,
              background: `${directionColor}20`,
              color: directionColor,
              border: `1px solid ${directionColor}40`,
            }}>
              {directionLabel}
            </span>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: 'var(--text-muted)', fontSize: '1.2rem', padding: '0.2rem',
            }}
          >
            ✕
          </button>
        </div>

        {/* Value comparison */}
        <div style={{
          background: 'var(--bg-secondary)',
          borderRadius: 'var(--radius)',
          padding: '1rem',
          marginBottom: '1rem',
        }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.4rem' }}>
            Giá trị đầu vào
          </div>
          <div style={{ fontSize: '1.3rem', fontWeight: 700 }}>
            {formatFieldValue(factor.field_value, factor.field_code)}
          </div>
          {factor.comparable_mean != null && (
            <>
              <div style={{
                display: 'flex', gap: '1rem', marginTop: '0.6rem',
                fontSize: '0.82rem', color: 'var(--text-muted)',
              }}>
                <span>Mean: <strong style={{ color: 'var(--text)' }}>
                  {formatFieldValue(factor.comparable_mean, factor.field_code)}
                </strong></span>
                {factor.comparable_range && (
                  <span>Range: <strong style={{ color: 'var(--text)' }}>
                    {formatFieldValue(factor.comparable_range[0], factor.field_code)}
                    {' – '}
                    {formatFieldValue(factor.comparable_range[1], factor.field_code)}
                  </strong></span>
                )}
              </div>
            </>
          )}
        </div>

        {/* Delta breakdown */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1rem' }}>
          <DeltaBox
            label="Raw δ%"
            value={`${factor.raw_delta_pct > 0 ? '+' : ''}${factor.raw_delta_pct?.toFixed(2)}%`}
            note="Giá trị thực (audit)"
            color={directionColor}
          />
          <DeltaBox
            label="Display δ%"
            value={`${factor.display_delta_pct > 0 ? '+' : ''}${factor.display_delta_pct?.toFixed(2)}%`}
            note={factor.raw_delta_pct !== factor.display_delta_pct ? 'Đã clamp ±15%' : 'Trong giới hạn'}
            color={directionColor}
          />
        </div>

        {/* Metadata */}
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
          <MetaTag label="VND" value={formatVnd(factor.contribution_vnd)} />
          <MetaTag label="Tin cậy" value={factor.confidence ? `${(factor.confidence * 100).toFixed(0)}%` : '—'} />
          <MetaTag label="Nguồn" value={factor.source} />
          <MetaTag label="Missing" value={factor.is_missing ? 'Có' : 'Không'} />
        </div>

        {/* Detail */}
        {factor.detail && (
          <div style={{
            padding: '0.75rem',
            background: 'var(--bg-secondary)',
            borderRadius: 'var(--radius)',
            fontSize: '0.82rem',
            color: 'var(--text-secondary)',
            lineHeight: 1.5,
          }}>
            {factor.detail}
          </div>
        )}
      </div>
    </div>
  );
}

function DeltaBox({ label, value, note, color }) {
  return (
    <div style={{
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius)',
      padding: '0.6rem 0.8rem',
    }}>
      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
        {label}
      </div>
      <div style={{ fontSize: '1.1rem', fontWeight: 700, color }}>
        {value}
      </div>
      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
        {note}
      </div>
    </div>
  );
}

function MetaTag({ label, value }) {
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '0.3rem',
      padding: '2px 8px',
      background: 'var(--bg-secondary)',
      borderRadius: 'var(--radius-full)',
      fontSize: '0.75rem',
      border: '1px solid var(--border)',
    }}>
      <span style={{ color: 'var(--text-muted)' }}>{label}:</span>
      <strong>{value}</strong>
    </span>
  );
}

function formatFieldValue(value, fieldCode) {
  if (value === null || value === undefined) return '—';
  if (fieldCode === 'area_m2') return `${value} m²`;
  if (fieldCode === 'frontage_m') return `${value} m`;
  if (fieldCode === 'road_width_m') return `${value} m`;
  if (fieldCode === 'bedrooms') return `${value} phòng`;
  if (fieldCode === 'floor_count') return `${value} tầng`;
  if (fieldCode === 'latitude' || fieldCode === 'longitude') return `${value}`;
  if (typeof value === 'boolean') return value ? 'Có' : 'Không';
  return String(value);
}

function formatVnd(v) {
  if (!v) return '—';
  if (Math.abs(v) >= 1e9) return `${(v / 1e9).toFixed(2)} tỷ`;
  if (Math.abs(v) >= 1e6) return `${(v / 1e6).toFixed(0)} triệu`;
  return `${v.toLocaleString('vi-VN')} đ`;
}
