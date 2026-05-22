import React from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell } from 'recharts'
import ChartWrapper from '../ui/ChartWrapper'

const COLORS = {
  positive: '#22c55e',
  negative: '#ef4444',
  neutral: '#3b82f6',
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const val = payload[0]?.value || 0
  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 6,
      padding: '0.5rem 0.75rem',
      fontSize: '0.75rem',
      boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
    }}>
      <div style={{ fontWeight: 600, marginBottom: 4, maxWidth: 220, wordBreak: 'break-word' }}>{label}</div>
      <div style={{ color: 'var(--primary)' }}>Importance: {typeof val === 'number' ? val.toFixed(4) : val}</div>
    </div>
  )
}

export default function FeatureImportanceChart({ data, topN = 15, height = 300, showLabels = false }) {
  if (!data || data.length === 0) return null

  const chartData = data
    .slice(0, topN)
    .map(item => ({
      name: item.feature.replace(/_norm|_feature|_score/g, '').replace(/_/g, ' '),
      fullName: item.feature,
      value: item.importance,
      color: item.importance >= 0 ? COLORS.neutral : COLORS.negative,
    }))
    .reverse()

  return (
    <ChartWrapper height={height}>
      <BarChart
        data={chartData}
        layout="vertical"
        margin={{ top: 5, right: showLabels ? 80 : 20, left: showLabels ? 10 : 10, bottom: 5 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
        <XAxis
          type="number"
          tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
          axisLine={{ stroke: '#334155' }}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="name"
          width={showLabels ? 160 : 130}
          tick={{ fontSize: showLabels ? 10 : 9, fill: 'var(--text-secondary)' }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="value" radius={[0, 3, 3, 0]}>
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Bar>
      </BarChart>
    </ChartWrapper>
  )
}
