/**
 * Community — User Feed (Facebook-style)
 * 100% social experience, zero technical jargon.
 * AI classification, moderation, trust — all invisible to users.
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Navigate } from 'react-router-dom';
import './Community.css';
import { useAuth } from '../../components/auth';
import { icon } from '../../components/ui/icons';

const API = '/api/community';
const tk = () => localStorage.getItem('avm-token');
const hdr = () => ({ 'Content-Type': 'application/json', Authorization: `Bearer ${tk()}` });

const timeAgo = (d) => {
  const s = (Date.now() - new Date(d).getTime()) / 1000;
  if (s < 60) return 'Vừa xong';
  if (s < 3600) return `${Math.floor(s / 60)} phút trước`;
  if (s < 86400) return `${Math.floor(s / 3600)} giờ trước`;
  if (s < 604800) return `${Math.floor(s / 86400)} ngày trước`;
  return new Date(d).toLocaleDateString('vi-VN');
};

const TYPE_LABELS = {
  opinion: 'Thảo luận', field_observation: 'Thực địa', data_fact: 'Dữ liệu',
  legal_zoning: 'Pháp lý', forecast: 'Dự báo', recommendation: 'Khuyến nghị',
};

export default function Community() {
  const { user, isAdmin } = useAuth();

  // Admin sees the moderation dashboard
  if (isAdmin) return <Navigate to="/community/admin" replace />;

  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  // Composer
  const [draft, setDraft] = useState('');
  const [isAnon, setIsAnon] = useState(false);
  const [attachUrl, setAttachUrl] = useState('');
  const [attachments, setAttachments] = useState([]);
  const [posting, setPosting] = useState(false);
  const taRef = useRef(null);

  // Comments
  const [openId, setOpenId] = useState(null);
  const [cmts, setCmts] = useState([]);
  const [cmtDraft, setCmtDraft] = useState('');

  // Report modal
  const [reportId, setReportId] = useState(null);
  const [reportType, setReportType] = useState('wrong_fact');
  const [reportText, setReportText] = useState('');

  /* ── Data loading ── */
  const load = useCallback(async (p = 1, append = false) => {
    if (!append) setLoading(true);
    try {
      const r = await fetch(`${API}/feed?tab=all&page=${p}&limit=15`);
      if (r.ok) {
        const d = await r.json();
        setPosts(prev => append ? [...prev, ...d.claims] : d.claims);
        setHasMore(d.claims.length >= 15);
        setPage(p);
      }
    } catch (e) { console.error(e); }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  /* ── Composer actions ── */
  const autoGrow = (el) => { el.style.height = 'auto'; el.style.height = el.scrollHeight + 'px'; };

  const addAttach = () => {
    const url = attachUrl.trim();
    if (url && !attachments.includes(url)) setAttachments(prev => [...prev, url]);
    setAttachUrl('');
  };

  const submitPost = async () => {
    if (!draft.trim() || posting) return;
    setPosting(true);
    try {
      if (isAnon) {
        await fetch(`${API}/private-insight`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content: draft, area_hint: null }),
        });
      } else {
        const evidence = attachments.map(u => ({ evidence_type: 'link', evidence_url: u, metadata_json: {}, source_mode: 'public' }));
        await fetch(`${API}/claims`, {
          method: 'POST', headers: hdr(),
          body: JSON.stringify({ content: draft, evidence, conflict_flags: [] }),
        });
      }
      setDraft(''); setAttachments([]); setIsAnon(false);
      if (taRef.current) taRef.current.style.height = 'auto';
      load(1);
    } catch (e) { console.error(e); }
    setPosting(false);
  };

  /* ── Comments ── */
  const toggleCmts = async (id) => {
    if (openId === id) { setOpenId(null); return; }
    setOpenId(id); setCmtDraft('');
    try {
      const r = await fetch(`${API}/claims/${id}/comments`);
      if (r.ok) setCmts(await r.json());
      else setCmts([]);
    } catch { setCmts([]); }
  };

  const sendCmt = async (id) => {
    if (!cmtDraft.trim()) return;
    await fetch(`${API}/claims/${id}/comments`, { method: 'POST', headers: hdr(), body: JSON.stringify({ content: cmtDraft }) });
    setCmtDraft('');
    const r = await fetch(`${API}/claims/${id}/comments`);
    if (r.ok) setCmts(await r.json());
    load(page);
  };

  /* ── Report ── */
  const sendReport = async () => {
    if (!reportText.trim()) return;
    await fetch(`${API}/claims/${reportId}/challenges`, {
      method: 'POST', headers: hdr(),
      body: JSON.stringify({ reason_type: reportType, argument_content: reportText }),
    });
    setReportId(null); setReportText(''); load(page);
  };

  /* ── Render ── */
  return (
    <div className="fb">
      {/* ── COMPOSER ── */}
      {user && (
        <div className="fb-composer">
          <div className="fb-c-row">
            <div className="fb-avatar fb-avatar--me">{user.username?.[0]?.toUpperCase()}</div>
            <textarea
              ref={taRef}
              className="fb-c-input"
              rows={1}
              placeholder={isAnon ? 'Chia sẻ ẩn danh về thị trường...' : `${user.username} ơi, thị trường hôm nay thế nào?`}
              value={draft}
              onChange={e => { setDraft(e.target.value); autoGrow(e.target); }}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submitPost(); } }}
            />
          </div>
          {attachments.length > 0 && (
            <div className="fb-c-attachments">
              {attachments.map((u, i) => (
                <span key={i} className="fb-c-chip">
                  {u.length > 40 ? u.slice(0, 40) + '…' : u}
                  <button onClick={() => setAttachments(a => a.filter((_, j) => j !== i))}>×</button>
                </span>
              ))}
            </div>
          )}
          <div className="fb-c-bar">
            <div className="fb-c-tools">
              <div className="fb-c-link-group">
                <input className="fb-c-link" placeholder="Đính kèm link bằng chứng…" value={attachUrl}
                  onChange={e => setAttachUrl(e.target.value)} onKeyDown={e => e.key === 'Enter' && addAttach()} />
                <button className="fb-c-icon-btn" onClick={addAttach} disabled={!attachUrl.trim()} title="Thêm link">Đính kèm</button>
              </div>
              <button className={`fb-c-icon-btn ${isAnon ? 'active' : ''}`} onClick={() => setIsAnon(!isAnon)}
                title={isAnon ? 'Đang ẩn danh — bấm để tắt' : 'Bật chế độ ẩn danh'}>
                {isAnon ? 'Ẩn' : 'Công khai'}
              </button>
            </div>
            <button className="fb-c-send" onClick={submitPost} disabled={!draft.trim() || posting} title="Đăng bài">
              {posting ? <span className="fb-spin" /> : (
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
              )}
            </button>
          </div>
        </div>
      )}

      {/* ── FEED ── */}
      {loading && posts.length === 0 ? (
        <div className="fb-loading"><span className="fb-spin-lg" /><p>Đang tải bảng tin…</p></div>
      ) : posts.length === 0 ? (
        <div className="fb-empty"><span>{icon('chat', 34)}</span><h3>Chưa có bài đăng</h3><p>Hãy là người đầu tiên chia sẻ!</p></div>
      ) : (
        <div className="fb-feed">
          {posts.map(p => (
            <article key={p.id} className={`fb-post ${p.status === 'resolved_true' ? 'verified' : ''} ${p.status === 'disputed' ? 'flagged' : ''}`}>
              {/* Header */}
              <div className="fb-p-head">
                <div className="fb-avatar">{p.author_name?.[0]?.toUpperCase() || '?'}</div>
                <div className="fb-p-meta">
                  <div className="fb-p-top">
                    <span className="fb-p-name">{p.author_name || 'Ẩn danh'}</span>
                    {p.status === 'resolved_true' && <span className="fb-badge fb-badge--ok" title="Đã xác minh">✓</span>}
                  </div>
                  <span className="fb-p-sub">
                    {timeAgo(p.created_at)}
                    <i>·</i>
                    <span className="fb-tag">{TYPE_LABELS[p.claim_type] || p.claim_type}</span>
                  </span>
                </div>
                {user && p.author_id !== user.id && (
                  <button className="fb-p-more" onClick={() => setReportId(p.id)} title="Báo cáo">
                    <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><circle cx="12" cy="5" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/></svg>
                  </button>
                )}
              </div>
              {/* Content */}
              <p className="fb-p-body">{p.content}</p>
              {p.evidence_count > 0 && <div className="fb-p-ev">{p.evidence_count} nguồn đính kèm</div>}
              {p.challenge_count > 0 && <div className="fb-p-warn">{icon('warning', 14)} {p.challenge_count} báo cáo</div>}
              {/* Actions */}
              <div className="fb-p-actions">
                <button className={`fb-act ${openId === p.id ? 'active' : ''}`} onClick={() => toggleCmts(p.id)}>
                  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                  {p.comment_count > 0 && <span>{p.comment_count}</span>}
                </button>
                <button className="fb-act" onClick={() => navigator.clipboard?.writeText(location.origin + '/community#p' + p.id)} title="Chia sẻ">
                  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>
                </button>
              </div>
              {/* Comments */}
              {openId === p.id && (
                <div className="fb-cmts">
                  {cmts.length === 0 && <p className="fb-cmts-empty">Chưa có bình luận.</p>}
                  {cmts.map(c => (
                    <div key={c.id} className="fb-cmt">
                      <div className="fb-avatar fb-avatar--sm">{c.author_name?.[0] || '?'}</div>
                      <div className="fb-cmt-bubble">
                        <b>{c.author_name || 'Ẩn danh'}</b>
                        <span>{c.content}</span>
                        <small>{timeAgo(c.created_at)}</small>
                      </div>
                    </div>
                  ))}
                  {user && (
                    <div className="fb-cmt-input">
                      <div className="fb-avatar fb-avatar--sm">{user.username?.[0]?.toUpperCase()}</div>
                      <input placeholder="Viết bình luận…" value={cmtDraft} onChange={e => setCmtDraft(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && sendCmt(p.id)} />
                      <button onClick={() => sendCmt(p.id)} disabled={!cmtDraft.trim()}>
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
                      </button>
                    </div>
                  )}
                </div>
              )}
            </article>
          ))}
          {hasMore && <button className="fb-more" onClick={() => load(page + 1, true)} disabled={loading}>{loading ? 'Đang tải…' : 'Xem thêm'}</button>}
        </div>
      )}

      {/* ── REPORT MODAL ── */}
      {reportId && (
        <div className="fb-overlay" onClick={() => setReportId(null)}>
          <div className="fb-modal" onClick={e => e.stopPropagation()}>
            <h3>Báo cáo bài viết</h3>
            <select value={reportType} onChange={e => setReportType(e.target.value)}>
              <option value="wrong_fact">Sai sự thật</option>
              <option value="fake_evidence">Bằng chứng giả</option>
              <option value="market_manipulation">Thao túng giá</option>
              <option value="misleading">Gây hiểu lầm</option>
            </select>
            <textarea placeholder="Mô tả chi tiết…" value={reportText} onChange={e => setReportText(e.target.value)} />
            <div className="fb-modal-btns">
              <button className="fb-btn--ghost" onClick={() => setReportId(null)}>Hủy</button>
              <button className="fb-btn--red" onClick={sendReport} disabled={!reportText.trim()}>Gửi báo cáo</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
