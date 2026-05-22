/**
 * SkeletonLoader — Production shimmer skeleton components
 * - Consistent animation timing
 * - Multiple preset shapes
 * - Accessible (aria-busy)
 */

import React from 'react'

const SHIMMER = {
  background: 'linear-gradient(90deg, var(--bg-elevated) 25%, rgba(255,255,255,0.06) 50%, var(--bg-elevated) 75%)',
  backgroundSize: '200% 100%',
  animation: 'skeleton-loading 1.4s ease-in-out infinite',
}

export function SkeletonText({ lines = 3, lastWidth = '60%' }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          style={{
            ...SHIMMER,
            height: 12,
            width: i === lines - 1 ? lastWidth : '100%',
            borderRadius: 6,
          }}
        />
      ))}
    </div>
  )
}

export function SkeletonCard({ height = 200, style = {} }) {
  return (
    <div
      aria-busy="true"
      aria-label="Đang tải..."
      style={{
        ...SHIMMER,
        height,
        borderRadius: 'var(--radius-lg)',
        ...style,
      }}
    />
  )
}

export function SkeletonChart({ height = 220 }) {
  return (
    <div
      aria-busy="true"
      aria-label="Đang tải biểu đồ..."
      style={{
        height,
        borderRadius: 'var(--radius)',
        padding: '1rem',
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        background: 'var(--surface)',
        border: '1px solid var(--border)',
      }}
    >
      {/* Bar placeholder */}
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, height: 140 }}>
        {[65, 85, 45, 90, 55, 70, 40].map((h, i) => (
          <div key={i} style={{ ...SHIMMER, flex: 1, height: `${h}%`, borderRadius: '4px 4px 0 0' }} />
        ))}
      </div>
      {/* Label placeholders */}
      <div style={{ display: 'flex', gap: 8 }}>
        {[1, 2, 3, 4].map(i => (
          <div key={i} style={{ ...SHIMMER, flex: 1, height: 8, borderRadius: 4 }} />
        ))}
      </div>
    </div>
  )
}

export function SkeletonTable({ rows = 5, cols = 4 }) {
  return (
    <div aria-busy="true" aria-label="Đang tải bảng...">
      {/* Header */}
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: 8, marginBottom: 8 }}>
        {Array.from({ length: cols }).map((_, i) => (
          <div key={i} style={{ ...SHIMMER, height: 14, borderRadius: 4 }} />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, row) => (
        <div
          key={row}
          style={{ display: 'grid', gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: 8, marginBottom: 8 }}
        >
          {Array.from({ length: cols }).map((_, col) => (
            <div key={col} style={{ ...SHIMMER, height: 36, borderRadius: 4 }} />
          ))}
        </div>
      ))}
    </div>
  )
}

export function SkeletonStatCards({ count = 6 }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12 }}>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          style={{
            padding: '1rem',
            borderRadius: 'var(--radius)',
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
          }}
        >
          <div style={{ ...SHIMMER, width: 32, height: 32, borderRadius: 8 }} />
          <div style={{ ...SHIMMER, height: 24, width: '60%', borderRadius: 4 }} />
          <div style={{ ...SHIMMER, height: 12, width: '80%', borderRadius: 4 }} />
        </div>
      ))}
    </div>
  )
}

export function SkeletonResultCard() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }} aria-busy="true" aria-label="Đang tải kết quả...">
      {/* Hero price */}
      <div style={{ ...SHIMMER, height: 140, borderRadius: 'var(--radius-lg)' }} />
      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
        {[1, 2, 3, 4].map(i => (
          <div key={i} style={{ ...SHIMMER, height: 70, borderRadius: 'var(--radius)' }} />
        ))}
      </div>
      {/* Table */}
      <div style={{ ...SHIMMER, height: 200, borderRadius: 'var(--radius)' }} />
    </div>
  )
}

/**
 * LoadingOverlay — spinner với overlay (dùng cho initial page load)
 */
export function LoadingOverlay({ message = 'Đang tải...' }) {
  return (
    <div
      style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        gap: '1rem', padding: '4rem', minHeight: '40vh',
      }}
    >
      <div className="spinner" style={{ width: 40, height: 40, borderWidth: 3 }} />
      <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>{message}</p>
    </div>
  )
}
