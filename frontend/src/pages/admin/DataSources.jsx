import React, { useEffect, useMemo, useState } from 'react'
import { icon } from '../../components/ui/icons'
import RecordDetailModal from '../../components/RecordDetailModal'
import { authFetch } from '../../api/client'

const API_BASE = '/api'

function asArray(value) {
  if (Array.isArray(value)) return value
  if (Array.isArray(value?.data)) return value.data
  if (Array.isArray(value?.sources)) return value.sources
  if (Array.isArray(value?.records)) return value.records
  return []
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  try { return new Date(dateStr).toLocaleDateString('vi-VN') } catch { return dateStr }
}

function buildPageItems(totalPages, currentPage) {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1)
  }

  const pageSet = new Set([
    1, 2, 3, 4,
    totalPages - 3, totalPages - 2, totalPages - 1, totalPages,
    currentPage - 1, currentPage, currentPage + 1,
  ])

  const pages = [...pageSet]
    .filter(page => page >= 1 && page <= totalPages)
    .sort((a, b) => a - b)

  const items = []
  let previous = 0
  pages.forEach(page => {
    if (page - previous > 1) items.push('ellipsis-' + page)
    items.push(page)
    previous = page
  })
  return items
}

function buildSourcesFromProperties(records) {
  const rows = asArray(records)
  const sourceMap = rows.reduce((acc, row) => {
    const sourceName = row.source_name || (row.data_origin_type === 'self_collected' ? 'Khảo sát thực địa' : 'Nguồn công khai')
    if (!acc[sourceName]) {
      acc[sourceName] = {
        id: sourceName,
        source_name: sourceName,
        source_type: row.data_origin_type === 'self_collected' ? 'field_survey' : 'website',
        total_records: 0,
        verified_records: 0,
        trace_ready_records: 0,
        iot_records: 0,
        self_collected_records: 0,
        latest_seen_at: row.updated_at || row.created_at || row.collected_at || '',
      }
    }
    const source = acc[sourceName]
    source.total_records += 1
    if (row.verification_status === 'verified') source.verified_records += 1
    if (row.source_url || row.data_origin_type === 'self_collected') source.trace_ready_records += 1
    if (row.noise_level != null || row.temperature != null || row.iot_device_id) source.iot_records += 1
    if (row.data_origin_type === 'self_collected') source.self_collected_records += 1
    source.latest_seen_at = row.updated_at || row.created_at || row.collected_at || source.latest_seen_at
    return acc
  }, {})
  return Object.values(sourceMap).map(source => ({
    ...source,
    source_link_ready: source.total_records > 0 && source.trace_ready_records / source.total_records >= 0.7,
    verified_ratio: source.total_records ? Math.round((source.verified_records / source.total_records) * 100) : 0,
    trace_ratio: source.total_records ? Math.round((source.trace_ready_records / source.total_records) * 100) : 0,
  }))
}

