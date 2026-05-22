import * as React from 'react'
import { cva } from 'class-variance-authority'
import { cn } from '../../lib/utils'

const badgeVariants = cva(
  `
    inline-flex items-center gap-1.5 px-3 py-1 rounded-full
    text-[0.7rem] font-bold tracking-wide
    border whitespace-nowrap
  `,
  {
    variants: {
      variant: {
        default: `
          bg-[var(--bg-elevated)] text-[var(--text-secondary)]
          border-[var(--border)]
        `,
        success: `
          bg-[var(--success-bg)] text-[var(--success)]
          border-[var(--success-border)]
        `,
        warning: `
          bg-[var(--warning-bg)] text-[var(--warning)]
          border-[var(--warning-border)]
        `,
        danger: `
          bg-[var(--danger-bg)] text-[var(--danger)]
          border-[var(--danger-border)]
        `,
        info: `
          bg-[var(--info-bg)] text-[var(--info)]
          border-[var(--info-border)]
        `,
        primary: `
          bg-[var(--primary-50)] text-[var(--primary)]
          border-[var(--primary-200)]
        `,
        outline: `
          bg-transparent text-[var(--text-secondary)]
          border-[var(--border)]
        `,
        // Evidence tier colors
        e1: `
          bg-[rgba(6,214,160,0.12)] text-[#06d6a0]
          border-[rgba(6,214,160,0.3)]
        `,
        e2: `
          bg-[rgba(0,153,255,0.12)] text-[#0099ff]
          border-[rgba(0,153,255,0.3)]
        `,
        e3: `
          bg-[rgba(0,153,204,0.12)] text-[#0099cc]
          border-[rgba(0,153,204,0.3)]
        `,
        e4: `
          bg-[rgba(245,158,11,0.12)] text-[#f59e0b]
          border-[rgba(245,158,11,0.3)]
        `,
        e5: `
          bg-[rgba(239,68,68,0.12)] text-[#ef4444]
          border-[rgba(239,68,68,0.3)]
        `,
      },
      size: {
        sm: 'text-[0.65rem] px-2 py-0.5',
        md: 'text-[0.7rem] px-3 py-1',
        lg: 'text-[0.8rem] px-4 py-1.5',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'md',
    },
  }
)

/**
 * Process children — if any is a Lucide component class (function),
 * render it as a React element.
 */
function processChildren(children) {
  if (!children) return children
  if (typeof children === 'function') {
    return React.createElement(children, { size: 12 })
  }
  if (Array.isArray(children)) {
    return children.map((child, i) =>
      typeof child === 'function'
        ? React.createElement(child, { size: 12, key: i })
        : child
    )
  }
  if (typeof children === 'function') {
    return React.createElement(children, { size: 12 })
  }
  return children
}

function Badge({ className, variant, size, children, ...props }) {
  return (
    <span
      className={cn(badgeVariants({ variant, size }), className)}
      {...props}
    >
      {processChildren(children)}
    </span>
  )
}

export { Badge, badgeVariants }
