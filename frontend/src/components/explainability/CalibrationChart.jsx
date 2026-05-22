import React from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, LineChart, Line, ReferenceLine } from 'recharts'
import ChartWrapper from '../ui/ChartWrapper'

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 6,
      padding: '0.5rem 0.75rem',
      fontSize: '0.75rem',
      boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
    }}>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>Confidence Band: {label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color }}>{p.name}: {p.value?.toFixed(1)}%</div>
      ))}
      <div style={{ color: 'var(--text-muted)', marginTop: 4 }}>
        Samples: {payload[0]?.payload?.n_samples}
      </div>
    </div>
  )
}

export default function CalibrationChart({ data, height = 300, showDetails = false }) {
  if (!data || data.length === 0) return null

  const chartData = data.map(b => ({
    band: `Band ${b.band}`,
    fullBand: b.band,
    'Predicted ICP': b.predicted_coverage_pct,
    'Actual ICP': b.actual_coverage_pct,
    'Calibration Error': b.calibration_error,
    n_samples: b.n_samples,
    mean_width: b.mean_interval_width,
    predicted: b.predicted_coverage_pct,
    actual: b.actual_coverage_pct,
    error: b.calibration_error,
  }))

  const bandColors = { A: '#22c55e', B: '#3b82f6', C: '#f59e0b', D: '#ef4444' }

  return (
    <div>
      <ChartWrapper height={height - 40}>
        <BarChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="band" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} axisLine={{ stroke: '#334155' }} tickLine={false} />
          <YAxis
            domain={[0, 100]}
            tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
            axisLine={{ stroke: '#334155' }}
            tickLine={false}
            tickFormatter={v => `${v}%`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ fontSize: '0.75rem' }}
            formatter={(value) => <span style={{ color: 'var(--text-secondary)' }}>{value}</span>}
          />
          <Bar dataKey="Predicted ICP" fill="#3b82f6" opacity={0.6} radius={[3, 3, 0, 0]} />
          <Bar dataKey="Actual ICP" fill="#22c55e" opacity={0.8} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ChartWrapper>

      {showDetails && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '0.5rem', marginTop: '0.5rem' }}>
          {chartData.map(b => (
            <div key={b.band} style={{
              background: 'var(--bg-elevated)',
              borderRadius: 6,
              padding: '0.5rem',
              fontSize: '0.7rem',
              borderLeft: `3px solid ${bandColors[b.fullBand] || 'var(--border)'}`,
            }}>
              <div style={{ fontWeight: 600 }}>{b.band}</div>
              <div style={{ color: 'var(--text-muted)' }}>Pred: {b.predicted}%</div>
              <div style={{ color: 'var(--text-muted)' }}>Actual: {b.actual}%</div>
              <div style={{ color: Math.abs(b.error) < 5 ? '#22c55e' : '#f59e0b' }}>Error: {b.error}%</div>
            </div>
          ))}
        </div>
      )}

      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
        <span style={{ color: '#3b82f6' }}>■</span> Predicted vs{' '}
        <span style={{ color: '#22c55e' }}>■</span> Actual coverage. Target: actual within ±5% of predicted.
      </div>
    </div>
  )
}
