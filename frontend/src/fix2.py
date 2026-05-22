# -*- coding: utf-8 -*-
import os

base = 'C:/Users/Admin/Documents/real-estate-avm/frontend/src'

# Login.jsx - error span
with open(f'{base}/pages/public/Login.jsx', 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace('<span>⚠️</span> {error}', '<span></span> {error}')
with open(f'{base}/pages/public/Login.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated Login.jsx')

# CommunityAdmin.jsx
with open(f'{base}/pages/admin/CommunityAdmin.jsx', 'r', encoding='utf-8') as f:
    content = f.read()
original = content

# Use dict-based approach to avoid quoting issues
replacements = [
    ("{ id: 'all', label: 'Tất cả', icon: '📋' }", "{ id: 'all', label: 'Tất cả', icon: null }"),
    ("{ id: 'discussion', label: 'Thảo luận', icon: '💬' }", "{ id: 'discussion', label: 'Thảo luận', icon: null }"),
    ("{ id: 'market_signals', label: 'Tín hiệu', icon: '📡' }", "{ id: 'market_signals', label: 'Tín hiệu', icon: null }"),
    ("{ id: 'verified_insights', label: 'Đã xác minh', icon: '✅' }", "{ id: 'verified_insights', label: 'Đã xác minh', icon: null }"),
    ("{ id: 'under_dispute', label: 'Tranh chấp', icon: '⚠️' }", "{ id: 'under_dispute', label: 'Tranh chấp', icon: null }"),
    ("opinion: '💬', field_observation: '📍', data_fact: '📊'", "opinion: null, field_observation: null, data_fact: null,"),
    ("legal_zoning: '📋', forecast: '📈', recommendation: '🎯',", "legal_zoning: null, forecast: null, recommendation: null,"),
    ("<h1>🛡️ Moderation Center</h1>", "<h1>Moderation Center</h1>"),
    ("<button className=\"ca-btn ca-btn--accent\" onClick={runCoalitionScan}>🔍 Coalition Scan</button>", "<button className=\"ca-btn ca-btn--accent\" onClick={runCoalitionScan}>Coalition Scan</button>"),
    ("<button className=\"ca-btn ca-btn--purple\" onClick={processVerdicts}>⚖️ Process Verdicts</button>", "<button className=\"ca-btn ca-btn--purple\" onClick={processVerdicts}>Process Verdicts</button>"),
    ('<div className="ca-stat-icon" style={{background:\'rgba(124,58,237,.1)\',color:\'#a78bfa\'}}>📊</div>', '<div className="ca-stat-icon" style={{background:\'rgba(124,58,237,.1)\',color:\'#a78bfa\'}}></div>'),
    ('<div className="ca-stat-icon" style={{background:\'rgba(239,68,68,.1)\',color:\'#ef4444\'}}>⚠️</div>', '<div className="ca-stat-icon" style={{background:\'rgba(239,68,68,.1)\',color:\'#ef4444\'}}></div>'),
    ('<div className="ca-stat-icon" style={{background:\'rgba(16,185,129,.1)\',color:\'#10b981\'}}>✅</div>', '<div className="ca-stat-icon" style={{background:\'rgba(16,185,129,.1)\',color:\'#10b981\'}}></div>'),
    ('<div className="ca-stat-icon" style={{background:\'rgba(6,182,212,.1)\',color:\'#06b6d4\'}}>🧠</div>', '<div className="ca-stat-icon" style={{background:\'rgba(6,182,212,.1)\',color:\'#06b6d4\'}}></div>'),
    ("<span>{t.icon}</span> {t.label}", "<span>{t.icon}</span> {t.label}"),
    ("<span className=\"ca-type\">{TYPE_ICONS[p.claim_type]} {p.claim_type}</span>", "<span className=\"ca-type\">{TYPE_ICONS[p.claim_type]} {p.claim_type}</span>"),
    ("<button className=\"ca-act-btn\" onClick={() => loadDetail(p.id)} title=\"Chi tiết\">🔎</button>", "<button className=\"ca-act-btn\" onClick={() => loadDetail(p.id)} title=\"Chi tiết\"></button>"),
    ("<button className=\"ca-act-btn ca-act-court\" onClick={() => setCourtTarget(p.id)} title=\"Mở phiên tòa\">⚖️</button>", "<button className=\"ca-act-btn ca-act-court\" onClick={() => setCourtTarget(p.id)} title=\"Mở phiên tòa\"></button>"),
    ("<h4>📄 Nội dung</h4>", "<h4>Nội dung</h4>"),
    ("<h4>🤖 AI Agent Analysis</h4>", "<h4>AI Agent Analysis</h4>"),
    ("<h4>👤 Tác giả</h4>", "<h4>Tác giả</h4>"),
    ("<h3>⚖️ Mở phiên tòa cho bài #{courtTarget}?</h3>", "<h3>Mở phiên tòa cho bài #{courtTarget}?</h3>"),
]

for old, new in replacements:
    content = content.replace(old, new)

if content != original:
    with open(f'{base}/pages/admin/CommunityAdmin.jsx', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Updated CommunityAdmin.jsx')
else:
    print('No changes: CommunityAdmin.jsx')

print('Done.')
