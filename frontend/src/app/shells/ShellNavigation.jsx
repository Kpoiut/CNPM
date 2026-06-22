import React from 'react'
import { Link, useLocation } from 'react-router-dom'

import { icon } from '../../components/ui/icons'
import { getNavigationForRole } from '../routes/routeRegistry'
import { isNavigationItemActive } from './shellModel'

export function ShellNavigation({ role, ariaLabel, variant = 'horizontal' }) {
  const location = useLocation()
  const items = getNavigationForRole(role)

  return (
    <nav className={`shell-navigation shell-navigation--${variant}`} aria-label={ariaLabel}>
      {items.map(item => {
        const active = isNavigationItemActive(location.pathname, item)
        const showChildren = item.children?.length > 0 && (variant === 'vertical' || active)
        return (
          <div key={item.path} className={`shell-navigation__group ${showChildren ? 'is-expanded' : ''}`}>
            <Link
              to={item.path}
              className={`shell-navigation__item ${active ? 'is-active' : ''}`}
              aria-current={active ? 'page' : undefined}
              aria-expanded={item.children?.length > 0 ? showChildren : undefined}
            >
              <span className="shell-navigation__icon">{icon(item.iconKey, 18)}</span>
              <span>{item.label}</span>
            </Link>
            {showChildren && (
              <div className="shell-navigation__children" aria-label={`${item.label} tác vụ con`}>
                {item.children.map(child => {
                  const childActive = location.pathname === child.path
                  return (
                    <Link
                      key={child.path}
                      to={child.path}
                      className={`shell-navigation__child ${childActive ? 'is-active' : ''}`}
                      aria-current={childActive ? 'page' : undefined}
                    >
                      {child.label}
                    </Link>
                  )
                })}
              </div>
            )}
          </div>
        )
      })}
    </nav>
  )
}

export default ShellNavigation
