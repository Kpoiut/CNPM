import * as React from 'react'
import { cn } from '../../lib/utils'
import { Badge } from './badge'

/**
 * Render an icon which may be:
 * - A pre-rendered React element (<Icon />)
 * - A Lucide component class (Icon = Database, passed as icon prop)
 * - A function that returns a component class (icon("database") => Database)
 */
function renderIcon(iconProp, defaultSize = 20) {
  if (!iconProp) return null
  if (/* pre-rendered element */ iconProp && typeof iconProp === 'object' && iconProp.type) return iconProp
  if (/* Lucide component class */ typeof iconProp === 'function') {
    return React.createElement(iconProp, { size: defaultSize })
  }
  return null
}

/**
 * Enhanced StatCard with Lucide icons and trend indicators.
 * Integrates seamlessly with the existing design system CSS variables.
 */
function StatCard({ icon, label, value, sub, delta, color = 'primary', className, ...props }) {
  const colorMap = {
    primary: {
      bg: 'bg-[var(--primary-50)]',
      text: 'text-[var(--primary)]',
      ring: 'ring-[var(--primary-200)]',
    },
    success: {
      bg: 'bg-[var(--success-bg)]',
      text: 'text-[var(--success)]',
      ring: 'ring-[var(--success-border)]',
    },
    warning: {
      bg: 'bg-[var(--warning-bg)]',
      text: 'text-[var(--warning)]',
      ring: 'ring-[var(--warning-border)]',
    },
    danger: {
      bg: 'bg-[var(--danger-bg)]',
      text: 'text-[var(--danger)]',
      ring: 'ring-[var(--danger-border)]',
    },
    info: {
      bg: 'bg-[var(--info-bg)]',
      text: 'text-[var(--info)]',
      ring: 'ring-[var(--info-border)]',
    },
  }
  const c = colorMap[color] || colorMap.primary

  return (
    <div
      className={cn(
        `
        bg-[var(--bg-card)] backdrop-blur-[12px]
        border border-[var(--border)]
        rounded-[16px] p-5 flex gap-4
        items-start relative overflow-hidden
        transition-all duration-300 ease-[cubic-bezier(0.4,0,0.2,1)]
        hover:border-[var(--border-glow)]
        hover:shadow-[0_20px_50px_rgba(0,0,0,0.6),0_0_0_1px_rgba(124,58,237,0.2)]
        hover:-translate-y-1
      `,
        className
      )}
      {...props}
    >
      {/* Top accent line */}
      <div
        className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-[#7c3aed] via-[#6366f1] to-[#06b6d4] opacity-0 transition-opacity duration-300 hover:opacity-100"
      />

      {/* Icon */}
      {icon && (
        <div
          className={cn(
            `w-12 h-12 rounded-[12px] flex items-center justify-center text-xl
            flex-shrink-0 ring-1 ${c.bg} ${c.text} ${c.ring}`
          )}
        >
          {renderIcon(icon)}
        </div>
      )}

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="text-[1.8rem] leading-none font-extrabold font-['Space_Grotesk'] tracking-tight text-[var(--text-primary)] mb-1">
          {value}
        </div>
        <div className="text-[0.78rem] font-medium text-[var(--text-muted)] mb-2">
          {label}
        </div>

        {/* Sub + Delta row */}
        <div className="flex items-center gap-2 flex-wrap">
          {sub && (
            <span className="text-[0.72rem] text-[var(--text-muted)]">
              {sub}
            </span>
          )}
          {delta && (
            <Badge
              variant={delta === 'up' ? 'success' : delta === 'down' ? 'danger' : 'default'}
              size="sm"
            >
              {delta === 'up' ? '↑' : delta === 'down' ? '↓' : '→'}
              {sub}
            </Badge>
          )}
        </div>
      </div>
    </div>
  )
}

/**
 * Mini stat for inline display in tables/lists
 */
function MiniStat({ label, value, icon, trend, className, ...props }) {
  return (
    <div className={cn('flex items-center gap-2', className)} {...props}>
      {icon && <span className="text-sm">{renderIcon(icon, 14)}</span>}
      <div>
        <div className="text-[0.72rem] text-[var(--text-muted)]">{label}</div>
        <div className="text-sm font-semibold font-['Space_Grotesk'] text-[var(--text-primary)]">
          {value}
        </div>
      </div>
    </div>
  )
}

export { StatCard, MiniStat }
