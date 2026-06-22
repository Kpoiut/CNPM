/**
 * Auth context + provider — JWT authentication state management.
 *
 * Usage:
 *   <AuthProvider>
 *     <App />
 *   </AuthProvider>
 *
 *   const { user, login, logout, isLoading } = useAuth()
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { fetchCurrentAccount } from './authSession.js'

const TOKEN_KEY = 'avm-token'
const USER_KEY = 'avm-user'
const RESEARCH_LAB_TOKEN_KEY = 'research_lab_token'
const RESEARCH_LAB_EXPIRES_KEY = 'research_lab_token_expires_at'

const AuthContext = createContext(null)

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  const clearSession = useCallback(() => {
    setToken(null)
    setUser(null)
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem('avm-refresh')
    localStorage.removeItem(USER_KEY)
    sessionStorage.removeItem(RESEARCH_LAB_TOKEN_KEY)
    sessionStorage.removeItem(RESEARCH_LAB_EXPIRES_KEY)
  }, [])

  const storeCurrentUser = useCallback(account => {
    setUser(account)
    localStorage.setItem(USER_KEY, JSON.stringify(account))
  }, [])

  const revalidateAccount = useCallback(async activeToken => {
    if (!activeToken) return null
    try {
      const account = await fetchCurrentAccount(activeToken)
      storeCurrentUser(account)
      return account
    } catch (error) {
      if (error.status === 401 || error.status === 403) clearSession()
      throw error
    }
  }, [clearSession, storeCurrentUser])

  // Restore the token, then ask PostgreSQL-backed /me for the current role/state.
  useEffect(() => {
    let active = true
    const restore = async () => {
    try {
      const savedToken = localStorage.getItem(TOKEN_KEY)
      const savedUser = localStorage.getItem(USER_KEY)
      if (savedToken && savedUser) {
        setToken(savedToken)
        setUser(JSON.parse(savedUser))
          try {
            const account = await fetchCurrentAccount(savedToken)
            if (active) storeCurrentUser(account)
          } catch (error) {
            if (active && (error.status === 401 || error.status === 403)) clearSession()
          }
      }
    } catch { /* ignore */ }
      if (active) setIsLoading(false)
    }
    restore()
    return () => { active = false }
  }, [clearSession, storeCurrentUser])

  useEffect(() => {
    if (!token) return undefined
    const refresh = () => revalidateAccount(token).catch(() => {})
    const refreshWhenVisible = () => {
      if (document.visibilityState === 'visible') refresh()
    }
    const interval = window.setInterval(refresh, 30_000)
    window.addEventListener('focus', refresh)
    document.addEventListener('visibilitychange', refreshWhenVisible)
    return () => {
      window.clearInterval(interval)
      window.removeEventListener('focus', refresh)
      document.removeEventListener('visibilitychange', refreshWhenVisible)
    }
  }, [revalidateAccount, token])

  const login = useCallback(async (username, password) => {
    sessionStorage.removeItem(RESEARCH_LAB_TOKEN_KEY)
    sessionStorage.removeItem(RESEARCH_LAB_EXPIRES_KEY)
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error(body.detail || `Đăng nhập thất bại (HTTP ${res.status})`)
    }
    const data = await res.json()
    setToken(data.access_token)
    setUser(data.user)
    localStorage.setItem(TOKEN_KEY, data.access_token)
    if (data.refresh_token) localStorage.setItem('avm-refresh', data.refresh_token)
    localStorage.setItem(USER_KEY, JSON.stringify(data.user))
    return data.user
  }, [])

  const register = useCallback(async (username, password, email) => {
    sessionStorage.removeItem(RESEARCH_LAB_TOKEN_KEY)
    sessionStorage.removeItem(RESEARCH_LAB_EXPIRES_KEY)
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, email: email || undefined }),
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error(body.detail || `Đăng ký thất bại (HTTP ${res.status})`)
    }
    const data = await res.json()
    setToken(data.access_token)
    setUser(data.user)
    localStorage.setItem(TOKEN_KEY, data.access_token)
    if (data.refresh_token) localStorage.setItem('avm-refresh', data.refresh_token)
    localStorage.setItem(USER_KEY, JSON.stringify(data.user))
    return data.user
  }, [])

  const logout = clearSession

  const value = {
    user,
    token,
    isLoading,
    isAuthenticated: !!user,
    isAdmin: user?.role === 'admin',
    login,
    register,
    logout,
    refreshAccount: () => revalidateAccount(token),
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export default AuthContext
