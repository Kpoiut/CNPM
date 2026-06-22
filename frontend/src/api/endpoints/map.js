/**
 * Map Intelligence API — location picker cho trang dự đoán.
 * Mọi request đi qua backend (proxy Nominatim + cache + IoT auto-profile).
 */
import { BASE, getJson } from '../client'

/** GET /api/map/search?q= — tìm địa chỉ/dự án */
export const mapSearch = (q, limit = 6) =>
  getJson(`${BASE}/map/search?q=${encodeURIComponent(q)}&limit=${limit}`)

/** GET /api/map/reverse?lat=&lng= — tọa độ → địa chỉ */
export const mapReverse = (lat, lng) =>
  getJson(`${BASE}/map/reverse?lat=${lat}&lng=${lng}`)

/** GET /api/map/location-context — gói đầy đủ: địa chỉ + BĐS gần + IoT + prefill */
export const mapLocationContext = ({ lat, lng, propertyType, limit = 6 }) => {
  const params = new URLSearchParams({ lat: String(lat), lng: String(lng), limit: String(limit) })
  if (propertyType) params.set('property_type', propertyType)
  return getJson(`${BASE}/map/location-context?${params.toString()}`)
}

/** GET /api/map/enrich — làm giàu từ OSM (tiện ích + thửa đất + đường) — gọi lazy */
export const mapEnrich = ({ lat, lng, propertyType }) => {
  const params = new URLSearchParams({ lat: String(lat), lng: String(lng) })
  if (propertyType) params.set('property_type', propertyType)
  return getJson(`${BASE}/map/enrich?${params.toString()}`)
}

/** GET /api/map/parcel — hình học lô đất + công trình lân cận để vẽ sơ đồ lô */
export const mapParcel = ({ lat, lng }) =>
  getJson(`${BASE}/map/parcel?lat=${lat}&lng=${lng}`)

/** GET /api/map/listings — BĐS rao bán thật tương đồng (Chợ Tốt), ảnh + giá + diện tích */
export const mapListings = ({ propertyType, provinceCity, district, areaM2, limit = 12 }) => {
  const params = new URLSearchParams({ property_type: propertyType, limit: String(limit) })
  if (provinceCity) params.set('province_city', provinceCity)
  if (district) params.set('district', district)
  if (areaM2) params.set('area_m2', String(areaM2))
  return getJson(`${BASE}/map/listings?${params.toString()}`)
}

/** GET /api/map/zoning — lớp quy hoạch sử dụng đất theo bbox (nạp theo khung nhìn) */
export const mapZoning = ({ minLat, minLng, maxLat, maxLng }) =>
  getJson(`${BASE}/map/zoning?min_lat=${minLat}&min_lng=${minLng}&max_lat=${maxLat}&max_lng=${maxLng}`)

/** GET /api/iot/area-signal — phát tín hiệu thu IoT từ mạng cảm biến khu vực */
export const iotAreaSignal = ({ lat, lng, radiusM = 1500 }) =>
  getJson(`${BASE}/iot/area-signal?lat=${lat}&lng=${lng}&radius_m=${radiusM}`)

/** GET /api/iot/auto-fill — nhập địa chỉ → geocode tọa độ + IoT theo tầng (live→phường→quận→ước lượng) */
export const iotAutoFill = ({ province_city, district, ward, street_or_project, lat, lng }) => {
  const params = new URLSearchParams()
  if (province_city) params.set('province_city', province_city)
  if (district) params.set('district', district)
  if (ward) params.set('ward', ward)
  if (street_or_project) params.set('street_or_project', street_or_project)
  if (lat) params.set('lat', String(lat))
  if (lng) params.set('lng', String(lng))
  return getJson(`${BASE}/iot/auto-fill?${params.toString()}`)
}
