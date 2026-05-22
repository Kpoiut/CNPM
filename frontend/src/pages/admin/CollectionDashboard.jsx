import React, { useState, useEffect, useCallback } from 'react'
import { icon as uiIcon } from '../../components/ui/icons'
import { authFetch } from '../../api/client'

const API = '/api'

const ALLOWED_DISTRICTS = [
  { province: 'Hà Nội', district: 'Quận Cầu Giấy', priority: 1, flow: 'high' },
  { province: 'Hà Nội', district: 'Quận Thanh Xuân', priority: 2, flow: 'high' },
  { province: 'Hà Nội', district: 'Quận Đống Đa', priority: 3, flow: 'medium' },
  { province: 'TP. Hồ Chí Minh', district: 'Quận 7', priority: 1, flow: 'high' },
  { province: 'TP. Hồ Chí Minh', district: 'Quận Bình Thạnh', priority: 2, flow: 'high' },
  { province: 'TP. Hồ Chí Minh', district: 'Quận Tân Bình', priority: 3, flow: 'medium' },
]

function StatCard({ icon, label, value, sub, color = '#7c3aed' }) {
  return (
    <div className="card" style={{ textAlign: 'center', padding: '20px 16px' }}>
      <div style={{ fontSize: '1.8rem', marginBottom: '6px' }}>{icon}</div>
      <div style={{ fontSize: '1.8rem', fontWeight: 700, color, fontFamily: 'Space Grotesk, monospace' }}>
        {value}
      </div>
      <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: 600, marginTop: '4px' }}>{label}</div>
      {sub && <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '2px' }}>{sub}</div>}
    </div>
  )
}

function SourceRow({ source }) {
  const statusColor = source.is_active ? '#06d6a0' : '#64748b'
  const statusLabel = source.is_active ? 'Active' : 'Inactive'
  const approvedColor = source.is_approved ? '#06d6a0' : '#ef233c'

  return (
    <tr>
      <td>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{source.type}</span>
      </td>
      <td>
        <span style={{ fontWeight: 600 }}>{source.name || source.domain}</span>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{source.domain}</div>
      </td>
      <td>
        <span style={{
          display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
          background: statusColor, marginRight: 6, verticalAlign: 'middle'
        }}></span>
        <span style={{ color: statusColor, fontSize: '0.8rem' }}>{statusLabel}</span>
      </td>
      <td>
        <span style={{
          display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
          background: approvedColor, marginRight: 6, verticalAlign: 'middle'
        }}></span>
        <span style={{ color: approvedColor, fontSize: '0.8rem' }}>
          {source.is_approved ? 'Approved' : 'Pending'}
        </span>
      </td>
      <td style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
        {source.total_records?.toLocaleString('vi-VN')}
      </td>
      <td style={{ fontFamily: 'monospace', fontSize: '0.85rem', color: '#06d6a0' }}>
        {source.successful_records?.toLocaleString('vi-VN')}
      </td>
      <td style={{ fontFamily: 'monospace', fontSize: '0.85rem', color: '#ef233c' }}>
        {source.failed_records?.toLocaleString('vi-VN')}
      </td>
      <td style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
        {source.last_run_at ? new Date(source.last_run_at).toLocaleString('vi-VN') : '—'}
      </td>
      <td>
        <button
          className="btn btn-sm"
          disabled={!source.is_active}
          onClick={() => alert('Collection start: ' + source.domain)}
          title="Bắt đầu thu thập"
        >
          ▶
        </button>
      </td>
    </tr>
  )
}

function DistrictProgress({ district, recordCount }) {
  const maxRecords = 500  // target per district
  const pct = Math.min(100, Math.round((recordCount / maxRecords) * 100))
  const flowColor = district.flow === 'high' ? '#06d6a0' : '#7c3aed'

  return (
    <div style={{ marginBottom: '8px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '3px' }}>
        <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>
          {district.district}
          <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginLeft: 4 }}>
            [{district.province}]
          </span>
        </span>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          {recordCount} records
        </span>
      </div>
      <div style={{
        height: 6, borderRadius: 3, background: 'var(--surface-2)',
        overflow: 'hidden'
      }}>
        <div style={{
          height: '100%', width: `${pct}%`, borderRadius: 3,
          background: pct > 80 ? flowColor : (pct > 20 ? flowColor + '80' : flowColor + '40'),
          transition: 'width 0.5s ease',
        }} />
      </div>
    </div>
  )
}

function asArray(value) {
  if (Array.isArray(value)) return value
  if (Array.isArray(value?.data)) return value.data
  if (Array.isArray(value?.records)) return value.records
  return []
}

