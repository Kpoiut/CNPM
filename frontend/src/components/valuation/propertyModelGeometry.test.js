import test from 'node:test'
import assert from 'node:assert/strict'

import { buildPropertyMassing } from './propertyModelGeometry.js'

const RECTANGLE = [[-5, -10], [5, -10], [5, 10], [-5, 10]]

test('đất nền chỉ dựng parcel và không tạo khối công trình', () => {
  const model = buildPropertyMassing(RECTANGLE, {
    propertyType: 'land',
    isLand: true,
    landArea: 200,
    frontageM: 10,
    depthM: 20,
  })

  assert.equal(model.floorCount, 0)
  assert.deepEqual(model.buildingFootprint, [])
  assert.equal(model.sourceLabel, 'Hình thửa thật')
  assert.equal(model.dimensions.widthM, 10)
  assert.equal(model.dimensions.depthM, 20)
})

test('nhà phố tách footprint xây dựng và từng tầng trong giới hạn parcel', () => {
  const model = buildPropertyMassing(RECTANGLE, {
    propertyType: 'townhouse',
    floors: 4,
    frontageM: 10,
    depthM: 20,
  })

  assert.equal(model.floorCount, 4)
  assert.equal(model.buildingFootprint.length, 4)
  assert.ok(model.buildingFootprint.every(([x, y]) => Math.abs(x) < 5 && Math.abs(y) < 10))
  assert.equal(model.highlightedFloorIndex, null)
})

test('căn hộ làm nổi đúng tầng căn nhưng không vượt tổng số tầng', () => {
  const model = buildPropertyMassing(RECTANGLE, {
    propertyType: 'apartment',
    isTower: true,
    aptFloor: 15,
    towerFloors: 22,
  })

  assert.equal(model.floorCount, 22)
  assert.equal(model.highlightedFloorIndex, 14)
  assert.ok(model.buildingHeightM > 60)
})

test('polygon lỗi dùng footprint fallback ổn định và ghi rõ là ước lượng', () => {
  const model = buildPropertyMassing([[0, 0], [Number.NaN, 1]], {
    propertyType: 'house',
    floors: 2,
    frontageM: 8,
    depthM: 12,
  })

  assert.equal(model.parcel.length, 4)
  assert.equal(model.sourceLabel, 'Kích thước ước lượng')
  assert.equal(model.dimensions.widthM, 8)
  assert.equal(model.dimensions.depthM, 12)
})
