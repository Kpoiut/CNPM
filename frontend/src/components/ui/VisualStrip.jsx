import * as React from 'react'
import { cn } from '../../lib/utils'

function VisualStrip({ className, label, title, description, items = [] }) {
  if (!items.length) return null

  return (
    <section className={cn('visual-strip', className)}>
      {(label || title || description) && (
        <div className="visual-strip-header">
          {label && <span className="visual-strip-kicker">{label}</span>}
          {title && <strong className="visual-strip-heading">{title}</strong>}
          {description && <p className="visual-strip-description">{description}</p>}
        </div>
      )}

      <div className="visual-strip-grid">
        {items.map((item, index) => (
          <article key={`${item.title || item.alt || index}`} className="visual-strip-tile">
            <img
              src={item.src}
              alt={item.alt || item.title || ''}
              loading="lazy"
            />
            <div className="visual-strip-overlay">
              {item.kicker && <span className="visual-strip-tile-kicker">{item.kicker}</span>}
              {item.title && <strong className="visual-strip-tile-title">{item.title}</strong>}
              {item.caption && <small className="visual-strip-tile-caption">{item.caption}</small>}
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}

export { VisualStrip }
