import React from 'react'
import { Outlet } from 'react-router-dom'

import ShellBrand from './ShellBrand'
import ShellNavigation from './ShellNavigation'
import ShellUtilities from './ShellUtilities'

export function UserWorkspaceShell({ actions }) {
  return (
    <div className="role-shell role-shell--workspace">
      <header className="role-shell__topbar workspace-shell__topbar">
        <ShellBrand homePath="/app/valuations/new" compact subtitle="Không gian định giá" />
        <div className="workspace-shell__context">
          <strong>Không gian của bạn</strong>
          <span>Định giá, bằng chứng và lịch sử</span>
        </div>
        <ShellUtilities>{actions}</ShellUtilities>
      </header>
      <div className="role-shell__frame">
        <aside className="role-shell__sidebar">
          <ShellNavigation role="user" ariaLabel="Tác vụ người dùng" variant="vertical" />
        </aside>
        <main className="role-shell__content role-shell__content--workspace">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default UserWorkspaceShell
