import React, { useState } from 'react'
import { icon } from '../../components/ui/icons'

const API = '/api'

const EVIDENCE_TIER_CONFIG = {
  E5: { color: '#06d6a0', label: 'E5 — Rất cao', desc: 'Verified field-survey + evidence + traceable collector' },
  E4: { color: '#00b4d8', label: 'E4 — Cao', desc: 'Verified + strong source + independent check' },
  E3: { color: '#90e0ef', label: 'E3 — Trung bình', desc: 'Supported public + partial validation' },
  E2: { color: '#ffb703', label: 'E2 — Thấp', desc: 'Public listing + traceability' },
  E1: { color: '#ef233c', label: 'E1 — Rất thấp', desc: 'Low-evidence record' },
}

const STEP_CONFIG = {
  crawled:   { iconKey: 'search', color: '#7c3aed', label: 'CRAWLED' },
  parsed:    { iconKey: 'fileSearch', color: '#06b7ce', label: 'PARSED' },
  deduped:   { iconKey: 'copy', color: '#f59e0b', label: 'DEDUPED' },
  validated: { iconKey: 'checkCircle', color: '#06d6a0', label: 'VALIDATED' },
  enriched:  { iconKey: 'sparkles', color: '#8b5cf6', label: 'ENRICHED' },
  reviewed:  { iconKey: 'eye', color: '#3b82f6', label: 'REVIEWED' },
  verified:  { iconKey: 'shieldCheck', color: '#10b981', label: 'VERIFIED' },
  imported:  { iconKey: 'database', color: '#7c3aed', label: 'IMPORTED' },
}

const ACTOR_CONFIG = {
  'system:Scraper':    { color: '#ef4444', label: 'Scraper' },
  'system:Validator':  { color: '#f59e0b', label: 'Validator' },
  'system:DataCollector': { color: '#7c3aed', label: 'DataCollector' },
  'user:admin':        { color: '#3b82f6', label: 'Admin' },
  'user:reviewer':      { color: '#06b7ce', label: 'Reviewer' },
  'user:manual_entry':  { color: '#64748b', label: 'Manual' },
  'system:SeedDemo':   { color: '#a855f7', label: 'Demo Seed' },
}

function ProvenanceStepCard({ step, index, total }) {
  const cfg = STEP_CONFIG[step.step] || { iconKey: 'activity', color: '#64748b', label: step.step?.toUpperCase() }
  const actor = ACTOR_CONFIG[step.actor] || { color: '#94a3b8', label: step.actor }

  return (
    <>
      {index > 0 && (
        <div style={{
          display: 'flex', justifyContent: 'center', margin: '4px 0',
          color: 'var(--border-color)', fontSize: '0.7rem'
        }}>
          <span style={{ padding: '2px 8px', background: 'var(--surface-2)', borderRadius: '4px' }}>
            ↓ chain #{index + 1}
          </span>
        </div>
      )}
      <div style={{
        border: `1px solid ${cfg.color}30`,
        borderRadius: '12px',
        overflow: 'hidden',
        background: 'var(--surface-2)',
      }}>
        {/* Header */}
        <div style={{
          padding: '10px 16px',
          background: `${cfg.color}15`,
          borderBottom: `1px solid ${cfg.color}30`,
          display: 'flex', alignItems: 'center', gap: '8px'
        }}>
          <span style={{ color: cfg.color }}>{icon(cfg.iconKey, 18)}</span>
          <span style={{
            color: cfg.color, fontWeight: 700, fontSize: '0.75rem',
            letterSpacing: '0.05em'
          }}>STEP {index + 1}: {cfg.label}</span>
          <span style={{
            marginLeft: 'auto', fontSize: '0.7rem', color: 'var(--text-muted)'
          }}>
            {step.timestamp ? new Date(step.timestamp).toLocaleString('vi-VN') : '—'}
          </span>
        </div>

        {/* Content */}
        <div style={{ padding: '12px 16px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
          <InfoItem label="Actor" value={actor.label} />
          <InfoItem label="Source" value={step.source || '—'} />
          {step.verify_url && (
            <div style={{ gridColumn: '1/-1' }}>
              <a href={step.verify_url} target="_blank" rel="noopener noreferrer" style={{
                display: 'inline-flex', alignItems: 'center', gap: '4px',
                color: '#7c3aed', fontSize: '0.8rem', textDecoration: 'none'
              }}>
                Verify Online
              </a>
            </div>
          )}
          {step.input_hash && <InfoItem label="Input Hash" value={step.input_hash.slice(0, 24) + '...'} mono />}
          {step.output_hash && <InfoItem label="Output Hash" value={step.output_hash.slice(0, 24) + '...'} mono />}
          {step.metadata && (
            <div style={{ gridColumn: '1/-1' }}>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Metadata: </span>
              <code style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                {JSON.stringify(step.metadata, null, 0).slice(0, 120)}
              </code>
            </div>
          )}
        </div>
      </div>
    </>
  )
}

function InfoItem({ label, value, mono }) {
  return (
    <div>
      <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: '2px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</div>
      <div style={{
        fontSize: '0.8rem', color: 'var(--text-primary)',
        fontFamily: mono ? 'monospace' : undefined,
        wordBreak: 'break-all'
      }}>{value || '—'}</div>
    </div>
  )
}

function ProvenanceChainView({ chainData, property }) {
  const { verified, tampering_detected, total_steps, first_step, last_step, chain = [] } = chainData

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      {/* Verification Banner */}
      <div style={{
        padding: '12px 16px',
        borderRadius: '10px',
        display: 'flex', alignItems: 'center', gap: '12px',
        background: tampering_detected ? '#ef233c15' : '#06d6a015',
        border: `1px solid ${tampering_detected ? '#ef233c30' : '#06d6a030'}`,
      }}>
        <span style={{ color: tampering_detected ? '#ef233c' : '#06d6a0' }}>
          {icon(tampering_detected ? 'shieldAlert' : 'shieldCheck', 24)}
        </span>
        <div>
          <div style={{
            fontSize: '0.85rem', fontWeight: 700,
            color: tampering_detected ? '#ef233c' : '#06d6a0'
          }}>
            {tampering_detected ? 'TAMPERING DETECTED — Chain đã bị can thiệp!' : 'Chain INTEGRITY VERIFIED'}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            {total_steps} bước • First: {first_step ? new Date(first_step).toLocaleString('vi-VN') : '—'}
            • Last: {last_step ? new Date(last_step).toLocaleString('vi-VN') : '—'}
          </div>
        </div>
      </div>

      {/* Property Summary */}
      {property && (
        <div style={{
          padding: '12px 16px',
          background: 'var(--surface-2)',
          borderRadius: '10px',
          display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px'
        }}>
          <SummaryItem label="Loại" value={property.property_type} />
          <SummaryItem label="Quận" value={`${property.district}, ${property.province_city}`} />
          <SummaryItem label="Diện tích" value={property.area_m2 ? `${property.area_m2} m²` : '—'} />
          <SummaryItem label="Giá" value={property.price ? `${(property.price / 1e9).toFixed(1)} tỷ` : '—'} />
        </div>
      )}

      {/* Chain Steps */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Provenance Chain ({chain.length} bước)
        </div>
        {chain.map((step, i) => (
          <ProvenanceStepCard key={i} step={step} index={i} total={chain.length} />
        ))}
      </div>
    </div>
  )
}

function SummaryItem({ label, value }) {
  return (
    <div>
      <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: '2px', textTransform: 'uppercase' }}>{label}</div>
      <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: 600 }}>{value || '—'}</div>
    </div>
  )
}

