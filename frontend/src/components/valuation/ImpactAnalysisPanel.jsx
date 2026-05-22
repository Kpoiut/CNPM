import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ContributionChart } from './ContributionChart';
import { FactorDetailModal } from './FactorDetailModal';
import { ScenarioComparison } from './ScenarioComparison';
import { fetchImpactAnalysis } from '../../api/endpoints/prediction';
import { icon } from '../ui/icons';
import { useAuth } from '../auth';

const GRADE_COLORS = {
  A: '#06d6a0', B: '#0099ff', C: '#f59e0b', D: '#ef233c',
};

function fmtVnd(v) {
  if (!v) return '—';
  if (v >= 1e9) return `${(v / 1e9).toFixed(2)} tỷ`;
  if (v >= 1e6) return `${(v / 1e6).toFixed(0)} triệu`;
  return `${(v / 1e3).toFixed(0)}K`;
}

function fmtPct(v) {
  if (v == null) return '—';
  return `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`;
}

/**
 * ImpactAnalysisPanel — Admin-only tab for "Tác động" analysis.
 *
 * Shows:
 * 1. Summary: FMV, baseline, delta, confidence, N_eff
 * 2. ContributionChart: horizontal bar chart of δ% per field
 * 3. MissingDataPanel: missing fields with confidence loss
 * 4. ScenarioComparison: current / full-info / max-credibility cards
 */
