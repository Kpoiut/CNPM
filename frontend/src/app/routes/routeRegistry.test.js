import test from 'node:test'
import assert from 'node:assert/strict'

import {
  APP_ROUTES,
  getNavigationForRole,
  getLegacyDestination,
  getRouteByPath,
  hasRouteAccess,
} from './routeRegistry.js'
import { appendSearch } from './redirectModel.js'
import { canAccess, filterNavItems } from '../../constants/permissions.js'
import { getShellForRole, isNavigationItemActive } from '../shells/shellModel.js'

test('every canonical path is unique', () => {
  const paths = APP_ROUTES.map(route => route.path)
  assert.equal(new Set(paths).size, paths.length)
})

test('admin navigation exposes operations areas and visible Research Lab entry', () => {
  assert.deepEqual(
    getNavigationForRole('admin').map(item => item.label),
    ['Tổng quan', 'Định giá', 'Dữ liệu', 'Mô hình', 'Quản trị', 'Tài liệu'],
  )
  const modelGroup = getNavigationForRole('admin').find(item => item.label === 'Mô hình')
  assert.ok(modelGroup.children.some(child => child.path === '/admin/models/experiments' && child.label === 'Research Lab'))
})

test('user navigation keeps legacy user pages visible without admin operations', () => {
  assert.deepEqual(
    getNavigationForRole('user').map(item => item.path),
    ['/app/valuations/new', '/app/valuations/history', '/app/map', '/app/community', '/app/preferences', '/trust', '/methodology'],
  )
})

test('public navigation keeps legacy map and community pages visible', () => {
  assert.deepEqual(
    getNavigationForRole('public').map(item => item.path),
    ['/', '/trust', '/methodology', '/map', '/community', '/about'],
  )
})

test('public cannot access an admin route', () => {
  const route = getRouteByPath('/admin/data/overview')
  assert.equal(hasRouteAccess(route, null), false)
  assert.equal(hasRouteAccess(route, 'admin'), true)
})

test('google oauth callback route is public and hidden from navigation', () => {
  const route = getRouteByPath('/signin-google')
  assert.equal(route.component, 'GoogleOAuthCallback')
  assert.equal(route.minRole, 'public')
  assert.equal(route.hidden, true)
  assert.equal(hasRouteAccess(route, null), true)
})

test('unknown roles receive public navigation only', () => {
  assert.deepEqual(getNavigationForRole('unexpected'), getNavigationForRole('public'))
})

test('unknown routes deny access', () => {
  assert.equal(hasRouteAccess(getRouteByPath('/missing'), 'admin'), false)
})

test('compatibility permissions use canonical user and admin routes', () => {
  assert.equal(canAccess('/app/map', 'user'), true)
  assert.equal(canAccess('/admin/data/records', 'user'), false)
  assert.equal(canAccess('/admin/data/records', 'admin'), true)
  assert.equal(canAccess('/missing', 'admin'), false)
})

test('navigation filtering uses the canonical registry', () => {
  const items = [
    { to: '/app/map', label: 'Bản đồ' },
    { to: '/trust', label: 'Độ tin cậy' },
    { to: '/admin/data/records', label: 'Dữ liệu' },
  ]
  assert.deepEqual(filterNavItems(items, 'user'), [items[0], items[1]])
})

test('shell selection follows the authenticated role', () => {
  assert.equal(getShellForRole(null), 'public')
  assert.equal(getShellForRole('user'), 'user')
  assert.equal(getShellForRole('admin'), 'admin')
  assert.equal(getShellForRole('unexpected'), 'public')
})

test('nested admin routes keep their top-level area active', () => {
  assert.equal(isNavigationItemActive('/admin/data/records', {
    path: '/admin/data/overview',
    matchPrefix: '/admin/data',
  }), true)
  assert.equal(isNavigationItemActive('/admin/models/experiments', {
    path: '/admin/data/overview',
    matchPrefix: '/admin/data',
  }), false)
  assert.equal(isNavigationItemActive('/about/team', { path: '/' }), false)
})

test('legacy destinations can vary by role without duplicating routes', () => {
  const legacy = { toByRole: { public: '/trust', admin: '/admin/data/quality' } }
  assert.equal(getLegacyDestination(legacy, null), '/trust')
  assert.equal(getLegacyDestination(legacy, 'admin'), '/admin/data/quality')
})

test('legacy redirect preserves existing destination and source queries', () => {
  assert.equal(
    appendSearch('/admin/data/records?origin=self_collected', '?page=2'),
    '/admin/data/records?origin=self_collected&page=2',
  )
  assert.equal(appendSearch('/app/map', '?district=1'), '/app/map?district=1')
  assert.equal(appendSearch('/app/map', ''), '/app/map')
})
