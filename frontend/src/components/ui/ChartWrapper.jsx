import React, { useRef, useState, useCallback } from 'react'
import { ResponsiveContainer } from 'recharts'

/**
 * ChartWrapper — eliminates recharts -1/-1 warnings by gating chart
 * render behind confirmed container dimensions.
 *
 * Uses ResizeObserver to track the parent container's size.
 * Only renders <ResponsiveContainer> when w > 0 && h > 0.
 * Shows a loading skeleton while measuring.
 *
 * Usage:
 *   <ChartWrapper height={220}>
 *     <PieChart>...</PieChart>
 *   </ChartWrapper>
 */
export default function ChartWrapper({ children, height = 220, minHeight, className, style }) {
  const ref = useRef(null)
  const [dims, setDims] = useState({ w: 0, h: 0 })

  const setRef = useCallback((node) => {
    ref.current = node
    if (!node) return
    const { width, height: h } = node.getBoundingClientRect()
    if (width > 0 && h > 0) setDims({ w: width, h })
  }, [])

  React.useEffect(() => {
    const el = ref.current
    if (!el) return
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width: w, height: h } = entry.contentRect
        if (w > 0 && h > 0) setDims({ w, h })
      }
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  constMH = minHeight || height

  if (dims.w <= 0 || dims.h <= 0) {
    return (
      <div
        ref={setRef}
        style={{
          height: minHeight || height,
          minHeight: minHeight || height,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: 'var(--text-muted)', fontSize: '0.8rem',
          background: 'var(--bg-elevated)', borderRadius: 8,
          ...style,
        }}
      >
        Đang đo kích thước...
      </div>
    )
  }

  return (
    <div ref={setRef} style={{ height: dims.h, minHeight: minHeight || 0, ...style }}>
      <ResponsiveContainer width="100%" height="100%">
        {children}
      </ResponsiveContainer>
    </div>
  )
}
