import React from 'react'

export const CURRENT_ENGINE_LABEL = 'Chạy Valuation Engine v2'

export function submitLabel(isAdmin, loading, engineLabel = CURRENT_ENGINE_LABEL, suffix = '') {
  if (loading) return 'Đang định giá...'
  return isAdmin ? `${engineLabel || CURRENT_ENGINE_LABEL}${suffix}` : 'Dự đoán'
}

export function scrollInvalidField(e) {
  const field = e.target
  field.closest('.form-group')?.classList.add('is-invalid')
  window.requestAnimationFrame(() => {
    field.scrollIntoView({ behavior: 'smooth', block: 'center' })
    field.focus({ preventScroll: true })
  })
}

export function clearInvalidField(e) {
  e.target.closest('.form-group')?.classList.remove('is-invalid')
}

export function toFloat(value, fallback = undefined) {
  if (value === '' || value == null) return fallback
  const n = Number.parseFloat(value)
  return Number.isFinite(n) ? n : fallback
}

export function toInt(value, fallback = undefined) {
  if (value === '' || value == null) return fallback
  const n = Number.parseInt(value, 10)
  return Number.isFinite(n) ? n : fallback
}

export const LOCATION_HINTS = {
  hanoiWards: ['Dịch Vọng', 'Dịch Vọng Hậu', 'Mai Dịch', 'Quan Hoa', 'Thanh Xuân Trung', 'Khương Mai', 'Láng Thượng'],
  hcmWards: ['Tân Phong', 'Tân Quy', 'Bình Thuận', 'Phường 25', 'Phường 2', 'Phường 15'],
  streets: ['Xuân Thủy', 'Cầu Giấy', 'Trần Duy Hưng', 'Nguyễn Trãi', 'Láng Hạ', 'Nguyễn Thị Thập', 'Điện Biên Phủ'],
  projects: ['Vinhomes Riverside', 'Masteri Thảo Điền', 'Sunwah Pearl', 'EcoPark', 'The Manor', 'Mipec Rubik 360'],
  blocks: ['Tower A', 'Tower B', 'Block B2', 'S1', 'S2', 'Tòa N07', 'Landmark Plus'],
}

export function HintOptions({ id, options }) {
  return React.createElement(
    'datalist',
    { id },
    options.map(option => {
      const value = Array.isArray(option) ? option[0] : option
      const label = Array.isArray(option) ? option[1] : option
      return React.createElement('option', { key: value, value: label }, label)
    })
  )
}

export function mapEntriesToOptions(map = {}) {
  return Object.entries(map).map(([value, label]) => [value, label])
}

export function displayOption(options = [], value = '') {
  const match = options.find(option => Array.isArray(option) && option[0] === value)
  return match ? match[1] : value
}

export function inputToOptionCode(options = [], input = '') {
  const normalized = String(input || '').trim()
  const match = options.find(option => Array.isArray(option) && (option[1] === normalized || option[0] === normalized))
  return match ? match[0] : input
}

export const COMMON_HINTS = {
  riskLevels: [
    ['none', 'Không có thông tin'],
    ['low', 'Thấp'],
    ['medium', 'Trung bình'],
    ['high', 'Cao'],
    ['severe', 'Nghiêm trọng'],
  ],
  orientations: ['Đông', 'Tây', 'Nam', 'Bắc', 'Đông Nam', 'Tây Nam', 'Đông Bắc', 'Tây Bắc'],
  unitPositions: [
    ['middle', 'Giữa block'],
    ['end', 'Đầu/cuối block'],
    ['corner', 'Góc block'],
    ['wing_A', 'Cánh A'],
    ['wing_B', 'Cánh B'],
  ],
  sunlight: [
    ['GOOD', 'Tốt, ít nắng Tây'],
    ['FAIR', 'Trung bình'],
    ['POOR', 'Nắng Tây gay gắt'],
  ],
  distances: [
    ['very_close', 'Rất gần'],
    ['close', 'Gần'],
    ['medium', 'Trung bình'],
    ['far', 'Xa'],
    ['very_far', 'Rất xa'],
  ],
}
