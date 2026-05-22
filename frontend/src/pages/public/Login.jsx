/**
 * Login / Register page — Premium glassmorphism design.
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

  return (
    <div className="login-page">
      <div className="login-backdrop" />

      <div className="login-container animate-scaleIn">
        {/* Logo */}
        <div className="login-logo">
          <div className="login-logo-icon">{icon('house', 32)}</div>
          <h1 className="login-logo-text">Real Estate AVM</h1>
          <p className="login-logo-sub">Hệ thống định giá bất động sản thông minh</p>
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
              placeholder="Nhập tên đăng nhập"
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
              'Đăng nhập'
            ) : (
              'Tạo tài khoản'
            )}
          </button>
        </form>

        <div className="login-footer">
          <span className="login-footer-text">Real Estate AVM v2.0</span>
          <span className="login-footer-dot">·</span>
          <span className="login-footer-text">JWT Authentication</span>
        </div>
      </div>
    </div>
  )
}

export default Login
