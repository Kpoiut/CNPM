// ============================================================
// Shared Vietnamese string constants for Real Estate AVM
// ============================================================

// === Asset Type Taxonomy v2 ===

// Asset Class → Asset Type
export const ASSET_CLASSES = {
  RESIDENTIAL: 'Nhà ở',
  COMMERCIAL: 'Thương mại',
  LAND: 'Đất',
  INDUSTRIAL: 'Công nghiệp',
  MIXED: 'Hỗn hợp',
}

// Asset Types per class
export const ASSET_TYPES = {
  RESIDENTIAL: {
    APARTMENT: 'Căn hộ chung cư',
    TOWNHOUSE: 'Nhà phố liền kề',
    VILLA: 'Biệt thự',
    ROWHOUSE: 'Row house',
    PENTHOUSE: 'Penthouse',
    STUDIO: 'Căn hộ studio',
  },
  COMMERCIAL: {
    SHOPHOUSE: 'Shophouse',
    OFFICE_TEL: 'Officetel',
    RETAIL_UNIT: 'Mặt bằng bán lẻ',
  },
  LAND: {
    LAND_URBAN: 'Đất đô thị',
    LAND_SUBURBAN: 'Đất ngoại thành',
    LAND_PROJECT: 'Đất dự án',
  },
  MIXED: {
    HOTEL: 'Khách sạn',
    CONDO_HOTEL: 'Condotel',
  },
}

// Backward compatible — kept for existing pages
// Phase 2: 5 canonical types — no conflations
export const PROPERTY_TYPES = {
  house:      'Nhà riêng',    // Detached house, traditional/aged
  apartment:  'Căn hộ',
  land:       'Đất nền',
  townhouse:  'Nhà phố',    // Attached townhouse
  villa:      'Biệt thự',
}

// Asset subtypes — Phase 2: Extended to cover all 5 canonical types
export const ASSET_SUBTYPES = {
  APARTMENT: {
    APT_STANDARD: 'Tiêu chuẩn',
    APT_PREMIUM: 'Cao cấp (≥25tr/m²)',
    APT_LUXURY: 'Hạng sang (≥50tr/m²)',
    APT_ECONOMY: 'Kinh tế (<15tr/m²)',
    APT_PENTHOUSE: 'Penthouse',
  },
  LAND_URBAN: {
    LAND_LEGAL_STREET: 'Đất mặt đường chính',
    LAND_ALLEY_3M: 'Đất hẻm ≥3m',
    LAND_ALLEY_2M: 'Đất hẻm 2-3m',
    LAND_ALLEY_1M: 'Đất hẻm <2m',
    LAND_CORNER: 'Đất góc 2+ mặt tiền',
    LAND_ODD_SHAPE: 'Đất hình dạng bất thường',
  },
  TOWNHOUSE: {
    TH_SINGLE_FACADE: '1 mặt tiền',
    TH_DOUBLE_FACADE: '2 mặt tiền (góc)',
    TH_TRIPLE_FACADE: '3 mặt tiền',
    TH_ALLEY_EXTENDED: 'Có hẻm phụ mở rộng',
  },
  VILLA: {
    VILLA_MODERN: 'Biệt thự hiện đại',
    VILLA_CLASSIC: 'Biệt thự cổ điển',
    VILLA_COMPOUND: 'Biệt thự compound',
    VILLA_POOL: 'Biệt thự có hồ bơi',
    VILLA_PREMIUM: 'Biệt thự cao cấp (Vinhomes/Riverside)',
  },
  HOUSE: {
    HOUSE_SINGLE: 'Nhà cấp 4 (1 tầng)',
    HOUSE_DOUBLE: 'Nhà 2 tầng',
    HOUSE_TRIPLE: 'Nhà 3+ tầng',
    HOUSE_OLD: 'Nhà cũ / truyền thống',
    HOUSE_RENOVATED: 'Nhà đã cải tạo',
  },
}

