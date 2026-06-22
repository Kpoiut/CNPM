// novaBus — kênh chia sẻ ngữ cảnh trang hiện tại cho trợ lý Nova.
// Mỗi trang (Prediction, ResearchLab, ...) gọi setNovaContext({...}) để Nova
// "nhìn thấy" dữ liệu mảng đó (vd kết quả định giá, model đang chọn) và trả lời sâu hơn.

let _ctx = {}

/** Ghi đè/merge ngữ cảnh module hiện tại. Truyền null để xoá theo key. */
export function setNovaContext(partial = {}) {
  _ctx = { ...(_ctx || {}), ...partial }
}

/** Xoá toàn bộ ngữ cảnh (gọi khi rời trang / reset). */
export function clearNovaContext(keys) {
  if (!keys) { _ctx = {}; return }
  const next = { ...(_ctx || {}) }
  for (const k of keys) delete next[k]
  _ctx = next
}

/** Lấy snapshot ngữ cảnh hiện tại để đính vào payload chat. */
export function getNovaContext() {
  return _ctx || {}
}
