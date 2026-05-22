import React, { Suspense, useState, useEffect, useRef } from 'react'
import { BrowserRouter, Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  LogOut, User, ChevronDown, MoreHorizontal,
  LayoutDashboard, Home, BarChart3, Map, Globe, Radio,
  CheckCircle, Database, Shield, FlaskConical, Settings, Building2, Table2,
} from 'lucide-react'
import { icon } from './components/ui/icons'
import { NAV_ITEMS, NAV_ITEMS_SECONDARY, UI_LABELS } from './constants/vnStrings'
import { filterNavItems } from './constants/permissions'
import { AuthProvider, useAuth, ProtectedRoute } from './components/auth'
import {
  clearNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  notificationEvents,
  readNotifications,
} from './lib/notifications'
import NovaAssistant from './components/nova'

import {
  Prediction, BuyerSurvey, Dashboard, DataExplorer, MapExplorer, DataQuality,
  RecordExplorer, Community, About, Login,
  DataCollector, CollectionDashboard, ProvenanceTracker,
  ResearchLab, SelfCollected, DataSources, CommunityAdmin, UserManagement,
} from './pages'
import ExplainabilityDashboard from './pages/ExplainabilityDashboard'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 2, staleTime: 5 * 60 * 1000 },
    mutations: { retry: 1 },
  },
})

const THEME_KEY = 'avm-theme'

function useTheme() {
  const [theme, setTheme] = useState(() => {
    try { return localStorage.getItem(THEME_KEY) || 'dark' } catch { return 'dark' }
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    try { localStorage.setItem(THEME_KEY, theme) } catch {}
  }, [theme])

  const toggle = () => setTheme(t => t === 'dark' ? 'light' : 'dark')
  return { theme, toggle }
}

function NavLink({ to, children, abbr, iconKey }) {
  const location = useLocation()
  const isActive = location.pathname === to
  return (
    <Link to={to} className={`nav-link ${isActive ? 'active' : ''}`}>
      {iconKey && <span className="nav-icon">{icon(iconKey, 16)}</span>}
      <span className="nav-label">{children}</span>
      <span className="nav-abbr">{abbr}</span>
    </Link>
  )
}

