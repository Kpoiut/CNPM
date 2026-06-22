import React, { Suspense, lazy, useEffect, useRef, useState } from 'react'
import { BrowserRouter, Link, Route, Routes, useNavigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { icon } from './components/ui/icons'
import { AuthProvider, ProtectedRoute, useAuth } from './components/auth'
import {
  clearNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  notificationEvents,
  readNotifications,
} from './lib/notifications'
import NovaAssistant from './components/nova'
import AdminOperationsShell from './app/shells/AdminOperationsShell'
import PublicShell from './app/shells/PublicShell'
import UserWorkspaceShell from './app/shells/UserWorkspaceShell'
import LegacyRedirect, { RoleHomeRedirect } from './app/routes/LegacyRedirect'
import {
  LEGACY_ROUTES,
  SHELL,
  getRoutesForShell,
} from './app/routes/routeRegistry'
import './app/shells/shell.css'

const About = lazy(() => import('./pages/public/About'))
const BuyerSurvey = lazy(() => import('./pages/public/BuyerSurvey'))
const CollectionDashboard = lazy(() => import('./pages/admin/CollectionDashboard'))
const Community = lazy(() => import('./pages/public/Community'))
const CommunityAdmin = lazy(() => import('./pages/admin/CommunityAdmin'))
const Dashboard = lazy(() => import('./pages/public/Dashboard'))
const DataCollector = lazy(() => import('./pages/admin/DataCollector'))
const DataExplorer = lazy(() => import('./pages/public/DataExplorer'))
const DataQuality = lazy(() => import('./pages/public/DataQuality'))
const DataSources = lazy(() => import('./pages/admin/DataSources'))
const ExplainabilityDashboard = lazy(() => import('./pages/ExplainabilityDashboard'))
const GoogleOAuthCallback = lazy(() => import('./pages/public/GoogleOAuthCallback'))
const Login = lazy(() => import('./pages/public/Login'))
const MapExplorer = lazy(() => import('./pages/public/MapExplorer'))
const Methodology = lazy(() => import('./pages/public/Methodology'))
const Prediction = lazy(() => import('./pages/public/Prediction'))
const ProvenanceTracker = lazy(() => import('./pages/admin/ProvenanceTracker'))
const ResearchLab = lazy(() => import('./pages/admin/ResearchLab'))
const TrustCenter = lazy(() => import('./pages/public/TrustCenter'))
const UserManagement = lazy(() => import('./pages/admin/UserManagement'))
const ValuationHistory = lazy(() => import('./pages/user/ValuationHistory'))

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 2, staleTime: 5 * 60 * 1000 },
    mutations: { retry: 1 },
  },
})

const THEME_KEY = 'avm-theme'

const ROUTE_COMPONENTS = Object.freeze({
  About,
  BuyerSurvey,
  CollectionDashboard,
  Community,
  CommunityAdmin,
  Dashboard,
  DataCollector,
  DataExplorer,
  DataQuality,
  DataSources,
  ExplainabilityDashboard,
  GoogleOAuthCallback,
  Login,
  MapExplorer,
  Methodology,
  Prediction,
  ProvenanceTracker,
  ResearchLab,
  TrustCenter,
  UserManagement,
  ValuationHistory,
})

function useTheme() {
  const [theme, setTheme] = useState(() => {
    try { return localStorage.getItem(THEME_KEY) || 'dark' } catch { return 'dark' }
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    try { localStorage.setItem(THEME_KEY, theme) } catch { /* storage can be disabled */ }
  }, [theme])

  return {
    theme,
    toggle: () => setTheme(current => current === 'dark' ? 'light' : 'dark'),
  }
}

