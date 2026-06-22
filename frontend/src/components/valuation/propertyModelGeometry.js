const clamp = (value, min, max) => Math.max(min, Math.min(max, value))

const finiteNumber = (value, fallback) => {
  const number = Number(value)
  return Number.isFinite(number) ? number : fallback
}

const roundDimension = value => Math.round(value * 10) / 10

function fallbackParcel(spec) {
  const width = Math.max(3, finiteNumber(spec.frontageM, 8))
  const depth = Math.max(3, finiteNumber(spec.depthM, 12))
  return [
    [-width / 2, -depth / 2],
    [width / 2, -depth / 2],
    [width / 2, depth / 2],
    [-width / 2, depth / 2],
  ]
}

function normalizeParcel(meters, spec) {
  const valid = Array.isArray(meters)
    && meters.length >= 3
    && meters.every(point => (
      Array.isArray(point)
      && point.length >= 2
      && Number.isFinite(Number(point[0]))
      && Number.isFinite(Number(point[1]))
    ))
  const source = valid
    ? meters.map(([x, y]) => [Number(x), Number(y)])
    : fallbackParcel(spec)
  const centerX = source.reduce((sum, [x]) => sum + x, 0) / source.length
  const centerY = source.reduce((sum, [, y]) => sum + y, 0) / source.length
  return {
    parcel: source.map(([x, y]) => [x - centerX, y - centerY]),
    realShape: valid,
  }
}

function scaleFootprint(parcel, ratio) {
  return parcel.map(([x, y]) => [x * ratio, y * ratio])
}

export function buildPropertyMassing(meters = [], spec = {}) {
  const normalized = normalizeParcel(meters, spec)
  const { parcel } = normalized
  const realShape = normalized.realShape && spec.realShape !== false
  const xs = parcel.map(([x]) => x)
  const ys = parcel.map(([, y]) => y)
  const widthM = Math.max(...xs) - Math.min(...xs)
  const depthM = Math.max(...ys) - Math.min(...ys)
  const isLand = Boolean(spec.isLand || spec.propertyType === 'land')
  const isTower = Boolean(spec.isTower || spec.propertyType === 'apartment')
  const aptFloor = Math.max(1, Math.round(finiteNumber(spec.aptFloor, 1)))
  const floorCount = isLand
    ? 0
    : isTower
      ? clamp(Math.round(finiteNumber(spec.towerFloors, Math.max(aptFloor + 5, 18))), 6, 48)
      : clamp(Math.round(finiteNumber(spec.floors, 1)), 1, 14)
  const occupancyRatio = {
    apartment: 0.68,
    townhouse: 0.86,
    villa: 0.58,
    house: 0.76,
  }[spec.propertyType] || 0.74
  const floorHeightM = isTower ? 3.1 : 3.3

  return {
    parcel,
    realShape,
    sourceLabel: realShape ? 'Hình thửa thật' : 'Kích thước ước lượng',
    buildingFootprint: isLand ? [] : scaleFootprint(parcel, occupancyRatio),
    floorCount,
    floorHeightM,
    buildingHeightM: floorCount * floorHeightM,
    highlightedFloorIndex: isTower ? clamp(aptFloor - 1, 0, floorCount - 1) : null,
    radius: Math.max(widthM, depthM, 6) / 2,
    dimensions: {
      widthM: roundDimension(widthM),
      depthM: roundDimension(depthM),
      areaM2: roundDimension(finiteNumber(spec.landArea || spec.area, widthM * depthM)),
    },
  }
}