function buildCollectionStatusFromProperties(properties, overview) {
  const rows = asArray(properties)
  const counts = overview?.counts || {}
  const total = rows.length || counts.total || 0
  const verified = rows.filter(p => p.verification_status === 'verified').length || counts.verified || 0
  const selfCollected = rows.filter(p => p.data_origin_type === 'self_collected').length || counts.self_collected || 0
  const withGps = rows.filter(p => p.latitude || p.longitude || p.gps_lat || p.gps_lng).length
  const withIot = rows.filter(p => p.noise_level != null || p.temperature != null || p.iot_device_id).length
  const byOrigin = rows.reduce((acc, p) => {
    const key = p.data_origin_type || 'unknown'
    acc[key] = (acc[key] || 0) + 1
    return acc
  }, {})
  const byStatus = rows.reduce((acc, p) => {
    const key = p.record_status || p.verification_status || 'raw'
    acc[key] = (acc[key] || 0) + 1
    return acc
  }, {})
  const byDistrict = rows.reduce((acc, p) => {
    const key = `${p.province_city || p.city || ''} - ${p.district || ''}`
    acc[key] = (acc[key] || 0) + 1
    return acc
  }, {})
  const sourceMap = rows.reduce((acc, p) => {
    const name = p.source_name || (p.data_origin_type === 'self_collected' ? 'Khảo sát thực địa' : 'Nguồn công khai')
    if (!acc[name]) {
      acc[name] = {
        type: p.data_origin_type === 'self_collected' ? 'field_survey' : 'website',
        name,
        domain: name,
        is_active: true,
        is_approved: true,
        total_records: 0,
        successful_records: 0,
        failed_records: 0,
        last_run_at: p.updated_at || p.created_at || '',
      }
    }
    acc[name].total_records += 1
    if (p.verification_status === 'verified') acc[name].successful_records += 1
    if (p.verification_status === 'rejected') acc[name].failed_records += 1
    acc[name].last_run_at = p.updated_at || p.created_at || acc[name].last_run_at
    return acc
  }, {})
  return {
    stats: {
      total_properties: total,
      verified,
      with_gps_data: withGps,
      gps_coverage_rate: total ? Math.round((withGps / total) * 100) : 0,
      self_collected_ratio: total ? Number(((selfCollected / total) * 100).toFixed(2)) : 0,
      by_origin: { self_collected: selfCollected, public_collected: Math.max(0, total - selfCollected), ...byOrigin },
      by_status: byStatus,
      by_allowed_district: byDistrict,
      iot_records: withIot,
    },
    sources: Object.values(sourceMap),
  }
}

