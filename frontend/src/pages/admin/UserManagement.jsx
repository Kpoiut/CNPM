/**
 * UserManagement — Admin Panel for user account administration.
 * Admin can: view all users, change roles, toggle active status.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../components/auth';
import { icon } from '../../components/ui/icons';

const API = '/api/auth';
const tk = () => localStorage.getItem('avm-token');
const hdr = () => ({ 'Content-Type': 'application/json', Authorization: `Bearer ${tk()}` });

const ROLE_META = {
  admin: { label: 'Quản trị viên', color: '#a78bfa', bg: 'rgba(167,139,250,.1)' },
  user:  { label: 'Người dùng',   color: '#38bdf8', bg: 'rgba(56,189,248,.1)' },
};

export default function UserManagement() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [updating, setUpdating] = useState(null); // user_id being updated
  const [filter, setFilter] = useState('all'); // all | admin | user
  const [search, setSearch] = useState('');

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await fetch(`${API}/users`, { headers: hdr() });
      if (!r.ok) {
        const body = await r.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${r.status}`);
      }
      const data = await r.json();
      setUsers(data.users || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadUsers(); }, [loadUsers]);

  const handleRoleChange = async (userId, newRole) => {
    setUpdating(userId);
    try {
      const r = await fetch(`${API}/users/${userId}`, {
        method: 'PATCH',
        headers: hdr(),
        body: JSON.stringify({ role: newRole }),
      });
      if (!r.ok) {
        const body = await r.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${r.status}`);
      }
      const updated = await r.json();
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, role: updated.role } : u));
    } catch (err) {
      alert(`Lỗi cập nhật: ${err.message}`);
    } finally {
      setUpdating(null);
    }
  };

  const handleToggleActive = async (userId, currentActive) => {
    setUpdating(userId);
    try {
      const r = await fetch(`${API}/users/${userId}`, {
        method: 'PATCH',
        headers: hdr(),
        body: JSON.stringify({ is_active: !currentActive }),
      });
      if (!r.ok) {
        const body = await r.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${r.status}`);
      }
      const updated = await r.json();
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, is_active: updated.is_active } : u));
    } catch (err) {
      alert(`Lỗi cập nhật: ${err.message}`);
    } finally {
      setUpdating(null);
    }
  };

  const filtered = users.filter(u => {
    const matchFilter = filter === 'all' || u.role === filter;
    const matchSearch = !search || u.username.toLowerCase().includes(search.toLowerCase()) || (u.email || '').toLowerCase().includes(search.toLowerCase());
    return matchFilter && matchSearch;
  });

  const stats = {
    total: users.length,
    admins: users.filter(u => u.role === 'admin').length,
    users: users.filter(u => u.role === 'user').length,
    inactive: users.filter(u => !u.is_active).length,
  };

  return (
    <div style={{ padding: '1.5rem 2rem', maxWidth: 1200, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
          <span style={{ display: 'inline-flex', verticalAlign: 'middle', marginRight: 8 }}>{icon('users', 24)}</span>
          Quản lý tài khoản
        </h1>
        <p style={{ color: 'var(--text-muted)', margin: '0.25rem 0 0', fontSize: '0.875rem' }}>
          Quản lý phân quyền và trạng thái tài khoản người dùng
        </p>
      </div>

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
        {[
          { label: 'Tổng tài khoản', value: stats.total, iconKey: 'users', color: '#6366f1' },
          { label: 'Quản trị viên', value: stats.admins, iconKey: 'shieldCheck', color: '#a78bfa' },
          { label: 'Người dùng', value: stats.users, iconKey: 'user', color: '#38bdf8' },
          { label: 'Đã khóa', value: stats.inactive, iconKey: 'lock', color: '#f87171' },
        ].map(s => (
          <div key={s.label} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: '1rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{ color: s.color }}>{icon(s.iconKey, 24)}</span>
            <div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: s.color }}>{s.value}</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{s.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Controls */}
      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
        <input
          type="text"
          placeholder="Tìm kiếm username, email..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ flex: 1, minWidth: 200, padding: '0.5rem 0.75rem', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text-primary)', fontSize: '0.875rem' }}
        />
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {['all', 'admin', 'user'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                padding: '0.4rem 0.75rem',
                border: '1px solid var(--border)',
                borderRadius: 8,
                background: filter === f ? 'var(--primary)' : 'var(--surface)',
                color: filter === f ? '#fff' : 'var(--text-secondary)',
                cursor: 'pointer',
                fontSize: '0.8rem',
                fontWeight: filter === f ? 600 : 400,
                transition: 'all 150ms',
              }}
            >
              {f === 'all' ? 'Tất cả' : f === 'admin' ? 'Admin' : 'Người dùng'}
            </button>
          ))}
        </div>
        <button
          onClick={loadUsers}
          disabled={loading}
          style={{ padding: '0.4rem 0.75rem', border: '1px solid var(--border)', borderRadius: 8, background: 'var(--surface)', color: 'var(--text-secondary)', cursor: loading ? 'not-allowed' : 'pointer', fontSize: '0.8rem', opacity: loading ? 0.6 : 1 }}
        >
          🔄 Làm mới
        </button>
      </div>

      {/* Error */}
      {error && (
        <div style={{ background: 'rgba(239,68,68,.1)', border: '1px solid rgba(239,68,68,.3)', borderRadius: 8, padding: '0.75rem 1rem', color: '#f87171', marginBottom: '1rem', fontSize: '0.875rem' }}>
          <span style={{ display: 'inline-flex', verticalAlign: 'middle', marginRight: 6 }}>{icon('warning', 16)}</span>
          {error}
        </div>
      )}

      {/* Table */}
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            <span className="spinner" style={{ display: 'inline-block', width: 24, height: 24, border: '2px solid var(--border)', borderTopColor: 'var(--primary)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
            <p style={{ marginTop: '0.75rem' }}>Đang tải danh sách người dùng...</p>
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            <p>Không có người dùng nào.</p>
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
            <thead>
              <tr style={{ background: 'var(--bg-elevated)', borderBottom: '1px solid var(--border)' }}>
                <th style={{ padding: '0.75rem 1rem', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>ID</th>
                <th style={{ padding: '0.75rem 1rem', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Username</th>
                <th style={{ padding: '0.75rem 1rem', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Email</th>
                <th style={{ padding: '0.75rem 1rem', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Vai trò</th>
                <th style={{ padding: '0.75rem 1rem', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Trạng thái</th>
                <th style={{ padding: '0.75rem 1rem', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Đăng nhập cuối</th>
                <th style={{ padding: '0.75rem 1rem', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Phiên hoạt động</th>
                <th style={{ padding: '0.75rem 1rem', textAlign: 'center', color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Hành động</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(u => {
                const roleMeta = ROLE_META[u.role] || ROLE_META.user;
                const isSelf = u.id === currentUser?.id;
                return (
                  <tr key={u.id} style={{ borderBottom: '1px solid var(--border)', background: isSelf ? 'rgba(99,102,241,.05)' : 'transparent' }}>
                    <td style={{ padding: '0.75rem 1rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>#{u.id}</td>
                    <td style={{ padding: '0.75rem 1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {u.username}
                      {isSelf && <span style={{ marginLeft: 6, fontSize: '0.7rem', color: 'var(--primary)', fontWeight: 500 }}>(bạn)</span>}
                    </td>
                    <td style={{ padding: '0.75rem 1rem', color: 'var(--text-secondary)' }}>{u.email || '—'}</td>
                    <td style={{ padding: '0.75rem 1rem' }}>
                      <select
                        value={u.role}
                        disabled={updating === u.id || isSelf}
                        onChange={e => handleRoleChange(u.id, e.target.value)}
                        style={{
                          padding: '0.25rem 0.5rem',
                          border: `1px solid ${roleMeta.color}40`,
                          borderRadius: 6,
                          background: roleMeta.bg,
                          color: roleMeta.color,
                          fontSize: '0.8rem',
                          fontWeight: 600,
                          cursor: (updating === u.id || isSelf) ? 'not-allowed' : 'pointer',
                          opacity: (updating === u.id || isSelf) ? 0.6 : 1,
                        }}
                      >
                        <option value="user">Người dùng</option>
                        <option value="admin">Quản trị viên</option>
                      </select>
                    </td>
                    <td style={{ padding: '0.75rem 1rem' }}>
                      <span style={{
                        padding: '0.2rem 0.5rem',
                        borderRadius: 6,
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        background: u.is_active ? 'rgba(16,185,129,.1)' : 'rgba(239,68,68,.1)',
                        color: u.is_active ? '#10b981' : '#f87171',
                      }}>
                        {u.is_active ? 'Hoạt động' : 'Đã khóa'}
                      </span>
                    </td>
                    <td style={{ padding: '0.75rem 1rem', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                      {u.last_login ? new Date(u.last_login).toLocaleString('vi-VN') : '—'}
                    </td>
                    <td style={{ padding: '0.75rem 1rem', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                      <span style={{ color: u.active_sessions > 0 ? '#10b981' : 'var(--text-muted)' }}>
                        {u.active_sessions || 0}
                      </span>
                      <span style={{ color: 'var(--text-muted)' }}> / {u.total_sessions || 0}</span>
                    </td>
                    <td style={{ padding: '0.75rem 1rem', textAlign: 'center' }}>
                      <button
                        onClick={() => handleToggleActive(u.id, u.is_active)}
                        disabled={updating === u.id || isSelf}
                        title={u.is_active ? 'Khóa tài khoản' : 'Mở khóa tài khoản'}
                        style={{
                          padding: '0.3rem 0.6rem',
                          border: `1px solid ${u.is_active ? 'rgba(239,68,68,.3)' : 'rgba(16,185,129,.3)'}`,
                          borderRadius: 6,
                          background: u.is_active ? 'rgba(239,68,68,.1)' : 'rgba(16,185,129,.1)',
                          color: u.is_active ? '#f87171' : '#10b981',
                          cursor: (updating === u.id || isSelf) ? 'not-allowed' : 'pointer',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          opacity: (updating === u.id || isSelf) ? 0.6 : 1,
                          transition: 'all 150ms',
                        }}
                      >
                        {updating === u.id ? '...' : (
                          <>
                            {icon(u.is_active ? 'lock' : 'unlock', 13)} {u.is_active ? 'Khóa' : 'Mở khóa'}
                          </>
                        )}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: '0.75rem', textAlign: 'right' }}>
        {filtered.length} / {users.length} người dùng
      </p>
    </div>
  );
}
