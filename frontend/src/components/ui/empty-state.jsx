import * as React from 'react'
import { cn } from '../../lib/utils'
import { icon as uiIcon } from './icons'

function EmptyState({ icon, title, description, action, className, ...props }) {
  return (
    <div
      className={cn(
        `
        flex flex-col items-center justify-center
        py-12 px-6 text-center gap-3
      `,
        className
      )}
      {...props}
    >
      {icon && (
        <div className="w-16 h-16 rounded-full bg-[var(--bg-elevated)] flex items-center justify-center text-3xl opacity-40">
          {icon}
        </div>
      )}
      {title && (
        <h3 className="font-['Space_Grotesk'] font-bold text-[1.1rem] text-[var(--text-secondary)]">
          {title}
        </h3>
      )}
      {description && (
        <p className="text-sm text-[var(--text-muted)] max-w-sm leading-relaxed">
          {description}
        </p>
      )}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}

function AlertBanner({ variant = 'info', title, children, dismissible = false, onDismiss, className, ...props }) {
  const variants = {
    info: {
      bg: 'bg-[var(--info-bg)]',
      border: 'border-[var(--info-border)]',
      text: 'text-[var(--info)]',
      icon: uiIcon('info', 18),
    },
    success: {
      bg: 'bg-[var(--success-bg)]',
      border: 'border-[var(--success-border)]',
      text: 'text-[var(--success)]',
      icon: uiIcon('checkCircle', 18),
    },
    warning: {
      bg: 'bg-[var(--warning-bg)]',
      border: 'border-[var(--warning-border)]',
      text: 'text-[var(--warning)]',
      icon: uiIcon('warning', 18),
    },
    danger: {
      bg: 'bg-[var(--danger-bg)]',
      border: 'border-[var(--danger-border)]',
      text: 'text-[var(--danger)]',
      icon: uiIcon('error', 18),
    },
  }
  const v = variants[variant] || variants.info

  return (
    <div
      className={cn(
        `
        flex items-start gap-3 px-4 py-3 rounded-[12px]
        border backdrop-blur-[8px]
        ${v.bg} ${v.border}
      `,
        className
      )}
      {...props}
    >
      <span className="text-base flex-shrink-0 mt-0.5">{v.icon}</span>
      <div className="flex-1">
        {title && (
          <div className={`font-semibold text-sm mb-0.5 ${v.text}`}>{title}</div>
        )}
        <div className={`text-sm ${v.text} opacity-80`}>{children}</div>
      </div>
      {dismissible && (
        <button
          onClick={onDismiss}
          className="flex-shrink-0 w-6 h-6 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-xs opacity-60 hover:opacity-100 transition-opacity"
        >
          ×
        </button>
      )}
    </div>
  )
}

function StepProgress({ steps, currentStep, className }) {
  return (
    <div className={cn('flex items-center', className)}>
      {steps.map((step, i) => {
        const isDone = i < currentStep
        const isActive = i === currentStep
        const isLast = i === steps.length - 1

        return (
          <React.Fragment key={i}>
            <div className="flex items-center gap-2">
              <div
                className={cn(
                  'w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold transition-all duration-300',
                  isActive
                    ? 'bg-gradient-to-br from-[#7c3aed] via-[#6366f1] to-[#06b6d4] text-white shadow-[0_0_30px_rgba(124,58,237,0.35)] scale-110'
                    : isDone
                    ? 'bg-[var(--success-bg)] border-2 border-[var(--success)] text-[var(--success)]'
                    : 'bg-[var(--bg-surface)] border-2 border-[var(--border)] text-[var(--text-muted)]'
                )}
              >
                {isDone ? '✓' : i + 1}
              </div>
              <div className="text-xs font-medium">
                <div className={cn(
                  !isActive && !isDone && 'text-[var(--text-muted)]',
                  isActive && 'text-[var(--text-primary)] font-semibold',
                  isDone && 'text-[var(--success)]'
                )}>
                  {step}
                </div>
              </div>
            </div>
            {!isLast && (
              <div
                className={cn(
                  'flex-1 h-0.5 mx-3 rounded-full transition-all duration-500',
                  isDone ? 'bg-[var(--success)]' : 'bg-[var(--border)]'
                )}
              />
            )}
          </React.Fragment>
        )
      })}
    </div>
  )
}

export { EmptyState, AlertBanner, StepProgress }