export default function CollectionDashboard() {
  const [collectStatus, setCollectStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [collecting, setCollecting] = useState(false)
  const [error, setError] = useState(null)

  const fetchStatus = useCallback(async () => {
    try {
      const [propsRes, overviewRes] = await Promise.all([
        authFetch(`${API}/properties?limit=5000`),
        authFetch(`${API}/dataset/overview`),
      ])
      const [properties, overview] = await Promise.all([
        propsRes.json().catch(() => []),
        overviewRes.json().catch(() => ({})),
      ])
      if (!propsRes.ok) throw new Error(`HTTP ${propsRes.status}`)
      setCollectStatus(buildCollectionStatusFromProperties(properties, overview))
      setError(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchStatus() }, [fetchStatus])

  async function handleSeedDemo() {
    if (!confirm('Tạo 30 demo records/quận? Dùng để test ML pipeline.')) return
    setCollecting(true)
    try {
      const res = await authFetch(`${API}/admin/seed-demo?count=30`, { method: 'POST' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      await fetchStatus()
      alert('Đã tạo demo data!')
    } catch (e) {
      setError(e.message)
    } finally {
      setCollecting(false)
    }
  }

  async function handleCollect(source) {
    if (!confirm(`Bắt đầu thu thập từ ${source}?`)) return
    setCollecting(true)
    setError(null)
    try {
      const res = await authFetch(`${API}/collect/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source, max_pages: 5 }),
      })
      const data = await res.json()
      alert(`Hoàn thành: ${data.records_collected} records`)
      await fetchStatus()
    } catch (e) {
      setError(e.message)
    } finally {
      setCollecting(false)
    }
  }

  function handleExport() {
    if (!collectStatus || !collectStatus.sources) return
    const headers = ['Type', 'Name', 'Domain', 'Status', 'Approved', 'Total', 'Success', 'Failed', 'Last Run']
    const rows = collectStatus.sources.map(s => [
      s.type,
      s.name || s.domain,
      s.domain,
      s.is_active ? 'Active' : 'Inactive',
      s.is_approved ? 'Yes' : 'No',
      s.total_records || 0,
      s.successful_records || 0,
      s.failed_records || 0,
      s.last_run_at || ''
    ])
    const csvContent = [
      headers.join(','),
      ...rows.map(e => e.join(','))
    ].join('\n')
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `collection_sources_export_${new Date().toISOString().slice(0,10)}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  if (loading) return <div className="spinner" />

  const stats = collectStatus?.stats || {}
  const sources = collectStatus?.sources || []
  const byDistrict = stats.by_allowed_district || {}
  const hnDistricts = ALLOWED_DISTRICTS.filter(d => d.province === 'Hà Nội')
  const hcmDistricts = ALLOWED_DISTRICTS.filter(d => d.province === 'TP. Hồ Chí Minh')

  return (
    <div className="animate-fadeIn">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '4px' }}>
            Data Collection Dashboard
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            Trạng thái thu thập dữ liệu — scope: 2 thành phố, 6 quận
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-sm" onClick={fetchStatus} disabled={loading}>Refresh</button>
          <button className="btn btn-sm btn-secondary" onClick={handleExport} disabled={loading || !sources.length}>
            Export CSV
          </button>
          <button className="btn btn-sm" onClick={handleSeedDemo} disabled={collecting}>
            Seed Demo (30/quận)
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div style={{ padding: '12px 16px', borderRadius: '8px', marginBottom: '16px', background: '#ef233c15', border: '1px solid #ef233c30', color: '#ef233c', fontSize: '0.85rem' }}>
          Lỗi: {error}
        </div>
      )}

      {/* Stat Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '12px', marginBottom: '24px' }}>
        <StatCard icon={uiIcon('database', 24)} label="Tổng Records" value={stats.total_properties?.toLocaleString('vi-VN') || 0} color="#7c3aed" />
        <StatCard icon={uiIcon('shieldCheck', 24)} label="Đã xác minh" value={(stats.verified || 0).toLocaleString('vi-VN')} sub={`${stats.verified ? Math.round(stats.verified / stats.total_properties * 100) : 0}% đã xác minh`} color="#06d6a0" />
        <StatCard icon={uiIcon('mapPin', 24)} label="Có GPS" value={`${stats.gps_coverage_rate || 0}%`} sub={`${stats.with_gps_data || 0} records / ${(stats.total_properties || 0).toLocaleString()} total`} color="#f59e0b" />
        <StatCard icon={uiIcon('clipboardCheck', 24)} label="Self-Collected" value={`${stats.self_collected_ratio || 0}%`} sub={`${stats.by_origin?.['self_collected'] || 0} records · CVX target 3-5%`} color="#8b5cf6" />
      </div>

      {/* Collection Progress */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
        <div className="card">
          <h3 style={{ fontSize: '0.85rem', fontWeight: 700, marginBottom: '16px', color: '#7c3aed' }}>
            Hà Nội — Collection Progress
          </h3>
          {hnDistricts.map(d => (
            <DistrictProgress key={d.district} district={d} recordCount={byDistrict[`Hà Nội - ${d.district}`] || 0} />
          ))}
        </div>
        <div className="card">
          <h3 style={{ fontSize: '0.85rem', fontWeight: 700, marginBottom: '16px', color: '#06d6a0' }}>
            TP. Hồ Chí Minh — Collection Progress
          </h3>
          {hcmDistricts.map(d => (
            <DistrictProgress key={d.district} district={d} recordCount={byDistrict[`TP. Hồ Chí Minh - ${d.district}`] || 0} />
          ))}
        </div>
      </div>

      {/* Status by type */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
        <div className="card">
          <h3 style={{ fontSize: '0.8rem', fontWeight: 700, marginBottom: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Theo trạng thái</h3>
          {Object.entries(stats.by_status || {}).map(([status, count]) => (
            <div key={status} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border-color)', fontSize: '0.85rem' }}>
              <span style={{ color: 'var(--text-secondary)' }}>{status}</span>
              <span style={{ fontFamily: 'monospace', fontWeight: 600 }}>{count}</span>
            </div>
          ))}
        </div>
        <div className="card">
          <h3 style={{ fontSize: '0.8rem', fontWeight: 700, marginBottom: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Theo nguồn gốc</h3>
          {Object.entries(stats.by_origin || {}).map(([origin, count]) => (
            <div key={origin} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border-color)', fontSize: '0.85rem' }}>
              <span style={{ color: 'var(--text-secondary)' }}>{origin}</span>
              <span style={{ fontFamily: 'monospace', fontWeight: 600 }}>{count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Sources Table */}
      <div className="card">
        <h3 style={{ fontSize: '0.85rem', fontWeight: 700, marginBottom: '16px' }}>
          Approved Collection Sources
        </h3>
        {sources.length > 0 ? (
          <div className="table-wrapper">
            <table className="table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Name</th>
                  <th>Status</th>
                  <th>Approved</th>
                  <th>Total</th>
                  <th>Success</th>
                  <th>Failed</th>
                  <th>Last Run</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {sources.map(s => <SourceRow key={s.domain} source={s} />)}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
            Chưa có nguồn nào được thu thập
          </div>
        )}
      </div>

      {/* Scope info */}
      <div style={{ marginTop: '16px', padding: '12px 16px', background: '#7c3aed10', borderRadius: '8px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
        <strong style={{ color: '#7c3aed' }}>Scope giới hạn:</strong> Chỉ Hà Nội (3 quận) + TP.HCM (3 quận). Các nguồn phải được phê duyệt trong <code>approved_sources.py</code>. Thu thập từ nguồn không được phê duyệt sẽ bị từ chối.
      </div>
    </div>
  )
}
