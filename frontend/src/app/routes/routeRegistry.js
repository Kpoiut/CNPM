export const ROLE_LEVEL = Object.freeze({ public: 0, user: 1, admin: 2 })

export const SHELL = Object.freeze({
  PUBLIC: 'public',
  USER: 'user',
  ADMIN: 'admin',
})

const route = (path, component, minRole, shell, options = {}) => Object.freeze({
  path,
  component,
  minRole,
  shell,
  ...options,
})

export const APP_ROUTES = Object.freeze([
  route('/', 'Prediction', 'public', SHELL.PUBLIC, { title: 'Định giá' }),
  route('/trust', 'TrustCenter', 'public', SHELL.PUBLIC, { title: 'Độ tin cậy' }),
  route('/methodology', 'Methodology', 'public', SHELL.PUBLIC, { title: 'Phương pháp' }),
  route('/about', 'About', 'public', SHELL.PUBLIC, { title: 'Giới thiệu' }),
  route('/login', 'Login', 'public', SHELL.PUBLIC, { title: 'Đăng nhập', hidden: true }),

  route('/app/valuations/new', 'Prediction', 'user', SHELL.USER, { title: 'Định giá mới' }),
  route('/app/valuations/history', 'ValuationHistory', 'user', SHELL.USER, { title: 'Lịch sử định giá' }),
  route('/app/map', 'MapExplorer', 'user', SHELL.USER, { title: 'Bản đồ' }),
  route('/app/community', 'Community', 'user', SHELL.USER, { title: 'Cộng đồng' }),
  route('/app/preferences', 'BuyerSurvey', 'user', SHELL.USER, { title: 'Nhu cầu mua' }),

  route('/admin/overview', 'Dashboard', 'admin', SHELL.ADMIN, { title: 'Tổng quan vận hành' }),
  route('/admin/valuations/new', 'Prediction', 'admin', SHELL.ADMIN, { title: 'Định giá chuyên gia' }),
  route('/admin/data/overview', 'CollectionDashboard', 'admin', SHELL.ADMIN, { title: 'Tổng quan dữ liệu' }),
  route('/admin/data/ingestion', 'DataCollector', 'admin', SHELL.ADMIN, { title: 'Tiếp nhận dữ liệu' }),
  route('/admin/data/records', 'DataExplorer', 'admin', SHELL.ADMIN, { title: 'Bản ghi dữ liệu' }),
  route('/admin/data/sources', 'DataSources', 'admin', SHELL.ADMIN, { title: 'Nguồn dữ liệu' }),
  route('/admin/data/quality', 'DataQuality', 'admin', SHELL.ADMIN, { title: 'Chất lượng dữ liệu' }),
  route('/admin/data/provenance', 'ProvenanceTracker', 'admin', SHELL.ADMIN, { title: 'Nguồn gốc dữ liệu' }),
  route('/admin/models/experiments', 'ResearchLab', 'admin', SHELL.ADMIN, { title: 'Thử nghiệm mô hình' }),
  route('/admin/models/explainability', 'ExplainabilityDashboard', 'admin', SHELL.ADMIN, { title: 'Giải thích mô hình' }),
  route('/admin/governance/community', 'CommunityAdmin', 'admin', SHELL.ADMIN, { title: 'Kiểm duyệt cộng đồng' }),
  route('/admin/governance/accounts', 'UserManagement', 'admin', SHELL.ADMIN, { title: 'Tài khoản và quyền' }),
])

