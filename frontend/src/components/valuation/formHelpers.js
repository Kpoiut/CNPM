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

/**
 * useFormPrefill — merge dữ liệu tự điền (từ MapLocationPicker) vào state form.
 *
 * - Chỉ áp dụng khi prefill._v đổi (mỗi lần xác nhận vị trí là 1 version mới).
 * - Chỉ ghi đè các key MÀ form đã có → không tạo field rác, form nào chỉ nhận
 *   field nó hỗ trợ (vd apt_floor chỉ cho căn hộ).
 * - Bỏ qua các key nội bộ (bắt đầu bằng "_") và giá trị null/undefined.
 */
export function useFormPrefill(prefill, setForm) {
  const lastVersion = React.useRef(null)
  React.useEffect(() => {
    if (!prefill || !prefill._v || prefill._v === lastVersion.current) return
    lastVersion.current = prefill._v
    setForm(prev => {
      const next = { ...prev }
      Object.entries(prefill).forEach(([key, value]) => {
        if (key.startsWith('_')) return
        if (value === null || value === undefined) return
        if (!(key in prev)) return
        next[key] = typeof value === 'boolean' ? value : String(value)
      })
      return next
    })
  }, [prefill, setForm])
}

/**
 * useIotAutoFill — TỰ PHÁT IoT khi người dùng nhập trường địa chỉ.
 *
 * Khi đổi province/district/ward/đường → gọi backend:
 *  - geocode tự điền tọa độ (nếu form chưa có) — "thông minh".
 *  - lấy IoT theo tầng (live khu vực → cùng phường → cùng quận → ước lượng)
 *    rồi tự điền các trường môi trường (noise/temp/humidity...).
 * Trả về trạng thái tầng IoT để hiển thị.
 */
export function useIotAutoFill(form, setForm) {
  const [status, setStatus] = React.useState(null)
  const province = form.province_city
  const district = form.district
  const ward = form.ward
  const street = form.street_or_project

  React.useEffect(() => {
    if (!district) return undefined
    let cancelled = false
    const timer = setTimeout(async () => {
      try {
        const { iotAutoFill } = await import('../../api')
        const data = await iotAutoFill({
          province_city: province,
          district,
          ward,
          street_or_project: street,
          lat: form.latitude,
          lng: form.longitude,
        })
        if (cancelled || !data) return
        setStatus(data)
        setForm(prev => {
          const next = { ...prev }
          const r = data.readings || {}
          const envMap = {
            noise_level: r.noise_level,
            temperature: r.temperature,
            humidity: r.humidity,
            noise_day_db: r.noise_level,
          }
          Object.entries(envMap).forEach(([k, v]) => {
            if (v != null && k in prev) next[k] = String(v)
          })
          // Geocode tọa độ: chỉ điền khi form chưa có tọa độ
          if (data.geocoded && data.latitude != null && !prev.latitude) {
            if ('latitude' in prev) next.latitude = String(data.latitude)
            if ('longitude' in prev) next.longitude = String(data.longitude)
            if ('gps_lat' in prev) next.gps_lat = String(data.latitude)
            if ('gps_lng' in prev) next.gps_lng = String(data.longitude)
          }
          return next
        })
      } catch (_) { /* không chặn form nếu lỗi */ }
    }, 450)
    return () => { cancelled = true; clearTimeout(timer) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [province, district])

  return status
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
