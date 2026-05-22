import React, { useEffect, useMemo, useState } from 'react'
import RecordDetailModal from '../../components/RecordDetailModal'
import { icon } from '../../components/ui/icons'
import { PROPERTY_TYPES, VERIFICATION_STATUS } from '../../constants/vnStrings'

const API_BASE = '/api'

const PROPERTY_ICONS = {
  house: 'house', apartment: 'apartment', land: 'land', townhouse: 'townhouse', villa: 'villa',
}

function formatPrice(price) {
  if (!price) return '—'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(price)
}

function RecordExplorer() {
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [selectedRecord, setSelectedRecord] = useState(null)
  const [showDetail, setShowDetail] = useState(false)
  const [overview, setOverview] = useState(null)
  const [filters, setFilters] = useState({
    search: '', data_origin: '', verification_status: '',
    property_type: '', province_city: '', source_name: '',
    has_iot: '', has_image: ''
  })
  const [pagination, setPagination] = useState({ page: 1, limit: 20 })

  useEffect(() => { fetchData() }, [])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [rRes, oRes] = await Promise.all([
        fetch(`${API_BASE}/properties?limit=5000`),
        fetch(`${API_BASE}/dataset/overview`)
      ])
      setRecords(await rRes.json())
      setOverview(await oRes.json())
    } catch (err) { console.error(err) }
    finally { setLoading(false) }
  }

  const filteredRecords = useMemo(() => {
    return records.filter(record => {
      const search = filters.search.trim().toLowerCase()
      const hasIot = record.noise_level != null || record.temperature != null || record.humidity != null
      const hasImage = Boolean(record.image_url)
      const traceReady = Boolean(record.source_url || record.data_origin_type === 'self_collected')
      if (search) {
        const haystack = [record.id, record.district, record.ward, record.street_or_project,
          record.province_city, record.source_name].filter(Boolean).join(' ').toLowerCase()
        if (!haystack.includes(search)) return false
      }
      if (filters.data_origin && record.data_origin_type !== filters.data_origin) return false
      if (filters.verification_status && record.verification_status !== filters.verification_status) return false
      if (filters.property_type && record.property_type !== filters.property_type) return false
      if (filters.province_city && record.province_city !== filters.province_city) return false
      if (filters.source_name && record.source_name !== filters.source_name) return false
      if (filters.has_iot === 'yes' && !hasIot) return false
      if (filters.has_iot === 'no' && hasIot) return false
      if (filters.has_image === 'yes' && !hasImage) return false
      if (filters.has_image === 'no' && hasImage) return false
      if (filters.trace_ready === 'yes' && !traceReady) return false
      return true
    })
  }, [records, filters])

  const totalPages = Math.max(1, Math.ceil(filteredRecords.length / pagination.limit))
  const paginatedRecords = useMemo(() => {
    const start = (pagination.page - 1) * pagination.limit
    return filteredRecords.slice(start, start + pagination.limit)
  }, [filteredRecords, pagination])

  useEffect(() => {
    if (pagination.page > totalPages) setPagination(prev => ({ ...prev, page: 1 }))
  }, [totalPages])

  const provinces = useMemo(() => [...new Set(records.map(r => r.province_city).filter(Boolean))].sort(), [records])
  const sources = useMemo(() => [...new Set(records.map(r => r.source_name).filter(Boolean))].sort(), [records])

  const summary = useMemo(() => ({
    verified: filteredRecords.filter(r => r.verification_status === 'verified').length,
    selfCollected: filteredRecords.filter(r => r.data_origin_type === 'self_collected').length,
    withIot: filteredRecords.filter(r => r.noise_level != null || r.temperature != null || r.humidity != null).length,
    traceReady: filteredRecords.filter(r => r.source_url || r.data_origin_type === 'self_collected').length,
  }), [filteredRecords])

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }))
    setPagination(prev => ({ ...prev, page: 1 }))
  }

  const clearFilters = () => {
    setFilters({ search: '', data_origin: '', verification_status: '', property_type: '',
      province_city: '', source_name: '', has_iot: '', has_image: '' })
    setPagination(prev => ({ ...prev, page: 1 }))
  }

  const viewDetail = async (record) => {
    setDetailLoading(true)
    try {
      const res = await fetch(`${API_BASE}/properties/${record.id}/detail`)
      setSelectedRecord(await res.json())
      setShowDetail(true)
    } catch (err) { console.error(err) }
    finally { setDetailLoading(false) }
  }

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div className="page-header-row">
          <div>
            <h1 className="page-title">Trung tâm quan sát bản ghi dữ liệu</h1>
            <p className="page-subtitle">Xem từng mẫu, lọc theo nguồn và mở chi tiết truy vết của mỗi record</p>
          </div>
          <span className="badge badge-primary">{records.length.toLocaleString()} bản ghi</span>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid-4 mb-6 stagger">
        {[
          { label: 'Đang hiển thị', value: filteredRecords.length.toLocaleString(), color: 'primary', icon: icon('table', 18) },
          { label: 'Đã xác minh', value: summary.verified.toLocaleString(), color: 'success', icon: icon('shieldCheck', 18) },
          { label: 'Có trace link', value: summary.traceReady.toLocaleString(), color: 'info', icon: icon('link', 18) },
          { label: 'Có dữ liệu IoT', value: summary.withIot.toLocaleString(), color: 'warning', icon: icon('satellite', 18) },
        ].map((s, i) => (
          <div key={i} className="stat-card animate-slideUp">
            <div className="stat-icon" style={{ background: `var(--${s.color === 'primary' ? 'primary-50' : s.color === 'success' ? 'success-bg' : s.color === 'info' ? 'info-bg' : 'warning-bg'})` }}>
              {s.icon}
            </div>
            <div className="stat-content">
              <div className="stat-value">{s.value}</div>
              <div className="stat-label">{s.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="card mb-6 animate-fadeIn">
        <div className="card-header"><span className="card-title">Bộ lọc dữ liệu</span></div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem', marginBottom: '1rem' }}>
          <div className="form-group">
            <label className="form-label">Tìm kiếm</label>
            <input type="text" className="form-input" value={filters.search}
              placeholder="ID, địa điểm, nguồn..."
              onChange={e => handleFilterChange('search', e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Loại BĐS</label>
            <select className="form-select" value={filters.property_type}
              onChange={e => handleFilterChange('property_type', e.target.value)}>
              <option value="">Tất cả</option>
              {Object.entries(PROPERTY_TYPES).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Tỉnh / TP</label>
            <select className="form-select" value={filters.province_city}
              onChange={e => handleFilterChange('province_city', e.target.value)}>
              <option value="">Tất cả</option>
              {provinces.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Nguồn gốc</label>
            <select className="form-select" value={filters.data_origin}
              onChange={e => handleFilterChange('data_origin', e.target.value)}>
              <option value="">Tất cả</option>
              <option value="self_collected">Tự thu thập</option>
              <option value="public_collected">Nguồn công khai</option>
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Trạng thái xác minh</label>
            <select className="form-select" value={filters.verification_status}
              onChange={e => handleFilterChange('verification_status', e.target.value)}>
              <option value="">Tất cả</option>
              {Object.entries(VERIFICATION_STATUS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Có IoT</label>
            <select className="form-select" value={filters.has_iot}
              onChange={e => handleFilterChange('has_iot', e.target.value)}>
              <option value="">Tất cả</option>
              <option value="yes">Có</option>
              <option value="no">Không</option>
            </select>
          </div>
        </div>
        <div className="flex justify-between items-center">
          <button className="btn btn-ghost btn-sm" onClick={clearFilters}>Đặt lại bộ lọc</button>
          <span className="text-sm text-muted">
            {loading ? 'Đang tải...' : `Trang ${pagination.page}/${totalPages} · ${filteredRecords.length.toLocaleString()} bản ghi`}
          </span>
        </div>
      </div>

      {/* Table */}
      <div className="card animate-fadeIn">
        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>#ID</th><th>Tài sản</th><th>Vị trí</th><th>Giá</th>
                <th>Nguồn</th><th>Trace</th><th>IoT</th><th>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={8} style={{ textAlign: 'center' }}>Đang tải dữ liệu...</td></tr>
              ) : paginatedRecords.length === 0 ? (
                <tr><td colSpan={8} style={{ textAlign: 'center' }}>Không có bản ghi phù hợp</td></tr>
              ) : paginatedRecords.map(record => {
                const hasIot = record.noise_level != null || record.temperature != null || record.humidity != null
                const traceReady = Boolean(record.source_url || record.data_origin_type === 'self_collected')
                return (
                  <tr key={record.id}>
                    <td className="font-semibold">#{record.id}</td>
                    <td>
                      <div className="flex items-center gap-2">
                        <span>{icon(PROPERTY_ICONS[record.property_type] || 'house', 16)}</span>
                        <div>
                          <div className="font-medium">{PROPERTY_TYPES[record.property_type] || record.property_type}</div>
                          <div className="text-xs text-muted">{record.area_m2} m²</div>
                        </div>
                      </div>
                    </td>
                    <td>
                      <div className="font-medium">{record.district}</div>
                      <div className="text-xs text-muted">{record.province_city}</div>
                    </td>
                    <td>
                      <div className="font-semibold text-success">{formatPrice(record.price)}</div>
                      <div className="text-xs text-muted">{formatPrice(record.price_per_m2)}/m²</div>
                    </td>
                    <td>
                      <div className="text-sm">{record.source_name || '—'}</div>
                      <div className="text-xs text-muted">
                        {record.data_origin_type === 'self_collected' ? 'Tự thu thập' : 'Công khai'}
                      </div>
                    </td>
                    <td>
                      <span className={`badge ${traceReady ? 'badge-success' : 'badge-warning'}`}>
                        {traceReady ? '✓ Sẵn sàng' : 'Thiếu'}
                      </span>
                      <div className="text-xs text-muted mt-1">
                        {VERIFICATION_STATUS[record.verification_status] || record.verification_status || '—'}
                      </div>
                    </td>
                    <td>
                      <span className={`badge ${hasIot ? 'badge-info' : 'badge-neutral'}`}>
                        {hasIot ? 'Có IoT' : 'Cơ bản'}
                      </span>
                    </td>
                    <td>
                      <button className="btn btn-ghost btn-sm" onClick={() => viewDetail(record)}>
                        Chi tiết
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex justify-between items-center mt-4">
            <button className="btn btn-ghost btn-sm" disabled={pagination.page === 1}
              onClick={() => setPagination(p => ({ ...p, page: p.page - 1 }))}>
              ← Trước
            </button>
            <span className="text-sm text-muted">Trang {pagination.page} / {totalPages}</span>
            <button className="btn btn-ghost btn-sm" disabled={pagination.page === totalPages}
              onClick={() => setPagination(p => ({ ...p, page: p.page + 1 }))}>
              Sau →
            </button>
          </div>
        )}
      </div>

      <RecordDetailModal open={showDetail} record={selectedRecord} onClose={() => setShowDetail(false)} />
    </div>
  )
}

export default RecordExplorer
