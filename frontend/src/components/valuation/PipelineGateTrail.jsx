import React, { useState } from 'react';
import { icon } from '../ui/icons';

/**
 * PipelineGateTrail — Hiển thị audit trail 9 gates từ pipeline.
 *
 * Props:
 *   gates — [{gate_id, gate_name, status, duration_ms, details, warnings, block_reason}]
 *   finalStatus — PASS|WARN|BLOCK
 *   blockedAt — gate name nếu bị block
 *   completeness — {critical, important, optional, completeness_pct, completeness_grade}
 */

const GATE_ICONS = {
  INTAKE: 'clipboardCheck',
  NORMALIZE: 'slidersAlt',
  CLASSIFY: 'tag',
  LEGAL: 'shieldCheck',
  GEOMETRY: 'layoutGrid',
  ENVIRONMENT: 'tree',
  COMPARABLE: 'table',
  VALUATION: 'trendingUp',
  FIT: 'target',
};

const GATE_DESCRIPTIONS = {
  INTAKE: 'Kiểm tra trường bắt buộc và chất lượng dữ liệu người dùng nhập.',
  NORMALIZE: 'Chuẩn hóa đơn vị, mã hóa lựa chọn và làm sạch giá trị thiếu.',
  CLASSIFY: 'Nhận diện loại tài sản để chọn đúng nhánh mô hình và luật so sánh.',
  LEGAL: 'Đánh giá pháp lý, tranh chấp, thế chấp và rủi ro quy hoạch.',
  GEOMETRY: 'Đọc diện tích, mặt tiền, chiều sâu, tầng và hình dạng tài sản.',
  ENVIRONMENT: 'Đo ảnh hưởng ngập, tiếng ồn, công viên, sông và yếu tố môi trường.',
  COMPARABLE: 'Tìm các mẫu gần nhất theo khu vực, diện tích, loại tài sản và bậc nguồn.',
  VALUATION: 'Tổng hợp baseline, adjustment ledger và khoảng giá thị trường.',
  FIT: 'Tách lớp phù hợp cá nhân như phong thủy, lịch sử và nhu cầu người mua.',
};

const STATUS_STYLES = {
  PASS: { bg: 'var(--success-bg)', border: 'var(--success-border)', text: 'var(--success)', label: 'PASS' },
  WARN: { bg: 'var(--warning-bg)', border: 'var(--warning-border)', text: 'var(--warning)', label: 'WARN' },
  BLOCK: { bg: 'var(--danger-bg)', border: 'var(--danger-border)', text: 'var(--danger)', label: 'BLOCK' },
  SKIP: { bg: 'var(--bg-elevated)', border: 'var(--border)', text: 'var(--text-muted)', label: 'SKIP' },
};

const FIELD_LABELS = {
  asset_type: 'Loại tài sản',
  province_city: 'Tỉnh / TP',
  district: 'Quận / Huyện',
  area_m2: 'Diện tích',
  frontage_m: 'Mặt tiền',
  road_class: 'Hạng đường',
  ownership_type: 'Pháp lý',
  apt_floor: 'Tầng căn hộ',
  bedrooms: 'Phòng ngủ',
  floor_count: 'Số tầng',
}

function fieldLabel(name) {
  return FIELD_LABELS[name] || name
}

