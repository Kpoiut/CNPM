/**
 * CommunityAdmin — Moderation Dashboard (Admin Only)
 * Full visibility: DTS scores, distribution rings, trust graph, coalition detection,
 * AI agent tags, block/lock/revoke controls.
 */
import React, { useState, useEffect, useCallback } from 'react';
import './CommunityAdmin.css';
import { useAuth } from '../../components/auth';
import { icon } from '../../components/ui/icons';

const API = '/api/community';
const tk = () => localStorage.getItem('avm-token');
const hdr = () => ({ 'Content-Type': 'application/json', Authorization: `Bearer ${tk()}` });

const TABS = [
  { id: 'all', label: 'Tất cả', iconKey: 'clipboard' },
  { id: 'discussion', label: 'Thảo luận', iconKey: 'chat' },
  { id: 'market_signals', label: 'Tín hiệu', iconKey: 'radio' },
  { id: 'verified_insights', label: 'Đã xác minh', iconKey: 'shieldCheck' },
  { id: 'under_dispute', label: 'Tranh chấp', iconKey: 'warning' },
];

const STATUS_MAP = {
  shadow_pending: { label: 'Shadow Pending', color: '#94a3b8', bg: 'rgba(148,163,184,.1)' },
  limited_live: { label: 'Ring 1-2', color: '#f59e0b', bg: 'rgba(245,158,11,.1)' },
  expanded_live: { label: 'Ring 3-4', color: '#10b981', bg: 'rgba(16,185,129,.1)' },
  disputed: { label: 'Disputed', color: '#ef4444', bg: 'rgba(239,68,68,.1)' },
  under_jury_review: { label: 'Jury Review', color: '#8b5cf6', bg: 'rgba(139,92,246,.1)' },
  resolved_true: { label: 'Verified ✓', color: '#10b981', bg: 'rgba(16,185,129,.1)' },
  resolved_false: { label: 'FALSE ✗', color: '#ef4444', bg: 'rgba(239,68,68,.1)' },
  resolved_misleading: { label: 'Misleading', color: '#f59e0b', bg: 'rgba(245,158,11,.1)' },
  training_eligible: { label: 'AI Ready', color: '#06b6d4', bg: 'rgba(6,182,212,.1)' },
  training_excluded: { label: 'AI Excluded', color: '#94a3b8', bg: 'rgba(148,163,184,.1)' },
  archived: { label: 'Archived', color: '#64748b', bg: 'rgba(100,116,139,.1)' },
};

const TYPE_ICONS = {
  opinion: 'chat', field_observation: 'map', data_fact: 'barChart3',
  legal_zoning: 'clipboard', forecast: 'trendingUp', recommendation: 'target',
};

