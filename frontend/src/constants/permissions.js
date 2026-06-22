/**
 * Compatibility permission helpers backed by the canonical route registry.
 * New routing and navigation code should import from app/routes/routeRegistry.
 */

import {
  APP_ROUTES,
  getRouteByPath,
  hasRouteAccess,
} from '../app/routes/routeRegistry.js'

export const ROUTE_PERMISSIONS = Object.freeze(Object.fromEntries(
  APP_ROUTES.map(route => [route.path, Object.freeze({
    minRole: route.minRole,
    label: route.title,
    hidden: Boolean(route.hidden),
  })]),
))

export function canAccess(path, userRole) {
  return hasRouteAccess(getRouteByPath(path), userRole)
}

export function filterNavItems(navItems, userRole) {
  return navItems.filter(item => canAccess(item.to, userRole))
}
