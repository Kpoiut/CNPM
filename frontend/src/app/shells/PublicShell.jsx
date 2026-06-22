import React from 'react'
import { Link, Outlet } from 'react-router-dom'

import ShellBrand from './ShellBrand'
import ShellNavigation from './ShellNavigation'
import ShellUtilities from './ShellUtilities'

export function PublicShell({ actions }) {
  return (
    <div className="role-shell role-shell--public">
      <header className="role-shell__topbar public-shell__topbar">
        <ShellBrand />
        <ShellNavigation role="public" ariaLabel="Điều hướng công khai" />
        <ShellUtilities>{actions}</ShellUtilities>
      </header>
      <main className="role-shell__content role-shell__content--public">
        <Outlet />
      </main>
      <footer className="public-shell__footer">
        <span>Định giá có bằng chứng, phiên bản và mức độ tin cậy.</span>
        <span className="public-shell__footer-links">
          <Link to="/trust">Độ tin cậy</Link>
          <Link to="/methodology">Phương pháp</Link>
          <Link to="/about">Giới thiệu</Link>
        </span>
      </footer>
    </div>
  )
}

export default PublicShell
