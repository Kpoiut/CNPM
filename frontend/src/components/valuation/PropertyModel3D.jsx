import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Canvas, useThree } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import { DoubleSide, EdgesGeometry, ExtrudeGeometry, Shape } from 'three'
import { icon } from '../../components/ui/icons'
import { buildPropertyMassing } from './propertyModelGeometry'

const VIEW_PRESETS = [
  { key: 'top', label: 'Mặt bằng', iconKey: 'layers' },
  { key: 'iso', label: 'Isometric', iconKey: 'cube' },
  { key: 'front', label: 'Mặt đứng', iconKey: 'building' },
]

function useExtrusion(points, depth) {
  const geometries = useMemo(() => {
    const shape = new Shape()
    points.forEach(([x, y], index) => (
      index ? shape.lineTo(x, y) : shape.moveTo(x, y)
    ))
    shape.closePath()
    const geometry = new ExtrudeGeometry(shape, { depth, bevelEnabled: false })
    geometry.rotateX(-Math.PI / 2)
    geometry.computeVertexNormals()
    return {
      geometry,
      edges: new EdgesGeometry(geometry, 24),
    }
  }, [points, depth])

  useEffect(() => () => {
    geometries.geometry.dispose()
    geometries.edges.dispose()
  }, [geometries])

  return geometries
}

function ExtrudedVolume({ points, height, positionY = 0, capColor, sideColor, edgeColor, opacity = 1 }) {
  const { geometry, edges } = useExtrusion(points, height)
  return (
    <group position-y={positionY}>
      <mesh geometry={geometry} castShadow receiveShadow>
        <meshStandardMaterial attach="material-0" color={capColor} roughness={0.82} metalness={0.04} side={DoubleSide} transparent={opacity < 1} opacity={opacity} />
        <meshStandardMaterial attach="material-1" color={sideColor} roughness={0.7} metalness={0.08} side={DoubleSide} transparent={opacity < 1} opacity={opacity} />
      </mesh>
      <lineSegments geometry={edges}>
        <lineBasicMaterial color={edgeColor} transparent opacity={0.82} />
      </lineSegments>
    </group>
  )
}

function ParcelSlab({ model }) {
  return (
    <ExtrudedVolume
      points={model.parcel}
      height={0.42}
      positionY={0.04}
      capColor="#155e75"
      sideColor="#0f3f4b"
      edgeColor="#22d3ee"
      opacity={model.floorCount ? 0.82 : 1}
    />
  )
}

function BuildingMassing({ model, isTower }) {
  const floorBlockHeight = model.floorHeightM * 0.9
  const { geometry, edges } = useExtrusion(model.buildingFootprint, floorBlockHeight)

  return (
    <group position-y={0.5}>
      {Array.from({ length: model.floorCount }, (_, index) => {
        const highlighted = index === model.highlightedFloorIndex
        const capColor = highlighted ? '#fbbf24' : index % 2 ? '#d9e3ec' : '#edf3f7'
        const sideColor = highlighted ? '#f59e0b' : index % 2 ? '#9fb0bf' : '#b8c6d2'
        return (
          <group key={index} position-y={index * model.floorHeightM}>
            <mesh geometry={geometry} castShadow receiveShadow>
              <meshStandardMaterial attach="material-0" color={capColor} roughness={0.58} metalness={isTower ? 0.18 : 0.06} side={DoubleSide} emissive={highlighted ? '#7c3d00' : '#000000'} emissiveIntensity={highlighted ? 0.28 : 0} />
              <meshStandardMaterial attach="material-1" color={sideColor} roughness={0.5} metalness={isTower ? 0.22 : 0.08} side={DoubleSide} emissive={highlighted ? '#78350f' : '#000000'} emissiveIntensity={highlighted ? 0.22 : 0} />
            </mesh>
            <lineSegments geometry={edges}>
              <lineBasicMaterial color={highlighted ? '#fff7cc' : '#456175'} transparent opacity={highlighted ? 1 : 0.7} />
            </lineSegments>
          </group>
        )
      })}
      <ExtrudedVolume
        points={model.buildingFootprint}
        height={0.3}
        positionY={model.buildingHeightM + 0.08}
        capColor={isTower ? '#5f7182' : '#334e5d'}
        sideColor="#263b47"
        edgeColor="#8dd8e8"
      />
    </group>
  )
}

function CameraRig({ model, preset, revision, controlsRef }) {
  const { camera, invalidate } = useThree()

  useEffect(() => {
    const targetY = Math.max(0.2, model.buildingHeightM * 0.38)
    const horizontal = Math.max(model.radius * 2.8, 12)
    const vertical = Math.max(model.buildingHeightM * 1.15, horizontal)
    const positions = {
      top: [0, Math.max(vertical * 1.35, model.radius * 5), 0.01],
      iso: [horizontal * 1.15, targetY + vertical * 0.72, horizontal * 1.15],
      front: [0, targetY + model.radius * 0.15, Math.max(horizontal * 1.6, model.buildingHeightM * 1.25)],
    }
    camera.up.set(0, preset === 'top' ? 0 : 1, preset === 'top' ? -1 : 0)
    camera.position.set(...positions[preset])
    camera.near = 0.1
    camera.far = Math.max(500, vertical * 14)
    camera.updateProjectionMatrix()
    controlsRef.current?.target.set(0, targetY, 0)
    controlsRef.current?.update()
    invalidate()
  }, [camera, controlsRef, invalidate, model.buildingHeightM, model.radius, preset, revision])

  return null
}

