import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const predictionSource = await readFile(new URL('./Prediction.jsx', import.meta.url), 'utf8')
const visualizerSource = await readFile(new URL('../../components/valuation/PropertyVisualizer.jsx', import.meta.url), 'utf8')
const propertyModel3dSource = await readFile(new URL('../../components/valuation/PropertyModel3D.jsx', import.meta.url), 'utf8')
const uiAuditSource = await readFile(new URL('../../../scripts/capture-ui-baseline.mjs', import.meta.url), 'utf8')

test('trang dự đoán chỉ dùng một bộ điều hướng quy trình có trạng thái', () => {
  assert.doesNotMatch(predictionSource, />Luồng làm việc</)
  assert.match(predictionSource, /className="pp-step-stack"/)
  assert.match(predictionSource, /\['form', '01', 'Hồ sơ'\]/)
  assert.match(predictionSource, /\['pipeline', '04', 'Audit'\]/)
})

test('metric ML trên trang dự đoán luôn đến từ API và có model version', () => {
  assert.doesNotMatch(predictionSource, /Official MAPE 16\.09%/)
  assert.match(predictionSource, /\/api\/v2\/explain\/model-compare/)
  assert.match(predictionSource, /Model đang phục vụ/)
  assert.match(predictionSource, /Chu kỳ train mới nhất/)
})

test('mô hình 3D không nằm trong chunk chính của trang dự đoán', () => {
  assert.match(visualizerSource, /lazy\(\(\) => import\('\.\/PropertyModel3D'\)\)/)
  assert.doesNotMatch(visualizerSource, /from ['"]@react-three\/fiber['"]/)
  assert.doesNotMatch(visualizerSource, /from ['"]@react-three\/drei['"]/)
  assert.doesNotMatch(visualizerSource, /from ['"]three['"]/)
  assert.doesNotMatch(propertyModel3dSource, /import \* as THREE from ['"]three['"]/)
})

test('mô hình 3D phân biệt parcel, công trình, tầng và nguồn hình học', () => {
  assert.match(propertyModel3dSource, /function ParcelSlab/)
  assert.match(propertyModel3dSource, /function BuildingMassing/)
  assert.match(propertyModel3dSource, /highlightedFloorIndex/)
  assert.match(propertyModel3dSource, /data-testid="property-model-3d"/)
  assert.match(propertyModel3dSource, /Mặt bằng/)
  assert.match(propertyModel3dSource, /Isometric/)
  assert.match(propertyModel3dSource, /Mặt đứng/)
  assert.match(visualizerSource, /towerFloors/)
})

test('UI audit kiểm tra pixel canvas 3D và latency phản hồi thật', () => {
  assert.match(uiAuditSource, /readCanvasPixels/)
  assert.match(uiAuditSource, /prediction-model-3d/)
  assert.match(uiAuditSource, /loading_feedback_ms/)
  assert.match(uiAuditSource, /api_response_ms/)
  assert.match(uiAuditSource, /prediction-model-3d-apartment/)
  assert.match(uiAuditSource, /prediction-model-3d-townhouse/)
  assert.match(uiAuditSource, /\$\{variant\.captureSlug\}-mobile/)
})
