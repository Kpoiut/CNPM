import { SHELL } from '../routes/routeRegistry.js'

export function getShellForRole(role) {
  if (role === 'admin') return SHELL.ADMIN
  if (role === 'user') return SHELL.USER
  return SHELL.PUBLIC
}

export function isNavigationItemActive(pathname, item) {
  if (!pathname || !item?.path) return false
  if (item.matchPrefix) {
    return pathname === item.matchPrefix || pathname.startsWith(`${item.matchPrefix}/`)
  }
  return item.path === '/' ? pathname === '/' : pathname === item.path
}
