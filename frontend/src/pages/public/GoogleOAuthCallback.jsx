import React, { useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'

function GoogleOAuthCallback() {
  const query = useMemo(() => window.location.search || '', [])
  const params = useMemo(() => new URLSearchParams(query), [query])
  const error = params.get('error')
  const hasCode = Boolean(params.get('code'))
  const hasState = Boolean(params.get('state'))

  useEffect(() => {
    if (!error && hasCode && hasState) {
      window.location.replace(`/api/auth/google/callback${query}`)
    }
  }, [error, hasCode, hasState, query])

  const message = error
    ? `Google từ chối đăng nhập: ${error}`
    : hasCode && hasState
      ? 'Đang xác thực Google OAuth 2.0...'
      : 'Thiếu mã xác thực Google. Vui lòng bắt đầu lại từ trang đăng nhập.'

  return (
    <main className="login-page">
      <section className="login-card login-card-single" aria-live="polite">
        <div className="login-brand">
          <span className="login-logo">AVM</span>
          <div>
            <h1>Đăng nhập Google</h1>
            <p>{message}</p>
          </div>
        </div>
        {(error || !hasCode || !hasState) && (
          <Link className="btn btn-primary" to="/login">Quay lại đăng nhập</Link>
        )}
      </section>
    </main>
  )
}

export default GoogleOAuthCallback
