import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Outlet } from 'react-router-dom'

import ShellBrand from './ShellBrand'
import ShellNavigation from './ShellNavigation'
import ShellUtilities from './ShellUtilities'

async function fetchSystemHealth() {
  const response = await fetch('/api/health')
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json()
}

function StatusPill({ label, value, state = 'neutral' }) {
  return (
    <span className={`operations-status operations-status--${state}`}>
      <small>{label}</small>
      <strong>{value}</strong>
    </span>
  )
}

export function AdminOperationsShell({ actions }) {
  const health = useQuery({
    queryKey: ['shell-system-health'],
    queryFn: fetchSystemHealth,
    staleTime: 60_000,
    refetchInterval: 60_000,
  })
  const database = health.data?.database
  const databaseValue = health.isPending
    ? 'Đang kiểm tra'
    : database?.ok
      ? String(database.dialect || 'Sẵn sàng').toUpperCase()
      : 'Chưa xác định'
  const databaseState = health.isError ? 'danger' : database?.ok ? 'healthy' : 'neutral'

  return (
    <div className="role-shell role-shell--operations">
      <header className="role-shell__topbar operations-shell__topbar">
        <ShellBrand homePath="/admin/overview" compact subtitle="Trung tâm vận hành" />
        <div className="operations-shell__status" aria-label="Trạng thái vận hành">
          <StatusPill label="Môi trường" value={import.meta.env.MODE === 'production' ? 'Production' : 'Development'} />
          <StatusPill label="Cơ sở dữ liệu" value={databaseValue} state={databaseState} />
          <StatusPill label="Mô hình" value="Chưa xác định" />
        </div>
        <ShellUtilities>{actions}</ShellUtilities>
      </header>
      <div className="role-shell__frame">
        <aside className="role-shell__sidebar role-shell__sidebar--admin">
          <div className="operations-shell__eyebrow">Vận hành hệ thống</div>
          <ShellNavigation role="admin" ariaLabel="Khu vực quản trị" variant="vertical" />
        </aside>
        <main className="role-shell__content role-shell__content--operations">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default AdminOperationsShell
