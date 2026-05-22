import React from 'react'
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ZAxis } from 'recharts'
import ChartWrapper from '../ui/ChartWrapper'

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
      <div style={{ fontWeight: 600, marginBottom: 4, maxWidth: 200, wordBreak: 'break-word' }}>{d.feature}</div>
      <div>SHAP: {d.shap?.toFixed(4)}</div>
      <div>Feature value: {typeof d.value === 'number' ? d.value.toFixed(4) : d.value}</div>
    </div>
  )
}

export default function SHAPBeeswarmChart({ data, height = 200 }) {
  if (!data || data.length === 0) {
    return (
      <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
        SHAP beeswarm data not available. Run compute_shap_explanations.py first.
      </div>
    )
  }

  // Build flat scatter data: each point = (feature_index, shap_value, color by feature_value)
  const allPoints = []
  const featureNames = data.map(d => d.feature.replace(/_norm|_feature|_score/g, '').replace(/_/g, ' '))

  data.forEach((featData, featIdx) => {
    const values = featData.values || []
    const shapVals = featData.shap_values || []
    const n = Math.min(values.length, shapVals.length)

    for (let i = 0; i < n; i++) {
      const normVal = (values[i] - Math.min(...values)) / (Math.max(...values) - Math.min(...values) + 1e-9)
      allPoints.push({
        feature: featureNames[featIdx],
        featureIdx: featIdx,
        shap: shapVals[i],
        value: values[i],
        normValue: normVal,
      })
    }
  })

  if (allPoints.length === 0) {
    return (
      <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
        No SHAP beeswarm points available
      </div>
    )
  }

  return (
    <div>
      <ChartWrapper height={height}>
        <ScatterChart margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            type="number"
            tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
            axisLine={{ stroke: '#334155' }}
            tickLine={false}
            tickFormatter={v => {
              const name = featureNames[Math.round(v)]
              return name ? name.slice(0, 8) : ''
            }}
            domain={[0, featureNames.length - 1]}
            dataKey="featureIdx"
            name="Feature"
          />
          <YAxis
            type="number"
            dataKey="shap"
            tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
            axisLine={{ stroke: '#334155' }}
            tickLine={false}
            name="SHAP Value"
            width={60}
          />
          <ZAxis range={[15, 40]} />
          <Tooltip content={<CustomTooltip />} />
          <Scatter data={allPoints}>
            {allPoints.map((p, i) => (
              <Cell
                key={i}
                fill={
                  p.normValue > 0.7 ? '#ef4444' :
                  p.normValue > 0.4 ? '#f59e0b' :
                  p.normValue < 0.3 ? '#3b82f6' :
                  '#60a5fa'
                }
                opacity={0.5}
              />
            ))}
          </Scatter>
        </ScatterChart>
      </ChartWrapper>
      <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', display: 'flex', gap: '0.75rem', marginTop: '0.25rem' }}>
        <span style={{ color: '#3b82f6' }}>●</span> Low feature value
        <span style={{ color: '#60a5fa' }}>●</span> Mid
        <span style={{ color: '#f59e0b' }}>●</span> High
        <span style={{ color: '#ef4444' }}>●</span> Very high
        <span style={{ marginLeft: 'auto' }}>X = SHAP contribution to prediction</span>
      </div>
    </div>
  )
}