export default function PipelineGateTrail({ gates = [], finalStatus, blockedAt, completeness }) {
  const [expandedGate, setExpandedGate] = useState(null);

  if (!gates || gates.length === 0) return null;

  const statusStyle = STATUS_STYLES[finalStatus] || STATUS_STYLES.WARN;
  const counts = gates.reduce((acc, gate) => {
    acc[gate.status] = (acc[gate.status] || 0) + 1;
    return acc;
  }, {});
  const pct = Number(completeness?.completeness_pct || 0);
  const missingGroups = [
    { label: 'Bắt buộc', items: completeness?.missing_critical || [], tone: 'var(--danger)' },
    { label: 'Quan trọng', items: completeness?.missing_important || [], tone: 'var(--warning)' },
    { label: 'Bổ sung', items: completeness?.missing_optional || [], tone: 'var(--text-muted)' },
  ].filter(group => group.items.length > 0);

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0.75rem 1rem', borderBottom: '1px solid var(--border, #e5e7eb)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span>{icon('flask', 16)}</span>
          <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>Pipeline Audit Trail</span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted, #64748b)' }}>
            — {gates.length} gates
          </span>
        </div>
        <span style={{
          padding: '0.2rem 0.6rem', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 700,
          background: statusStyle.bg, border: `1px solid ${statusStyle.border}`, color: statusStyle.text,
        }}>
          {finalStatus}
        </span>
      </div>

      {/* Completeness meter */}
      {completeness && (
        <div style={{
          padding: '0.875rem 1rem', borderBottom: '1px solid var(--border, #e5e7eb)',
          display: 'flex', flexDirection: 'column', gap: '0.75rem',
        }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: '0.75rem' }}>
            {[
              { label: 'Critical', value: completeness.critical || '0/0', color: pct >= 40 ? 'var(--success)' : 'var(--danger)' },
              { label: 'Important', value: completeness.important || '0/0', color: 'var(--warning)' },
              { label: 'Optional', value: completeness.optional || '0/0', color: 'var(--info)' },
              { label: 'Gate status', value: `${counts.PASS || 0} pass / ${counts.WARN || 0} warn / ${counts.BLOCK || 0} block`, color: statusStyle.text },
            ].map(item => (
              <div key={item.label} style={{
                padding: '0.625rem 0.75rem',
                borderRadius: 8,
                border: '1px solid var(--border)',
                background: 'var(--bg-elevated)',
              }}>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginBottom: 4 }}>{item.label}</div>
                <div style={{ fontSize: '0.82rem', fontWeight: 800, color: item.color }}>{item.value}</div>
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', width: '100%' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Độ đầy đủ dữ liệu</span>
            <div style={{ flex: 1, height: 8, borderRadius: 4, background: 'var(--surface-2)', overflow: 'hidden' }}>
              <div style={{
                height: '100%', borderRadius: 4,
                width: `${Math.max(0, Math.min(100, pct))}%`,
                background: pct >= 70 ? 'var(--success)' : pct >= 40 ? 'var(--warning)' : 'var(--danger)',
                transition: 'width 0.5s ease',
              }} />
            </div>
            <span style={{ fontSize: '0.75rem', fontWeight: 800, color: pct >= 70 ? 'var(--success)' : pct >= 40 ? 'var(--warning)' : 'var(--danger)' }}>
              {pct.toFixed(0)}% (Grade {completeness.completeness_grade || 'D'})
            </span>
          </div>
          {missingGroups.length > 0 && (
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              {missingGroups.map(group => (
                <span key={group.label} style={{
                  display: 'inline-flex', alignItems: 'center', gap: 6,
                  padding: '0.25rem 0.5rem', borderRadius: 999,
                  background: 'var(--surface-2)', border: '1px solid var(--border)',
                  color: group.tone, fontSize: '0.72rem', fontWeight: 700,
                }}>
                  {group.label}: {group.items.map(fieldLabel).join(', ')}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Gate chain */}
      <div style={{ padding: '0.75rem 1rem' }}>
        <div style={{
          marginBottom: '0.75rem',
          padding: '0.7rem 0.85rem',
          borderRadius: 8,
          background: 'var(--surface-2)',
          border: '1px solid var(--border)',
          color: 'var(--text-secondary)',
          fontSize: '0.8rem',
          lineHeight: 1.55,
        }}>
          Pipeline này không chỉ báo pass/fail. Mỗi gate giải thích dữ liệu đang đi qua bước nào, bước đó ảnh hưởng đến giá hay độ tin cậy ra sao, và nếu có cảnh báo thì người dùng cần bổ sung trường nào để kết quả minh bạch hơn.
        </div>
        {gates.map((gate, i) => {
          const s = STATUS_STYLES[gate.status] || STATUS_STYLES.WARN;
          const isExpanded = expandedGate === gate.gate_id;
          const isLast = i === gates.length - 1;

          return (
            <div key={gate.gate_id}>
              <div
                onClick={() => setExpandedGate(isExpanded ? null : gate.gate_id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '0.75rem',
                  padding: '0.5rem 0.75rem', borderRadius: '8px', cursor: 'pointer',
                  background: isExpanded ? s.bg : 'transparent',
                  border: `1px solid ${isExpanded ? s.border : 'transparent'}`,
                  transition: 'all 0.2s ease',
                }}
              >
                {/* Icon */}
                <span style={{ fontSize: '1.1rem', width: '24px', textAlign: 'center' }}>
                  {icon(GATE_ICONS[gate.gate_name] || 'activity', 16)}
                </span>

                {/* Name */}
                <div style={{ minWidth: 210 }}>
                  <div style={{ fontWeight: 700, fontSize: '0.82rem' }}>{gate.gate_name}</div>
                  <div style={{ marginTop: 2, color: 'var(--text-muted)', fontSize: '0.7rem', lineHeight: 1.35 }}>
                    {GATE_DESCRIPTIONS[gate.gate_name] || 'Bước kiểm tra trong pipeline định giá.'}
                  </div>
                </div>

                {/* Status badge */}
                <span style={{
                  padding: '0.1rem 0.4rem', borderRadius: '3px', fontSize: '0.68rem', fontWeight: 700,
                  background: s.bg, border: `1px solid ${s.border}`, color: s.text,
                }}>
                  {gate.status}
                </span>

                {/* Duration */}
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted, #64748b)', marginLeft: 'auto' }}>
                  {gate.duration_ms?.toFixed(1)}ms
                </span>

                {/* Warning count */}
                {gate.warnings?.length > 0 && (
                  <span style={{
                    fontSize: '0.68rem', color: '#f59e0b', background: '#f59e0b15',
                    padding: '0.1rem 0.3rem', borderRadius: '3px',
                  }}>
                    {gate.warnings.length} warn
                  </span>
                )}

                {/* Expand arrow */}
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted, #64748b)', transform: isExpanded ? 'rotate(180deg)' : 'rotate(0)', transition: 'transform 0.2s' }}>
                  {icon('chevronDown', 14)}
                </span>
              </div>

              {/* Expanded details */}
              {isExpanded && (
                <div style={{
                  padding: '0.5rem 1rem 0.5rem 3rem', fontSize: '0.78rem',
                  color: 'var(--text-secondary, #475569)',
                }}>
                  {gate.block_reason && (
                    <div style={{ color: 'var(--danger)', fontWeight: 700, marginBottom: '0.35rem' }}>
                      BLOCK: {gate.block_reason}
                    </div>
                  )}
                  {gate.warnings?.map((w, wi) => (
                    <div key={wi} style={{ color: 'var(--warning)', marginBottom: '0.2rem', display: 'flex', gap: 6, alignItems: 'center' }}>
                      {icon('warning', 13)} <span>{w}</span>
                    </div>
                  ))}
                  {gate.details && Object.entries(gate.details)
                    .filter(([k]) => !k.startsWith('_'))
                    .map(([k, v]) => (
                      <div key={k} style={{ display: 'flex', gap: '0.5rem' }}>
                        <span style={{ color: 'var(--text-muted, #64748b)', minWidth: '120px' }}>{fieldLabel(k)}:</span>
                        <span style={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                          {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                        </span>
                      </div>
                    ))
                  }
                </div>
              )}

              {/* Connector line */}
              {!isLast && (
                <div style={{
                  width: '2px', height: '12px', marginLeft: '23px',
                  background: gate.status === 'BLOCK' ? '#ef233c40' : '#e5e7eb',
                }} />
              )}
            </div>
          );
        })}
      </div>

      {/* Blocked banner */}
      {blockedAt && (
        <div style={{
          padding: '0.5rem 1rem', background: '#ef233c10', borderTop: '1px solid #ef233c30',
          fontSize: '0.8rem', color: '#ef233c', fontWeight: 600,
          display: 'flex', alignItems: 'center', gap: '0.5rem',
        }}>
          <span>BLOCKED tại gate: {blockedAt}</span>
          <span style={{ marginLeft: 'auto', fontWeight: 400, fontSize: '0.75rem' }}>
            Các gate phía sau không được thực thi
          </span>
        </div>
      )}
    </div>
  );
}
