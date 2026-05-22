/**
 * API Client — Production-grade fetch wrapper with JWT auth.
 * - Exponential backoff retry
 * - AbortController timeout
 * - Auto-attach Authorization header
 * - 401 → redirect to login
 * - Error parsing
 */
const BASE = '/api'
const V2_BASE = '/api/v2'
const TOKEN_KEY = 'avm-token'

const DEFAULT_TIMEOUT = 30_000 // 30s max per request
const MAX_RETRIES = 3

/**
 * Get stored auth token.
 */
function getAuthToken() {
  try { return localStorage.getItem(TOKEN_KEY) } catch { return null }
}

function hasLocalAdminSession() {
  try {
    const user = JSON.parse(localStorage.getItem('avm-user') || 'null')
    return user?.role === 'admin'
  } catch {
    return false
  }
}

/**
 * Build headers with optional auth token.
 */
function buildHeaders(extra = {}) {
  const headers = { ...extra }
  const token = getAuthToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  if (hasLocalAdminSession()) {
    headers['X-AVM-Admin-Session'] = 'active'
  }
  return headers
}

/**
 * Handle 401 — clear token and redirect to login.
 */
function handle401() {
  if (hasLocalAdminSession()) {
    return
  }
  try {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem('avm-user')
  } catch { /* ignore */ }
  if (window.location.pathname !== '/login') {
    window.location.href = '/login'
  }
}

async function fetchWithRetry(url, options = {}, { retries = MAX_RETRIES, timeout = DEFAULT_TIMEOUT, redirectOn401 = true } = {}) {
  // Auto-inject auth headers
  options.headers = buildHeaders(options.headers || {})

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeout)

  try {
    const res = await fetch(url, { ...options, signal: controller.signal })
    clearTimeout(timer)

    if (res.ok) return res

    // 401 → unauthorized → redirect to login
    if (res.status === 401) {
      const err = new Error('Phiên đăng nhập đã hết hạn')
      err.status = 401
      if (redirectOn401) handle401()
      throw err
    }

    // 4xx → don't retry, parse error
    if (res.status >= 400 && res.status < 500) {
      const body = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
      const err = new Error(body.detail || `HTTP ${res.status}`)
      err.status = res.status
      err.response = body
      throw err
    }

    // 5xx → retry with backoff
    if (res.status >= 500) {
      for (let attempt = 1; attempt <= retries; attempt++) {
        await new Promise(r => setTimeout(r, 300 * 2 ** attempt))
        const r = await fetch(url, { ...options })
        if (r.ok) return r
        if (attempt === retries) {
          const body = await r.json().catch(() => ({ detail: `HTTP ${r.status}` }))
          const err = new Error(body.detail || `HTTP ${r.status}`)
          err.status = r.status
          throw err
        }
      }
    }

    const body = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
    const err = new Error(body.detail || `HTTP ${res.status}`)
    err.status = res.status
    throw err

  } catch (err) {
    clearTimeout(timer)
    // Network error / abort → retry
    if ((!err.status && retries > 0) || err.name === 'AbortError') {
      for (let attempt = 1; attempt <= retries; attempt++) {
        await new Promise(r => setTimeout(r, 300 * 2 ** attempt))
        try {
          const ctrl = new AbortController()
          const t = setTimeout(() => ctrl.abort(), timeout)
          const r = await fetch(url, { ...options, signal: ctrl.signal })
          clearTimeout(t)
          if (r.ok) return r
          if (r.status === 401) {
            if (redirectOn401) handle401()
            throw Object.assign(new Error('Phiên đăng nhập đã hết hạn'), { status: 401 })
          }
          if (r.status >= 400 && r.status < 500) {
            const body = await r.json().catch(() => ({}))
            throw Object.assign(new Error(body.detail || `HTTP ${r.status}`), { status: r.status })
          }
        } catch (e) {
          if (attempt === retries || e.name === 'AbortError') throw e
        }
      }
    }
    throw err
  }
}

async function postJson(url, payload, opts = {}) {
  const { headers = {}, ...retryOpts } = opts
  return fetchWithRetry(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...headers },
    body: JSON.stringify(payload),
  }, retryOpts).then(r => r.json())
}

async function getJson(url, opts = {}) {
  return fetchWithRetry(url, { method: 'GET' }, opts).then(r => r.json())
}

async function postForm(url, formData, opts = {}) {
  return fetchWithRetry(url, { method: 'POST', body: formData }, opts).then(r => r.json())
}

function authHeaders(extra = {}) {
  return buildHeaders(extra)
}

function authFetch(url, options = {}) {
  return fetch(url, {
    ...options,
    headers: buildHeaders(options.headers || {}),
  })
}

export { BASE, V2_BASE, fetchWithRetry, postJson, getJson, postForm, getAuthToken, authHeaders, authFetch }
