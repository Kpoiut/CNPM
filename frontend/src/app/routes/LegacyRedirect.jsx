import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'

import { useAuth } from '../../components/auth'
import { getLegacyDestination } from './routeRegistry'
import { appendSearch } from './redirectModel'

export function LegacyRedirect({ route }) {
  const location = useLocation()
  const { user } = useAuth()
  const destination = getLegacyDestination(route, user?.role)

  if (!destination) return <Navigate to="/" replace />
  return <Navigate to={appendSearch(destination, location.search)} replace />
}

export function RoleHomeRedirect() {
  const { user } = useAuth()
  if (user?.role === 'admin') return <Navigate to="/admin/overview" replace />
  if (user?.role === 'user') return <Navigate to="/app/valuations/new" replace />
  return <Navigate to="/" replace />
}

export default LegacyRedirect
