import React from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ReferenceLine } from 'recharts'
import ChartWrapper from '../ui/ChartWrapper'

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const val = payload[0]?.value || 0
  const dataPoint = payload[0]?.payload
  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 6,
      padding: '0.5rem 0.75rem',
      fontSize: '0.75rem',
      boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
    }}>
      <div style={{ fontWeight: 600, marginBottom: 4, maxWidth: 200, wordBreak: 'break-word' }}>
        {label}
      </div>
      <div style={{ color: val >= 0 ? '#22c55e' : '#ef4444' }}>
        {val >= 0 ? '+' : ''}{val.toLocaleString('vi-VN')} VND
      </div>
      {dataPoint?.value !== undefined && (
        <div style={{ color: 'var(--text-muted)', marginTop: 2 }}>
          Feature value: {typeof dataPoint.value === 'number' ? dataPoint.value.toFixed(4) : dataPoint.value}
        </div>
      )}
    </div>
  )
}

export default function SHAPWaterfallChart({ data, height = 400 }) {
  if (!data || !data.steps?.length) {
    return (
      <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
        No waterfall data available
      </div>
    )
  }

  const { steps, base_value, final_value, predicted_price_vnd } = data
  const topSteps = steps.slice(0, 20)

  // Build cumulative data
  let cumulative = base_value
  const chartData = topSteps.map((step, i) => {
    const start = cumulative
    cumulative += step.contribution
    return {
      name: step.feature.replace(/_norm|_feature|_score/g, '').replace(/_/g, ' '),
      fullName: step.feature,
      contribution: step.contribution,
      start: start,
      end: cumulative,
      value: step.value,
      is_positive: step.is_positive,
    }
  })

  return (
    <div>
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          Base: <strong style={{ color: 'var(--text-primary)' }}>{base_value?.toLocaleString('vi-VN')} VND</strong>
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          Final: <strong style={{ color: 'var(--primary)' }}>{predicted_price_vnd}</strong>
        </div>
      </div>
      <ChartWrapper height={height - 50}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 2, right: 100, left: 8, bottom: 2 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
          <XAxis
            type="number"
            tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
            axisLine={{ stroke: '#334155' }}
            tickLine={false}
            tickFormatter={v => `${(v / 1e9).toFixed(1)}B`}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={130}
            tick={{ fontSize: 9, fill: 'var(--text-secondary)' }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine x={final_value} stroke="#7c3aed" strokeDasharray="3 3" strokeWidth={2} />
          <Bar dataKey="contribution" radius={[0, 3, 3, 0]} stackId="a">
            {chartData.map((entry, i) => (
              <Cell
                key={`cell-${i}`}
                fill={entry.is_positive
                  ? (i === 0 ? 'rgba(34,197,94,0.3)' : '#22c55e')
                  : (i === 0 ? 'rgba(239,68,68,0.3)' : '#ef4444')}
              />
            ))}
          </Bar>
        </BarChart>
      </ChartWrapper>
      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.25rem', display: 'flex', gap: '1rem' }}>
        <span style={{ color: '#22c55e' }}>● Green = positive contribution</span>
        <span style={{ color: '#ef4444' }}>● Red = negative contribution</span>
      </div>
    </div>
  )
}
