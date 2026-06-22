/**
 * Prediction API endpoints — dùng fetchWithRetry có timeout + retry
 */
import { BASE, V2_BASE, postJson, getJson } from '../client'

/** POST /api/v2/pipeline — Production 9-gate locked pipeline */
export const predictPipeline = (payload) => postJson(`${V2_BASE}/pipeline`, payload)

/** @deprecated Use predictPipeline instead */
export const predictV2 = (payload) => postJson(`${V2_BASE}/valuation`, payload)

/** @deprecated Legacy prediction endpoint */
export const predict = (payload) => postJson(`${BASE}/predict`, payload)

/** GET /api/v2/factors?layer=&asset_type= */
export const listFactors = (params = {}) => {
  const qs = new URLSearchParams(params).toString()
  const url = qs ? `${V2_BASE}/factors?${qs}` : `${V2_BASE}/factors`
  return getJson(url)
}

/** GET /api/v2/valuation/:id */
export const getValuation = (id) => getJson(`${V2_BASE}/valuation/${id}`)

/** GET /api/v2/valuation/runs — lịch sử định giá theo account */
export const listValuationRuns = (limit = 20) =>
  getJson(`${V2_BASE}/valuation/runs?limit=${encodeURIComponent(limit)}`)

/** POST /api/v2/valuation/:requestId/feedback — user gửi giá thật để admin duyệt training */
export const submitValuationFeedback = (requestId, payload) =>
  postJson(`${V2_BASE}/valuation/${encodeURIComponent(requestId)}/feedback`, payload)

/** POST /api/v2/impact-analysis — Contextual Comparable-SHAP δ% analysis (Admin-only) */
export const fetchImpactAnalysis = (payload, options = {}) =>
  postJson(`${V2_BASE}/impact-analysis`, payload, {
    redirectOn401: false,
    headers: options.adminSession ? { 'X-AVM-Admin-Session': 'active' } : {},
  })

/** POST /api/v2/sdev — Supply-Demand Equilibrium Valuation */
export const predictSDEV = (payload) => postJson(`${V2_BASE}/sdev`, {
  asset_type: payload.asset_type,
  province_city: payload.province_city,
  district: payload.district,
  area_m2: payload.area_m2,
  bedrooms: payload.bedrooms || 2,
})

// ============================================================
// Nova Voice Assistant endpoints — dùng fetchWithRetry
// ============================================================

/** POST /api/nova/chat */
export const novaChat = (message, context = {}) =>
  postJson(`${BASE}/nova/chat`, { message, context })

/** POST /api/nova/voice — Web Speech transcript, backend expects JSON text */
export const novaVoice = (text) => postJson(`${BASE}/nova/voice`, { text })

/** GET /api/nova/status */
export const getNovaStatus = () => getJson(`${BASE}/nova/status`)
