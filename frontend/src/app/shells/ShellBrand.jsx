import React from 'react'
import { Link } from 'react-router-dom'

export function ShellBrand({ homePath = '/', compact = false, subtitle = 'Định giá minh bạch' }) {
  return (
    <Link className={`shell-brand ${compact ? 'shell-brand--compact' : ''}`} to={homePath}>
      <svg className="shell-brand__mark" viewBox="0 0 36 36" aria-hidden="true">
        <path d="M5.5 17.2 18 6.8l12.5 10.4" fill="none" stroke="currentColor" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M9.2 16.5h17.6v12.7a2 2 0 0 1-2 2H11.2a2 2 0 0 1-2-2V16.5Z" fill="none" stroke="currentColor" strokeWidth="2" />
        <path d="M15.2 31.2v-8.6h5.6v8.6" fill="none" stroke="currentColor" strokeWidth="2" />
      </svg>
      <span className="shell-brand__copy">
        <strong>Real Estate AVM</strong>
        {!compact && <small>{subtitle}</small>}
      </span>
      <span className="shell-brand__locale">VN</span>
    </Link>
  )
}

export default ShellBrand