export default function PropertyModel3D({ meters = [], realShape = false, spec = {}, noun = 'Tài sản' }) {
  const [preset, setPreset] = useState('iso')
  const [cameraRevision, setCameraRevision] = useState(0)
  const [autoRotate, setAutoRotate] = useState(false)
  const controlsRef = useRef(null)
  const model = useMemo(
    () => buildPropertyMassing(meters, { ...spec, realShape }),
    [meters, realShape, spec],
  )
  const isTower = Boolean(spec.isTower)
  const shapeNote = realShape
    ? 'Polygon OSM được quy đổi sang mét; cần đối chiếu hồ sơ địa chính trước giao dịch.'
    : 'Footprint dựng từ mặt tiền, chiều sâu và diện tích đã nhập; không phải bản vẽ hoàn công.'

  return (
    <section className="property-model3d" data-testid="property-model-3d">
      <div className="property-model3d__toolbar" aria-label="Điều khiển góc nhìn 3D">
        <div className="property-model3d__view-switch" role="group" aria-label="Góc nhìn">
          {VIEW_PRESETS.map(view => (
            <button
              key={view.key}
              type="button"
              className={preset === view.key ? 'is-active' : ''}
              aria-pressed={preset === view.key}
              onClick={() => setPreset(view.key)}
            >
              {icon(view.iconKey, 13)}
              <span>{view.label}</span>
            </button>
          ))}
        </div>
        <button
          type="button"
          className={`property-model3d__icon-button${autoRotate ? ' is-active' : ''}`}
          aria-label={autoRotate ? 'Dừng tự xoay' : 'Bật tự xoay'}
          aria-pressed={autoRotate}
          title={autoRotate ? 'Dừng tự xoay' : 'Bật tự xoay'}
          onClick={() => setAutoRotate(value => !value)}
        >
          {icon(autoRotate ? 'pause' : 'rotateCw', 14, '', autoRotate ? '#ffffff' : undefined)}
        </button>
        <button
          type="button"
          className="property-model3d__icon-button"
          aria-label="Đặt lại góc nhìn"
          title="Đặt lại góc nhìn"
          onClick={() => {
            setPreset('iso')
            setCameraRevision(value => value + 1)
          }}
        >
          {icon('refreshCcw', 14)}
        </button>
      </div>

      <div className="property-model3d__canvas">
        <Canvas
          shadows
          dpr={[1, 1.5]}
          frameloop={autoRotate ? 'always' : 'demand'}
          camera={{ position: [18, 18, 18], fov: 42 }}
          gl={{ antialias: true, alpha: false, powerPreference: 'high-performance', preserveDrawingBuffer: true }}
        >
          <color attach="background" args={['#07131d']} />
          <fog attach="fog" args={['#07131d', model.radius * 8, model.radius * 24 + model.buildingHeightM]} />
          <ambientLight intensity={0.38} />
          <hemisphereLight args={['#b9e6f2', '#0b1f22', 0.9]} />
          <directionalLight
            position={[model.radius * 2.4, model.buildingHeightM + model.radius * 4, model.radius * 1.8]}
            intensity={1.4}
            castShadow
            shadow-mapSize-width={1024}
            shadow-mapSize-height={1024}
            shadow-camera-left={-model.radius * 3}
            shadow-camera-right={model.radius * 3}
            shadow-camera-top={model.radius * 3}
            shadow-camera-bottom={-model.radius * 3}
            shadow-camera-far={model.radius * 14 + model.buildingHeightM}
          />
          <ParcelSlab model={model} />
          {model.floorCount > 0 && <BuildingMassing model={model} isTower={isTower} />}
          <gridHelper args={[model.radius * 14, 32, '#315568', '#17303d']} position={[0, 0.015, 0]} />
          <mesh rotation-x={-Math.PI / 2} receiveShadow position={[0, -0.02, 0]}>
            <planeGeometry args={[model.radius * 18, model.radius * 18]} />
            <meshStandardMaterial color="#0a1b25" roughness={1} />
          </mesh>
          <CameraRig model={model} preset={preset} revision={cameraRevision} controlsRef={controlsRef} />
          <OrbitControls
            ref={controlsRef}
            enableDamping
            dampingFactor={0.08}
            autoRotate={autoRotate}
            autoRotateSpeed={0.7}
            maxPolarAngle={Math.PI / 2.02}
            minDistance={Math.max(4, model.radius * 0.75)}
            maxDistance={model.radius * 10 + model.buildingHeightM * 1.8 + 40}
          />
        </Canvas>

        <div className="property-model3d__source">
          {icon(realShape ? 'mapPinned' : 'ruler', 13, '', '#67e8f9')}
          <span>{model.sourceLabel}</span>
        </div>
        <div className="property-model3d__compass" aria-label="Hướng Bắc">
          <span>B</span>
          {icon('navigation', 14, '', '#fbbf24')}
        </div>
        <div className="property-model3d__gesture">
          {icon('mouse', 12, '', '#a7bdca')} Kéo xoay · cuộn zoom · chuột phải di chuyển
        </div>
      </div>

      <div className="property-model3d__facts">
        <div>
          <span>Footprint</span>
          <strong>{model.dimensions.widthM} × {model.dimensions.depthM} m</strong>
        </div>
        <div>
          <span>Quy mô</span>
          <strong>{model.floorCount ? `${model.floorCount} tầng` : `${model.dimensions.areaM2} m² đất`}</strong>
        </div>
        <div>
          <span>Đối tượng</span>
          <strong>{isTower && model.highlightedFloorIndex != null ? `${noun} · tầng ${model.highlightedFloorIndex + 1}` : noun}</strong>
        </div>
        <div className="property-model3d__provenance">
          <span>Mức chính xác</span>
          <strong>{realShape ? 'Theo polygon tham chiếu' : 'Massing ước lượng'}</strong>
        </div>
      </div>
      <p className="property-model3d__note">{shapeNote}</p>
    </section>
  )
}
