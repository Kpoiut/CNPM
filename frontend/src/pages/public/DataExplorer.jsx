import React, { useState, useEffect, useMemo, useCallback } from 'react'
import { icon } from '../../components/ui/icons'
import { PROPERTY_TYPES, VERIFICATION_STATUS, DATA_ORIGIN } from '../../constants/vnStrings'

const API = '/api'

const PROPERTY_ICONS = {
  house: 'house', apartment: 'apartment', land: 'land', townhouse: 'townhouse', villa: 'villa',
}

const EVIDENCE_CONFIG = {
  E5: { color: '#06d6a0', label: 'E5', desc: 'Rất cao' },
  E4: { color: '#00b4d8', label: 'E4', desc: 'Cao' },
  E3: { color: '#90e0ef', label: 'E3', desc: 'Trung bình' },
  E2: { color: '#ffb703', label: 'E2', desc: 'Thấp' },
  E1: { color: '#ef233c', label: 'E1', desc: 'Rất thấp' },
}

const STATUS_CONFIG = {
  verified:     { color: '#06d6a0', label: 'Đã xác minh' },
  pending:      { color: '#f59e0b', label: 'Chờ xác minh' },
  rejected:     { color: '#ef233c', label: 'Từ chối' },
  unverified:   { color: '#64748b', label: 'Chưa xác minh' },
}

function formatPrice(price) {
  if (!price) return '—'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(price)
}