export const NAVIGATION = Object.freeze({
  public: Object.freeze([
    { path: '/', label: 'Định giá', iconKey: 'zap' },
    { path: '/trust', label: 'Độ tin cậy', iconKey: 'shieldCheck' },
    { path: '/methodology', label: 'Phương pháp', iconKey: 'experiment' },
    { path: '/about', label: 'Giới thiệu', iconKey: 'info' },
  ]),
  user: Object.freeze([
    { path: '/app/valuations/new', label: 'Định giá', iconKey: 'zap', matchPrefix: '/app/valuations' },
    { path: '/app/valuations/history', label: 'Lịch sử', iconKey: 'activity' },
    { path: '/app/map', label: 'Bản đồ', iconKey: 'map' },
    { path: '/app/community', label: 'Cộng đồng', iconKey: 'globe' },
  ]),
  admin: Object.freeze([
    { path: '/admin/overview', label: 'Tổng quan', iconKey: 'dashboard' },
    { path: '/admin/valuations/new', label: 'Định giá', iconKey: 'zap', matchPrefix: '/admin/valuations' },
    {
      path: '/admin/data/overview',
      label: 'Dữ liệu',
      iconKey: 'database',
      matchPrefix: '/admin/data',
      children: Object.freeze([
        { path: '/admin/data/overview', label: 'Tổng quan' },
        { path: '/admin/data/ingestion', label: 'Tiếp nhận' },
        { path: '/admin/data/records', label: 'Bản ghi' },
        { path: '/admin/data/sources', label: 'Nguồn' },
        { path: '/admin/data/quality', label: 'Chất lượng' },
        { path: '/admin/data/provenance', label: 'Nguồn gốc' },
      ]),
    },
    {
      path: '/admin/models/experiments',
      label: 'Mô hình',
      iconKey: 'experiment',
      matchPrefix: '/admin/models',
      children: Object.freeze([
        { path: '/admin/models/experiments', label: 'Thử nghiệm' },
        { path: '/admin/models/explainability', label: 'Giải thích' },
      ]),
    },
    {
      path: '/admin/governance/community',
      label: 'Quản trị',
      iconKey: 'shieldCheck',
      matchPrefix: '/admin/governance',
      children: Object.freeze([
        { path: '/admin/governance/community', label: 'Cộng đồng' },
        { path: '/admin/governance/accounts', label: 'Tài khoản' },
      ]),
    },
  ]),
})

export const LEGACY_ROUTES = Object.freeze([
  { path: '/buyer-survey', to: '/app/preferences', minRole: 'user' },
  { path: '/dashboard', to: '/admin/overview', minRole: 'admin' },
  { path: '/map', to: '/app/map', minRole: 'user' },
  { path: '/community', to: '/app/community', minRole: 'user' },
  {
    path: '/data-quality',
    toByRole: { public: '/trust', user: '/trust', admin: '/admin/data/quality' },
    minRole: 'public',
  },
  { path: '/collector', to: '/admin/data/ingestion', minRole: 'admin' },
  { path: '/collection', to: '/admin/data/overview', minRole: 'admin' },
  { path: '/provenance-tracker', to: '/admin/data/provenance', minRole: 'admin' },
  { path: '/research-lab', to: '/admin/models/experiments', minRole: 'admin' },
  { path: '/self-collected', to: '/admin/data/records?origin=self_collected', minRole: 'admin' },
  { path: '/data-sources', to: '/admin/data/sources', minRole: 'admin' },
  { path: '/community/admin', to: '/admin/governance/community', minRole: 'admin' },
  { path: '/admin/users', to: '/admin/governance/accounts', minRole: 'admin' },
  { path: '/data-explorer', to: '/admin/data/records', minRole: 'admin' },
  { path: '/records', to: '/admin/data/records', minRole: 'admin' },
  {
    path: '/explainability',
    toByRole: {
      public: '/login',
      user: '/app/valuations/history?reason=select-valuation',
      admin: '/admin/models/explainability',
    },
    minRole: 'public',
  },
])

export function getRouteByPath(path) {
  return APP_ROUTES.find(item => item.path === path) ?? null
}

export function hasRouteAccess(routeConfig, role) {
  if (!routeConfig) return false
  const actual = ROLE_LEVEL[role ?? 'public'] ?? ROLE_LEVEL.public
  const required = ROLE_LEVEL[routeConfig.minRole]
  return Number.isInteger(required) && actual >= required
}

export function getNavigationForRole(role) {
  return NAVIGATION[role] ?? NAVIGATION.public
}

export function getRoutesForShell(shell) {
  return APP_ROUTES.filter(item => item.shell === shell)
}

export function getLegacyDestination(legacyRoute, role) {
  if (!legacyRoute) return null
  return legacyRoute.toByRole?.[role ?? 'public'] ?? legacyRoute.to ?? null
}
