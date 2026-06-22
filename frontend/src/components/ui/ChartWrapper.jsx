import React, { useRef, useState, useCallback } from 'react'

/**
 * ChartWrapper — eliminates recharts -1/-1 warnings by gating chart
 * render behind confirmed container dimensions.
 *
 * Uses ResizeObserver to track the parent container's size.
 * Renders charts only when w > 0 && h > 0, then injects numeric width/height.
 * This avoids Recharts' own parent measurement path, which can briefly report
 * -1/-1 in Vite/HMR and audit browsers.
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
  const frameHeight = minHeight || height

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

  if (dims.w <= 0 || dims.h <= 0) {
    return (
      <div
        ref={setRef}
        style={{
          width: '100%',
          height: frameHeight,
          minHeight: frameHeight,
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
    <div ref={setRef} style={{ width: '100%', minWidth: 0, height: dims.h, minHeight: frameHeight, ...style }}>
      {React.isValidElement(children)
        ? React.cloneElement(children, {
            width: Math.max(1, Math.floor(dims.w)),
            height: Math.max(1, Math.floor(dims.h)),
          })
        : children}
    </div>
  )
}