export default function CommunityAdmin() {
  const { user } = useAuth();
  const [tab, setTab] = useState('all');
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  // Stats
  const [stats, setStats] = useState({ total: 0, pending: 0, disputed: 0, verified: 0, training: 0 });

  // Detail modal
  const [detail, setDetail] = useState(null);

  // Court modal
  const [courtTarget, setCourtTarget] = useState(null);

  const loadPosts = useCallback(async (t, p) => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/admin/feed?tab=${t}&page=${p}&limit=20`, { headers: hdr() });
      if (r.ok) {
        const d = await r.json();
        setPosts(d.claims);
        setTotal(d.total_count);
      }
    } catch (e) { console.error(e); }
    setLoading(false);
  }, []);

  const loadStats = useCallback(async () => {
    try {
      const tabs = ['all', 'under_dispute', 'verified_insights'];
      const results = await Promise.all(tabs.map(t => fetch(`${API}/feed?tab=${t}&page=1&limit=1`).then(r => r.json())));
      setStats({
        total: results[0]?.total_count || 0,
        disputed: results[1]?.total_count || 0,
        verified: results[2]?.total_count || 0,
        pending: 0,
        training: 0,
      });
    } catch {}
  }, []);

  useEffect(() => { loadPosts(tab, 1); loadStats(); }, [tab, loadPosts, loadStats]);

  const loadDetail = async (id) => {
    try {
      const r = await fetch(`${API}/claims/${id}`, { headers: hdr() });
      if (r.ok) setDetail(await r.json());
    } catch {}
  };

  // Admin actions
  const runCoalitionScan = async () => {
    await fetch(`${API}/admin/run-coalition-scan`, { method: 'POST', headers: hdr() });
    alert('Coalition scan started');
  };

  const processVerdicts = async () => {
    await fetch(`${API}/court/process-verdicts`, { method: 'POST', headers: hdr() });
    alert('Verdicts processed');
    loadPosts(tab, page);
  };

  const openCourt = async (claimId) => {
    await fetch(`${API}/claims/${claimId}/court`, { method: 'POST', headers: hdr() });
    setCourtTarget(null);
    loadPosts(tab, page);
  };

  const getStatus = (s) => STATUS_MAP[s] || { label: s, color: '#94a3b8', bg: 'rgba(148,163,184,.1)' };
  const pages = Math.ceil(total / 20);

  return (
    <div className="ca">
      {/* ── HEADER ── */}
      <div className="ca-header">
        <div className="ca-header-left">
          <h1><span>{icon('shieldCheck', 24)}</span> Moderation Center</h1>
          <p>Giám sát & kiểm duyệt cộng đồng BĐS</p>
        </div>
        <div className="ca-header-actions">
          <button className="ca-btn ca-btn--accent" onClick={runCoalitionScan}>{icon('search', 14)} Coalition Scan</button>
          <button className="ca-btn ca-btn--purple" onClick={processVerdicts}>{icon('scale', 14)} Process Verdicts</button>
        </div>
      </div>

      {/* ── STATS ── */}
      <div className="ca-stats">
        <div className="ca-stat"><div className="ca-stat-icon" style={{background:'rgba(124,58,237,.1)',color:'#a78bfa'}}>📊</div><div><div className="ca-stat-val">{stats.total}</div><div className="ca-stat-label">Tổng bài đăng</div></div></div>
        <div className="ca-stat"><div className="ca-stat-icon" style={{background:'rgba(239,68,68,.1)',color:'#ef4444'}}>{icon('warning', 18)}</div><div><div className="ca-stat-val">{stats.disputed}</div><div className="ca-stat-label">Đang tranh chấp</div></div></div>
        <div className="ca-stat"><div className="ca-stat-icon" style={{background:'rgba(16,185,129,.1)',color:'#10b981'}}>{icon('shieldCheck', 18)}</div><div><div className="ca-stat-val">{stats.verified}</div><div className="ca-stat-label">Đã xác minh</div></div></div>
        <div className="ca-stat"><div className="ca-stat-icon" style={{background:'rgba(6,182,212,.1)',color:'#06b6d4'}}>🧠</div><div><div className="ca-stat-val">{stats.training}</div><div className="ca-stat-label">AI Training</div></div></div>
      </div>

      {/* ── TABS ── */}
      <div className="ca-tabs">
        {TABS.map(t => (
          <button key={t.id} className={`ca-tab ${tab === t.id ? 'active' : ''}`} onClick={() => { setTab(t.id); setPage(1); }}>
            <span>{icon(t.iconKey, 14)}</span> {t.label}
          </button>
        ))}
      </div>

      {/* ── SYSTEM MODULES STATUS ── */}
      <div className="ca-modules">
        <span className="ca-mod"><i className="ca-dot green"/>NLP Moderation</span>
        <span className="ca-mod"><i className="ca-dot green"/>SafeLink Scanner</span>
        <span className="ca-mod"><i className="ca-dot green"/>DTS Routing</span>
        <span className="ca-mod"><i className="ca-dot green"/>Trust Graph</span>
        <span className="ca-mod"><i className="ca-dot green"/>Claim Court</span>
        <span className="ca-mod"><i className="ca-dot green"/>Reputation Engine</span>
        <span className="ca-mod"><i className="ca-dot green"/>AI Firewall</span>
        <span className="ca-mod"><i className="ca-dot green"/>Abuse Detection</span>
      </div>

      {/* ── POST TABLE ── */}
      <div className="ca-table-wrap">
        {loading ? (
          <div className="ca-loading"><span className="ca-spinner" /> Đang tải...</div>
        ) : posts.length === 0 ? (
          <div className="ca-loading">Không có bài đăng nào trong tab này.</div>
        ) : (
          <table className="ca-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Tác giả</th>
                <th>Loại</th>
                <th>Nội dung</th>
                <th>Status</th>
                <th>DTS</th>
                <th>Ring</th>
                <th>Coalition</th>
                <th>Comments</th>
                <th>Challenges</th>
                <th>Hành động</th>
              </tr>
            </thead>
            <tbody>
              {posts.map(p => {
                const st = getStatus(p.status);
                return (
                  <tr key={p.id} className={p.status === 'disputed' ? 'row-danger' : ''}>
                    <td className="td-id">#{p.id}</td>
                    <td className="td-author">{p.author_name}</td>
                    <td><span className="ca-type">{icon(TYPE_ICONS[p.claim_type] || 'fileSearch', 14)} {p.claim_type}</span></td>
                    <td className="td-content" title={p.content}>{p.content?.slice(0, 80)}{p.content?.length > 80 ? '…' : ''}</td>
                    <td><span className="ca-status" style={{color: st.color, background: st.bg, borderColor: st.color+'30'}}>{st.label}</span></td>
                    <td className="td-num">{p.dts_score?.toFixed(2) ?? '—'}</td>
                    <td className="td-num"><span className={`ca-ring ring-${p.distribution_ring ?? 0}`}>{p.distribution_ring ?? '—'}</span></td>
                    <td className="td-num">{p.coalition_risk_score?.toFixed(2) ?? '—'}</td>
                    <td className="td-num">{p.comment_count}</td>
                    <td className="td-num">{p.challenge_count}</td>
                    <td className="td-actions">
                      <button className="ca-act-btn" onClick={() => loadDetail(p.id)} title="Chi tiết">{icon('search', 14)}</button>
                      {!['disputed','under_jury_review'].includes(p.status) && (
                        <button className="ca-act-btn ca-act-court" onClick={() => setCourtTarget(p.id)} title="Mở phiên tòa">{icon('scale', 14)}</button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {pages > 1 && (
        <div className="ca-pagination">
          <button disabled={page<=1} onClick={() => { setPage(page-1); loadPosts(tab, page-1); }}>← Trước</button>
          <span>Trang {page} / {pages} ({total} bài)</span>
          <button disabled={page>=pages} onClick={() => { setPage(page+1); loadPosts(tab, page+1); }}>Sau →</button>
        </div>
      )}

      {/* ── DETAIL MODAL ── */}
      {detail && (
        <div className="ca-overlay" onClick={() => setDetail(null)}>
          <div className="ca-modal ca-modal--lg" onClick={e => e.stopPropagation()}>
            <div className="ca-modal-head">
              <h2>Chi tiết bài #{detail.id}</h2>
              <button onClick={() => setDetail(null)}>✕</button>
            </div>
            <div className="ca-detail-grid">
              <div className="ca-detail-section">
                <h4>{icon('fileSearch', 16)} Nội dung</h4>
                <p className="ca-detail-content">{detail.content}</p>
              </div>
              <div className="ca-detail-section">
                <h4>{icon('bot', 16)} AI Agent Analysis</h4>
                <div className="ca-detail-kv">
                  <span>Claim Type (AI detected)</span><b>{detail.claim_type}</b>
                  <span>Status</span><b>{detail.status}</b>
                  <span>DTS Score</span><b>{detail.dts_score?.toFixed(3) ?? 'N/A'}</b>
                  <span>Distribution Ring</span><b>Ring {detail.distribution_ring ?? '?'} / 4</b>
                  <span>Topic Sensitivity</span><b>{detail.topic_sensitivity_score?.toFixed(2) ?? '0'}</b>
                  <span>Coalition Risk</span><b style={{color: (detail.coalition_risk_score||0)>.5?'#ef4444':'inherit'}}>{detail.coalition_risk_score?.toFixed(3) ?? '0'}</b>
                  <span>Trust Distance</span><b>{detail.trust_distance_scope?.toFixed(2) ?? '0'}</b>
                  <span>Conflict Flags</span><b>{detail.conflict_flags?.join(', ') || 'None'}</b>
                </div>
              </div>
              <div className="ca-detail-section">
                <h4>{icon('user', 16)} Tác giả</h4>
                <div className="ca-detail-kv">
                  <span>ID</span><b>{detail.author_id}</b>
                  <span>Username</span><b>{detail.author_name}</b>
                  <span>Evidence</span><b>{detail.evidence_count} đính kèm</b>
                  <span>Comments</span><b>{detail.comment_count}</b>
                  <span>Challenges</span><b>{detail.challenge_count}</b>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── COURT CONFIRM ── */}
      {courtTarget && (
        <div className="ca-overlay" onClick={() => setCourtTarget(null)}>
          <div className="ca-modal" onClick={e => e.stopPropagation()}>
            <h3>{icon('scale', 18)} Mở phiên tòa cho bài #{courtTarget}?</h3>
            <p style={{color:'var(--text-muted)',margin:'.5rem 0 1rem'}}>Claim sẽ chuyển trạng thái sang "Under Jury Review". Jury sẽ bỏ phiếu quyết định.</p>
            <div className="ca-modal-btns">
              <button className="fb-btn--ghost" onClick={() => setCourtTarget(null)}>Hủy</button>
              <button className="ca-btn ca-btn--purple" onClick={() => openCourt(courtTarget)}>Mở phiên tòa</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