export function ImpactAnalysisPanel({ formData, runId }) {
  const [selectedFactor, setSelectedFactor] = useState(null);
  const { isAdmin } = useAuth();

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['impact-analysis', runId, formData?.district, formData?.area_m2],
    queryFn: () => fetchImpactAnalysis(
      { ...formData, run_id: runId },
      { adminSession: isAdmin }
    ),
    enabled: !!(isAdmin && formData?.asset_type && formData?.district),
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  if (isLoading) {
    return (
      <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        <div style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>
          {icon('flask', 32)}
        </div>
        <div>Đang phân tích tác động...</div>
        <div style={{ fontSize: '0.78rem', marginTop: '0.3rem' }}>
          Contextual Comparable-SHAP δ% Engine
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="card" style={{
        border: '1px solid #ef444440',
        background: '#ef233c08',
        padding: '1.5rem',
        color: '#ef233c',
      }}>
        <strong>Lỗi phân tích tác động</strong>
        <div style={{ fontSize: '0.82rem', marginTop: '0.3rem' }}>
          {error?.message || 'Không thể phân tích tác động. Vui lòng thử lại.'}
        </div>
      </div>
    );
  }

  if (!data) return null;

  const gradeColor = GRADE_COLORS[data.current_scenario?.confidence_grade] || '#94a3b8';
  const confidence = data.current_scenario?.confidence ?? 0;
  const topPositives = data.top_positive ?? [];
  const topNegatives = data.top_negative ?? [];
  const confidenceLoss = Number(data.total_confidence_loss || 0);
  const missingCount = data.missing_data?.length || 0;

  return (
    <div className="animate-fadeIn" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>

      {/* ── 1. Summary ── */}
      <div className="card">
        <div className="card-header">
          <span className="stat-icon primary">{icon('chart', 20)}</span>
          <span className="card-title">Tổng quan kết quả</span>
          <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{
              padding: '2px 12px',
              borderRadius: 'var(--radius-full)',
              background: `${gradeColor}20`,
              color: gradeColor,
              fontWeight: 700,
              fontSize: '0.85rem',
              border: `1px solid ${gradeColor}40`,
            }}>
              {data.current_scenario?.confidence_grade || '—'}
            </span>
          </span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '1rem', padding: '0 0 0.5rem' }}>
          <SummaryStat
            label="Giá dự đoán"
            value={fmtVnd(data.fair_market_value)}
            icon="house"
            highlight
          />
          <SummaryStat
            label="Baseline comparable"
            value={fmtVnd(data.baseline_value)}
            icon="table"
          />
          <SummaryStat
            label="Chênh lệch"
            value={fmtPct(data.delta_vs_baseline_pct)}
            icon="trending"
            color={data.delta_vs_baseline_pct >= 0 ? '#10b981' : '#ef4444'}
          />
          <SummaryStat
            label="Mức độ tin cậy dự đoán"
            value={confidence ? `${(confidence * 100).toFixed(0)}%` : '—'}
            icon="shield"
            color={gradeColor}
          />
          <SummaryStat
            label="Khoảng giá"
            value={`${fmtVnd(data.current_scenario?.fmv_low)} – ${fmtVnd(data.current_scenario?.fmv_high)}`}
            icon="range"
          />
          <SummaryStat
            label="N_eff (comparable)"
            value={data.n_eff?.toFixed(1) ?? '—'}
            icon="database"
            sub={`Level ${data.comparable_level} · ${data.n_comparables_used} records`}
          />
        </div>

        {/* Top positive / negative */}
        <div style={{ display: 'flex', gap: '1rem', marginTop: '0.8rem', flexWrap: 'wrap' }}>
          {topPositives.length > 0 && (
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
                Top tích cực
              </div>
              <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap' }}>
                {topPositives.map(l => (
                  <span key={l} style={{
                    padding: '2px 8px',
                    background: '#10b98115',
                    color: '#10b981',
                    borderRadius: 'var(--radius-full)',
                    fontSize: '0.72rem',
                    border: '1px solid #10b98130',
                  }}>
                    + {l}
                  </span>
                ))}
              </div>
            </div>
          )}
          {topNegatives.length > 0 && (
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
                Top tiêu cực
              </div>
              <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap' }}>
                {topNegatives.map(l => (
                  <span key={l} style={{
                    padding: '2px 8px',
                    background: '#ef444415',
                    color: '#ef4444',
                    borderRadius: 'var(--radius-full)',
                    fontSize: '0.72rem',
                    border: '1px solid #ef444430',
                  }}>
                    – {l}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Raw vs Display audit note */}
        {data.raw_total_pct !== data.display_total_pct && (
          <div style={{
            marginTop: '0.8rem',
            padding: '0.4rem 0.7rem',
            background: 'var(--bg-secondary)',
            borderRadius: 'var(--radius)',
            fontSize: '0.75rem',
            color: 'var(--text-muted)',
            display: 'flex',
            gap: '0.5rem',
            alignItems: 'center',
          }}>
            <span>{icon('info', 14)}</span>
            <span>
              Raw total: <strong>{fmtPct(data.raw_total_pct)}</strong>
              {' · '}Display total: <strong>{fmtPct(data.display_total_pct)}</strong>
              {' · '}Residual ghi nhận phần bị clamp và tương tác.
            </span>
          </div>
        )}
      </div>

      <div className="card" style={{ borderColor: 'var(--info-border)' }}>
        <div className="card-header">
          <span className="stat-icon info">{icon('shieldCheck', 20)}</span>
          <span className="card-title">Cơ chế mức độ tin cậy dự đoán</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '1rem', alignItems: 'center' }}>
          <div style={{ color: 'var(--text-secondary)', fontSize: '0.84rem', lineHeight: 1.65 }}>
            Mức độ tin cậy dự đoán không phải là độ tin cậy dữ liệu. Điểm này bị chặn mạnh bởi số lượng mẫu gần giống: mốc A cần khoảng <strong style={{ color: 'var(--text-primary)' }}>800 mẫu</strong>. Thiếu dữ liệu làm giảm minh bạch và làm khoảng giá rộng hơn, nhưng không thể tự kéo vài chục mẫu lên hạng xanh.
          </div>
          <div style={{ padding: '0.85rem', borderRadius: 8, border: '1px solid var(--border)', background: 'var(--surface-2)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              <span>Điểm gốc 100</span>
              <span>Trừ {confidenceLoss.toFixed(0)} điểm</span>
            </div>
            <div style={{ marginTop: '0.5rem', height: 10, borderRadius: 999, background: 'var(--border)', overflow: 'hidden' }}>
              <div style={{
                height: '100%',
                width: `${Math.max(0, Math.min(100, confidence * 100))}%`,
                background: confidence >= 0.75 ? 'var(--success)' : confidence >= 0.5 ? 'var(--warning)' : 'var(--danger)',
              }} />
            </div>
            <div style={{ marginTop: '0.65rem', display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem', textAlign: 'center' }}>
              {[
                ['Hiện tại', confidence ? `${(confidence * 100).toFixed(0)}%` : '—'],
                ['Thiếu trường', `${missingCount}`],
                ['N_eff', data.n_eff?.toFixed(1) ?? '—'],
              ].map(([label, value]) => (
                <div key={label}>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>{label}</div>
                  <div style={{ fontWeight: 800, color: 'var(--text-primary)' }}>{value}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── 2. Contribution Bar Chart ── */}
      <div className="card">
        <div className="card-header">
          <span className="stat-icon primary">{icon('chart', 20)}</span>
          <span className="card-title">Biểu đồ tác động (δ%)</span>
          <span style={{ marginLeft: 'auto', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            Display: clamp ±15% · Click bar để xem chi tiết
          </span>
        </div>
        <ContributionChart
          contributions={data.contributions ?? []}
          onSelect={(d) => setSelectedFactor(d)}
        />
      </div>

      {/* ── 3. Missing Data ── */}
      {data.missing_data && data.missing_data.length > 0 && (
        <div className="card">
          <div className="card-header">
            <span className="stat-icon warning">{icon('warning', 20)}</span>
            <span className="card-title">Thiếu dữ liệu</span>
            <span style={{
              marginLeft: 'auto',
              padding: '2px 10px',
              borderRadius: 'var(--radius-full)',
              background: '#f59e0b15',
              color: '#f59e0b',
              fontSize: '0.78rem',
              fontWeight: 600,
              border: '1px solid #f59e0b30',
            }}>
              -{confidenceLoss.toFixed(0)} điểm tin cậy
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            {data.missing_data.map((m) => (
              <MissingDataRow key={m.field} item={m} />
            ))}
          </div>
        </div>
      )}

      {/* ── 4. Scenarios ── */}
      <div className="card">
        <div className="card-header">
          <span className="stat-icon primary">{icon('star', 20)}</span>
          <span className="card-title">What-If Scenarios</span>
          <span style={{
            marginLeft: 'auto',
            fontSize: '0.72rem',
            color: 'var(--text-muted)',
            fontStyle: 'italic',
          }}>
            Simulation — không phải dự đoán
          </span>
        </div>
        <ScenarioComparison
          current={data.current_scenario}
          fullInfo={data.full_info_scenario}
          maxCred={data.max_credibility_scenario}
        />
      </div>

      {/* Factor detail modal */}
      {selectedFactor && (
        <FactorDetailModal
          factor={selectedFactor}
          onClose={() => setSelectedFactor(null)}
        />
      )}
    </div>
  );
}

function SummaryStat({ label, value, icon: iconKey, color, highlight, sub }) {
  return (
    <div style={{
      background: highlight ? 'var(--surface-1)' : 'var(--surface-2)',
      borderRadius: 'var(--radius)',
      padding: '0.6rem 0.8rem',
      border: highlight ? '1px solid var(--border)' : 'none',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', marginBottom: '0.2rem' }}>
        <span style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>{label}</span>
      </div>
      <div style={{
        fontSize: highlight ? '1.1rem' : '0.95rem',
        fontWeight: 700,
        color: color || 'var(--text-primary)',
      }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>{sub}</div>}
    </div>
  );
}

function MissingDataRow({ item }) {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '160px 1fr auto',
      gap: '0.75rem',
      alignItems: 'start',
      padding: '0.6rem 0.75rem',
      background: 'var(--surface-2)',
      borderRadius: 'var(--radius)',
      fontSize: '0.82rem',
    }}>
      <div>
        <div style={{ fontWeight: 600, marginBottom: '0.1rem' }}>{item.field_label}</div>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{item.field}</div>
      </div>
      <div>
        <div style={{ color: 'var(--text-secondary)', marginBottom: '0.15rem' }}>
          {item.recommendation}
        </div>
        {item.price_effect_pct !== 0 && (
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            Tác động giá: {fmtPct(item.price_effect_pct)}
          </div>
        )}
      </div>
      <div style={{ textAlign: 'right' }}>
        <div style={{
          fontWeight: 700,
          color: '#f59e0b',
          fontSize: '0.9rem',
        }}>
          -{item.confidence_penalty?.toFixed(0)} điểm
        </div>
        <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
          {fmtVnd(item.confidence_penalty_vnd)}
        </div>
      </div>
    </div>
  );
}
