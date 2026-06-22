import React from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, Cell, ReferenceLine } from 'recharts'
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
      <div style={{ fontWeight: 600, marginBottom: 4, maxWidth: 200, wordBreak: 'break-word' }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color }}>
          {p.name}: {
            p.dataKey === 'mape_pct' ? `${p.value?.toFixed(1)}%` :
            p.dataKey === 'mae_vnd' ? `${(p.value / 1e9).toFixed(2)}B` :
            p.dataKey === 'r2' ? p.value?.toFixed(3) :
            p.value?.toLocaleString('vi-VN')
          }
        </div>
      ))}
    </div>
  )
}

export default function ModelComparisonChart({ data, height = 300, showAllMetrics = false }) {
  if (!data || data.length === 0) return null

  const chartData = data.map(m => ({
    name: m.model_name
      .replace(/ReliabilityAwareGradientBoosting/g, 'ReliabilityGB')
      .replace(/QualityWeightedRandomForest/g, 'QW-RandomForest')
      .replace(/ConfidenceWeightedXGBoost/g, 'CW-XGBoost')
      .slice(0, 20),
    fullName: m.model_name,
    mape_pct: m.mape_pct,
    r2: m.r2 * 100,
    mae_vnd: m.mae_vnd,
    n_test: m.n_test,
    is_serving: Boolean(m.is_serving),
    is_latest: Boolean(m.is_latest),
    is_best_verified: Boolean(m.is_best_verified),
  }))

  if (showAllMetrics) {
    return (
      <ChartWrapper height={height}>
        <BarChart data={chartData} margin={{ top: 5, right: 10, left: 20, bottom: 25 }} barGap={2}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="name" tick={{ fontSize: 9, fill: 'var(--text-muted)' }} axisLine={{ stroke: '#334155' }} tickLine={false} angle={-20} textAnchor="end" />
          <YAxis yAxisId="left" orientation="left" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} axisLine={{ stroke: '#334155' }} tickLine={false} tickFormatter={v => `${v}%`} />
          <YAxis yAxisId="right" orientation="right" domain={[0, 1]} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} axisLine={{ stroke: '#334155' }} tickLine={false} tickFormatter={v => `${v.toFixed(0)}%`} />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize: '0.7rem' }} formatter={(v) => <span style={{ color: 'var(--text-secondary)' }}>{v}</span>} />
          <ReferenceLine yAxisId="left" y={15} stroke="#f59e0b" strokeDasharray="3 3" label={{ value: 'MAPE<15%', position: 'insideTopRight', fontSize: 9, fill: '#f59e0b' }} />
          <Bar yAxisId="left" dataKey="mape_pct" name="MAPE %" fill="#ef4444" opacity={0.8} radius={[3, 3, 0, 0]} />
          <Bar yAxisId="right" dataKey="r2" name="R2 %" fill="#22c55e" opacity={0.8} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ChartWrapper>
    )
  }

  return (
    <ChartWrapper height={height}>
      <BarChart data={chartData} margin={{ top: 5, right: 10, left: -5, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis dataKey="name" tick={{ fontSize: 9, fill: 'var(--text-muted)' }} axisLine={{ stroke: '#334155' }} tickLine={false} />
        <YAxis tick={{ fontSize: 10, fill: 'var(--text-muted)' }} axisLine={{ stroke: '#334155' }} tickLine={false} tickFormatter={v => `${v}%`} />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine y={15} stroke="#f59e0b" strokeDasharray="3 3" />
        <Bar dataKey="mape_pct" name="MAPE %" radius={[3, 3, 0, 0]}>
          {chartData.map((entry, i) => {
            const fill = entry.is_serving ? '#38bdf8' : entry.mape_pct < 15 ? '#22c55e' : entry.mape_pct < 25 ? '#f59e0b' : '#ef4444'
            return <Cell key={i} fill={fill} opacity={0.85} />
          })}
        </Bar>
      </BarChart>
    </ChartWrapper>
  )
}