function MoreMenu({ items }) {
  const [open, setOpen] = useState(false)
  const [menuStyle, setMenuStyle] = useState({})
  const ref = useRef(null)
  const buttonRef = useRef(null)

  const placeMenu = () => {
    const rect = buttonRef.current?.getBoundingClientRect()
    if (!rect) return
    const width = 280
    setMenuStyle({
      top: Math.min(window.innerHeight - 12, rect.bottom + 8),
      left: Math.max(12, Math.min(rect.right - width, window.innerWidth - width - 12)),
      width,
    })
  }

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  useEffect(() => {
    if (!open) return undefined
    placeMenu()
    window.addEventListener('resize', placeMenu)
    window.addEventListener('scroll', placeMenu, true)
    return () => {
      window.removeEventListener('resize', placeMenu)
      window.removeEventListener('scroll', placeMenu, true)
    }
  }, [open])

  if (!items || items.length === 0) return null

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        ref={buttonRef}
        className="nav-link"
        onClick={() => {
          placeMenu()
          setOpen(o => !o)
        }}
        style={{
          background: 'none', border: 'none', cursor: 'pointer',
          color: open ? 'var(--primary)' : 'var(--text-secondary)',
          fontSize: 'inherit', fontFamily: 'inherit', display: 'flex',
          alignItems: 'center', gap: '0.25rem',
        }}
      >
        <span className="nav-icon">{icon('list', 16)}</span>
        <span className="nav-label">Thêm</span>
        <span className="nav-abbr">{icon('chevronDown', 12)}</span>
      </button>
      {open && (
        <div style={{
          position: 'fixed',
          top: menuStyle.top ?? 58,
          left: menuStyle.left ?? 12,
          zIndex: 5000,
          background: 'var(--nav-dropdown-bg)',
          border: '1px solid rgba(148, 163, 184, 0.22)',
          borderRadius: '12px',
          padding: '8px',
          width: menuStyle.width ?? 280,
          maxHeight: '70vh',
          overflowY: 'auto',
          boxShadow: '0 22px 60px rgba(0,0,0,0.75), 0 0 0 1px rgba(255,255,255,0.06)',
          marginTop: 4,
        }}>
          {items.map(item => (
            <Link
              key={item.to}
              to={item.to}
              onClick={() => setOpen(false)}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '8px 12px', borderRadius: '10px',
                textDecoration: 'none', color: 'var(--text-primary)',
                fontSize: '0.82rem', transition: 'all 150ms',
              }}
              onMouseEnter={e => { e.currentTarget.style.background = 'var(--bg-elevated)'; e.currentTarget.style.color = 'var(--text-primary)' }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-primary)' }}
            >
              <span>{icon(item.iconKey, 16)}</span>
              <span>{item.label}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

function UserMenu() {
  const { user, isAuthenticated, isAdmin, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  if (!isAuthenticated) {
    return (
      <Link to="/login" className="btn btn-ghost" style={{ fontSize: '0.82rem', gap: 4 }}>
        Đăng nhập
      </Link>
    )
  }

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        className="user-avatar-btn"
        onClick={() => setOpen(o => !o)}
        title={`${user.username} (${user.role})`}
      >
        <span className="user-avatar-name">{user.username}</span>
        {isAdmin && <span className="user-badge-admin">Admin</span>}
      </button>
      {open && (
        <div className="user-dropdown animate-slideUp">
          <div className="user-dropdown-header">
            <span className="user-dropdown-name">{user.username}</span>
            <span className="user-dropdown-role">{isAdmin ? 'Quản trị viên' : 'Người dùng'}</span>
          </div>
          <div className="user-dropdown-divider" />
          <button
            className="user-dropdown-item"
            onClick={() => { setOpen(false); logout(); navigate('/login') }}
          >
            Đăng xuất
          </button>
        </div>
      )}
    </div>
  )
}

function NotificationBell() {
  const { user, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState([])
  const ref = useRef(null)

  const refresh = () => setItems(readNotifications(user))

  useEffect(() => {
    if (!isAuthenticated) {
      setItems([])
      return undefined
    }
    refresh()
    const onUpdate = () => refresh()
    const onOpen = () => { refresh(); setOpen(true) }
    const onStorage = (event) => {
      if (event.key?.startsWith('avm-notifications:')) refresh()
    }
    window.addEventListener(notificationEvents.updated, onUpdate)
    window.addEventListener(notificationEvents.open, onOpen)
    window.addEventListener('storage', onStorage)
    return () => {
      window.removeEventListener(notificationEvents.updated, onUpdate)
      window.removeEventListener(notificationEvents.open, onOpen)
      window.removeEventListener('storage', onStorage)
    }
  }, [isAuthenticated, user?.username])

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  if (!isAuthenticated) return null

  const unread = items.filter(item => !item.read).length
  const copyCode = async (code) => {
    if (!code) return
    try { await navigator.clipboard.writeText(code) } catch {}
  }
  const goTo = (item) => {
    markNotificationRead(user, item.id)
    refresh()
    if (item.actionTo) {
      setOpen(false)
      navigate(item.actionTo)
    }
  }

  return (
    <div className="notification-center" ref={ref}>
      <button
        className={`notification-bell ${open ? 'active' : ''}`}
        type="button"
        onClick={() => setOpen(prev => !prev)}
        aria-label="Thông báo"
        title="Thông báo"
      >
        {icon('bell', 18)}
        {unread > 0 && <span className="notification-count">{unread > 9 ? '9+' : unread}</span>}
      </button>
      {open && (
        <div className="notification-panel animate-slideUp">
          <div className="notification-panel-header">
            <div>
              <strong>Thông báo</strong>
              <span>{items.length ? `${items.length} tin nhắn đã lưu` : 'Chưa có tin nhắn'}</span>
            </div>
            <button type="button" onClick={() => { markAllNotificationsRead(user); refresh() }}>
              Đánh dấu đã đọc
            </button>
          </div>
          <div className="notification-list">
            {items.length === 0 ? (
              <div className="notification-empty">Các tin nhắn hệ thống, mã truy cập và cảnh báo sẽ được lưu ở đây.</div>
            ) : items.map(item => (
              <div key={item.id} className={`notification-item ${item.read ? '' : 'unread'}`}>
                <button type="button" className="notification-item-main" onClick={() => goTo(item)}>
                  <span className={`notification-dot ${item.type}`} />
                  <span>
                    <strong>{item.title}</strong>
                    <em>{item.body}</em>
                    {item.expiresAt && (
                      <small>Hết hạn: {new Date(item.expiresAt).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}</small>
                    )}
                  </span>
                </button>
                {item.code && (
                  <div className="notification-code-row">
                    <code>{item.code}</code>
                    <button type="button" onClick={() => copyCode(item.code)}>Chép</button>
                  </div>
                )}
              </div>
            ))}
          </div>
          {items.length > 0 && (
            <button className="notification-clear" type="button" onClick={() => { clearNotifications(user); refresh() }}>
              Xóa toàn bộ tin nhắn
            </button>
          )}
        </div>
      )}
    </div>
  )
}

function BrandLogoIcon() {
  return (
    <svg className="logo-mark" viewBox="0 0 36 36" aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id="brand-logo-roof" x1="4" y1="6" x2="32" y2="30" gradientUnits="userSpaceOnUse">
          <stop stopColor="#38bdf8" />
          <stop offset="0.5" stopColor="#14b8a6" />
          <stop offset="1" stopColor="#10b981" />
        </linearGradient>
        <linearGradient id="brand-logo-body" x1="8" y1="15" x2="29" y2="31" gradientUnits="userSpaceOnUse">
          <stop stopColor="#ffffff" />
          <stop offset="1" stopColor="#d1fae5" />
        </linearGradient>
      </defs>
      <path d="M5.5 17.2 18 6.8l12.5 10.4" fill="none" stroke="url(#brand-logo-roof)" strokeWidth="4.2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M9.2 16.5h17.6v12.7a2 2 0 0 1-2 2H11.2a2 2 0 0 1-2-2V16.5Z" fill="url(#brand-logo-body)" stroke="#0891b2" strokeWidth="2" />
      <path d="M15.2 31.2v-8.6h5.6v8.6" fill="#67e8f9" stroke="#0891b2" strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M23.6 22.4h3.2" stroke="#10b981" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function Header({ theme, onToggle }) {
  const { user } = useAuth()
  const userRole = user?.role || null

  const visibleNav = filterNavItems(NAV_ITEMS, userRole)
  const visibleSecondary = filterNavItems(NAV_ITEMS_SECONDARY, userRole)

  return (
    <header className="header">
      <Link to="/" className="logo">
        <div className="logo-icon"><BrandLogoIcon /></div>
        <span>Real Estate AVM</span>
        <span className="logo-badge">VN</span>
      </Link>

      <nav className="nav">
        {visibleNav.map(item => (
          <NavLink key={item.to} to={item.to} iconKey={item.iconKey} abbr={item.abbr}>
            {item.label}
          </NavLink>
        ))}
        <MoreMenu items={visibleSecondary} />
      </nav>

      <div className="header-actions">
        <NotificationBell />
        <button
          className="theme-toggle"
          onClick={onToggle}
          title={theme === 'dark' ? 'Chuyển sang chế độ sáng' : 'Chuyển sang chế độ tối'}
          aria-label="Toggle theme"
        >
          <span className="moon-icon">{icon('moon', 18)}</span>
          <span className="sun-icon">{icon('sun', 18)}</span>
        </button>
        <UserMenu />
      </div>
    </header>
  )
}

const LoadingFallback = (
  <div className="card animate-scaleIn" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '1.25rem', padding: '4rem', textAlign: 'center', borderRadius: '16px' }}>
    <div className="spinner" style={{ width: 44, height: 44, borderWidth: 3 }}></div>
    <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>{UI_LABELS.loading}</p>
  </div>
)

function AppRoutes() {
  const { theme, toggle } = useTheme()

  return (
    <div className="app">
      <Header theme={theme} onToggle={toggle} />
      <main className="main">
        <Suspense fallback={LoadingFallback}>
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<Prediction />} />
            <Route path="/buyer-survey" element={<BuyerSurvey />} />
            <Route path="/about" element={<About />} />

            {/* User routes — require login */}
            <Route path="/dashboard" element={<ProtectedRoute minRole="admin"><Dashboard /></ProtectedRoute>} />
            <Route path="/map" element={<ProtectedRoute minRole="user"><MapExplorer /></ProtectedRoute>} />
            <Route path="/community" element={<ProtectedRoute minRole="user"><Community /></ProtectedRoute>} />
            <Route path="/data-quality" element={<ProtectedRoute minRole="user"><DataQuality /></ProtectedRoute>} />

            {/* Admin routes */}
            <Route path="/collector" element={<ProtectedRoute minRole="admin"><DataCollector /></ProtectedRoute>} />
            <Route path="/collection" element={<ProtectedRoute minRole="admin"><CollectionDashboard /></ProtectedRoute>} />
            <Route path="/provenance-tracker" element={<ProtectedRoute minRole="admin"><ProvenanceTracker /></ProtectedRoute>} />
            <Route path="/research-lab" element={<ProtectedRoute minRole="admin"><ResearchLab /></ProtectedRoute>} />
            <Route path="/self-collected" element={<ProtectedRoute minRole="admin"><SelfCollected /></ProtectedRoute>} />
            <Route path="/data-sources" element={<ProtectedRoute minRole="admin"><DataSources /></ProtectedRoute>} />
            <Route path="/community/admin" element={<ProtectedRoute minRole="admin"><CommunityAdmin /></ProtectedRoute>} />
            <Route path="/admin/users" element={<ProtectedRoute minRole="admin"><UserManagement /></ProtectedRoute>} />
            {/* Internal data management — admin only (bản ghi là dữ liệu nội bộ dự án) */}
            <Route path="/data-explorer" element={<ProtectedRoute minRole="admin"><DataExplorer /></ProtectedRoute>} />
            <Route path="/records" element={<ProtectedRoute minRole="admin"><RecordExplorer /></ProtectedRoute>} />

            {/* ML Explainability Dashboard */}
            <Route path="/explainability" element={<ProtectedRoute minRole="user"><ExplainabilityDashboard /></ProtectedRoute>} />
          </Routes>
        </Suspense>
      </main>
      <NovaAssistant />
    </div>
  )
}

function App() {
  return (
    <BrowserRouter
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </QueryClientProvider>
    </BrowserRouter>
  )
}

export default App