// Mini provenance modal
function ProvenanceModal({ record, onClose }) {
  const [chain, setChain] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API}/properties/${record.id}/provenance`)
      .then(r => r.ok ? r.json() : null)
      .then(d => setChain(d))
      .catch(() => setChain(null))
      .finally(() => setLoading(false))
  }, [record.id])

  const STEP_COLORS = {
    crawled: '#7c3aed', parsed: '#06b7ce', deduped: '#f59e0b',
    validated: '#06d6a0', enriched: '#8b5cf6', reviewed: '#3b82f6',
    verified: '#10b981', imported: '#7c3aed',
  }

  return (
    <div className="data-modal-overlay" onClick={onClose}>
      <div className="data-modal-panel animate-scaleIn" onClick={e => e.stopPropagation()} style={{ maxWidth: 680 }}>
        <div className="data-modal-header">
          <div>
            <div className="eyebrow"> Provenance Chain</div>
            <h2>Bản ghi #{record.id}</h2>
          </div>
          <button className="modal-close" onClick={onClose}>Đóng</button>
        </div>
        <div style={{ padding: '1.5rem', maxHeight: '70vh', overflowY: 'auto' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '2rem' }}>
              <div className="spinner" style={{ margin: '0 auto' }}></div>
            </div>
          ) : chain ? (
            <>
              <div style={{
                padding: '10px 14px', borderRadius: 8, marginBottom: 16, fontSize: '0.82rem',
                background: chain.tampering_detected ? '#ef233c15' : '#06d6a015',
                border: `1px solid ${chain.tampering_detected ? '#ef233c30' : '#06d6a030'}`,
                color: chain.tampering_detected ? '#ef233c' : '#06d6a0',
                display: 'flex', alignItems: 'center', gap: 8,
              }}>
                <span style={{ fontSize: '1.1rem' }}>{chain.tampering_detected ? '' : ''}</span>
                <strong>{chain.tampering_detected ? 'TAMPERING DETECTED' : 'Chain INTEGRITY VERIFIED'}</strong>
                <span style={{ marginLeft: 'auto', color: 'var(--text-muted)' }}>
                  {chain.total_steps} bước
                </span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {(chain.chain || []).map((step, i) => {
                  const color = STEP_COLORS[step.step] || '#64748b'
                  return (
                    <React.Fragment key={i}>
                      {i > 0 && (
                        <div style={{ textAlign: 'center', color: 'var(--border-color)', fontSize: '0.65rem', padding: '2px 0' }}>
                          ↓ chain #{i + 1}
                        </div>
                      )}
                      <div style={{
                        border: `1px solid ${color}30`, borderRadius: 10, overflow: 'hidden',
                        background: 'var(--surface-2)',
                      }}>
                        <div style={{
                          padding: '8px 14px', background: `${color}15`,
                          borderBottom: `1px solid ${color}30`,
                          display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.75rem',
                        }}>
                          <span style={{ fontWeight: 700, color }}>{step.step?.toUpperCase()}</span>
                          <span style={{ color: 'var(--text-muted)' }}>· {step.actor}</span>
                          <span style={{ marginLeft: 'auto', color: 'var(--text-muted)', fontSize: '0.7rem' }}>
                            {step.timestamp ? new Date(step.timestamp).toLocaleString('vi-VN') : '—'}
                          </span>
                        </div>
                        <div style={{ padding: '10px 14px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: '0.78rem' }}>
                          {step.source && <div><span style={{ color: 'var(--text-muted)' }}>Source: </span><strong>{step.source}</strong></div>}
                          {step.verify_url && (
                            <div style={{ gridColumn: '1/-1' }}>
                              <a href={step.verify_url} target="_blank" rel="noopener noreferrer" style={{ color: '#7c3aed', fontSize: '0.78rem' }}>
                                 Verify Online
                              </a>
                            </div>
                          )}
                          {step.input_hash && <div><span style={{ color: 'var(--text-muted)' }}>Input: </span><code style={{ fontSize: '0.7rem' }}>{step.input_hash.slice(0, 20)}...</code></div>}
                          {step.output_hash && <div><span style={{ color: 'var(--text-muted)' }}>Output: </span><code style={{ fontSize: '0.7rem' }}>{step.output_hash.slice(0, 20)}...</code></div>}
                        </div>
                      </div>
                    </React.Fragment>
                  )
                })}
              </div>
              <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
                <button className="btn btn-sm btn-secondary" onClick={() => {
                  const blob = new Blob([JSON.stringify(chain, null, 2)], { type: 'application/json' })
                  const url = URL.createObjectURL(blob)
                  const a = document.createElement('a')
                  a.href = url; a.download = `provenance-${record.id}.json`; a.click()
                }}>
                   Export JSON
                </button>
              </div>
            </>
          ) : (
            <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
              Không có provenance chain cho bản ghi này
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Delete Confirmation Modal (Phase 4: CRUD support)
function DeleteModal({ record, onClose, onConfirm }) {
  if (!record) return null
  return (
    <div className="data-modal-overlay" onClick={onClose}>
      <div className="data-modal-panel animate-scaleIn" onClick={e => e.stopPropagation()} style={{ maxWidth: 420 }}>
        <div className="data-modal-header">
          <div>
            <div className="eyebrow" style={{ color: 'var(--danger)' }}> Xác nhận xóa</div>
            <h2>Xóa bản ghi</h2>
          </div>
          <button className="modal-close" onClick={onClose}>Đóng</button>
        </div>
        <div style={{ padding: '1.5rem' }}>
          <p style={{ marginBottom: '1rem', color: 'var(--text-secondary)' }}>
            Bạn có chắc muốn xóa bản ghi <strong>#{record.id}</strong>?
          </p>
          <div className="card" style={{ marginBottom: '1rem', padding: '0.875rem' }}>
            <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>
              {PROPERTY_TYPES[record.property_type] || record.property_type} — {record.district || '—'}
            </div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              {record.area_m2 ? `${record.area_m2} m²` : '—'} · {formatPrice(record.price)}
            </div>
          </div>
          <p style={{ fontSize: '0.8rem', color: 'var(--danger)', marginBottom: '1rem' }}>
            Hành động này không thể hoàn tác.
          </p>
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button className="btn btn-danger" onClick={onConfirm}>Xóa vĩnh viễn</button>
            <button className="btn btn-ghost" onClick={onClose}>Hủy</button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function DataExplorer() {
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedRecord, setSelectedRecord] = useState(null)
  const [showProvModal, setShowProvModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState(null)
  const [stats, setStats] = useState(null)
  const [page, setPage] = useState(1)
  const PAGE_SIZE = 20
  const [filters, setFilters] = useState({
    search: '', property_type: '', province_city: '',
    source_domain: '', data_origin: '', evidence_tier: '', status: '',
  })
  const [sortCol, setSortCol] = useState('id')
  const [sortDir, setSortDir] = useState('desc')

  useEffect(() => {
    fetch(`${API}/properties?limit=5000`).then(r => r.json()).then((props) => {
      const rows = Array.isArray(props) ? props : []
      setRecords(rows)
      const verified = rows.filter(r => r.verification_status === 'verified').length
      const selfCollected = rows.filter(r => r.data_origin_type === 'self_collected').length
      const withGps = rows.filter(r => r.latitude || r.longitude || r.gps_lat || r.gps_lng).length
      setStats({
        total_properties: rows.length,
        verified,
        with_gps_data: withGps,
        gps_coverage_rate: rows.length ? Math.round((withGps / rows.length) * 100) : 0,
        self_collected_ratio: rows.length ? Number(((selfCollected / rows.length) * 100).toFixed(2)) : 0,
        by_origin: { self_collected: selfCollected, public_collected: Math.max(0, rows.length - selfCollected) },
      })
    }).catch(() => setRecords([])).finally(() => setLoading(false))
  }, [])

  const provinces = useMemo(() =>
    [...new Set(records.map(r => r.province_city).filter(Boolean))].sort(), [records])

  const filtered = useMemo(() => {
    let r = records
    const s = filters.search.trim().toLowerCase()
    if (s) r = r.filter(x => [x.id, x.district, x.ward, x.street_or_project, x.province_city, x.source_name]
      .filter(Boolean).join(' ').toLowerCase().includes(s))
    if (filters.property_type) r = r.filter(x => x.property_type === filters.property_type)
    if (filters.province_city) r = r.filter(x => x.province_city === filters.province_city)
    if (filters.source_domain) r = r.filter(x => x.source_domain === filters.source_domain)
    if (filters.data_origin) r = r.filter(x => x.data_origin_type === filters.data_origin)
    if (filters.evidence_tier) r = r.filter(x => x.evidence_tier === filters.evidence_tier)
    if (filters.status) r = r.filter(x => x.verification_status === filters.status)
    return r
  }, [records, filters])

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      let av = a[sortCol], bv = b[sortCol]
      if (av == null) av = 0; if (bv == null) bv = 0
      if (typeof av === 'string') av = av.toLowerCase(); if (typeof bv === 'string') bv = bv.toLowerCase()
      if (av < bv) return sortDir === 'asc' ? -1 : 1
      if (av > bv) return sortDir === 'asc' ? 1 : -1
      return 0
    })
  }, [filtered, sortCol, sortDir])

  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE))
  const paginated = sorted.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  const handleSort = useCallback((col) => {
    if (sortCol === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortCol(col); setSortDir('asc') }
    setPage(1)
  }, [sortCol])

  const clearFilters = () => setFilters({ search: '', property_type: '', province_city: '', source_domain: '', data_origin: '', evidence_tier: '', status: '' })

  const viewProvenance = (rec) => { setSelectedRecord(rec); setShowProvModal(true) }
  const confirmDelete = (rec) => { setDeleteTarget(rec); setShowDeleteModal(true) }

  const executeDelete = async () => {
    if (!deleteTarget) return
    try {
      const res = await fetch(`${API}/admin/properties/${deleteTarget.id}`, { method: 'DELETE' })
      if (res.ok) {
        setRecords(rs => rs.filter(r => r.id !== deleteTarget.id))
      }
    } catch (err) { console.error('Delete failed:', err) }
    finally { setShowDeleteModal(false); setDeleteTarget(null) }
  }

  const handleCSVImport = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setImporting(true)
    setImportResult(null)
    const formData = new FormData()
    formData.append('file', file)
    try {
      const res = await fetch(`${API}/admin/properties/import`, { method: 'POST', body: formData })
      const data = await res.json()
      setImportResult(data)
      if (res.ok) { e.target.value = ''; setRecords(prev => [...prev, ...(data.imported || [])]) }
    } catch (err) { setImportResult({ error: err.message }) }
    finally { setImporting(false) }
  }

  const exportCSV = () => {
    const headers = ['ID', 'Type', 'Province', 'District', 'Area', 'Price', 'Source', 'Origin', 'Status', 'RQS']
    const rows = sorted.map(r => [
      r.id, r.property_type, r.province_city, r.district, r.area_m2,
      r.price, r.source_name || '', r.data_origin_type || '', r.verification_status || '', r.record_quality_score || '',
    ])
    const csv = [headers, ...rows].map(r => r.map(v => `"${v}"`).join(',')).join('\n')
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = 'data-explorer.csv'; a.click()
  }

  const SortIcon = ({ col }) => sortCol === col ? (sortDir === 'asc' ? ' ↑' : ' ↓') : ''

  return (
    <div>
      <div className="data-explorer-hero animate-fadeIn">
        <div className="data-explorer-hero-copy">
          <div className="data-explorer-eyebrow">Data explorer</div>
          <h1 className="data-explorer-title">Trung tâm quan sát bản ghi dữ liệu</h1>
          <p className="data-explorer-description">
            Toàn bộ bản ghi, provenance chain, evidence tier và RQS scoring trong một console duy nhất.
            Mọi thao tác import, export và lọc đều chạy trên dữ liệu thật.
          </p>
          <div className="data-explorer-points">
            <span className="data-explorer-chip">{records.length.toLocaleString('vi-VN')} bản ghi</span>
            <span className="data-explorer-chip">{filteredRecords.length.toLocaleString('vi-VN')} đang lọc</span>
            <span className="data-explorer-chip">{summary.traceReady.toLocaleString('vi-VN')} trace-ready</span>
            <span className="data-explorer-chip">{summary.withIot.toLocaleString('vi-VN')} có IoT</span>
          </div>
        </div>
        <div className="data-explorer-hero-actions">
          <div className="data-explorer-action-row">
            <label className="btn btn-sm" style={{ cursor: 'pointer' }}>
              {importing ? 'Đang nhập...' : 'Import CSV'}
              <input type="file" accept=".csv" onChange={handleCSVImport} style={{ display: 'none' }} disabled={importing} />
            </label>
            <button className="btn btn-sm" onClick={exportCSV}>Export CSV</button>
            <button className="btn btn-sm btn-ghost" onClick={clearFilters}>Đặt lại lọc</button>
          </div>
          <div className="data-explorer-hero-note">
            {icon('database', 16)}
            <span>Trace thật, provenance thật, bảng dữ liệu thật.</span>
          </div>
        </div>
      </div>

      {/* Summary */}
      <div className="data-explorer-summary-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 16 }}>
        {[
          { icon: '', label: 'Tổng bản ghi', value: records.length.toLocaleString('vi-VN'), color: '#7c3aed' },
          { icon: '', label: 'Đã lọc', value: filtered.length.toLocaleString('vi-VN'), color: '#06b7ce' },
          { icon: '', label: 'Đã xác minh', value: records.filter(r => r.verification_status === 'verified').length.toLocaleString('vi-VN'), color: '#06d6a0' },
          { icon: '', label: 'Self-Collected', value: records.filter(r => r.data_origin_type === 'self_collected').length.toLocaleString('vi-VN'), color: '#f59e0b' },
        ].map((s, i) => (
          <div key={i} className="card" style={{ textAlign: 'center', padding: '12px 10px' }}>
            <div style={{ fontSize: '1.5rem', marginBottom: 4 }}>{s.icon}</div>
            <div style={{ fontFamily: 'Space Grotesk, monospace', fontSize: '1.4rem', fontWeight: 700, color: s.color }}>
              {s.value}
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 2 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="card mb-4 data-explorer-filter-card" style={{ padding: '14px 16px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr 1fr 1fr', gap: 10, alignItems: 'end' }}>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" style={{ fontSize: '0.7rem' }}>Tìm kiếm</label>
            <input type="text" className="form-input" value={filters.search}
              placeholder="ID, địa điểm, nguồn..."
              onChange={e => { setFilters(f => ({ ...f, search: e.target.value })); setPage(1) }} />
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" style={{ fontSize: '0.7rem' }}>Loại BĐS</label>
            <select className="form-select" value={filters.property_type}
              onChange={e => { setFilters(f => ({ ...f, property_type: e.target.value })); setPage(1) }}>
              <option value="">Tất cả</option>
              {Object.entries(PROPERTY_TYPES).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" style={{ fontSize: '0.7rem' }}>Tỉnh/TP</label>
            <select className="form-select" value={filters.province_city}
              onChange={e => { setFilters(f => ({ ...f, province_city: e.target.value })); setPage(1) }}>
              <option value="">Tất cả</option>
              {provinces.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" style={{ fontSize: '0.7rem' }}>Nguồn gốc</label>
            <select className="form-select" value={filters.data_origin}
              onChange={e => { setFilters(f => ({ ...f, data_origin: e.target.value })); setPage(1) }}>
              <option value="">Tất cả</option>
              <option value="self_collected">Tự thu thập</option>
              <option value="public_collected">Nguồn công khai</option>
            </select>
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" style={{ fontSize: '0.7rem' }}>Evidence</label>
            <select className="form-select" value={filters.evidence_tier}
              onChange={e => { setFilters(f => ({ ...f, evidence_tier: e.target.value })); setPage(1) }}>
              <option value="">Tất cả</option>
              {Object.entries(EVIDENCE_CONFIG).map(([k, v]) => <option key={k} value={k}>{v.label} — {v.desc}</option>)}
            </select>
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" style={{ fontSize: '0.7rem' }}>Trạng thái</label>
            <select className="form-select" value={filters.status}
              onChange={e => { setFilters(f => ({ ...f, status: e.target.value })); setPage(1) }}>
              <option value="">Tất cả</option>
              {Object.entries(STATUS_CONFIG).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
            </select>
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" style={{ fontSize: '0.7rem' }}>RQS</label>
            <select className="form-select"
              onChange={e => {
                const v = e.target.value
                setFilters(f => ({ ...f, evidence_tier: v }))
                setPage(1)
              }}>
              <option value="">Tất cả</option>
              <option value="E1">E1 — Rất cao</option>
              <option value="E2">E2 — Cao</option>
              <option value="E3">E3 — Trung bình</option>
              <option value="E4">E4 — Thấp</option>
              <option value="E5">E5 — Rất thấp</option>
            </select>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="card data-explorer-table-card">
        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th onClick={() => handleSort('id')} style={{ cursor: 'pointer' }}>#ID<SortIcon col="id" /></th>
                <th>Loại</th>
                <th onClick={() => handleSort('district')} style={{ cursor: 'pointer' }}>Quận<SortIcon col="district" /></th>
                <th onClick={() => handleSort('area_m2')} style={{ cursor: 'pointer' }}>Diện tích<SortIcon col="area_m2" /></th>
                <th onClick={() => handleSort('price')} style={{ cursor: 'pointer' }}>Giá<SortIcon col="price" /></th>
                <th>Nguồn</th>
                <th>Origin</th>
                <th>RQS</th>
                <th>Evidence</th>
                <th onClick={() => handleSort('verification_status')} style={{ cursor: 'pointer' }}>Status<SortIcon col="verification_status" /></th>
                <th>Provenance</th>
                <th>Hành động</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={11} style={{ textAlign: 'center', padding: '2rem' }}>
                  <div className="spinner" style={{ margin: '0 auto' }}></div>
                </td></tr>
              ) : paginated.length === 0 ? (
                <tr><td colSpan={11} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                  Không có bản ghi phù hợp
                </td></tr>
              ) : paginated.map(rec => {
                const evCfg = EVIDENCE_CONFIG[rec.evidence_tier] || { color: '#64748b', label: '—', desc: '—' }
                const stCfg = STATUS_CONFIG[rec.verification_status] || { color: '#64748b', label: '—' }
                return (
                  <tr key={rec.id}>
                    <td className="font-semibold">#{rec.id}</td>
                    <td>
                      <span>{icon(PROPERTY_ICONS[rec.property_type] || 'house', 16)}</span>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{PROPERTY_TYPES[rec.property_type] || rec.property_type}</div>
                    </td>
                    <td>
                      <div style={{ fontWeight: 600, fontSize: '0.82rem' }}>{rec.district || '—'}</div>
                      <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>{rec.province_city}</div>
                    </td>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.82rem' }}>
                      {rec.area_m2 ? `${rec.area_m2} m²` : '—'}
                      {rec.price_per_m2 ? <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>{formatPrice(rec.price_per_m2)}/m²</div> : null}
                    </td>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.82rem', color: '#06d6a0', fontWeight: 600 }}>
                      {rec.price ? formatPrice(rec.price) : '—'}
                    </td>
                    <td>
                      <div style={{ fontSize: '0.75rem' }}>{rec.source_name || rec.source_domain || '—'}</div>
                      {rec.source_crawl_at && <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                        {new Date(rec.source_crawl_at).toLocaleDateString('vi-VN')}
                      </div>}
                    </td>
                    <td>
                      <span className={`badge ${rec.data_origin_type === 'self_collected' ? 'badge-success' : 'badge-primary'}`} style={{ fontSize: '0.7rem' }}>
                        {rec.data_origin_type === 'self_collected' ? 'Tự thu' : 'Công khai'}
                      </span>
                    </td>
                    <td>
                      <span style={{
                        fontFamily: 'monospace', fontWeight: 700, fontSize: '0.88rem',
                        color: rec.record_quality_score >= 7 ? '#06d6a0' : rec.record_quality_score >= 4 ? '#f59e0b' : '#ef233c',
                      }}>
                        {rec.record_quality_score != null ? rec.record_quality_score.toFixed(1) : '—'}
                      </span>
                    </td>
                    <td>
                      <span style={{
                        display: 'inline-block', padding: '2px 7px', borderRadius: 4,
                        background: evCfg.color + '20', color: evCfg.color,
                        border: `1px solid ${evCfg.color}50`,
                        fontWeight: 700, fontSize: '0.72rem',
                      }}>
                        {evCfg.label}
                      </span>
                    </td>
                    <td>
                      <span style={{ color: stCfg.color, fontSize: '0.78rem', fontWeight: 600 }}>{stCfg.label}</span>
                    </td>
                    <td>
                      <button className="btn btn-sm" style={{ fontSize: '0.72rem' }}
                        onClick={() => viewProvenance(rec)} title="Xem provenance chain">
                         Chain
                      </button>
                    </td>
                    <td>
                      <button className="btn btn-sm btn-ghost" style={{ fontSize: '0.72rem', color: 'var(--danger)' }}
                        onClick={() => confirmDelete(rec)} title="Xóa bản ghi">
                        {icon('trash2', 14)}
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', borderTop: '1px solid var(--border-color)' }}>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Trang {page}/{totalPages} · {filtered.length.toLocaleString('vi-VN')} bản ghi
          </span>
          <div style={{ display: 'flex', gap: 6 }}>
            <button className="btn btn-sm btn-ghost" disabled={page === 1} onClick={() => setPage(p => p - 1)}>← Trước</button>
            <button className="btn btn-sm btn-ghost" disabled={page === totalPages} onClick={() => setPage(p => p + 1)}>Sau →</button>
          </div>
        </div>
      </div>

      {showProvModal && selectedRecord && (
        <ProvenanceModal record={selectedRecord} onClose={() => { setShowProvModal(false); setSelectedRecord(null) }} />
      )}

      {/* Import Result Banner */}
      {importResult && (
        <div className={`card ${importResult.error ? 'animate-shake' : 'animate-scaleIn'}`} style={{
          marginTop: '1rem',
          background: importResult.error ? 'var(--danger-bg)' : 'var(--success-bg)',
          border: `1px solid ${importResult.error ? 'var(--danger-border)' : 'var(--success-border)'}`,
          padding: '0.75rem 1rem',
        }}>
          {importResult.error ? (
            <span>{icon('error', 16)} Import thất bại: {importResult.error}</span>
          ) : (
            <span> Đã nhập {importResult.imported_count || 0} bản ghi từ CSV</span>
          )}
          <button style={{ marginLeft: '1rem', fontSize: '0.75rem', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
            onClick={() => setImportResult(null)}>Đóng</button>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && deleteTarget && (
        <DeleteModal
          record={deleteTarget}
          onClose={() => { setShowDeleteModal(false); setDeleteTarget(null) }}
          onConfirm={executeDelete}
        />
      )}
    </div>
  )
}
