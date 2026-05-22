/**
 * StatCard — shared stat display component
 * Replaces 3 different implementations across Dashboard, CollectionDashboard, SelfCollected
 */
import React from 'react'

/**
 * @param {object} props
 * @param {string} props.icon — emoji
 * @param {string|number} props.value — big number
 * @param {string} props.label — description
 * @param {string} [props.sub] — secondary line
 * @param {'up'|'down'|'neutral'} [props.delta] — trend indicator
 * @param {string} [props.color] — primary|success|warning|info|danger
 * @param {string} [props.unit] — e.g. "%", "B", "M"
 */
export default function StatCard({ icon, value, label, sub, delta, color = 'primary', unit }) {
  const colorMap = {
    primary: { bg: 'var(--primary-50)', text: 'var(--primary)' },
    success: { bg: 'var(--success-bg)', text: 'var(--success)' },
    warning: { bg: 'var(--warning-bg)', text: 'var(--warning)' },
    info:    { bg: 'var(--info-bg)',    text: 'var(--info)' },
    danger:  { bg: 'var(--danger-bg)',  text: 'var(--danger)' },
  }
  const c = colorMap[color] || colorMap.primary

  const deltaIcon = delta === 'up' ? '↑' : delta === 'down' ? '↓' : null
  const deltaColor = delta === 'up' ? 'var(--success)' : delta === 'down' ? 'var(--danger)' : 'var(--text-muted)'

  return (
    <div
      className="stat-card animate-slideUp"
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        padding: '1rem',
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
      }}
    >
      <div style={{
        width: 32, height: 32, borderRadius: 8,
        background: c.bg, display: 'flex',
        alignItems: 'center', justifyContent: 'center',
        fontSize: '1.1rem',
      }}>
        {icon}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
        <span style={{
          fontFamily: 'var(--font-display)',
          fontSize: '1.5rem', fontWeight: 800,
          color: c.text, lineHeight: 1,
        }}>
          {value}
        </span>
        {unit && (
          <span style={{ fontSize: '0.9rem', fontWeight: 600, color: c.text, opacity: 0.7 }}>
            {unit}
          </span>
        )}
      </div>
      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 500 }}>
        {label}
      </div>
      {sub && (
        deltaIcon ? (
          <span style={{ fontSize: '0.68rem', color: deltaColor, fontWeight: 600 }}>
            {deltaIcon} {sub}
          </span>
        ) : (
          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>{sub}</div>
        )
      )}
    </div>
  )
}
