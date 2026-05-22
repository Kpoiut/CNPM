import React from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ReferenceLine, LineChart, Line } from 'recharts'
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
      <div style={{ fontWeight: 600, marginBottom: 4 }}>{label}</div>
      <div>Count: {payload[0]?.value}</div>
    </div>
  )
}

export default function PredictionDistributionChart({ data, height = 300 }) {
  if (!data || !data.scatter_sample?.length) return null

  const residuals = data.scatter_sample.map(p => p.residual_pct)

  // Histogram bins
  const binEdges = [-100, -50, -30, -20, -10, -5, 5, 10, 20, 30, 50, 100]
  const bins = []
  for (let i = 0; i < binEdges.length - 1; i++) {
    const count = residuals.filter(r => r >= binEdges[i] && r < binEdges[i + 1]).length
    bins.push({
      range: `${binEdges[i]}% – ${binEdges[i + 1]}%`,
      count,
      mid: (binEdges[i] + binEdges[i + 1]) / 2,
    })
  }
  // Overflow
  const overflowNeg = residuals.filter(r => r < -100).length
  const overflowPos = residuals.filter(r => r >= 100).length

  const chartData = [
    ...bins.map(b => ({ range: b.range, count: b.count, mid: b.mid })),
    overflowNeg > 0 && { range: '< -100%', count: overflowNeg, mid: -110 },
    overflowPos > 0 && { range: '>= +100%', count: overflowPos, mid: 110 },
  ].filter(Boolean)

  const medianResidual = residuals.sort((a, b) => a - b)[Math.floor(residuals.length / 2)]
  const meanResidual = residuals.reduce((a, b) => a + b, 0) / residuals.length
  const p5 = residuals.sort((a, b) => a - b)[Math.floor(residuals.length * 0.05)]
  const p95 = residuals.sort((a, b) => a - b)[Math.floor(residuals.length * 0.95)]

  return (
    <div>
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '0.5rem', flexWrap: 'wrap' }}>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
          Median: <strong style={{ color: 'var(--text-primary)' }}>{medianResidual.toFixed(1)}%</strong>
        </div>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
          Mean: <strong style={{ color: 'var(--text-primary)' }}>{meanResidual.toFixed(1)}%</strong>
        </div>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
          P5-P95: <strong style={{ color: 'var(--text-primary)' }}>{p5.toFixed(1)}% – {p95.toFixed(1)}%</strong>
        </div>
      </div>
      <ChartWrapper height={height - 50}>
        <BarChart data={chartData} margin={{ top: 5, right: 10, left: -15, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="range"
            tick={{ fontSize: 9, fill: 'var(--text-muted)' }}
            axisLine={{ stroke: '#334155' }}
            tickLine={false}
            angle={-20}
            textAnchor="end"
          />
          <YAxis tick={{ fontSize: 10, fill: 'var(--text-muted)' }} axisLine={{ stroke: '#334155' }} tickLine={false} />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine x={0} stroke="#7c3aed" strokeDasharray="3 3" />
          <Bar dataKey="count" name="Count" radius={[3, 3, 0, 0]}>
            {chartData.map((entry, i) => {
              const mid = entry.mid
              let color = '#22c55e'
              if (mid >= 20 || mid <= -20) color = '#ef4444'
              else if (mid >= 10 || mid <= -10) color = '#f59e0b'
              else if (mid >= 5 || mid <= -5) color = '#f59e0b'
              return <Cell key={i} fill={color} opacity={0.7} />
            })}
          </Bar>
        </BarChart>
      </ChartWrapper>
      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        <span style={{ color: '#22c55e' }}>{'■'} {'<±'}5% good</span>
        <span style={{ color: '#f59e0b' }}>{'■'} {'±'}5-20% acceptable</span>
        <span style={{ color: '#ef4444' }}>{'■'} {'>±'}20% high error</span>
      </div>
    </div>
  )
}