function UserMenu() {
  const { user, isAuthenticated, isAdmin, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const roleLabel = isAdmin ? 'Quản trị viên' : 'Người dùng'

  useEffect(() => {
    const closeOutside = event => {
      if (ref.current && !ref.current.contains(event.target)) setOpen(false)
    }
    document.addEventListener('mousedown', closeOutside)
    return () => document.removeEventListener('mousedown', closeOutside)
  }, [])

  if (!isAuthenticated) {
    return <Link to="/login" className="btn btn-ghost">Đăng nhập</Link>
  }

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        className="user-avatar-btn"
        type="button"
        onClick={() => setOpen(current => !current)}
        aria-expanded={open}
        aria-haspopup="menu"
      >
        <span className="user-avatar-name">{user.username}</span>
        {isAdmin && <span className="user-badge-admin">QL</span>}
      </button>
      {open && (
        <div className="user-dropdown animate-slideUp" role="menu">
          <div className="user-dropdown-header">
            <span className="user-dropdown-name">{user.username}</span>
            <span className="user-dropdown-role">{roleLabel}</span>
          </div>
          <div className="user-dropdown-divider" />
          <button
            className="user-dropdown-item"
            type="button"
            role="menuitem"
            onClick={() => {
              setOpen(false)
              logout()
              navigate('/login')
            }}
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
    const onStorage = event => {
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
    const closeOutside = event => {
      if (ref.current && !ref.current.contains(event.target)) setOpen(false)
    }
    document.addEventListener('mousedown', closeOutside)
    return () => document.removeEventListener('mousedown', closeOutside)
  }, [])

  if (!isAuthenticated) return null

  const unread = items.filter(item => !item.read).length
  const openItem = item => {
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
        onClick={() => setOpen(current => !current)}
        aria-label="Thông báo"
        aria-expanded={open}
      >
        {icon('bell', 18)}
        {unread > 0 && <span className="notification-count">{unread > 9 ? '9+' : unread}</span>}
      </button>
      {open && (
        <div className="notification-panel animate-slideUp">
          <div className="notification-panel-header">
            <div>
              <strong>Thông báo</strong>
              <span>{items.length ? `${items.length} tin đã lưu` : 'Chưa có thông báo'}</span>
            </div>
            <button type="button" onClick={() => { markAllNotificationsRead(user); refresh() }}>Đánh dấu đã đọc</button>
          </div>
          <div className="notification-list">
            {items.length === 0 ? (
              <div className="notification-empty">Cảnh báo và cập nhật hệ thống sẽ xuất hiện tại đây.</div>
            ) : items.map(item => (
              <button
                key={item.id}
                type="button"
                className={`notification-item notification-item-main ${item.read ? '' : 'unread'}`}
                onClick={() => openItem(item)}
              >
                <span className={`notification-dot ${item.type}`} />
                <span>
                  <strong>{item.title}</strong>
                  <em>{item.body}</em>
                </span>
              </button>
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

function ShellActions({ theme, onToggle }) {
  return (
    <>
      <NotificationBell />
      <button
        className="theme-toggle"
        type="button"
        onClick={onToggle}
        title={theme === 'dark' ? 'Chuyển sang chế độ sáng' : 'Chuyển sang chế độ tối'}
        aria-label={theme === 'dark' ? 'Bật chế độ sáng' : 'Bật chế độ tối'}
      >
        <span className="moon-icon">{icon('moon', 18)}</span>
        <span className="sun-icon">{icon('sun', 18)}</span>
      </button>
      <UserMenu />
    </>
  )
}

const LoadingFallback = (
  <div className="card animate-scaleIn" style={{ display: 'grid', placeItems: 'center', gap: '1rem', margin: '2rem', padding: '4rem' }}>
    <div className="spinner" style={{ width: 44, height: 44, borderWidth: 3 }} />
    <p style={{ color: 'var(--text-muted)' }}>Đang tải giao diện...</p>
  </div>
)

function renderCanonicalRoutes(shell) {
  return getRoutesForShell(shell).map(route => {
    const Component = ROUTE_COMPONENTS[route.component]
    if (!Component) throw new Error(`Missing route component: ${route.component}`)
    return <Route key={route.path} path={route.path} element={<Component />} />
  })
}

function AppRoutes() {
  const { theme, toggle } = useTheme()
  const actions = <ShellActions theme={theme} onToggle={toggle} />

  return (
    <>
      <Suspense fallback={LoadingFallback}>
        <Routes>
          <Route element={<PublicShell actions={actions} />}>
            {renderCanonicalRoutes(SHELL.PUBLIC)}
          </Route>
          <Route element={<ProtectedRoute minRole="user"><UserWorkspaceShell actions={actions} /></ProtectedRoute>}>
            {renderCanonicalRoutes(SHELL.USER)}
          </Route>
          <Route element={<ProtectedRoute minRole="admin"><AdminOperationsShell actions={actions} /></ProtectedRoute>}>
            {renderCanonicalRoutes(SHELL.ADMIN)}
          </Route>
          {LEGACY_ROUTES.map(route => (
            <Route
              key={route.path}
              path={route.path}
              element={(
                <ProtectedRoute minRole={route.minRole}>
                  <LegacyRedirect route={route} />
                </ProtectedRoute>
              )}
            />
          ))}
          <Route path="*" element={<RoleHomeRedirect />} />
        </Routes>
      </Suspense>
      <NovaAssistant />
    </>
  )
}

export default function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </QueryClientProvider>
    </BrowserRouter>
  )
}