// View types for apartments
export const APT_VIEW_TYPES = {
  CITY: 'View thành phố',
  PARK: 'View công viên',
  RIVER: 'View sông',
  MOUNTAIN: 'View núi',
  NOTHING: 'Không có view',
  CITY_PARK: 'View thành phố + cây xanh',
  PARK_RIVER: 'View sông + cây xanh',
}

// Access/road class
export const ROAD_CLASSES = {
  MAIN_STREET: 'Đường chính ≥8m',
  SECONDARY_STREET: 'Đường thứ cấp',
  ALLEY_5M: 'Hẻm ≥5m',
  ALLEY_3M: 'Hẻm 3-5m',
  ALLEY_2M: 'Hẻm 2-3m',
  ALLEY_1M: 'Hẻm <2m',
}

// Flood risk levels
export const FLOOD_RISK = {
  none: 'Không ngập',
  minor: 'Ngập nhẹ (theo mùa)',
  moderate: 'Ngập trung bình',
  severe: 'Ngập nặng/thường xuyên',
  unknown: 'Không rõ',
}

// Feng shui sensitivities
export const FENG_SHUI_SENSITIVITIES = {
  NONE: 'Không quan tâm',
  LOW: 'Tham khảo nhẹ (±1-2%)',
  MEDIUM: 'Tham khảo vừa (±3-5%)',
  HIGH: 'Quan tâm cao (±5-10%)',
  CRITICAL: 'Quyết định bắt buộc (thay đổi quyết định)',
}

// Buyer archetypes
export const BUYER_ARCHETYPES = {
  FIRST_HOME: 'Người mua nhà lần đầu',
  UPGRADER: 'Nâng cấp tài sản',
  INVESTOR: 'Nhà đầu tư cho thuê',
  SPECULATOR: 'Đầu cơ ngắn hạn',
  RETIREE: 'Người về hưu / bảo toàn',
}

// Liquidity preferences
export const LIQUIDITY_PREFERENCES = {
  MAX_LIQUID: 'Ưu tiên thanh khoản cao nhất',
  PREFER_LIQUID: 'Thanh khoản quan trọng',
  BALANCED: 'Cân bằng',
  PREFER_APPRECIATION: 'Ưu tiên tăng giá',
}

// Family structures
export const FAMILY_STRUCTURES = {
  SINGLE: 'Độc thân',
  COUPLE_NO_KIDS: 'Vợ chồng chưa có con',
  COUPLE_WITH_KIDS: 'Gia đình có con',
  LARGE_FAMILY: 'Gia đình đông người (5+)',
  ELDERLY_PARENTS: 'Có người già/nhạy cảm cao',
}

// Noise tolerance
export const NOISE_TOLERANCES = {
  VERY_SENSITIVE: 'Rất nhạy cảm',
  SENSITIVE: 'Nhạy cảm',
  NEUTRAL: 'Bình thường',
  TOLERANT: 'Chịu được ồn',
  VERY_TOLERANT: 'Không quan tâm',
}

// Legal ownership types
export const OWNERSHIP_TYPES = {
  FULL_OWNERSHIP: 'Sổ đỏ/Sổ hồng đầy đủ',
  LURC: 'Giấy phép sử dụng đất',
  PENDING: 'Đang chờ cấp',
  DISPUTE: 'Đang tranh chấp',
  LEASEHOLD: 'Thuê có thời hạn',
  OTHER: 'Khác',
}

export const VERIFICATION_STATUS = {
  verified:     'Đã xác minh',
  pending:      'Chờ xác minh',
  rejected:     'Từ chối',
  unverified:   'Chưa xác minh',
}

export const RECORD_STATUS = {
  raw:            'Dữ liệu thô',
  pending_review: 'Chờ xét duyệt',
  verified:       'Đã xác minh',
  rejected:       'Bị từ chối',
  archived:       'Đã lưu trữ',
}

export const DATA_ORIGIN = {
  self_collected:   'Tự thu thập',
  public_collected: 'Nguồn công khai',
  system_demo:       'Chỉ để demo UI',
}

