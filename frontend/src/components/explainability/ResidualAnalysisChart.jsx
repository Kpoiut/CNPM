import React from 'react'
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ZAxis, Cell
} from 'recharts'
import ChartWrapper from '../ui/ChartWrapper'

// E5 = HIGHEST confidence (green), E1 = LOWEST (red)
const TIER_COLORS = { E5: '#22c55e', E4: '#3b82f6', E3: '#f59e0b', E2: '#a855f7', E1: '#ef4444' }

function formatVND(v) {
  if (v >= 1e9) return `${(v / 1e9).toFixed(1)}B`
  if (v >= 1e6) return `${(v / 1e6).toFixed(0)}M`
  return `${(v / 1e3).toFixed(0)}K`
}

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  if (!d) return null
  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 6,
      padding: '0.5rem 0.75rem',
      fontSize: '0.75rem',
      boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
    }}>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>ID: {d.id}</div>
      <div>District: {d.district}</div>
      <div>Type: {d.property_type}</div>
      <div>Actual: {formatVND(d.actual_price)} VND</div>
      <div>Predicted: {formatVND(d.predicted_price)} VND</div>
      <div style={{ color: Math.abs(d.residual_pct) < 15 ? '#22c55e' : '#ef4444' }}>
        Error: {d.residual_pct > 0 ? '+' : ''}{d.residual_pct.toFixed(1)}%
      </div>
    </div>
  )
}

export default function ResidualAnalysisChart({ data, height = 300, fullScatter = false }) {
  if (!data || !data.scatter_sample?.length) return null

  const points = data.scatter_sample.map(p => ({
    ...p,
    residual_abs: Math.abs(p.residual_pct),
  }))

  // For histogram: residual bins
  const residuals = points.map(p => p.residual_pct)
  const histData = []
  const bins = [-50, -30, -15, -5, 5, 15, 30, 50, 100]
  for (let i = 0; i < bins.length - 1; i++) {
    const count = residuals.filter(r => r >= bins[i] && r < bins[i + 1]).length
    if (count > 0 || true) {
      histData.push({
        range: `${bins[i]}% – ${bins[i + 1]}%`,
        count,
        color: bins[i] >= 0 ? '#ef4444' : '#3b82f6',
      })
    }
  }

  if (fullScatter) {
    return (
      <ChartWrapper height={height}>
        <ScatterChart margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="actual_price"
            type="number"
            tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
            axisLine={{ stroke: '#334155' }}
            tickFormatter={formatVND}
            name="Actual Price"
            tickLine={false}
          />
          <YAxis
            dataKey="predicted_price"
            type="number"
            tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
            axisLine={{ stroke: '#334155' }}
            tickFormatter={formatVND}
            name="Predicted Price"
            tickLine={false}
          />
          <ZAxis range={[20, 60]} />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine
            segment={[{ x: 0, y: 0 }, { x: 1e10, y: 1e10 }]}
            stroke="#7c3aed"
            strokeDasharray="3 3"
            strokeWidth={1.5}
          />
          <Scatter data={points} name="Properties">
            {points.map((p, i) => (
              <Cell
                key={`cell-${i}`}
                fill={TIER_COLORS[p.tier] || '#a855f7'}
                opacity={0.6}
              />
            ))}
          </Scatter>
        </ScatterChart>
      </ChartWrapper>
    )
  }

  return (
    <ChartWrapper height={height}>
      <ScatterChart margin={{ top: 5, right: 10, left: -10, bottom: 20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis
          dataKey="residual_pct"
          type="number"
          tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
          axisLine={{ stroke: '#334155' }}
          tickLine={false}
          tickFormatter={v => `${v}%`}
          name="Residual %"
        />
        <YAxis
          dataKey="residual_abs"
          type="number"
          tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
          axisLine={{ stroke: '#334155' }}
          tickLine={false}
          tickFormatter={v => `${v}%`}
          name="Abs Residual %"
        />
        <ZAxis range={[20, 60]} />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine x={0} stroke="#64748b" strokeWidth={1} />
        <Scatter data={points} name="Properties">
          {points.map((p, i) => (
            <Cell
              key={`cell-${i}`}
              fill={Math.abs(p.residual_pct) < 15 ? '#22c55e'
                : Math.abs(p.residual_pct) < 30 ? '#f59e0b'
                : '#ef4444'}
              opacity={0.5}
            />
          ))}
        </Scatter>
      </ScatterChart>
    </ChartWrapper>
  )
}
