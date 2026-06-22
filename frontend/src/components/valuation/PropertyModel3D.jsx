import React, { useMemo } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import { DoubleSide, EdgesGeometry, ExtrudeGeometry, Shape } from 'three'
import { icon } from '../../components/ui/icons'

const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v))

function Massing({ meters, isLand, height }) {
  const { geo, edges } = useMemo(() => {
    const shape = new Shape()
    meters.forEach(([x, y], i) => (i ? shape.lineTo(x, y) : shape.moveTo(x, y)))
    shape.closePath()
    const g = new ExtrudeGeometry(shape, { depth: height, bevelEnabled: false })
    g.rotateX(-Math.PI / 2)
    g.computeVertexNormals()
    const e = new EdgesGeometry(g, 30)
    return { geo: g, edges: e }
  }, [meters, height])

  const capColor = isLand ? '#74c365' : '#c2ccd9'
  const sideColor = isLand ? '#8a6a45' : '#dde4ee'
  return (
    <group>
      <mesh geometry={geo} castShadow receiveShadow>
        <meshStandardMaterial attach="material-0" color={capColor} roughness={0.92} metalness={0.02} side={DoubleSide} />
        <meshStandardMaterial attach="material-1" color={sideColor} roughness={0.8} metalness={0.04} side={DoubleSide} />
      </mesh>
      <lineSegments geometry={edges}>
        <lineBasicMaterial color="#0ea5e9" linewidth={2} />
      </lineSegments>
    </group>
  )
}

export default function PropertyModel3D({ meters = [], realShape = false, spec = {} }) {
  const safeMeters = meters.length >= 3 ? meters : [[-4, -6], [4, -6], [4, 6], [-4, 6]]
  const r = useMemo(() => {
    const xs = safeMeters.map(p => p[0])
    const ys = safeMeters.map(p => p[1])
    return Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys), 6) / 2
  }, [safeMeters])
  const height = spec.isLand ? Math.max(1.4, r * 0.12) : clamp((spec.floors || 1) * 3.3, 3, 60)

  return (
    <div style={{ width: '100%', height: 480, borderRadius: 14, overflow: 'hidden', border: '1px solid var(--border)', position: 'relative', background: '#0b1a2b' }}>
      <Canvas shadows dpr={[1, 2]} camera={{ position: [r * 1.9, height + r * 1.5, r * 1.9], fov: 42 }}>
        <color attach="background" args={['#0b1a2b']} />
        <hemisphereLight args={['#bcd6ff', '#13202c', 0.75]} />
        <directionalLight
          position={[r * 2, r * 3 + height * 2, r * 1.5]} intensity={1.25} castShadow
          shadow-mapSize-width={1024} shadow-mapSize-height={1024}
          shadow-camera-left={-r * 3} shadow-camera-right={r * 3} shadow-camera-top={r * 3} shadow-camera-bottom={-r * 3} shadow-camera-far={r * 12 + 60} />
        <Massing meters={safeMeters} isLand={Boolean(spec.isLand)} height={height} />
        <gridHelper args={[r * 12, 30, '#274a66', '#163045']} position={[0, 0.01, 0]} />
        <mesh rotation-x={-Math.PI / 2} receiveShadow position={[0, 0, 0]}>
          <planeGeometry args={[r * 14, r * 14]} />
          <shadowMaterial opacity={0.32} />
        </mesh>
        <OrbitControls enableDamping dampingFactor={0.1} target={[0, height * 0.4, 0]} maxPolarAngle={Math.PI / 2.04} minDistance={r} maxDistance={r * 8 + 40} />
      </Canvas>
      <div style={{ position: 'absolute', top: 10, left: 12, display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: '0.7rem', color: '#cbd5e1', background: 'rgba(2,8,20,0.55)', padding: '3px 9px', borderRadius: 7 }}>
        {icon('ruler', 12)} {realShape ? 'Hình thửa thật (OSM)' : 'Khối ước lượng (mặt tiền x sâu)'}{spec.isLand ? ` · ${Math.round(spec.landArea || 0)} m²` : ` · ${spec.floors || 1} tầng`}
      </div>
      <div style={{ position: 'absolute', bottom: 10, left: 12, display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: '0.66rem', color: '#94a3b8' }}>
        {icon('mouse', 12)} Kéo xoay · cuộn để phóng to · chuột phải để di chuyển
      </div>
    </div>
  )
}
