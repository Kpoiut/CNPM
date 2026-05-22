import * as React from 'react'
import { cn } from '../../lib/utils'

function Progress({ value, max = 100, className, color, size = 'md', ...props }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100))
  const heights = { sm: 'h-1.5', md: 'h-2', lg: 'h-3', xl: 'h-5' }

  return (
    <div
      className={cn(
        'w-full bg-[var(--bg-elevated)] rounded-full overflow-hidden',
        heights[size],
        className
      )}
      {...props}
    >
      <div
        className={cn(
          'h-full rounded-full transition-all duration-700',
          color || 'bg-gradient-to-r from-[#7c3aed] via-[#6366f1] to-[#06b6d4]'
        )}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}

function ProgressBar({
  value,
  max = 100,
  label,
  showValue = false,
  color,
  size = 'md',
  className,
  ...props
}) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100))

  return (
    <div className={cn('space-y-1.5', className)} {...props}>
      {(label || showValue) && (
        <div className="flex justify-between items-center text-xs font-medium">
          {label && (
            <span className="text-[var(--text-muted)]">{label}</span>
          )}
          {showValue && (
            <span className="text-[var(--text-secondary)] font-semibold font-['Space_Grotesk']">
              {pct.toFixed(0)}%
            </span>
          )}
        </div>
      )}
      <Progress value={value} max={max} color={color} size={size} />
    </div>
  )
}

function ScoreRing({ value, max = 1, size = 80, stroke = 6, grade = 'A', className, ...props }) {
  const pct = Math.min(1, Math.max(0, value / max))
  const r = (size - stroke) / 2
  const circ = 2 * Math.PI * r
  const offset = circ * (1 - pct)

  const gradeColors = {
    A: '#06d6a0',
    B: '#0099ff',
    C: '#f59e0b',
    D: '#ef4444',
  }
  const ringColor = gradeColors[grade] || gradeColors.B

  return (
    <div className={cn('relative inline-flex items-center justify-center', className)} style={{ width: size, height: size }} {...props}>
      <svg width={size} height={size} className="transform -rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#1a2438" strokeWidth={stroke} />
        <circle
          cx={size / 2} cy={size / 2} r={r} fill="none"
          stroke={ringColor}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          className="transition-all duration-1000 ease-[cubic-bezier(0.34,1.56,0.64,1)]"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="font-['Space_Grotesk'] font-extrabold text-[1.1rem]" style={{ color: ringColor }}>
          {(pct * 100).toFixed(0)}
        </span>
      </div>
    </div>
  )
}

export { Progress, ProgressBar, ScoreRing }
