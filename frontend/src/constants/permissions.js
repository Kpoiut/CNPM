/**
 * Route-Role permission matrix — single source of truth.
 *
 * minRole: 'public' (no auth needed), 'user', 'admin'
 * hidden:  true = ẩn khỏi nav khi không đủ quyền
 */

export const ROUTE_PERMISSIONS = {
  '/':                    { minRole: 'public', label: 'Dự đoán' },
  '/dashboard':           { minRole: 'admin',  label: 'Thống kê' },
  '/map':                 { minRole: 'user',   label: 'Bản đồ' },
  '/community':           { minRole: 'user',   label: 'Cộng đồng' },
  '/data-quality':        { minRole: 'user',   label: 'Tin cậy' },
  '/buyer-survey':        { minRole: 'user',   label: 'Khảo sát nhu cầu' },
  '/explainability':      { minRole: 'user',   label: 'Giải thích ML' },
  '/about':               { minRole: 'public', label: 'Giới thiệu' },
  '/login':               { minRole: 'public', label: 'Đăng nhập', hidden: true },
  '/collector':           { minRole: 'admin',  label: 'Thu thập' },
  '/collection':          { minRole: 'admin',  label: 'Collection Dashboard' },
  '/provenance-tracker':  { minRole: 'admin',  label: 'Provenance' },
  '/research-lab':        { minRole: 'admin',  label: 'Research Lab' },
  '/self-collected':      { minRole: 'admin',  label: 'Tự thu thập' },
  '/data-sources':        { minRole: 'admin',  label: 'Nguồn dữ liệu' },
  '/community/admin':     { minRole: 'admin',  label: 'Quản trị cộng đồng' },
  '/data-explorer':       { minRole: 'admin',  label: 'Bảng dữ liệu' },
  '/records':             { minRole: 'admin',  label: 'Bản ghi' },
  '/admin/users':          { minRole: 'admin',  label: 'Quản lý tài khoản' },
}

const ROLE_LEVEL = { public: 0, user: 1, admin: 2 }

/**
 * Check if a user role can access a given route.
 * @param {string} route  — path like '/dashboard'
 * @param {string|null} userRole — 'user', 'admin', or null (unauthenticated)
 * @returns {boolean}
 */
export function canAccess(route, userRole) {
  const perm = ROUTE_PERMISSIONS[route]
  if (!perm) return false
  const required = ROLE_LEVEL[perm.minRole] || 0
  const actual = ROLE_LEVEL[userRole] || 0
  return actual >= required
}

/**
 * Filter nav items based on user role.
 * @param {Array} navItems — array of { to, label, icon, ... }
 * @param {string|null} userRole
 * @returns {Array} — filtered items
 */
export function filterNavItems(navItems, userRole) {
  return navItems.filter(item => {
    const perm = ROUTE_PERMISSIONS[item.to]
    if (!perm) return true
    if (perm.hidden) return false
    return canAccess(item.to, userRole)
  })
}
