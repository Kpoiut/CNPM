import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const predictionSource = await readFile(new URL('./Prediction.jsx', import.meta.url), 'utf8')
const dashboardSource = await readFile(new URL('./Dashboard.jsx', import.meta.url), 'utf8')
const visualizerSource = await readFile(new URL('../../components/valuation/PropertyVisualizer.jsx', import.meta.url), 'utf8')
const propertyModel3dSource = await readFile(new URL('../../components/valuation/PropertyModel3D.jsx', import.meta.url), 'utf8')
const uiAuditSource = await readFile(new URL('../../../scripts/capture-ui-baseline.mjs', import.meta.url), 'utf8')

test('trang dự đoán chỉ dùng một bộ điều hướng quy trình có trạng thái', () => {
  assert.doesNotMatch(predictionSource, />Luồng làm việc</)
  assert.match(predictionSource, /className="pp-step-stack"/)
  assert.match(predictionSource, /\['form', '01', 'Hồ sơ'\]/)
  assert.match(predictionSource, /\['pipeline', '04', 'Audit'\]/)
})

test('metric vận hành chỉ nằm ở dashboard admin và được làm mới từ API', () => {
  assert.doesNotMatch(predictionSource, /User workspace/)
  assert.doesNotMatch(predictionSource, /Cached target <200ms/)
  assert.doesNotMatch(predictionSource, /PostgreSQL\/PostGIS source/)
  assert.doesNotMatch(predictionSource, /Model đang phục vụ/)
  assert.match(dashboardSource, /dashboard\/stats/)
  assert.match(dashboardSource, /refetchInterval: 30_000/)
  assert.match(dashboardSource, /serving_model/)
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