export default function ProvenanceTracker() {
  const [propertyId, setPropertyId] = useState('')
  const [chainData, setChainData] = useState(null)
  const [property, setProperty] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function fetchProvenance(id) {
    if (!id) return
    setLoading(true)
    setError(null)
    setChainData(null)
    setProperty(null)

    try {
      const [chainRes, reportRes] = await Promise.all([
        fetch(`${API}/properties/${id}/provenance`),
        fetch(`${API}/properties/${id}/provenance/report`),
      ])

      if (!chainRes.ok) {
        const err = await chainRes.json().catch(() => ({}))
        throw new Error(err.detail || `HTTP ${chainRes.status}`)
      }

      const chainJson = await chainRes.json()
      const reportJson = await reportRes.ok ? await reportRes.json() : null

      setChainData(chainJson)
      setProperty(chainJson.property_summary)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  function handleSearch(e) {
    e.preventDefault()
    fetchProvenance(propertyId.trim())
  }

  function handleExport() {
    if (!chainData) return
    const blob = new Blob([JSON.stringify(chainData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `provenance-${propertyId}.json`
    a.click()
  }

  return (
    <div className="animate-fadeIn">
      {/* Page Header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '4px' }}>
          Provenance Tracker
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          Tra cứu nguồn gốc đầy đủ của bất kỳ bản ghi nào — hash chain, verify online
        </p>
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} style={{
        display: 'flex', gap: '8px', marginBottom: '24px',
        maxWidth: '500px'
      }}>
        <input
          type="number"
          value={propertyId}
          onChange={e => setPropertyId(e.target.value)}
          placeholder="Nhập Property ID..."
          style={{
            flex: 1, padding: '10px 14px', borderRadius: '8px',
            background: 'var(--surface-2)', border: '1px solid var(--border-color)',
            color: 'var(--text-primary)', fontSize: '0.9rem'
          }}
        />
        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? 'Đang tìm...' : 'Tra cứu'}
        </button>
      </form>

      {/* Error */}
      {error && (
        <div style={{
          padding: '12px 16px', borderRadius: '8px', marginBottom: '16px',
          background: '#ef233c15', border: '1px solid #ef233c30',
          color: '#ef233c', fontSize: '0.85rem'
        }}>
          {error}
        </div>
      )}

      {/* Results */}
      {chainData && !loading && (
        <div>
          {/* Actions */}
          <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
            <button className="btn btn-secondary" onClick={handleExport}>
              Export JSON
            </button>
            {chainData.verify_url && (
              <a href={chainData.verify_url} target="_blank" rel="noopener noreferrer" className="btn btn-secondary">
                Verify Online
              </a>
            )}
          </div>

          {/* Provenance Chain */}
          <ProvenanceChainView chainData={chainData} property={property} />
        </div>
      )}

      {/* Empty State */}
      {!chainData && !loading && !error && (
        <div className="empty-state">
          <div style={{ fontSize: '3rem', marginBottom: '12px' }}></div>
          <h3>Tra cứu Provenance</h3>
          <p>Nhập Property ID để xem provenance chain đầy đủ</p>
          <div style={{ marginTop: '16px', textAlign: 'left', maxWidth: '400px' }}>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
              <strong>Provenance Chain gồm:</strong><br/>
              • <strong>CRAWLED</strong> — Nguồn gốc từ web<br/>
              • <strong>PARSED</strong> — Parse HTML/JSON<br/>
              • <strong>VALIDATED</strong> — Kiểm tra schema<br/>
              • <strong>IMPORTED</strong> — Import vào DB<br/>
              • Mỗi bước có SHA256 hash để detect tampering
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
