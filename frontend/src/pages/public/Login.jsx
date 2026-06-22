/**
 * Login / Register page — production access console.
 */

import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../components/auth'
import { icon } from '../../components/ui/icons'

function Login() {
  const { login, register, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [mode, setMode] = useState('login') // 'login' | 'register'
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [email, setEmail] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  // Redirect if already authenticated — useEffect to avoid setState during render
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/', { replace: true })
    }
  }, [isAuthenticated, navigate])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      if (mode === 'login') {
        await login(username, password)
      } else {
        await register(username, password, email)
      }
      navigate('/', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleGoogleLogin = () => {
    setError(null)
    window.location.assign('/api/auth/google/start')
  }

  return (
    <div className="login-page">
      <div className="login-backdrop" />

      <div className="login-experience animate-scaleIn">
        <section className="login-hero-panel" aria-label="Real Estate AVM access summary">
          <div className="login-hero-mark">{icon('house', 42, '', '#f8fafc')}</div>
          <div className="login-hero-eyebrow">Production access</div>
          <h1 className="login-hero-title">Real Estate AVM</h1>
          <p className="login-hero-copy">
            Cổng truy cập cho định giá, lịch sử dự đoán, vận hành dữ liệu và audit model. User và admin dùng chung
            hệ giao diện, nhưng quyền thao tác và mức chi tiết được tách rõ.
          </p>

          <div className="login-hero-grid">
            {[
              ['OAuth 2.0', 'Google callback', 'đăng nhập bên thứ ba qua backend'],
              ['JWT', 'session guard', 'token và phân quyền theo role'],
              ['PostgreSQL', 'production DB', 'lưu dự đoán, model và lineage'],
              ['CI/CD', 'release evidence', 'test, security và Docker smoke'],
            ].map(([value, label, note]) => (
              <div className="login-hero-metric" key={label}>
                <strong>{value}</strong>
                <span>{label}</span>
                <small>{note}</small>
              </div>
            ))}
          </div>

          <div className="login-role-strip">
            <span>{icon('user', 16)} User workspace</span>
            <span>{icon('shieldCheck', 16)} Admin operations</span>
            <span>{icon('fileText', 16)} Reviewer evidence</span>
          </div>
        </section>

        <div className="login-container">
          {/* Logo */}
          <div className="login-logo">
            <div className="login-logo-icon">{icon('house', 32, '', '#f8fafc')}</div>
            <h2 className="login-logo-text">Real Estate AVM</h2>
            <p className="login-logo-sub">Đăng nhập vào workspace định giá</p>
          </div>

          {/* Tab toggle */}
          <div className="login-tabs">
            <button
              className={`login-tab ${mode === 'login' ? 'active' : ''}`}
              onClick={() => { setMode('login'); setError(null) }}
            >
              Đăng nhập
            </button>
            <button
              className={`login-tab ${mode === 'register' ? 'active' : ''}`}
              onClick={() => { setMode('register'); setError(null) }}
            >
              Đăng ký
            </button>
          </div>

          <div className="login-security-badges">
            <span className="badge badge-primary">{icon('shieldCheck', 14)} OAuth 2.0</span>
            <span className="badge badge-info">{icon('lock', 14)} JWT session</span>
            <span className="badge badge-neutral">{icon('database', 14)} PostgreSQL</span>
          </div>

          {/* Error */}
          {error && (
            <div className="login-error animate-slideUp">
              <span>{icon('warning', 16)}</span> {error}
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="login-form">
            <div className="login-field">
              <label className="login-label" htmlFor="login-username">Tên đăng nhập</label>
              <input
                id="login-username"
                className="login-input"
                type="text"
                value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder="admin hoặc tài khoản người dùng"
                required
                autoComplete="username"
                autoFocus
              />
            </div>

            {mode === 'register' && (
              <div className="login-field animate-slideUp">
                <label className="login-label" htmlFor="login-email">Email (tùy chọn)</label>
                <input
                  id="login-email"
                  className="login-input"
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="email@example.com"
                  autoComplete="email"
                />
              </div>
            )}

            <div className="login-field">
              <label className="login-label" htmlFor="login-password">Mật khẩu</label>
              <input
                id="login-password"
                className="login-input"
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Nhập mật khẩu"
                required
                minLength={6}
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              />
            </div>

            <button
              type="submit"
              className="login-submit"
              disabled={loading || !username || !password}
            >
              {loading ? (
                <><span className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }} /> Đang xử lý...</>
              ) : mode === 'login' ? (
                <>Vào workspace {icon('arrowRight', 16)}</>
              ) : (
                <>Tạo tài khoản {icon('plus', 16)}</>
              )}
            </button>
          </form>

          <div className="login-divider">
            <span />
            hoặc đăng nhập bảo mật
            <span />
          </div>

          <button type="button" className="login-google" onClick={handleGoogleLogin}>
            <span className="login-google-mark">G</span>
            <span>Đăng nhập bằng Google OAuth 2.0</span>
            {icon('shieldCheck', 18)}
          </button>

          <div className="login-footer">
            <span className="login-footer-text">Real Estate AVM v2.0</span>
            <span className="login-footer-dot">·</span>
            <span className="login-footer-text">Role-aware UI</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Login
