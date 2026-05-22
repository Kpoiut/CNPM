import React from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  PieChart, Pie, Cell,
  LineChart, Line,
} from 'recharts';
import { useState } from 'react';
import ChartWrapper from '../ui/ChartWrapper';

// Hardcoded values → centralized constants
export const TIER_COLORS = {
  E5: '#06d6a0',
  E4: '#00b4d8',
  E3: '#90e0ef',
  E2: '#f59e0b',
  E1: '#ef233c',
}

export const GRADE_COLORS = {
  A: '#06d6a0',
  B: '#0099ff',
  C: '#f59e0b',
  D: '#ef233c',
}

export const EVIDENCE_LABELS = {
  E5: 'E5 — Rất cao',
  E4: 'E4 — Cao',
  E3: 'E3 — Trung bình',
  E2: 'E2 — Thấp',
  E1: 'E1 — Rất thấp',
}

export const EVIDENCE_WEIGHTS = {
  E5: 3.0, E4: 2.0, E3: 1.0, E2: 0.5, E1: 0.15,
}

export const PRICE_RANGES = [
  { name: '< 1 tỷ',   min: 0,          max: 1e9 },
  { name: '1–2 tỷ',   min: 1e9,        max: 2e9 },
  { name: '2–3 tỷ',   min: 2e9,        max: 3e9 },
  { name: '3–5 tỷ',   min: 3e9,        max: 5e9 },
  { name: '5–10 tỷ',  min: 5e9,        max: 1e10 },
  { name: '> 10 tỷ',  min: 1e10,       max: Infinity },
]

export const PROPERTY_TYPE_COLORS = {
  house:      '#f59e0b',
  apartment:  '#3b82f6',
  land:       '#22c55e',
  townhouse:   '#8b5cf6',
  villa:      '#ec4899',
}

// fmtVnd — shared formatter
function fmtVnd(v) {
  if (!v) return '—';
  if (v >= 1e9) return `${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6) return `${(v / 1e6).toFixed(0)}M`;
  return `${(v / 1e3).toFixed(0)}K`;
}

/** Comparable price comparison bar chart */
export function ComparablePriceChart({ comparables }) {
  if (!comparables || comparables.length === 0) return null;
  const top6 = comparables.slice(0, 6).map((c, i) => ({
    id: `#${c.legacy_id || i + 1}`,
    ppm2: c.price_per_m2,
    tier: c.evidence_tier || 'E5',
  }));
  const avg = top6.reduce((s, d) => s + d.ppm2, 0) / top6.length;

  return (
    <div className="card">
      <div className="card-header">So sánh giá thực tế (VND/m2)</div>
      <ChartWrapper height={180}>
        <BarChart data={top6} margin={{ top: 4, right: 8, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="id" tick={{ fontSize: 11 }} />
          <YAxis tickFormatter={v => fmtVnd(v)} tick={{ fontSize: 10 }} />
          <Tooltip formatter={(v) => [`${fmtVnd(v)}/m2`, 'Gia/m2']} />
          <Bar dataKey="ppm2" radius={[3, 3, 0, 0]}>
            {top6.map((d) => (
              <Cell
                key={d.id}
                fill={TIER_COLORS[d.tier] || '#7c3aed'}
                fillOpacity={0.8}
              />
            ))}
          </Bar>
        </BarChart>
      </ChartWrapper>
      <div style={{ textAlign: 'center', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
        Trung bình: <strong>{fmtVnd(avg)}/m2</strong> | {top6.length} records | Danh sách gốc: top-6 comparable nhất
      </div>
    </div>
  );
}

/** Adjustment factor impact chart */
export function AdjustmentImpactChart({ ledger }) {
  if (!ledger || ledger.length === 0) return null;
  const sorted = ledger
    .filter(a => a.delta_pct !== 0)
    .sort((a, b) => Math.abs(b.delta_pct) - Math.abs(a.delta_pct))
    .slice(0, 10);

  const data = sorted.map(a => ({
    code: a.factor_code.length > 16 ? a.factor_code.slice(0, 15) + '…' : a.factor_code,
    fullCode: a.factor_code,
    delta: a.delta_pct,
    dir: a.direction,
    conf: a.confidence,
  }));

  if (data.length === 0) return null;

  return (
    <div className="card">
      <div className="card-header">Các yếu tố điều chỉnh (tác động lên giá)</div>
      <ChartWrapper height={200}>
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
          <XAxis type="number" tickFormatter={v => `${(v * 100).toFixed(1)}%`} tick={{ fontSize: 10 }} />
          <YAxis type="category" dataKey="code" tick={{ fontSize: 9 }} width={100} />
          <Tooltip formatter={(v) => [`${(v * 100).toFixed(2)}%`, 'Delta']} />
          <Bar dataKey="delta" radius={[0, 3, 3, 0]}>
            {data.map(d => (
              <Cell key={d.fullCode} fill={d.dir === 'POSITIVE' ? '#06d6a0' : '#ef233c'} fillOpacity={0.85} />
            ))}
          </Bar>
        </BarChart>
      </ChartWrapper>
      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textAlign: 'center' }}>
        Chênh lệch: {data.length} factors | Tăng: {data.filter(d => d.dir === 'POSITIVE').length} | Giảm: {data.filter(d => d.dir === 'NEGATIVE').length}
      </div>
    </div>
  );
}

/** Grade badge with fill animation */
export function GradeBadge({ grade }) {
  if (!grade) return null;
  const color = GRADE_COLORS[grade] || '#888';
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      width: 32, height: 32, borderRadius: '50%',
      background: color + '20', border: `2px solid ${color}`,
      color: color, fontWeight: 800, fontSize: '1rem',
      fontFamily: 'var(--font-display)',
    }}>
      {grade}
    </span>
  );
}

/** API truthfulness log entry */
export function ApiTruthfulnessBadge({ endpoint, duration, status }) {
  const ok = status >= 200 && status < 300;
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: '0.4rem',
      fontSize: '0.7rem', fontFamily: 'monospace',
      color: ok ? '#06d6a0' : '#ef233c',
    }}>
      <span>{ok ? 'ML' : 'ERR'}</span>
      <span style={{ opacity: 0.7 }}>{endpoint}</span>
      <span style={{ opacity: 0.5 }}>{duration}ms</span>
    </div>
  );
}
