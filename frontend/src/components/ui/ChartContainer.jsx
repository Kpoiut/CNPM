import React, { useEffect, useRef, useState } from 'react'

/**
 * ChartContainer — wraps recharts ResponsiveContainer to eliminate -1/-1 warnings.
 *
 * Uses ResizeObserver to track container dimensions.
 * Renders chart ONLY when both width and height are > 0.
 * Shows a skeleton placeholder while measuring.
 *
 * Usage:
 *   <ChartContainer height={300}>
 *     <ResponsiveContainer>
 *       <BarChart ...>
 *         ...
 *       </BarChart>
 *     </ResponsiveContainer>
 *   </ChartContainer>
 */
export default function ChartContainer({
  children,
  width = '100%',
  height = 300,
  minHeight = 200,
  className = '',
  style = {},
  loading = false,
}) {
  const ref = useRef(null)
  const [dims, setDims] = useState({ w: 0, h: 0 })

  useEffect(() => {
    const el = ref.current
    if (!el) return

    // Initial measurement
    const { width: w, height: h } = el.getBoundingClientRect()
    if (w > 0 && h > 0) setDims({ w, h })

    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width: cw, height: ch } = entry.contentRect
        if (cw > 0 && ch > 0) {
          setDims({ w: cw, h: ch })
        }
      }
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const isReady = dims.w > 0 && dims.h > 0

  return (
    <div
      ref={ref}
      className={className}
      style={{
        width,
        minHeight,
        height: isReady ? dims.h : minHeight,
        position: 'relative',
        ...style,
      }}
    >
      {isReady ? children : (
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: 'var(--text-muted)', fontSize: '0.8rem',
        }}>
          <div style={{ textAlign: 'center' }}>
            <div className="spinner" style={{ width: 24, height: 24, borderWidth: 2, margin: '0 auto 8px' }} />
            {loading ? 'Đang tải...' : 'Đo kích thước...'}
          </div>
        </div>
      )}
    </div>
  )
}