function DataSources() {
  const [sources, setSources] = useState([])
  const [overview, setOverview] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedSource, setSelectedSource] = useState(null)
  const [sourcePage, setSourcePage] = useState(1)
  const [sourceRecords, setSourceRecords] = useState([])
  const [loadingRecords, setLoadingRecords] = useState(false)
  const [selectedRecordForDetail, setSelectedRecordForDetail] = useState(null)
  const [showDetail, setShowDetail] = useState(false)
  const SOURCE_PAGE_SIZE = 10

  useEffect(() => { fetchData() }, [])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [recordsRes, oRes] = await Promise.all([
        authFetch(`${API_BASE}/properties?limit=5000`),
        authFetch(`${API_BASE}/dataset/overview`),
      ])
      const [recordsData, oData] = await Promise.all([
        recordsRes.json().catch(() => []),
        oRes.json().catch(() => ({})),
      ])
      const normalizedSources = buildSourcesFromProperties(recordsData)
      setSources(normalizedSources)
      setOverview(oData)
      if (normalizedSources.length > 0) handleSourceClick(normalizedSources[0])
    } catch (_err) {
      setSources([])
      setOverview({})
    }
    finally { setLoading(false) }
  }

  const handleSourceClick = async (source) => {
    setSelectedSource(source)
    setSourcePage(1)
    setLoadingRecords(true)
    try {
      const res = await authFetch(`${API_BASE}/properties?limit=5000`)
      const allRecords = asArray(await res.json())
      setSourceRecords(allRecords.filter(r => r.source_name === source.source_name))
    } catch (_err) {
      setSourceRecords([])
    }
    finally { setLoadingRecords(false) }
  }

  const openRecordDetail = async (record) => {
    try {
      const res = await authFetch(`${API_BASE}/properties/${record.id}/detail`)
      setSelectedRecordForDetail(await res.json())
      setShowDetail(true)
    } catch (err) { console.error(err) }
  }

  const fieldSources = useMemo(() => sources.filter(s => s.source_type === 'field_survey'), [sources])
  const websiteSources = useMemo(() => sources.filter(s => s.source_type !== 'field_survey'), [sources])
  const totalSourcePages = Math.max(1, Math.ceil(sourceRecords.length / SOURCE_PAGE_SIZE))
  const paginatedSourceRecords = useMemo(() => {
    const start = (sourcePage - 1) * SOURCE_PAGE_SIZE
    return sourceRecords.slice(start, start + SOURCE_PAGE_SIZE)
  }, [sourceRecords, sourcePage])
  const sourcePageItems = useMemo(() => buildPageItems(totalSourcePages, sourcePage), [totalSourcePages, sourcePage])

  useEffect(() => {
    if (sourcePage > totalSourcePages) setSourcePage(1)
  }, [sourcePage, totalSourcePages])

  if (loading) return (
    <div className="loading-overlay">
      <div className="spinner"></div>
      <p>Đang tải nguồn dữ liệu...</p>
    </div>
  )

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div className="page-header-row">
          <div>
            <h1 className="page-title">Bản đồ nguồn dữ liệu</h1>
            <p className="page-subtitle">Theo dõi từng nguồn, mức độ xác minh, khả năng truy vết và mở thông tin chi tiết từng mẫu</p>
          </div>
          <div className="card stat-card" style={{ padding: '1rem 1.5rem' }}>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.75rem', fontWeight: 800, color: 'var(--primary)' }}>
              {overview?.counts?.total?.toLocaleString() || 0}
            </div>
            <div className="text-xs text-muted">tổng bản ghi được quản lý</div>
            <div className="text-xs text-muted mt-1">
              External: {overview?.counts?.external?.toLocaleString() || 0} · Self: {overview?.counts?.self_collected?.toLocaleString() || 0}
            </div>
          </div>
        </div>
      </div>

      {/* Compliance Grid */}
      <div className="grid-4 mb-6">
        {[
          { label: 'Tổng bộ dữ liệu', value: overview?.counts?.total?.toLocaleString() || 0, ok: overview?.standard_targets?.total_over_3000 },
          { label: 'Dữ liệu nguồn ngoài', value: overview?.counts?.external?.toLocaleString() || 0, ok: overview?.standard_targets?.external_over_3000 },
          { label: 'Tự thu thập', value: overview?.counts?.self_collected?.toLocaleString() || 0, ok: overview?.standard_targets?.self_collected_over_150 },
          { label: 'Link truy vết ngoài', value: `${overview?.ratios?.external_source_link_ratio || 0}%`, ok: overview?.standard_targets?.all_external_have_source_link },
        ].map((c, i) => (
          <div key={i} className="card animate-slideUp" style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
            <div className="text-xs text-muted font-semibold">{c.label}</div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', fontWeight: 800, color: c.ok ? 'var(--success)' : 'var(--warning)' }}>
              {c.value}
            </div>
            <div className={`badge ${c.ok ? 'badge-success' : 'badge-warning'}`}>
              {c.ok ? '✓ Đạt tiêu chuẩn' : 'Cần cải thiện'}
            </div>
          </div>
        ))}
      </div>

      <div className="grid-2" style={{ gridTemplateColumns: '1fr 1.5fr', gap: '1.5rem' }}>
        {/* Source Atlas */}
        <div className="card animate-fadeIn">
          <div className="card-header"><span className="card-title">Atlas nguồn dữ liệu</span></div>

          {websiteSources.length > 0 && (
            <>
              <div className="text-xs font-semibold text-muted mb-3" style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Nguồn bên ngoài ({websiteSources.length})
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1.5rem' }}>
                {websiteSources.map(source => (
                  <button key={source.id}
                    onClick={() => handleSourceClick(source)}
                    style={{
                      background: selectedSource?.id === source.id ? 'var(--primary-50)' : 'transparent',
                      border: `1px solid ${selectedSource?.id === source.id ? 'var(--primary)' : 'var(--border)'}`,
                      borderRadius: 'var(--radius)',
                      padding: '0.875rem',
                      cursor: 'pointer',
                      textAlign: 'left',
                      transition: 'all var(--transition)',
                      width: '100%',
                    }}>
                    <div className="flex justify-between items-start mb-2">
                      <strong style={{ color: 'var(--text-primary)', fontSize: '0.875rem' }}>{source.source_name}</strong>
                      <span className={`badge ${source.source_link_ready ? 'badge-success' : 'badge-warning'}`}>
                        {source.source_link_ready ? '✓ Trace ready' : 'Thiếu trace'}
                      </span>
                    </div>
                    <div className="flex gap-4">
                      {[{ l: 'Verified', v: `${source.verified_ratio}%` }, { l: 'Trace', v: `${source.trace_ratio}%` }, { l: 'IoT', v: source.iot_records }].map(m => (
                        <div key={m.l}>
                          <div className="text-xs text-muted">{m.l}</div>
                          <div className="text-sm font-semibold">{m.v}</div>
                        </div>
                      ))}
                    </div>
                  </button>
                ))}
              </div>
            </>
          )}

          {fieldSources.length > 0 && (
            <>
              <div className="text-xs font-semibold text-muted mb-3" style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Nguồn tự thu thập ({fieldSources.length})
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {fieldSources.map(source => (
                  <button key={source.id}
                    onClick={() => handleSourceClick(source)}
                    style={{
                      background: selectedSource?.id === source.id ? 'var(--success-bg)' : 'transparent',
                      border: `1px solid ${selectedSource?.id === source.id ? 'var(--success)' : 'var(--border)'}`,
                      borderRadius: 'var(--radius)',
                      padding: '0.875rem',
                      cursor: 'pointer',
                      textAlign: 'left',
                      transition: 'all var(--transition)',
                      width: '100%',
                    }}>
                    <div className="flex justify-between items-start mb-2">
                      <strong style={{ color: 'var(--text-primary)', fontSize: '0.875rem' }}>{source.source_name}</strong>
                      <span className="badge badge-success">Khảo sát thực địa</span>
                    </div>
                    <div className="flex gap-4">
                      {[{ l: 'Tổng', v: source.total_records?.toLocaleString() }, { l: 'Verified', v: source.verified_records }, { l: 'Trace', v: source.trace_ready_records }].map(m => (
                        <div key={m.l}>
                          <div className="text-xs text-muted">{m.l}</div>
                          <div className="text-sm font-semibold">{m.v}</div>
                        </div>
                      ))}
                    </div>
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Source Detail */}
        <div className="card animate-fadeIn">
          <div className="card-header"><span className="card-title">Chi tiết theo nguồn</span></div>

          {selectedSource ? (
            <>
              <div className="mb-4">
                <div className="text-xs font-semibold text-primary mb-1" style={{ textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  Nguồn đang xem
                </div>
                <h2 style={{ fontFamily: 'var(--font-display)', marginBottom: '0.5rem' }}>{selectedSource.source_name}</h2>
                <p className="text-sm text-muted">{selectedSource.notes || 'Không có ghi chú mở rộng.'}</p>
              </div>

              <div className="grid-3 mb-4">
                {[
                  { l: 'Tổng bản ghi', v: selectedSource.total_records?.toLocaleString() },
                  { l: 'Đã xác minh', v: selectedSource.verified_records },
                  { l: 'Trace ready', v: selectedSource.trace_ready_records },
                ].map(m => (
                  <div key={m.l} className="card" style={{ padding: '0.875rem', textAlign: 'center' }}>
                    <div className="text-xs text-muted">{m.l}</div>
                    <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', fontWeight: 800, color: 'var(--primary)' }}>{m.v}</div>
                  </div>
                ))}
              </div>

              <div className="flex gap-2 items-center mb-4">
                {selectedSource.source_url && (
                  <a className="btn btn-primary btn-sm" href={selectedSource.source_url} target="_blank" rel="noopener noreferrer">
                    Mở website nguồn
                  </a>
                )}
                <span className="text-xs text-muted">Cập nhật lần cuối: {formatDate(selectedSource.last_collected_at)}</span>
              </div>

              <div className="table-wrapper">
                <table className="table">
                  <thead>
                    <tr><th>#ID</th><th>Tài sản</th><th>Khu vực</th><th>Giá</th><th>Xác minh</th><th></th></tr>
                  </thead>
                  <tbody>
                    {loadingRecords ? (
                      <tr><td colSpan={6} style={{ textAlign: 'center' }}>Đang tải bản ghi từ nguồn này...</td></tr>
                    ) : sourceRecords.length === 0 ? (
                      <tr><td colSpan={6} style={{ textAlign: 'center' }}>Không có bản ghi</td></tr>
                    ) : (
                      paginatedSourceRecords.map(record => (
                        <tr key={record.id}>
                          <td className="font-semibold">#{record.id}</td>
                          <td>
                            <div className="font-medium">{record.property_type}</div>
                            <div className="text-xs text-muted">{record.area_m2} m²</div>
                          </td>
                          <td>{record.district}</td>
                          <td className="text-success font-semibold">
                            {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(record.price || 0)}
                          </td>
                          <td>
                            <span className={`badge ${record.verification_status === 'verified' ? 'badge-success' : record.verification_status === 'pending' ? 'badge-warning' : 'badge-neutral'}`}>
                              {record.verification_status}
                            </span>
                          </td>
                          <td>
                            <button className="btn btn-ghost btn-sm" onClick={() => openRecordDetail(record)}>Chi tiết</button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              {totalSourcePages > 1 && (
                <div className="app-pagination">
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    Trang {sourcePage} / {totalSourcePages} · {sourceRecords.length.toLocaleString('vi-VN')} bản ghi
                  </span>
                  <div className="app-pagination-pages">
                    {sourcePageItems.map(item => (
                      typeof item === 'number' ? (
                        <button
                          key={item}
                          type="button"
                          className={`app-pagination-page ${sourcePage === item ? 'active' : ''}`}
                          onClick={() => setSourcePage(item)}
                        >
                          {item}
                        </button>
                      ) : (
                        <span key={item} className="app-pagination-ellipsis">…</span>
                      )
                    ))}
                  </div>
                  <div style={{ display: 'flex', gap: '0.45rem', flexWrap: 'wrap' }}>
                    <button className="btn btn-ghost btn-sm" disabled={sourcePage <= 1} onClick={() => setSourcePage(p => Math.max(1, p - 1))}>
                      ← Trước
                    </button>
                    <button className="btn btn-ghost btn-sm" disabled={sourcePage >= totalSourcePages} onClick={() => setSourcePage(p => Math.min(totalSourcePages, p + 1))}>
                      Sau →
                    </button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">{icon('inbox', 40)}</div>
              <div className="empty-title">Chọn một nguồn để xem chi tiết</div>
            </div>
          )}
        </div>
      </div>

      <RecordDetailModal open={showDetail} record={selectedRecordForDetail} onClose={() => setShowDetail(false)} />
    </div>
  )
}

export default DataSources
