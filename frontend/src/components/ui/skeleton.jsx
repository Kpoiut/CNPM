import * as React from 'react'
import { cn } from '../../lib/utils'

function Skeleton({ className, ...props }) {
  return (
    <div
      className={cn(
        `
        rounded-[8px] bg-[var(--bg-elevated)]
        animate-pulse
      `,
        className
      )}
      {...props}
    />
  )
}

function SkeletonText({ className, lines = 3, ...props }) {
  return (
    <div className={cn('space-y-2', className)} {...props}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={`h-4 ${i === lines - 1 ? 'w-3/4' : 'w-full'}`}
        />
      ))}
    </div>
  )
}

function SkeletonCard({ className, ...props }) {
  return (
    <div
      className={cn(
        `
        bg-[var(--bg-card)] border border-[var(--border)]
        rounded-[16px] p-6 space-y-4
      `,
        className
      )}
      {...props}
    >
      <Skeleton className="h-4 w-1/3" />
      <Skeleton className="h-8 w-1/2" />
      <Skeleton className="h-3 w-full" />
      <Skeleton className="h-3 w-5/6" />
    </div>
  )
}

function SkeletonStatCard({ className, ...props }) {
  return (
    <div
      className={cn(
        `
        bg-[var(--bg-card)] border border-[var(--border)]
        rounded-[16px] p-5 flex gap-4 items-start
      `,
        className
      )}
      {...props}
    >
      <Skeleton className="w-12 h-12 rounded-[12px] flex-shrink-0" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-9 w-24" />
        <Skeleton className="h-3 w-16" />
      </div>
    </div>
  )
}

function SkeletonTable({ className, rows = 5, cols = 4, ...props }) {
  return (
    <div
      className={cn(
        `
        rounded-[12px] border border-[var(--border)]
        bg-[var(--bg-surface)] overflow-hidden
      `,
        className
      )}
      {...props}
    >
      {/* Header */}
      <div
        className="grid gap-4 px-4 py-3 border-b border-[var(--border)]"
        style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}
      >
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-3" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, r) => (
        <div
          key={r}
          className="grid gap-4 px-4 py-3.5 border-b border-[var(--border-light)] last:border-0"
          style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}
        >
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} className="h-3" />
          ))}
        </div>
      ))}
    </div>
  )
}

function SkeletonChart({ className, ...props }) {
  return (
    <div
      className={cn(
        `
        bg-[var(--bg-card)] border border-[var(--border)]
        rounded-[16px] p-6 space-y-4
      `,
        className
      )}
      {...props}
    >
      <div className="flex justify-between items-center">
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-4 w-20" />
      </div>
      <Skeleton className="h-60 w-full rounded-[8px]" />
    </div>
  )
}

function LoadingSpinner({ className, size = 'md', ...props }) {
  const sizes = {
    sm: 'w-4 h-4 border-[1.5px]',
    md: 'w-6 h-6 border-2',
    lg: 'w-10 h-10 border-[3px]',
  }
  return (
    <div
      className={cn(
        `
        ${sizes[size]} border-[var(--border)]
        border-t-[var(--primary)] rounded-full
        animate-spin
      `,
        className
      )}
      {...props}
    />
  )
}

function LoadingOverlay({ message = 'Đang tải...', className, ...props }) {
  return (
    <div
      className={cn(
        `
        flex flex-col items-center justify-center gap-4
        py-12 text-center
      `,
        className
      )}
      {...props}
    >
      <LoadingSpinner size="lg" />
      {message && (
        <p className="text-[var(--text-muted)] text-sm font-medium">
          {message}
        </p>
      )}
    </div>
  )
}

export {
  Skeleton,
  SkeletonText,
  SkeletonCard,
  SkeletonStatCard,
  SkeletonTable,
  SkeletonChart,
  LoadingSpinner,
  LoadingOverlay,
}
