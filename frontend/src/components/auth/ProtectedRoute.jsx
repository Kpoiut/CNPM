/**
 * ProtectedRoute — route guard based on role permissions.
 *
 * Usage:
 *   <Route path="/collector" element={
 *     <ProtectedRoute minRole="admin"><DataCollector /></ProtectedRoute>
 *   } />
 */

import React from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from './AuthContext'
import { icon } from '../ui/icons'

const ROLE_LEVEL = { public: 0, user: 1, admin: 2 }

export function ProtectedRoute({ children, minRole = 'user' }) {
  const { user, isLoading, isAuthenticated } = useAuth()

  if (isLoading) {
    return (
      <div className="card animate-scaleIn" style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center', gap: '1.25rem', padding: '4rem', textAlign: 'center',
      }}>
        <div className="spinner" style={{ width: 44, height: 44, borderWidth: 3 }}></div>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Đang xác thực...</p>
      </div>
    )
  }

  // Not authenticated → redirect to login
  if (!isAuthenticated && minRole !== 'public') {
    return <Navigate to="/login" replace />
  }

  // Check role level
  const required = ROLE_LEVEL[minRole] || 0
  const actual = ROLE_LEVEL[user?.role] || 0

  if (actual < required) {
    return <AccessDeniedInline />
  }

  return children
}

/**
 * Inline access denied block — shown when user lacks permission.
 */
function AccessDeniedInline() {
  return (
    <div className="access-denied animate-scaleIn">
      <div className="access-denied-card">
        <div className="access-denied-icon">{icon('shieldAlert', 40)}</div>
        <h2 className="access-denied-title">Không có quyền truy cập</h2>
        <p className="access-denied-text">
          Trang này chỉ dành cho quản trị viên.<br />
          Vui lòng liên hệ admin nếu bạn cần truy cập.
        </p>
        <a href="/" className="btn btn-primary" style={{ marginTop: '1rem' }}>
          ← Quay về trang chính
        </a>
      </div>
    </div>
  )
}

export default ProtectedRoute