export const COLLECTION_METHODS = {
  field_survey:                  'Khảo sát thực địa',
  google_form_verified:          'Phiếu khảo sát',
  smartphone_sensor_capture:     'Từ cảm biến smartphone',
  app_user_submission:           'Người dùng gửi qua app',
  manual_verified_from_public:    'Xác minh từ tin rao công khai',
}

export const LEGAL_STATUSES = {
  ownership_certificate:          'Sổ đỏ / Sổ hồng',
  land_use_right_certificate:    'Giấy phép sử dụng đất',
  pending:                       'Đang chờ',
  other:                         'Khác',
}

export const FURNISHING_OPTIONS = {
  furnished:       'Có nội thất',
  semi_furnished:  'Nội thất một phần',
  unfurnished:     'Không nội thất',
  unknown:         'Không xác định',
}

export const NAV_ITEMS = [
  { to: '/',                   label: 'Dự đoán',        abbr: 'DĐ', iconKey: 'zap' },
  { to: '/dashboard',          label: 'Thống kê',       abbr: 'TK', iconKey: 'trendingUp' },
  { to: '/map',               label: 'Bản đồ',         abbr: 'BD', iconKey: 'map' },
  { to: '/community',          label: 'Cộng đồng',      abbr: 'CĐ', iconKey: 'globe' },
  { to: '/data-quality',       label: 'Tin cậy',       abbr: 'TC', iconKey: 'check' },
]

// Secondary nav — hidden behind "Thêm" dropdown
export const NAV_ITEMS_SECONDARY = [
  { to: '/buyer-survey',       label: 'Khảo sát nhu cầu', abbr: 'KS', iconKey: 'clipboardCheck' },
  { to: '/explainability',     label: 'Giải thích ML', abbr: 'GM', iconKey: 'experiment' },
  { to: '/collector',          label: 'Thu thập dữ liệu', abbr: 'TH', iconKey: 'database' },
  { to: '/collection',         label: 'Collection Dashboard', abbr: 'CD', iconKey: 'dashboard' },
  { to: '/provenance-tracker', label: 'Provenance',    abbr: 'PR', iconKey: 'link' },
  { to: '/research-lab',        label: 'Research Lab',  abbr: 'RL', iconKey: 'flask' },
  { to: '/self-collected',    label: 'Tự thu thập',   abbr: 'ST', iconKey: 'wrench' },
  { to: '/data-sources',       label: 'Nguồn dữ liệu', abbr: 'NG', iconKey: 'database' },
  { to: '/community/admin',    label: 'Quản trị cộng đồng', abbr: 'QC', iconKey: 'shieldCheck' },
  { to: '/data-explorer',      label: 'Bảng dữ liệu', abbr: 'DL', iconKey: 'table' },
  { to: '/records',            label: 'Bản ghi', abbr: 'BG', iconKey: 'fileSearch' },
  { to: '/admin/users',        label: 'Quản lý tài khoản', abbr: 'QL', iconKey: 'users' },
  { to: '/about',             label: 'Giới thiệu',     abbr: 'GT', iconKey: 'info' },
]

export const UI_LABELS = {
  loading:          'Đang tải giao diện...',
  noData:           'Không có dữ liệu',
  error:            'Đã xảy ra lỗi',
  refresh:          'Làm mới',
  save:             'Lưu',
  cancel:           'Hủy',
  close:            'Đóng',
  search:           'Tìm kiếm',
  filter:           'Lọc',
  reset:            'Đặt lại',
  detail:           'Chi tiết',
  view:             'Xem',
  add:              'Thêm',
  edit:             'Sửa',
  delete:           'Xóa',
  success:          'Thành công',
  fail:             'Thất bại',
  pending:          'Đang chờ',
  ready:            'Sẵn sàng',
  missing:          'Thiếu',
  previous:         'Trước',
  next:             'Sau',
  submit:           'Gửi',
  export:           'Xuất',
  import:           'Nhập',
  yes:              'Có',
  no:               'Không',
}
