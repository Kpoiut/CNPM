import React from 'react';
import { icon } from '../ui/icons';

const GRADE_COLORS = {
  A: '#06d6a0',
  B: '#0099ff',
  C: '#f59e0b',
  D: '#ef233c',
};

/**
 * ScenarioComparison — 3 scenario cards side-by-side.
 * current | full_info | max_credibility
 */
export function ScenarioComparison({ current, fullInfo, maxCred }) {
  const scenarios = [
    {
      key: 'current',
      label: 'Hiện tại',
      sublabel: 'Dữ liệu thực tế',
      icon: 'flask',
      scenario: current,
    },
    {
      key: 'full',
      label: 'Nếu đủ thông tin',
      sublabel: 'What-if simulation',
      icon: 'star',
      scenario: fullInfo,
    },
    {
      key: 'max',
      label: 'Max Uy tín',
      sublabel: 'Hypothetical best-case',
      icon: 'star',
      scenario: maxCred,
    },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
      {scenarios.map(({ key, ...scenarioProps }) => (
        <ScenarioCard key={key} {...scenarioProps} />
      ))}
    </div>
  );
}

function ScenarioCard({ label, sublabel, icon: iconKey, scenario }) {
  if (!scenario) {
    return (
      <div className="card" style={{ opacity: 0.5 }}>
        <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
          Đang tải...
        </div>
      </div>
    );
  }

  const gradeColor = GRADE_COLORS[scenario.confidence_grade] || '#94a3b8';
  const intervalWidth = scenario.interval_width_pct ?? 0;
  const uncertaintyReduction = scenario.uncertainty_reduction_pct ?? 0;

  return (
    <div
      className="card"
      style={{
        borderColor: `${gradeColor}30`,
        borderTop: `3px solid ${gradeColor}`,
      }}
    >
      {/* Header */}
      <div style={{ marginBottom: '0.8rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.2rem' }}>
          <span style={{ color: gradeColor }}>{icon(iconKey, 16)}</span>
          <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>{label}</span>
        </div>
        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{sublabel}</div>
      </div>

      {/* FMV */}
      <div style={{ marginBottom: '0.8rem' }}>
        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Giá trị ước tính</div>
        <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>
          {fmtVnd(scenario.fmv_mid)}
        </div>
        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
          {fmtVnd(scenario.fmv_low)} – {fmtVnd(scenario.fmv_high)}
        </div>
      </div>

      {/* Range bar */}
      <div style={{ marginBottom: '0.8rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '0.3rem' }}>
          <span>Khoảng giá</span>
          <span>±{(intervalWidth / 2).toFixed(1)}%</span>
        </div>
        <div style={{
          height: '6px',
          background: 'var(--bg-secondary)',
          borderRadius: '3px',
          overflow: 'hidden',
          position: 'relative',
        }}>
          <div style={{
            position: 'absolute',
            left: `${50 - intervalWidth / 2}%`,
            width: `${intervalWidth}%`,
            height: '100%',
            background: gradeColor,
            opacity: 0.6,
            borderRadius: '3px',
          }} />
          <div style={{
            position: 'absolute',
            left: '50%',
            top: '-2px',
            width: '2px',
            height: '10px',
            background: gradeColor,
            transform: 'translateX(-50%)',
          }} />
        </div>
      </div>

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
        <StatBox label="Độ tin cậy">
          <span style={{ color: gradeColor, fontWeight: 700 }}>
            {scenario.confidence != null ? `${(scenario.confidence * 100).toFixed(0)}%` : '—'}
          </span>
        </StatBox>
        <StatBox label="Grade">
          <span style={{
            color: gradeColor,
            fontWeight: 700,
            fontSize: '1rem',
          }}>
            {scenario.confidence_grade || '—'}
          </span>
        </StatBox>
      </div>

      {/* Uncertainty reduction */}
      {uncertaintyReduction > 0 && (
        <div style={{
          marginTop: '0.6rem',
          padding: '0.3rem 0.6rem',
          background: `${gradeColor}15`,
          borderRadius: 'var(--radius)',
          fontSize: '0.72rem',
          color: gradeColor,
          textAlign: 'center',
        }}>
          Thu hẹp khoảng: ▼ {uncertaintyReduction.toFixed(0)}%
        </div>
      )}
    </div>
  );
}

function StatBox({ label, children }) {
  return (
    <div style={{
      background: 'var(--bg-secondary)',
      borderRadius: 'var(--radius)',
      padding: '0.4rem 0.6rem',
      textAlign: 'center',
    }}>
      <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: '0.1rem' }}>
        {label}
      </div>
      {children}
    </div>
  );
}

function fmtVnd(v) {
  if (!v) return '—';
  if (v >= 1e9) return `${(v / 1e9).toFixed(2)} tỷ`;
  if (v >= 1e6) return `${(v / 1e6).toFixed(0)}M`;
  return `${(v / 1e3).toFixed(0)}K`;
}
