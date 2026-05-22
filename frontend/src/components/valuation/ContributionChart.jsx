import React from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Cell,
} from 'recharts';

function fmtVnd(v) {
  if (!v) return '—';
  if (v >= 1e9) return `${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6) return `${(v / 1e6).toFixed(0)}M`;
  return `${(v / 1e3).toFixed(0)}K`;
}

const MAX_DISPLAY = 15;

/**
 * Horizontal bar chart showing contribution % per field.
 * Positive → green, Negative → red, Residual → gray.
 * Bars are clamped at ±15% display layer.
 */
export function ContributionChart({ contributions = [], onSelect }) {
  if (!contributions || contributions.length === 0) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        Không có dữ liệu tác động.
      </div>
    );
  }

  const data = contributions.map(c => ({
    name: c.field_label,
    raw: c.raw_delta_pct,
    display: c.display_delta_pct,
    fieldCode: c.field_code,
    direction: c.direction,
    isResidual: c.is_residual,
    contributionVnd: c.contribution_vnd,
    confidence: c.confidence,
    source: c.source,
    detail: c.detail,
    rawDisplay: `${c.raw_delta_pct > 0 ? '+' : ''}${c.raw_delta_pct.toFixed(1)}%`,
    displayDisplay: `${c.display_delta_pct > 0 ? '+' : ''}${c.display_delta_pct.toFixed(1)}%`,
  }));

  function getBarColor(d) {
    if (d.isResidual) return '#94a3b8';
    if (d.direction === 'POSITIVE') return '#10b981';
    if (d.direction === 'NEGATIVE') return '#ef4444';
    return '#94a3b8';
  }

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    const d = payload[0].payload;
    return (
      <div style={{
        background: 'var(--card-bg)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        padding: '0.6rem 0.9rem',
        fontSize: '0.82rem',
        minWidth: '200px',
      }}>
        <div style={{ fontWeight: 600, marginBottom: '0.3rem' }}>{d.name}</div>
        <div style={{ color: getBarColor(d) }}>
          <span>Display: </span><strong>{d.displayDisplay}</strong>
        </div>
        {d.raw !== d.display && (
          <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
            Raw: {d.rawDisplay}
          </div>
        )}
        <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
          VND: {fmtVnd(d.contributionVnd)}
        </div>
        <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
          Độ tin cậy: {d.confidence ? `${(d.confidence * 100).toFixed(0)}%` : '—'}
        </div>
        <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: '0.2rem' }}>
          {d.detail}
        </div>
      </div>
    );
  };

  return (
    <ResponsiveContainer width="100%" height={Math.max(250, data.length * 36 + 20)}>
      <BarChart
        layout="vertical"
        data={data}
        margin={{ top: 0, right: 60, left: 10, bottom: 0 }}
        barSize={14}
      >
        <CartesianGrid strokeDasharray="2 2" stroke="var(--border)" horizontal={false} />
        <XAxis
          type="number"
          domain={[-MAX_DISPLAY, MAX_DISPLAY]}
          tickFormatter={v => `${v > 0 ? '+' : ''}${v}%`}
          tick={{ fontSize: 11 }}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="name"
          width={130}
          tick={{ fontSize: 12 }}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
        <ReferenceLine x={0} stroke="var(--border)" strokeWidth={1} />
        <Bar
          dataKey="display"
          radius={[0, 3, 3, 0]}
          onClick={(d) => onSelect && onSelect(d)}
          style={{ cursor: onSelect ? 'pointer' : 'default' }}
        >
          {data.map((entry, i) => (
            <Cell key={i} fill={getBarColor(entry)} fillOpacity={0.85} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
