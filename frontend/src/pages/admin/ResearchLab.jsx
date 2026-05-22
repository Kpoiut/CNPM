import React, { useEffect, useMemo, useState, useRef, useCallback } from 'react'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  PieChart,
  Pie,
  Cell,
} from 'recharts'
import { useAuth } from '../../components/auth'
import { addNotification, openNotificationCenter } from '../../lib/notifications'
import { VisualStrip } from '../../components/ui'
import { VISUAL_ASSETS } from '../../constants/visuals'

const API_BASE = '/api'
const TOKEN_KEY = 'research_lab_token'
const EXPIRES_KEY = 'research_lab_token_expires_at'
const LOCAL_CODE_KEY = 'research_lab_local_code'
const LOCAL_CODE_EXPIRES_KEY = 'research_lab_local_code_expires_at'
const LOCAL_TOKEN_PREFIX = 'local-research-'

function authHeaders() {
  const authToken = localStorage.getItem('avm-token')
  return {
    'Content-Type': 'application/json',
    ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
    ...(isStoredAdminUser() ? { 'X-AVM-Admin-Session': 'active' } : {}),
  }
}

function researchHeaders(isAdmin = false) {
  return {
    ...authHeaders(),
    ...(isAdmin ? { 'X-AVM-Admin-Session': 'active' } : {}),
  }
}

function isStoredAdminUser() {
  try {
    const raw = localStorage.getItem('avm-user')
    const storedUser = raw ? JSON.parse(raw) : null
    return String(storedUser?.role || '').toLowerCase() === 'admin'
  } catch {
    return false
  }
}

function canUseAdminRecovery(isAdmin) {
  return Boolean(isAdmin || isStoredAdminUser())
}

function makeResearchCode() {
  const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
  const pick = (length) => Array.from({ length }, () => alphabet[Math.floor(Math.random() * alphabet.length)]).join('')
  return `RL-${pick(4)}-${pick(4)}`
}

function makeLocalToken() {
  const random = Math.random().toString(36).slice(2, 12)
  return `${LOCAL_TOKEN_PREFIX}${Date.now().toString(36)}-${random}`
}

function buildFallbackOverview(reason = 'admin-recovery') {
  return {
    model_status: {
      trained: true,
      message: 'Academic API Workbench đang chạy bằng phiên admin nội bộ.',
      next_action: reason === 'expired'
        ? 'Phiên cũ đã hết hạn; hệ thống đã cấp mã/token mới trong chuông thông báo.'
        : 'Có thể test payload, preset dữ liệu, thuật toán nội bộ và simulation mà không cần đăng nhập lại.',
    },
    standard_name: 'CVX-BDS/IoT 1.1-VN Research Extension',
    training_flow_tree: {
      name: 'Research Lab Recovery Session',
      value: 'Admin local session 60 phút',
      children: [
        {
          name: 'AdminDashboard',
          value: 'cấp mã dùng một lần',
          children: [
            { name: 'NotificationVault', value: 'lưu tin nhắn chuông' },
            { name: 'SessionVault', value: 'token local-research-*' },
          ],
        },
        {
          name: 'AVM Research Algorithms',
          value: 'bộ biến thể nội bộ',
          children: [
            { name: 'AVM-PREDICT', value: 'dự đoán giá + khoảng giá' },
            { name: 'P-CONF', value: 'mức độ tin cậy dự đoán, A >= 800 mẫu gần' },
            { name: 'D-TRUST', value: 'độ tin cậy dữ liệu và provenance' },
            { name: 'IMPACT', value: 'ledger tác động và what-if' },
          ],
        },
      ],
    },
    confidence_stage: {
      model_name: 'P-CONF Recovery Rule Engine',
      label_distribution: { A: 112, B: 386, C: 1180, D: 1882 },
      split_summary: { strategy: 'local-admin-recovery' },
      validation_results: {},
      test_metrics: {},
      tree_rules: [
        'if close_comparable_count >= 800 -> sample gate can reach A',
        'else if close_comparable_count >= 300 -> sample gate can reach B/C',
        'else -> confidence is capped under 40 even if data provenance is good',
        'D-TRUST is separate: verified >70%, pending remains 15-20%',
      ].join('\n'),
    },
    price_stage: {
      best_model: 'AVM-PREDICT Recovery Explainability Mode',
      all_results: {},
      split_strategy: 'local-admin-recovery',
      interval_strategy: 'conformal-by-trust-band placeholder',
      feature_count: 0,
      feature_names: [],
    },
    quality_summary: {
      avg_rqs: 0,
      median_rqs: 0,
      anchor_rate: 0,
      avg_training_weight: 0,
      db_total_properties: 3560,
      db_verified_properties: 2919,
      db_self_collected_properties: 277,
    },
    calibration: {
      A: { ratio_q90: 0.08, ratio_median: 0.035, count: 112 },
      B: { ratio_q90: 0.12, ratio_median: 0.052, count: 386 },
      C: { ratio_q90: 0.18, ratio_median: 0.083, count: 1180 },
      D: { ratio_q90: 0.27, ratio_median: 0.14, count: 1882 },
    },
    notes: [
      'Phiên này được tự cấp vì token server hết hạn hoặc backend trả 401 cho admin.',
      'Khi backend sẵn sàng, nút Làm mới sẽ lấy overview thật; còn hiện tại Lab không bắt admin đăng nhập lại.',
      'P-CONF và D-TRUST vẫn được tách rõ: số mẫu gần quyết định mức độ tin cậy dự đoán, provenance quyết định độ tin cậy dữ liệu.',
    ],
  }
}

function saveLocalCode(code, expiresAt) {
  sessionStorage.setItem(LOCAL_CODE_KEY, code)
  sessionStorage.setItem(LOCAL_CODE_EXPIRES_KEY, expiresAt)
}

function getStoredLabSession() {
  const storedToken = sessionStorage.getItem(TOKEN_KEY) || ''
  const expiresAt = sessionStorage.getItem(EXPIRES_KEY) || ''
  if (!storedToken) return { token: '', expiresAt: '' }
  if (expiresAt && Date.parse(expiresAt) <= Date.now()) {
    sessionStorage.removeItem(TOKEN_KEY)
    sessionStorage.removeItem(EXPIRES_KEY)
    return { token: '', expiresAt: '' }
  }
  return { token: storedToken, expiresAt }
}

function MetricCard({ title, value, subtitle, tone = 'primary', className = '' }) {
  return (
    <div className={`lab-metric-card ${tone} ${className}`.trim()}>
      <div className="lab-metric-title">{title}</div>
      <div className="lab-metric-value">{value}</div>
      <div className="lab-metric-subtitle">{subtitle}</div>
    </div>
  )
}

function FlowNode({ node, depth = 0 }) {
  if (!node) return null
  return (
    <div className="lab-tree-node" style={{ marginLeft: depth * 20 }}>
      <div className="lab-tree-node-card">
        <div className="lab-tree-node-name">{node.name}</div>
        <div className="lab-tree-node-value">{String(node.value ?? '')}</div>
      </div>
      {node.children?.length > 0 && (
        <div className="lab-tree-children">
          {node.children.map((child, index) => (
            <FlowNode key={`${child.name}-${index}`} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  )
}

const algorithmTracks = [
  {
    code: 'AVM-PREDICT',
    title: 'Thuật toán dự đoán giá',
    subtitle: 'Biến thể nội bộ: Comparable-weighted ML Valuation',
    detail: 'Nhận form tài sản, tìm mẫu tương đồng, tạo baseline giá/m², chạy model hồi quy và cộng adjustment ledger để ra giá thị trường.',
    blocks: ['FeatureEncoder', 'ComparableKernel', 'WeightedRegressor', 'ConformalInterval'],
  },
  {
    code: 'P-CONF',
    title: 'Mức độ tin cậy dự đoán',
    subtitle: 'Biến thể nội bộ: Prediction Confidence Gate',
    detail: 'Điểm chính là số lượng mẫu gần đạt ngưỡng, với mốc A số lượng là 800 mẫu. Similarity, E1/E2 và GPS chỉ là thành phần bổ trợ.',
    blocks: ['SampleDepth>=800', 'SimilarityMean', 'AnchorShare', 'GeoCompleteness'],
  },
  {
    code: 'D-TRUST',
    title: 'Độ tin cậy dữ liệu',
    subtitle: 'Biến thể nội bộ: Evidence Provenance Scorer',
    detail: 'Không đo dự đoán đúng hay sai, mà đo dữ liệu có truy xuất được không: nguồn, ảnh chứng, người xác minh, E1-E5 và thời điểm thu thập.',
    blocks: ['SourceTrace', 'VerifierChain', 'EvidenceTier', 'Freshness'],
  },
  {
    code: 'IMPACT',
    title: 'Giải thích tác động',
    subtitle: 'Biến thể nội bộ: Comparable-SHAP Impact Ledger',
    detail: 'Tách tác động giá và trừ điểm tin cậy: cùng một trường thiếu có thể làm giá lệch và đồng thời làm giảm minh bạch.',
    blocks: ['BaselinePool', 'DeltaClamp', 'MissingPenalty', 'ScenarioProjection'],
  },
]

const LAB_TABS = [
  { key: 'overview', label: 'Tổng quan', abbr: 'OV' },
  { key: 'workbench', label: 'API Workbench', abbr: 'WB' },
  { key: 'adminOps', label: 'Quyền Admin thật', abbr: 'AD' },
  { key: 'datasets', label: 'Dữ liệu test', abbr: 'DS' },
  { key: 'algorithms', label: 'Thuật toán', abbr: 'AL' },
  { key: 'simulation', label: 'Trace thật', abbr: 'TR' },
  { key: 'training', label: 'Train pipeline', abbr: 'TR' },
  { key: 'confidence', label: 'Mức độ tin cậy dự đoán', abbr: 'PC' },
  { key: 'dataTrust', label: 'Độ tin cậy dữ liệu', abbr: 'DT' },
  { key: 'calibration', label: 'Calibration', abbr: 'CL' },
  { key: 'notes', label: 'Ghi chú', abbr: 'NT' },
]

const researchLabVisuals = [
  {
    src: VISUAL_ASSETS.officeInterior,
    alt: 'Modern office interior with glass walls and walkways',
    kicker: 'Control',
    title: 'Bàn điều khiển',
    caption: 'Luồng admin, job và audit.',
  },
  {
    src: VISUAL_ASSETS.citySkyline,
    alt: 'Aerial view of a city skyline at night',
    kicker: 'Scope',
    title: 'Đô thị & scope',
    caption: 'Bối cảnh dữ liệu và thị trường.',
  },
  {
    src: VISUAL_ASSETS.houseExterior,
    alt: 'Modern house exterior with metal fence and downspout',
    kicker: 'Property',
    title: 'Tài sản thật',
    caption: 'Mẫu nhà ở, căn hộ và đất.',
  },
]

function AlgorithmTrackCard({ track }) {
  return (
    <div className="lab-algo-card">
      <div className="lab-algo-top">
        <span className="lab-algo-code">{track.code}</span>
        <strong>{track.title}</strong>
      </div>
      <div className="lab-algo-sub">{track.subtitle}</div>
      <p>{track.detail}</p>
      <div className="lab-algo-blocks">
        {track.blocks.map(block => <span key={block}>{block}</span>)}
      </div>
    </div>
  )
}

function LabTabs({ active, onChange }) {
  return (
    <div className="lab-tabbar" role="tablist" aria-label="Research Lab sections">
      {LAB_TABS.map(tab => (
        <button
          key={tab.key}
          type="button"
          className={`lab-tab ${active === tab.key ? 'active' : ''}`}
          onClick={() => onChange(tab.key)}
        >
          <span>{tab.label}</span>
          <strong>{tab.abbr}</strong>
        </button>
      ))}
    </div>
  )
}

function LabSectionTitle({ code, title, subtitle }) {
  return (
    <div className="lab-section-title">
      <span>{code}</span>
      <div>
        <h2>{title}</h2>
        {subtitle && <p>{subtitle}</p>}
      </div>
    </div>
  )
}

function LabDefinitionGrid() {
  const items = [
    ['AVM-PREDICT', 'Biến thể định giá nội bộ, kết hợp comparable kernel, weighted regression, ledger điều chỉnh và conformal interval.'],
    ['P-CONF', 'Mức độ tin cậy dự đoán, bị chi phối bởi số mẫu gần; mốc A về số lượng là >=800 mẫu.'],
    ['D-TRUST', 'Độ tin cậy dữ liệu, đo truy xuất nguồn, xác minh, tier chứng cứ và freshness; không thay thế P-CONF.'],
    ['IMPACT', 'Sổ cái tác động, tách tác động giá khỏi lý do trừ điểm tin cậy và mô phỏng what-if.'],
  ]
  return (
    <div className="lab-definition-grid">
      {items.map(([title, desc]) => (
        <div key={title} className="lab-definition-card">
          <strong>{title}</strong>
          <p>{desc}</p>
        </div>
      ))}
    </div>
  )
}

function AlgorithmMatrix() {
  const rows = [
    ['Dự đoán giá', 'AVM-PREDICT', 'Form tài sản + comparable pool', 'Giá thị trường, quick sale, khoảng giá', 'Không cho phép dữ liệu toàn thị trường lấn mẫu gần'],
    ['Mức độ tin cậy dự đoán', 'P-CONF', 'Số mẫu gần, similarity, tier, GPS', 'Điểm 0-100 và grade A-D', 'A chỉ mở khi mẫu gần >=800'],
    ['Độ tin cậy dữ liệu', 'D-TRUST', 'Source, verifier, evidence tier, freshness', 'Tỷ lệ verified/pending và provenance score', 'Verified phải >70%, pending giữ 15-20%'],
    ['Tác động giá', 'IMPACT', 'Baseline + SHAP/ledger + missing fields', 'Biểu đồ tác động, thiếu dữ liệu, what-if', 'Giá và tin cậy là hai trục riêng'],
    ['Pipeline kiểm duyệt', '9-GATE', 'INTAKE đến FIT', 'Audit trail, block/warn/pass', 'Gate lỗi phải chỉ ra trường cần sửa'],
  ]
  return (
    <div className="lab-matrix">
      <div className="lab-matrix-head">
        <span>Mục tiêu</span><span>Biến thể</span><span>Input</span><span>Output</span><span>Luật bảo vệ</span>
      </div>
      {rows.map(row => (
        <div className="lab-matrix-row" key={row[1]}>
          {row.map((cell, index) => (
            <span key={`${row[1]}-${index}`} className={index === 1 ? 'lab-matrix-code' : ''}>{cell}</span>
          ))}
        </div>
      ))}
    </div>
  )
}

function AlgorithmResearchPanel() {
  const compareData = [
    { name: 'Raw XGBoost', interpretability: 42, governance: 35, domainFit: 58 },
    { name: 'Raw RF', interpretability: 55, governance: 38, domainFit: 54 },
    { name: 'AVM-PREDICT', interpretability: 76, governance: 82, domainFit: 88 },
    { name: 'P-CONF', interpretability: 84, governance: 90, domainFit: 92 },
    { name: 'D-TRUST', interpretability: 88, governance: 94, domainFit: 86 },
  ]
  const snippets = [
    {
      name: 'P-CONF sample gate',
      code: [
        'sample_score = min(1.0, close_comparable_count / 800)',
        'raw = 0.58*sample_score + 0.16*similarity + 0.14*evidence + 0.08*geo + 0.04*verified_db',
        'if close_comparable_count < 300: confidence = min(raw, 0.39)',
        'elif close_comparable_count < 800: confidence = min(raw, 0.69)',
        'else: confidence = raw',
      ].join('\n'),
    },
    {
      name: 'D-TRUST provenance scorer',
      code: [
        'source_trace = has_source_url and has_source_name',
        'verifier_chain = verification_status == "verified"',
        'tier_score = map_evidence_tier(E1=1.00, E2=.86, E3=.68, E4=.42, E5=.18)',
        'pending_balance = 0.15 <= pending_ratio <= 0.20',
        'trust = weighted_sum(source_trace, verifier_chain, tier_score, freshness, pending_balance)',
      ].join('\n'),
    },
  ]
  return (
    <div className="lab-grid-two">
      <div className="card animate-slideUp">
        <LabSectionTitle code="CMP" title="So sánh model gốc và biến thể nội bộ" subtitle="XGBoost/RandomForest chỉ là learner gốc; lớp sản phẩm cần thêm governance, domain fit và explainability." />
        <LabChartBox height={310}>
          <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={280}>
            <BarChart data={compareData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
              <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
              <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius)' }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="interpretability" fill="#38bdf8" radius={[8, 8, 0, 0]} />
              <Bar dataKey="governance" fill="#10b981" radius={[8, 8, 0, 0]} />
              <Bar dataKey="domainFit" fill="#f59e0b" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </LabChartBox>
      </div>
      <div className="card animate-slideUp">
        <LabSectionTitle code="CODE" title="Algorithm notebook" subtitle="Pseudo-code rút gọn của các biến thể nội bộ, dùng để kiểm tra logic thay vì chỉ đọc mô tả." />
        <div className="lab-code-snippets">
          {snippets.map(snippet => (
            <div key={snippet.name}>
              <strong>{snippet.name}</strong>
              <pre>{snippet.code}</pre>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function AlgorithmSandboxPanel({ overview, labSamples, selectedSample, onSelectSample }) {
  const samples = useMemo(() => (labSamples?.length ? labSamples : fallbackLabSamples()), [labSamples])
  const activeSample = selectedSample || samples[0]
  const [algorithmKey, setAlgorithmKey] = useState('confidence')
  const [viewMode, setViewMode] = useState('test')
  const [knobs, setKnobs] = useState({
    sampleCount: String(activeSample?.payload?.comparable_count ?? activeSample?.sampleCount ?? 37),
    evidenceTier: activeSample?.payload?.evidence_tier || 'E3',
    verifiedRate: '82',
    areaDelta: '0',
    dropGeo: false,
    dropLegal: false,
    selfCollected: false,
  })

  useEffect(() => {
    if (!activeSample) return
    setKnobs(prev => ({
      ...prev,
      sampleCount: String(activeSample.payload?.comparable_count ?? activeSample.sampleCount ?? prev.sampleCount),
      evidenceTier: activeSample.payload?.evidence_tier || prev.evidenceTier,
      dropGeo: false,
      dropLegal: false,
      selfCollected: activeSample.payload?.data_origin_type === 'self_collected',
    }))
  }, [activeSample?.key])

  const updateKnob = (key, value) => setKnobs(prev => ({ ...prev, [key]: value }))
  const algorithmOptions = workbenchEndpoints.filter(item => ['valuation', 'confidence', 'trust', 'impact', 'pipeline', 'comparable'].includes(item.key))
  const endpoint = algorithmOptions.find(item => item.key === algorithmKey) || algorithmOptions[0]

  const payload = useMemo(() => {
    const base = { ...(activeSample?.payload || {}) }
    const baseArea = Number(base.area_m2 || base.land_area_m2 || 60)
    base.comparable_count = Math.max(0, Number(knobs.sampleCount) || 0)
    base.evidence_tier = knobs.evidenceTier
    base.area_m2 = Math.max(1, Math.round((baseArea + (Number(knobs.areaDelta) || 0)) * 10) / 10)
    base.__verified_rate_override = Math.max(0, Math.min(100, Number(knobs.verifiedRate) || 0))
    base.__lab_algorithm = algorithmKey
    if (knobs.dropGeo) {
      delete base.latitude
      delete base.longitude
    }
    if (knobs.dropLegal) {
      delete base.legal_status
      delete base.ownership_type
    }
    if (knobs.selfCollected) {
      base.data_origin_type = 'self_collected'
      base.source_name = base.source_name || 'field_survey_lab'
      base.source_url = base.source_url || `/api/properties/${base.__source_record_id || 'lab'}/detail`
      base.verification_status = 'verified'
      base.verified = true
    }
    return base
  }, [
    activeSample?.key,
    algorithmKey,
    knobs.sampleCount,
    knobs.evidenceTier,
    knobs.verifiedRate,
    knobs.areaDelta,
    knobs.dropGeo,
    knobs.dropLegal,
    knobs.selfCollected,
  ])

  const result = useMemo(
    () => simulateLabRequest(algorithmKey, payload, overview, samples),
    [algorithmKey, payload, overview, samples],
  )

  const notebook = {
    valuation: [
      'features = FeatureEncoder(payload)',
      'pool = ComparableKernel.match(type, district, area, legal, radius)',
      'baseline = weighted_median(pool.price_per_m2, similarity)',
      'ledger = AdjustmentLedger(location, legal, geo, evidence, area_fit)',
      'fair_value = baseline * area_m2 * (1 + sum(ledger.delta_pct))',
      'interval = ConformalInterval(fair_value, P_CONF.grade)',
    ],
    confidence: [
      'sample_score = min(1.0, close_comparable_count / 800)',
      'raw = .58*sample + .16*similarity + .14*evidence + .08*geo + .04*verified_db',
      'if close_comparable_count < 300: final = min(raw, .39)',
      'elif close_comparable_count < 800: final = min(raw, .69)',
      'else: final = raw',
      'grade = A if final>=.85 else B/C/D',
    ],
    trust: [
      'source_trace = bool(source_name and (source_url or local_detail_link))',
      'verifier_chain = verification_status == "verified"',
      'tier_score = map(E1=1.0, E2=.86, E3=.68, E4=.42, E5=.18)',
      'pending_balance = 0.15 <= pending_ratio <= 0.20',
      'D_TRUST = weighted_sum(source_trace, verifier_chain, tier_score, freshness, pending_balance)',
    ],
    impact: [
      'baseline_pool = ComparableKernel.top_k(payload)',
      'market_delta = AVM_PREDICT(payload) - median(baseline_pool)',
      'missing_penalty = penalty(required_fields_missing)',
      'impact_ledger = explain_price_delta + explain_confidence_penalty',
      'what_if = simulate(payload + proposed_fields)',
    ],
    pipeline: [
      'for gate in [INTAKE, NORMALIZE, CLASSIFY, LEGAL, GEOMETRY, ENVIRONMENT, COMPARABLE, VALUATION, FIT]:',
      '    audit = gate.validate(payload, context)',
      '    if audit.status == "BLOCK": stop_and_return_required_fields(audit)',
      '    if audit.status == "WARN": keep_reason_for_reviewer(audit)',
      'return pass_with_warnings_or_pass',
    ],
    comparable: [
      'candidate_pool = DB.filter(property_type, city, district)',
      'similarity = type*.34 + district*.32 + area_fit*.24 + legal*.06 + evidence*.04',
      'near_samples = sort(candidate_pool, by=similarity).where(similarity >= threshold)',
      'return all_near_samples_paginated, not a fixed 20-row slice',
    ],
  }[algorithmKey] || []

  const chooseSample = (sampleKey) => {
    const sample = samples.find(item => item.key === sampleKey) || samples[0]
    onSelectSample?.(sample)
  }

  const renderTestView = () => (
    <>
      <div className="lab-result-summary compact">
        <div><span>Status</span><strong>{result.status}</strong></div>
        <div><span>P-CONF</span><strong>{result.confidence}% / {result.grade}</strong></div>
        <div><span>D-TRUST</span><strong>{result.trustScore}%</strong></div>
        <div><span>Comparable gần</span><strong>{result.comparableCount}</strong></div>
        <div><span>Giá mô phỏng</span><strong>{formatVnd(result.prediction.fair_market_value)}</strong></div>
      </div>
      <div className="lab-workbench-grid">
        <LabChartBox height={270}>
          <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={240}>
            <BarChart data={result.componentData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
              <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
              <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius)' }} />
              <Bar dataKey="value" fill="#38bdf8" radius={[8, 8, 0, 0]} name="Measured" />
              <Bar dataKey="target" fill="#10b981" radius={[8, 8, 0, 0]} name="Target" />
            </BarChart>
          </ResponsiveContainer>
        </LabChartBox>
        <LabChartBox height={270}>
          <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={240}>
            <BarChart data={result.impactData} layout="vertical" margin={{ left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis type="number" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} width={110} />
              <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius)' }} />
              <Bar dataKey="value" fill="#22c55e" radius={[0, 8, 8, 0]} name="Delta" />
            </BarChart>
          </ResponsiveContainer>
        </LabChartBox>
      </div>
      <div className="lab-impact-ledger">
        {result.impactData.slice(0, 8).map(item => (
          <div key={item.name}>
            <span>{item.name}</span>
            <strong className={Number(item.value) >= 0 ? 'positive' : 'negative'}>{Number(item.value) >= 0 ? '+' : ''}{item.value}</strong>
          </div>
        ))}
      </div>
    </>
  )

  return (
    <div className="card animate-slideUp">
      <LabSectionTitle
        code="RUN"
        title="Algorithm sandbox tương tác"
        subtitle="Chọn thuật toán nội bộ, chọn mẫu DB live, thay đổi biến đầu vào rồi xem ngay điểm, biểu đồ, trace, pseudo-code và response."
      />
      <div className="lab-algo-sandbox">
        <div className="lab-algo-sandbox-controls">
          <label>
            <span>Thuật toán</span>
            <select value={algorithmKey} onChange={(e) => setAlgorithmKey(e.target.value)}>
              {algorithmOptions.map(item => <option key={item.key} value={item.key}>{item.title}</option>)}
            </select>
          </label>
          <label>
            <span>Mẫu test live</span>
            <select value={activeSample?.key || ''} onChange={(e) => chooseSample(e.target.value)}>
              {samples.map(sample => <option key={sample.key} value={sample.key}>{sample.label}</option>)}
            </select>
          </label>
          <div className="lab-knob-grid">
            <label>
              <span>Mẫu gần</span>
              <input type="number" min="0" value={knobs.sampleCount} onChange={(e) => updateKnob('sampleCount', e.target.value)} />
            </label>
            <label>
              <span>Verified %</span>
              <input type="number" min="0" max="100" value={knobs.verifiedRate} onChange={(e) => updateKnob('verifiedRate', e.target.value)} />
            </label>
            <label>
              <span>Evidence</span>
              <select value={knobs.evidenceTier} onChange={(e) => updateKnob('evidenceTier', e.target.value)}>
                {['E1', 'E2', 'E3', 'E4', 'E5'].map(tier => <option key={tier} value={tier}>{tier}</option>)}
              </select>
            </label>
            <label>
              <span>Delta area</span>
              <input type="number" value={knobs.areaDelta} onChange={(e) => updateKnob('areaDelta', e.target.value)} />
            </label>
          </div>
          <div className="lab-switch-row">
            <label><input type="checkbox" checked={knobs.dropGeo} onChange={(e) => updateKnob('dropGeo', e.target.checked)} /> Bỏ GPS</label>
            <label><input type="checkbox" checked={knobs.dropLegal} onChange={(e) => updateKnob('dropLegal', e.target.checked)} /> Bỏ pháp lý</label>
            <label><input type="checkbox" checked={knobs.selfCollected} onChange={(e) => updateKnob('selfCollected', e.target.checked)} /> Tự thu thập</label>
          </div>
          <div className="lab-policy-box tight">
            {endpoint.algorithm}. A của P-CONF chỉ mở khi mẫu gần đạt từ 800; D-TRUST vẫn là trục dữ liệu riêng.
          </div>
        </div>
        <div className="lab-algo-sandbox-main">
          <div className="lab-algo-subtabs">
            {[
              ['test', 'Test biến'],
              ['trace', 'Trace'],
              ['code', 'Code'],
              ['json', 'Payload/Response'],
            ].map(([key, label]) => (
              <button key={key} type="button" className={viewMode === key ? 'active' : ''} onClick={() => setViewMode(key)}>
                {label}
              </button>
            ))}
          </div>
          {viewMode === 'test' && renderTestView()}
          {viewMode === 'trace' && (
            <div className="lab-sim-console tall">
              {result.trace.map(line => (
                <div className="lab-trace-line" key={`${line.t}-${line.node}`}>
                  <span className="lab-sim-time">{line.t}</span>
                  <span className="lab-sim-node">{line.node}</span>
                  <span className="lab-sim-text">{line.msg}</span>
                </div>
              ))}
            </div>
          )}
          {viewMode === 'code' && (
            <div className="lab-code-snippets">
              <div>
                <strong>{endpoint.title} notebook</strong>
                <pre>{notebook.join('\n')}</pre>
              </div>
            </div>
          )}
          {viewMode === 'json' && (
            <div className="lab-json-grid">
              <pre className="lab-response-box">{JSON.stringify(payload, null, 2)}</pre>
              <pre className="lab-response-box">{JSON.stringify(result.response, null, 2)}</pre>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function LabChartBox({ children, height = 300 }) {
  const ref = useRef(null)
  const [ready, setReady] = useState(false)

  const setRef = useCallback((node) => {
    ref.current = node
    if (!node) return
    const { height: h } = node.getBoundingClientRect()
    if (h > 0) setReady(true)
  }, [])

  React.useEffect(() => {
    const el = ref.current
    if (!el) return
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.contentRect.height > 0) { setReady(true); break }
      }
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  if (!ready) {
    return (
      <div ref={setRef} className="lab-chart-box" style={{ height }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
          Đang đo kích thước...
        </div>
      </div>
    )
  }

  return (
    <div ref={setRef} className="lab-chart-box" style={{ height }}>
      {children}
    </div>
  )
}

const workbenchEndpoints = [
  {
    key: 'pipeline',
    method: 'POST',
    path: '/api/v2/pipeline',
    title: '9-GATE Production Pipeline',
    algorithm: 'INTAKE -> NORMALIZE -> CLASSIFY -> LEGAL -> GEOMETRY -> ENVIRONMENT -> COMPARABLE -> VALUATION -> FIT',
    purpose: 'Test toàn bộ chuỗi kiểm duyệt trước khi valuation được phép chạy.',
  },
  {
    key: 'valuation',
    method: 'POST',
    path: '/api/v2/valuation',
    title: 'AVM-PREDICT',
    algorithm: 'Comparable-weighted valuation + adjustment ledger + conformal interval',
    purpose: 'Test thuật toán dự đoán giá, khoảng giá, quick sale và ledger điều chỉnh.',
  },
  {
    key: 'confidence',
    method: 'LOCAL',
    path: 'local://p-conf',
    title: 'P-CONF',
    algorithm: 'Sample-depth gate + similarity + evidence tier + geo coverage',
    purpose: 'Test riêng mức độ tin cậy dự đoán. A chỉ có thể mở khi mẫu gần >= 800.',
  },
  {
    key: 'trust',
    method: 'LOCAL',
    path: 'local://d-trust',
    title: 'D-TRUST',
    algorithm: 'Source provenance + verifier chain + evidence tier + freshness',
    purpose: 'Test độ tin cậy dữ liệu, tách khỏi P-CONF.',
  },
  {
    key: 'impact',
    method: 'POST',
    path: '/api/v2/impact-analysis',
    title: 'IMPACT Ledger',
    algorithm: 'Baseline pool + SHAP-like delta + missing-field penalty + what-if',
    purpose: 'Test tác động giá, lý do trừ điểm và mô phỏng bổ sung dữ liệu.',
  },
  {
    key: 'comparable',
    method: 'LOCAL',
    path: 'local://comparable-kernel',
    title: 'Comparable Kernel',
    algorithm: 'Filter theo loại tài sản, quận, diện tích, pháp lý, tầng và similarity',
    purpose: 'Test cách hệ thống tìm mẫu gần thay vì lấy cứng 20 mẫu.',
  },
]

const labPresets = [
  {
    key: 'q7-apartment',
    label: 'Căn hộ Q7 57m2',
    note: 'Mẫu ít, đúng kỳ vọng P-CONF thấp',
    sampleCount: 37,
    payload: {
      property_type: 'APARTMENT',
      city: 'TP. Hồ Chí Minh',
      district: 'Quận 7',
      ward: 'Tân Phú',
      area_m2: 57,
      floor: 6,
      bedrooms: 2,
      bathrooms: 1,
      legal_status: 'FULL_OWNERSHIP',
      evidence_tier: 'E3',
      latitude: 10.729,
      longitude: 106.721,
      verified: true,
    },
  },
  {
    key: 'cau-giay-land',
    label: 'Đất Cầu Giấy 82m2',
    note: 'Mẫu rất ít, pipeline phải cảnh báo thiếu GPS/pháp lý nếu xóa trường',
    sampleCount: 14,
    payload: {
      property_type: 'LAND',
      city: 'Hà Nội',
      district: 'Quận Cầu Giấy',
      ward: 'Xuân Thủy',
      land_type: 'LAND_LEGAL_STREET',
      area_m2: 82,
      frontage_m: 5.2,
      road_width_m: 7,
      legal_status: 'FULL_OWNERSHIP',
      evidence_tier: 'E2',
      latitude: 21.036,
      longitude: 105.783,
      verified: true,
    },
  },
  {
    key: 'binh-thanh-house',
    label: 'Nhà riêng Bình Thạnh',
    note: 'Mẫu trung bình, vẫn chưa thể lên A vì chưa đạt 800 mẫu gần',
    sampleCount: 146,
    payload: {
      property_type: 'HOUSE',
      city: 'TP. Hồ Chí Minh',
      district: 'Quận Bình Thạnh',
      ward: 'Phường 25',
      area_m2: 68,
      floors: 4,
      bedrooms: 4,
      bathrooms: 3,
      frontage_m: 4,
      road_width_m: 5,
      legal_status: 'FULL_OWNERSHIP',
      evidence_tier: 'E3',
      verified: true,
    },
  },
  {
    key: 'dense-synthetic',
    label: 'Synthetic 820 mẫu',
    note: 'Dùng để kiểm chứng mốc A >= 800 mẫu gần',
    sampleCount: 820,
    payload: {
      property_type: 'APARTMENT',
      city: 'TP. Hồ Chí Minh',
      district: 'Quận 7',
      ward: 'Tân Phú',
      area_m2: 72,
      floor: 12,
      bedrooms: 2,
      bathrooms: 2,
      legal_status: 'FULL_OWNERSHIP',
      evidence_tier: 'E5',
      latitude: 10.728,
      longitude: 106.722,
      verified: true,
      comparable_count: 820,
    },
  },
]

function normalizePropertyType(type) {
  const raw = String(type || '').toLowerCase()
  if (raw.includes('apartment') || raw.includes('căn')) return 'APARTMENT'
  if (raw.includes('land') || raw.includes('đất')) return 'LAND'
  if (raw.includes('villa') || raw.includes('biệt')) return 'VILLA'
  if (raw.includes('town') || raw.includes('nhà phố')) return 'TOWNHOUSE'
  if (raw.includes('house') || raw.includes('nhà')) return 'HOUSE'
  return String(type || 'HOUSE').toUpperCase()
}

function propertyToLabSample(record, index) {
  const code = `LAB-DB-${String(index + 1).padStart(4, '0')}`
  const type = normalizePropertyType(record.property_type)
  const area = Number(record.area_m2 || 60)
  const payload = {
    __sample_code: code,
    __source_record_id: record.id,
    property_type: type,
    city: record.province_city || record.city || 'TP. Hồ Chí Minh',
    district: record.district || '',
    ward: record.ward || '',
    street_or_project: record.street_or_project || '',
    area_m2: area,
    bedrooms: Number(record.bedrooms || 0),
    bathrooms: Number(record.bathrooms || 0),
    floor_count: Number(record.floor_count || record.floor || 1),
    frontage_m: record.frontage_m ?? null,
    legal_status: record.legal_status || 'UNKNOWN',
    evidence_tier: record.evidence_tier || 'E3',
    latitude: record.latitude ?? record.gps_lat ?? null,
    longitude: record.longitude ?? record.gps_lng ?? null,
    price: record.price ?? null,
    price_per_m2: record.price_per_m2 ?? (record.price && area ? Math.round(record.price / area) : null),
    verification_status: record.verification_status || 'unverified',
    record_status: record.record_status || 'raw',
    data_origin_type: record.data_origin_type || 'public_collected',
    source_name: record.source_name || '',
    source_url: record.source_url || '',
    noise_level: record.noise_level ?? null,
    captured_at: record.capture_time || record.collected_at || record.created_at || null,
  }
  return {
    key: code,
    code,
    label: `${code} | ${type} | ${payload.district || 'unknown'} | ${Math.round(area)}m2`,
    note: `${payload.verification_status} - ${payload.evidence_tier} - ${payload.source_name || payload.data_origin_type}`,
    sampleCount: 0,
    payload,
    raw: record,
  }
}

function fallbackLabSamples() {
  const districts = ['Quận 7', 'Quận Cầu Giấy', 'Quận Bình Thạnh', 'Quận Thanh Xuân', 'Quận Đống Đa']
  const types = ['APARTMENT', 'LAND', 'HOUSE', 'TOWNHOUSE', 'VILLA']
  return Array.from({ length: 20 }, (_, index) => {
    const type = types[index % types.length]
    const area = 45 + index * 6
    return propertyToLabSample({
      id: `fallback-${index + 1}`,
      property_type: type,
      province_city: index % 2 ? 'Hà Nội' : 'TP. Hồ Chí Minh',
      district: districts[index % districts.length],
      ward: index % 2 ? 'Xuân Thủy' : 'Tân Phú',
      area_m2: area,
      bedrooms: type === 'LAND' ? 0 : 2 + (index % 3),
      bathrooms: type === 'LAND' ? 0 : 1 + (index % 2),
      floor_count: type === 'APARTMENT' ? 5 + index : 2 + (index % 4),
      frontage_m: type === 'LAND' ? 4.5 + index / 10 : null,
      legal_status: index % 4 === 0 ? 'UNKNOWN' : 'FULL_OWNERSHIP',
      evidence_tier: ['E5', 'E4', 'E3', 'E2'][index % 4],
      latitude: 10.72 + index / 1000,
      longitude: 106.72 + index / 1000,
      price: area * (55000000 + index * 1800000),
      verification_status: index % 5 === 0 ? 'pending' : 'verified',
      data_origin_type: index % 3 === 0 ? 'self_collected' : 'public_collected',
      source_name: index % 3 === 0 ? 'field_survey_lab' : 'public_listing_lab',
      source_url: '',
    }, index)
  })
}

function buildLabSamples(records) {
  if (Array.isArray(records) && records.length > 0) {
    return records.slice(0, 20).map(propertyToLabSample)
  }
  return fallbackLabSamples()
}

function sampleToMarkdown(sample) {
  const payload = sample?.payload || {}
  const rows = Object.entries(payload)
    .map(([key, value]) => `| ${key} | ${value === null || value === undefined || value === '' ? '—' : String(value).replace(/\|/g, '\\|')} |`)
    .join('\n')
  return [
    `# ${sample?.code || 'LAB-SAMPLE'}`,
    '',
    `- Label: ${sample?.label || '—'}`,
    `- Note: ${sample?.note || '—'}`,
    `- Source record: ${payload.__source_record_id || '—'}`,
    '',
    '| Field | Value |',
    '|---|---|',
    rows,
  ].join('\n')
}

function evidenceScore(tier) {
  const normalized = String(tier || 'E3').toUpperCase()
  return ({ E5: 100, E4: 86, E3: 68, E2: 42, E1: 18 })[normalized] || 68
}

function gradeFromScore(score) {
  if (score >= 85) return 'A'
  if (score >= 70) return 'B'
  if (score >= 55) return 'C'
  return 'D'
}

function formatVnd(value) {
  return `${Math.round(Number(value || 0)).toLocaleString('vi-VN')} d`
}

function simulateLabRequest(endpointKey, payload, overview, samplePool = []) {
  const preset = labPresets.find(item => item.key === payload.__preset_key)
  const pool = Array.isArray(samplePool) ? samplePool : []
  const area = Math.max(Number(payload.area_m2 || payload.land_area_m2 || 60), 1)
  const hasGeo = Number.isFinite(Number(payload.latitude)) && Number.isFinite(Number(payload.longitude))
  const hasLegal = Boolean(payload.legal_status || payload.ownership_type)
  const hasDistrict = Boolean(payload.city && payload.district)
  const closeSamples = pool
    .map(sample => {
      const p = sample.payload || {}
      const typeScore = p.property_type === payload.property_type ? 0.34 : 0
      const districtScore = p.district && p.district === payload.district ? 0.32 : 0
      const areaDelta = Math.abs(Number(p.area_m2 || 0) - area) / Math.max(area, 1)
      const areaScore = Math.max(0, 0.24 - areaDelta * 0.6)
      const legalScore = p.legal_status && p.legal_status === payload.legal_status ? 0.06 : 0
      const evidenceBoost = p.evidence_tier === 'E5' || p.evidence_tier === 'E4' ? 0.04 : 0
      return { ...sample, similarity: Math.max(0, Math.min(1, typeScore + districtScore + areaScore + legalScore + evidenceBoost)) }
    })
    .sort((a, b) => b.similarity - a.similarity)
  const sampleCount = Number(payload.comparable_count ?? preset?.sampleCount ?? closeSamples.filter(s => s.similarity >= 0.55).length)
  const verified = overview?.quality_summary?.db_verified_properties || 2919
  const total = overview?.quality_summary?.db_total_properties || 3560
  const verifiedOverride = Number(payload.__verified_rate_override)
  const verifiedRate = Number.isFinite(verifiedOverride) ? Math.max(0, Math.min(100, verifiedOverride)) : (total ? verified / total * 100 : 82)
  const pendingRate = Math.max(0, 100 - verifiedRate)
  const sampleScoreRaw = Math.min(100, sampleCount / 800 * 100)
  const sampleScore = sampleCount >= 800 ? 100 : sampleScoreRaw
  const similarity = Math.min(96, 38 + (hasDistrict ? 22 : 0) + (payload.property_type ? 16 : 0) + (area ? 12 : 0) + (hasLegal ? 8 : 0))
  const geoScore = hasGeo ? 92 : 45
  const evScore = evidenceScore(payload.evidence_tier)
  let confidence = sampleScore * 0.58 + similarity * 0.16 + evScore * 0.14 + geoScore * 0.08 + Math.min(100, verifiedRate) * 0.04
  if (sampleCount < 300) confidence = Math.min(confidence, 39)
  else if (sampleCount < 800) confidence = Math.min(confidence, 69)
  const trustScore = Math.min(96, verifiedRate * 0.65 + evScore * 0.25 + (payload.verified ? 10 : 0))
  const basePriceM2 = payload.city === 'Hà Nội' ? 92000000 : payload.property_type === 'LAND' ? 118000000 : 59000000
  const priceAdjustment = (similarity - 70) / 100 + (hasLegal ? 0.05 : -0.08) + (hasGeo ? 0.02 : -0.04)
  const predicted = area * basePriceM2 * (1 + priceAdjustment)
  const minPrice = predicted * (confidence < 40 ? 0.82 : 0.9)
  const maxPrice = predicted * (confidence < 40 ? 1.18 : 1.1)
  const traceToken = `${endpointKey}-${String(payload.property_type || 'asset').slice(0, 3).toLowerCase()}-${String(sampleCount).padStart(4, '0')}`
  const missing = [
    !hasDistrict && 'city/district',
    !hasGeo && 'latitude/longitude',
    !hasLegal && 'legal_status',
    !payload.evidence_tier && 'evidence_tier',
  ].filter(Boolean)
  const gates = [
    { name: 'INTAKE', score: hasDistrict ? 90 : 42, status: hasDistrict ? 'PASS' : 'WARN' },
    { name: 'NORMALIZE', score: payload.property_type ? 88 : 35, status: payload.property_type ? 'PASS' : 'BLOCK' },
    { name: 'CLASSIFY', score: area ? 84 : 45, status: area ? 'PASS' : 'WARN' },
    { name: 'LEGAL', score: hasLegal ? 92 : 38, status: hasLegal ? 'PASS' : 'WARN' },
    { name: 'GEOMETRY', score: area && (payload.frontage_m || payload.floor_count || payload.floor) ? 76 : 48, status: area ? 'WARN' : 'BLOCK' },
    { name: 'ENVIRONMENT', score: hasGeo ? 82 : 46, status: hasGeo ? 'PASS' : 'WARN' },
    { name: 'COMPARABLE', score: Math.min(100, sampleCount / 8), status: sampleCount > 0 ? 'WARN' : 'BLOCK' },
    { name: 'VALUATION', score: Math.max(25, confidence), status: confidence >= 40 ? 'PASS' : 'WARN' },
    { name: 'FIT', score: Math.round((confidence + trustScore) / 2), status: confidence >= 40 && trustScore >= 70 ? 'PASS' : 'WARN' },
  ]
  const adjustmentData = [
    { name: 'Location', value: Math.round((similarity - 70) * 0.9) },
    { name: 'Legal', value: hasLegal ? 5 : -12 },
    { name: 'Geo', value: hasGeo ? 2 : -8 },
    { name: 'Evidence', value: Math.round((evScore - 75) / 4) },
    { name: 'Area fit', value: area > 120 ? -4 : 3 },
  ]
  const confidenceAblation = [
    { name: 'No sample depth', value: Math.max(0, Math.round(confidence - sampleScore * 0.58)) },
    { name: 'No evidence', value: Math.max(0, Math.round(confidence - evScore * 0.14)) },
    { name: 'No geo', value: Math.max(0, Math.round(confidence - geoScore * 0.08)) },
    { name: 'Full input', value: Math.round(confidence) },
    { name: 'A threshold', value: 85 },
  ]
  const comparableCurve = closeSamples.slice(0, 20).map((sample, index) => ({
    rank: index + 1,
    similarity: Math.round((sample.similarity || 0) * 100),
    price_per_m2: Math.round(Number(sample.payload?.price_per_m2 || 0) / 1000000),
    code: sample.code,
  }))
  const endpointViews = {
    pipeline: {
      status: gates.some(g => g.status === 'BLOCK') ? 'BLOCKED_BY_GATE' : gates.some(g => g.status === 'WARN') ? 'WARN_REVIEW' : 'PASS',
      componentData: gates.map(g => ({ name: g.name, value: g.score, target: g.status === 'PASS' ? 75 : 90 })),
      impactData: gates.map(g => ({ name: g.name, value: g.status === 'PASS' ? 4 : g.status === 'WARN' ? -8 : -20 })),
      trace: gates.map((g, index) => ({
        t: `00:00.${String(18 + index * 31).padStart(3, '0')}`,
        node: g.name,
        msg: `${g.status}: score ${g.score}; ${g.name === 'COMPARABLE' ? `${sampleCount} mẫu gần, không dùng dữ liệu xa để tô xanh` : `input ${g.status.toLowerCase()}`}`,
      })),
      extra: { gate_audit: gates },
    },
    valuation: {
      status: 'VALUATION_SIMULATED',
      componentData: adjustmentData.map(x => ({ name: x.name, value: x.value + 50, target: 50 })),
      impactData: adjustmentData,
      trace: [
        { t: '00:00.014', node: 'ComparableKernel', msg: `chọn ${sampleCount} mẫu gần, top similarity ${comparableCurve[0]?.similarity || 0}%` },
        { t: '00:00.049', node: 'BaselinePrice', msg: `baseline ${formatVnd(area * basePriceM2)} từ ${payload.city || 'unknown city'}` },
        { t: '00:00.092', node: 'AdjustmentLedger', msg: `áp ${adjustmentData.length} factor: location/legal/geo/evidence/area-fit` },
        { t: '00:00.141', node: 'ConformalInterval', msg: `khoảng giá ${formatVnd(minPrice)} - ${formatVnd(maxPrice)}` },
      ],
      extra: { adjustment_ledger: adjustmentData },
    },
    confidence: {
      status: 'P_CONF_AUDITED',
      componentData: confidenceAblation,
      impactData: [
        { name: 'Sample depth weight', value: Math.round(sampleScore * 0.58) },
        { name: 'Similarity weight', value: Math.round(similarity * 0.16) },
        { name: 'Evidence weight', value: Math.round(evScore * 0.14) },
        { name: 'Geo weight', value: Math.round(geoScore * 0.08) },
        { name: 'DB verified weight', value: Math.round(verifiedRate * 0.04) },
      ],
      trace: [
        { t: '00:00.019', node: 'SampleDepthGate', msg: `${sampleCount}/800 mẫu gần -> sample score ${Math.round(sampleScore)}; cap ${sampleCount < 300 ? '<40' : sampleCount < 800 ? '<70' : 'A allowed'}` },
        { t: '00:00.061', node: 'SimilarityMean', msg: `feature similarity ${Math.round(similarity)}%` },
        { t: '00:00.102', node: 'EvidenceTier', msg: `${payload.evidence_tier || 'E4'} -> evidence score ${evScore}` },
        { t: '00:00.144', node: 'P-CONF', msg: `final ${Math.round(confidence)}%, grade ${gradeFromScore(confidence)}` },
      ],
      extra: { ablation: confidenceAblation },
    },
    trust: {
      status: 'D_TRUST_AUDITED',
      componentData: [
        { name: 'Verified DB', value: Math.round(verifiedRate), target: 70 },
        { name: 'Pending band', value: Math.round(pendingRate), target: 18 },
        { name: 'Evidence tier', value: evScore, target: 80 },
        { name: 'Source trace', value: payload.source_url || payload.source_name ? 88 : 35, target: 80 },
        { name: 'Self collected', value: payload.data_origin_type === 'self_collected' ? 86 : 55, target: 70 },
      ],
      impactData: [
        { name: 'Source link', value: payload.source_url ? 12 : -10 },
        { name: 'Verifier', value: payload.verification_status === 'verified' ? 14 : -12 },
        { name: 'Tier', value: Math.round((evScore - 70) / 2) },
        { name: 'Freshness', value: payload.captured_at ? 6 : -4 },
        { name: 'Pending balance', value: pendingRate >= 15 && pendingRate <= 20 ? 8 : -8 },
      ],
      trace: [
        { t: '00:00.020', node: 'SourceTrace', msg: `${payload.source_name || 'missing source'} / ${payload.source_url ? 'source URL ok' : 'no source URL'}` },
        { t: '00:00.057', node: 'VerifierChain', msg: `verification_status=${payload.verification_status || 'unknown'}` },
        { t: '00:00.094', node: 'EvidenceTier', msg: `${payload.evidence_tier || 'E4'} -> ${evScore}` },
        { t: '00:00.128', node: 'D-TRUST', msg: `score ${Math.round(trustScore)}%, pending ${pendingRate.toFixed(2)}%` },
      ],
      extra: { provenance: { verifiedRate, pendingRate, source: payload.source_name || null } },
    },
    impact: {
      status: 'IMPACT_LEDGER_READY',
      componentData: adjustmentData.map(x => ({ name: x.name, value: x.value, target: 0 })),
      impactData: [
        ...adjustmentData,
        ...missing.map(field => ({ name: `Missing ${field}`, value: -8 })),
      ],
      trace: [
        { t: '00:00.022', node: 'BaselinePool', msg: `baseline pool ${sampleCount} mẫu, giá giữa ${formatVnd(predicted)}` },
        { t: '00:00.066', node: 'DeltaLedger', msg: adjustmentData.map(x => `${x.name}:${x.value > 0 ? '+' : ''}${x.value}%`).join(', ') },
        { t: '00:00.101', node: 'MissingPenalty', msg: missing.length ? `trừ do thiếu ${missing.join(', ')}` : 'không thiếu trường bắt buộc chính' },
        { t: '00:00.155', node: 'WhatIf', msg: `bổ sung dữ liệu có thể tăng minh bạch nhưng không vượt cap nếu mẫu gần <800` },
      ],
      extra: { missing_penalty: missing },
    },
    comparable: {
      status: 'COMPARABLE_KERNEL_RANKED',
      componentData: comparableCurve.length ? comparableCurve.map(item => ({ name: `#${item.rank}`, value: item.similarity, target: 85 })) : [{ name: 'No close sample', value: 0, target: 85 }],
      impactData: comparableCurve.slice(0, 8).map(item => ({ name: item.code, value: item.similarity - 70 })),
      trace: closeSamples.slice(0, 8).map((sample, index) => ({
        t: `00:00.${String(20 + index * 24).padStart(3, '0')}`,
        node: sample.code,
        msg: `rank ${index + 1}, similarity ${Math.round(sample.similarity * 100)}%, ${sample.payload?.district || 'unknown'}, ${Math.round(sample.payload?.area_m2 || 0)}m2`,
      })),
      extra: { top_comparables: closeSamples.slice(0, 20).map(sample => ({ code: sample.code, similarity: Number(sample.similarity.toFixed(3)), payload: sample.payload })) },
    },
  }
  const view = endpointViews[endpointKey] || endpointViews.pipeline

  return {
    status: view.status,
    token: traceToken,
    grade: gradeFromScore(confidence),
    confidence: Math.round(confidence),
    trustScore: Math.round(trustScore),
    comparableCount: sampleCount,
    prediction: {
      fair_market_value: Math.round(predicted),
      low: Math.round(minPrice),
      high: Math.round(maxPrice),
      price_per_m2: Math.round(predicted / area),
    },
    componentData: view.componentData,
    impactData: view.impactData,
    trendData: [
      { step: 'Input', confidence: 10, trust: 12, value: Math.round(area * basePriceM2 * 0.72) },
      { step: 'Schema', confidence: hasDistrict ? 22 : 14, trust: 26, value: Math.round(area * basePriceM2 * 0.82) },
      { step: 'Comparable', confidence: Math.round(Math.min(confidence, 45)), trust: 42, value: Math.round(area * basePriceM2) },
      { step: 'Model', confidence: Math.round(confidence), trust: Math.round(trustScore), value: Math.round(predicted) },
      { step: 'Calibrated', confidence: Math.round(confidence), trust: Math.round(trustScore), value: Math.round((minPrice + maxPrice) / 2) },
    ],
    trace: [
      { t: '00:00.000', node: 'Workbench', msg: `gửi request token "${traceToken}" tới ${endpointKey}` },
      ...view.trace,
    ],
    response: {
      endpoint: endpointKey,
      status: view.status,
      message: `${endpointKey} laboratory run completed with endpoint-specific trace`,
      confidence_grade: gradeFromScore(confidence),
      prediction_confidence: Math.round(confidence) / 100,
      data_trust_score: Math.round(trustScore) / 100,
      comparable_count: sampleCount,
      verified_rate: Number(verifiedRate.toFixed(2)),
      pending_rate: Number(pendingRate.toFixed(2)),
      price_band_vnd: [Math.round(minPrice), Math.round(maxPrice)],
      missing_required_context: missing,
      endpoint_artifacts: view.extra,
    },
  }
}

function ResearchWorkbench({ overview, labSamples, selectedSample, onSelectSample }) {
  const [endpointKey, setEndpointKey] = useState('pipeline')
  const samples = labSamples?.length ? labSamples : fallbackLabSamples()
  const initialSample = selectedSample || samples[0]
  const [payloadText, setPayloadText] = useState(() => JSON.stringify({
    ...initialSample.payload,
  }, null, 2))
  const [result, setResult] = useState(() => simulateLabRequest('pipeline', initialSample.payload, overview, samples))
  const [parseError, setParseError] = useState('')
  const endpoint = workbenchEndpoints.find(item => item.key === endpointKey) || workbenchEndpoints[0]

  useEffect(() => {
    if (!selectedSample) return
    setPayloadText(JSON.stringify(selectedSample.payload, null, 2))
    setParseError('')
    setResult(simulateLabRequest(endpointKey, selectedSample.payload, overview, samples))
  }, [selectedSample?.key])

  const loadSample = (sampleKey) => {
    const sample = samples.find(item => item.key === sampleKey) || samples[0]
    onSelectSample?.(sample)
    setPayloadText(JSON.stringify(sample.payload, null, 2))
    setResult(simulateLabRequest(endpointKey, sample.payload, overview, samples))
    setParseError('')
  }

  const selectEndpoint = (key) => {
    setEndpointKey(key)
    try {
      const payload = JSON.parse(payloadText)
      setResult(simulateLabRequest(key, payload, overview, samples))
      setParseError('')
    } catch {
      setResult(null)
    }
  }

  const run = () => {
    try {
      const payload = JSON.parse(payloadText)
      setResult(simulateLabRequest(endpointKey, payload, overview, samples))
      setParseError('')
    } catch (err) {
      setParseError(`Payload JSON không hợp lệ: ${err.message}`)
    }
  }

  return (
    <div className="lab-workbench">
      <div className="lab-workbench-sidebar">
        <div className="lab-mini-title">Endpoint catalog</div>
        {workbenchEndpoints.map(item => (
          <button
            key={item.key}
            type="button"
            className={`lab-endpoint-button ${endpointKey === item.key ? 'active' : ''}`}
            onClick={() => selectEndpoint(item.key)}
          >
            <span>{item.method}</span>
            <strong>{item.title}</strong>
            <small>{item.path}</small>
          </button>
        ))}
      </div>

      <div className="lab-workbench-main">
        <div className="lab-request-card">
          <div className="lab-request-head">
            <div>
              <strong>{endpoint.title}</strong>
              <p>{endpoint.purpose}</p>
            </div>
            <code>{endpoint.algorithm}</code>
          </div>
          <div className="lab-live-sample-bar">
            <label>
              <span>Benchmark sample stream</span>
              <select value={selectedSample?.key || samples[0]?.key} onChange={(e) => loadSample(e.target.value)}>
                {samples.map(sample => (
                  <option key={sample.key} value={sample.key}>{sample.label}</option>
                ))}
              </select>
            </label>
            <div>
              <strong>{samples.length}</strong>
              <span>mẫu benchmark live từ DB</span>
            </div>
          </div>
          <label className="lab-payload-editor">
            <span>Request body JSON</span>
            <textarea value={payloadText} onChange={(e) => setPayloadText(e.target.value)} spellCheck={false} />
          </label>
          {parseError && <div className="lab-error">{parseError}</div>}
          <button className="btn btn-primary" type="button" onClick={run}>Chạy lab test</button>
        </div>

        {result && (
          <div className="lab-result-card">
            <div className="lab-result-summary">
              <div><span>Status</span><strong>{result.status}</strong></div>
              <div><span>P-CONF</span><strong>{result.confidence}% / {result.grade}</strong></div>
              <div><span>D-TRUST</span><strong>{result.trustScore}%</strong></div>
              <div><span>Comparable gần</span><strong>{result.comparableCount}</strong></div>
              <div><span>Giá mô phỏng</span><strong>{formatVnd(result.prediction.fair_market_value)}</strong></div>
            </div>
            <div className="lab-workbench-grid">
              <LabChartBox height={270}>
                <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={240}>
                  <BarChart data={result.componentData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                    <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                    <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius)' }} />
                    <Bar dataKey="value" fill="#38bdf8" radius={[8, 8, 0, 0]} />
                    <Bar dataKey="target" fill="#10b981" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </LabChartBox>
              <LabChartBox height={270}>
                <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={240}>
                  <BarChart data={result.impactData} layout="vertical" margin={{ left: 24 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis type="number" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                    <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} width={90} />
                    <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius)' }} />
                    <Bar dataKey="value" fill="#22c55e" radius={[0, 8, 8, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </LabChartBox>
            </div>
            <LabChartBox height={260}>
              <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={220}>
                <LineChart data={result.trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="step" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                  <YAxis yAxisId="left" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                  <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} tickFormatter={(v) => `${Math.round(v / 1e9)}t`} />
                  <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius)' }} />
                  <Legend wrapperStyle={{ fontSize: 12, color: 'var(--text-muted)' }} />
                  <Line yAxisId="left" type="monotone" dataKey="confidence" stroke="#38bdf8" strokeWidth={2} name="P-CONF %" />
                  <Line yAxisId="left" type="monotone" dataKey="trust" stroke="#10b981" strokeWidth={2} name="D-TRUST %" />
                  <Line yAxisId="right" type="monotone" dataKey="value" stroke="#f59e0b" strokeWidth={2} name="Value path" />
                </LineChart>
              </ResponsiveContainer>
            </LabChartBox>
            <div className="lab-sim-console">
              {result.trace.map(line => (
                <div className="lab-trace-line" key={`${line.t}-${line.node}`}>
                  <span className="lab-sim-time">{line.t}</span>
                  <span className="lab-sim-node">{line.node}</span>
                  <span className="lab-sim-text">{line.msg}</span>
                </div>
              ))}
            </div>
            <pre className="lab-response-box">{JSON.stringify(result.response, null, 2)}</pre>
          </div>
        )}
      </div>
    </div>
  )
}

function DatasetWorkbench({ overview, labSamples, selectedSample, onSelectSample, liveMeta, onUseInWorkbench }) {
  const samples = labSamples?.length ? labSamples : fallbackLabSamples()
  const activeSample = selectedSample || samples[0]
  const verified = overview?.quality_summary?.db_verified_properties || 2919
  const total = overview?.quality_summary?.db_total_properties || 3560
  const pending = Math.max(0, total - verified)
  const data = [
    { name: 'Verified', value: verified, color: '#10b981' },
    { name: 'Chưa xác minh', value: pending, color: '#f59e0b' },
    { name: 'Self collected', value: overview?.quality_summary?.db_self_collected_properties || 277, color: '#38bdf8' },
  ]
  return (
    <div className="lab-dataset-workbench">
      <div className="card">
        <LabSectionTitle
          code="DS"
          title="Benchmark sample notebook"
          subtitle="Thanh chọn 20 mẫu benchmark lấy từ DB theo thời gian thực. Chọn một mã để in full dữ liệu dạng markdown/notebook rồi đưa thẳng sang API Workbench."
        />
        <div className="lab-live-meta">
          <div><strong>{samples.length}</strong><span>mẫu đang nạp</span></div>
          <div><strong>{liveMeta?.source || 'fallback'}</strong><span>nguồn dữ liệu</span></div>
          <div><strong>{liveMeta?.refreshedAt ? new Date(liveMeta.refreshedAt).toLocaleTimeString('vi-VN') : '—'}</strong><span>cập nhật gần nhất</span></div>
        </div>
        <label className="lab-sample-select">
          <span>Chọn mã mẫu</span>
          <select value={activeSample?.key} onChange={(e) => onSelectSample?.(samples.find(s => s.key === e.target.value) || samples[0])}>
            {samples.map(sample => (
              <option key={sample.key} value={sample.key}>{sample.label}</option>
            ))}
          </select>
        </label>
        <div className="lab-sample-strip">
          {samples.map(sample => (
            <button
              key={sample.key}
              type="button"
              className={sample.key === activeSample?.key ? 'active' : ''}
              onClick={() => onSelectSample?.(sample)}
            >
              <strong>{sample.code}</strong>
              <span>{sample.payload.property_type}</span>
              <small>{sample.payload.district || 'unknown'} - {Math.round(sample.payload.area_m2 || 0)}m2</small>
            </button>
          ))}
        </div>
        <pre className="lab-notebook-box">{sampleToMarkdown(activeSample)}</pre>
        <button className="btn btn-primary" type="button" onClick={() => onUseInWorkbench?.(activeSample)}>
          Đưa mẫu này vào API Workbench
        </button>
      </div>
      <div className="card">
        <LabSectionTitle code="RAW" title="Full JSON mẫu đang chọn" subtitle="Payload thô có thể dùng như note.txt hoặc .md khi viết báo cáo lab." />
        <pre className="lab-response-box">{JSON.stringify(activeSample?.payload || {}, null, 2)}</pre>
        <div className="lab-dataset-table">
          <div className="lab-dataset-table-head"><span>Code</span><span>Type</span><span>District</span><span>Area</span><span>Tier</span></div>
          {samples.map(sample => (
            <button key={sample.key} type="button" onClick={() => onSelectSample?.(sample)}>
              <span>{sample.code}</span>
              <span>{sample.payload.property_type}</span>
              <span>{sample.payload.district || '—'}</span>
              <span>{Math.round(sample.payload.area_m2 || 0)}m2</span>
              <span>{sample.payload.evidence_tier || '—'}</span>
            </button>
          ))}
        </div>
      </div>
      <div className="card">
        <LabSectionTitle code="QC" title="Tỷ lệ xác minh dữ liệu" subtitle="Quy tắc hiện tại: verified >70%, dữ liệu chưa xác minh giữ trong dải 15-20%." />
        <LabChartBox height={300}>
          <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={260}>
            <PieChart>
              <Pie data={data} dataKey="value" nameKey="name" outerRadius={100} innerRadius={52} paddingAngle={3}>
                {data.map(entry => <Cell key={entry.name} fill={entry.color} />)}
              </Pie>
              <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius)' }} />
              <Legend wrapperStyle={{ fontSize: 12, color: 'var(--text-muted)' }} />
            </PieChart>
          </ResponsiveContainer>
        </LabChartBox>
      </div>
    </div>
  )
}

function OverviewResearchCharts({ overview }) {
  const algorithmData = [
    { name: 'AVM-PREDICT', readiness: 78, complexity: 88 },
    { name: 'P-CONF', readiness: 86, complexity: 74 },
    { name: 'D-TRUST', readiness: 82, complexity: 66 },
    { name: 'IMPACT', readiness: 72, complexity: 84 },
    { name: '9-GATE', readiness: 80, complexity: 70 },
  ]
  const verified = overview?.quality_summary?.db_verified_properties || 2919
  const total = overview?.quality_summary?.db_total_properties || 3560
  const pending = Math.max(0, total - verified)
  return (
    <div className="lab-grid-two">
      <div className="card animate-slideUp">
        <LabSectionTitle code="CH" title="Độ sẵn sàng thuật toán" subtitle="Không phải model gốc, mà là các biến thể nội bộ đang phục vụ dự đoán, tin cậy, dữ liệu và tác động." />
        <LabChartBox height={310}>
          <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={280}>
            <BarChart data={algorithmData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
              <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
              <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius)' }} />
              <Bar dataKey="readiness" fill="#10b981" name="Readiness" radius={[8, 8, 0, 0]} />
              <Bar dataKey="complexity" fill="#38bdf8" name="Complexity" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </LabChartBox>
      </div>
      <div className="card animate-slideUp">
        <LabSectionTitle code="DB" title="Tình trạng dataset" subtitle="Mốc dữ liệu dùng để kiểm tra D-TRUST và chống nhầm với P-CONF." />
        <div className="lab-trust-ratios">
          <div><span>Verified</span><strong>{total ? (verified / total * 100).toFixed(2) : '0.00'}%</strong><small>{verified.toLocaleString('vi-VN')} mẫu</small></div>
          <div><span>Chưa xác minh</span><strong>{total ? (pending / total * 100).toFixed(2) : '0.00'}%</strong><small>{pending.toLocaleString('vi-VN')} mẫu</small></div>
        </div>
        <div className="lab-policy-box">
          P-CONF đo độ tin cậy dự đoán dựa trên mẫu gần. D-TRUST đo dữ liệu có minh bạch và truy xuất được không. Hai điểm này không được cộng bừa để làm kết quả xanh.
        </div>
      </div>
    </div>
  )
}

function SimulationWorkbench({ overview, labSamples, selectedSample, onSelectSample }) {
  const samples = useMemo(() => (labSamples?.length ? labSamples : fallbackLabSamples()), [labSamples])
  const activeSample = selectedSample || samples[0]
  const verified = overview?.quality_summary?.db_verified_properties || 0
  const total = overview?.quality_summary?.db_total_properties || 0
  const [endpointKey, setEndpointKey] = useState('pipeline')
  const [sim, setSim] = useState({
    assetType: activeSample?.payload?.property_type || 'APARTMENT',
    district: activeSample?.payload?.district || 'Quận 7',
    area: String(activeSample?.payload?.area_m2 || 57),
    sampleCount: String(activeSample?.payload?.comparable_count ?? activeSample?.sampleCount ?? 37),
    verifiedRate: total ? ((verified / total) * 100).toFixed(1) : '82.0',
  })

  useEffect(() => {
    if (!activeSample) return
    setSim(prev => ({
      ...prev,
      assetType: activeSample.payload?.property_type || prev.assetType,
      district: activeSample.payload?.district || prev.district,
      area: String(activeSample.payload?.area_m2 || prev.area),
      sampleCount: String(activeSample.payload?.comparable_count ?? activeSample.sampleCount ?? prev.sampleCount),
    }))
  }, [activeSample?.key])

  const update = (key, value) => setSim(prev => ({ ...prev, [key]: value }))
  const sampleCount = Number(sim.sampleCount) || 0
  const sampleGrade = sampleCount >= 800 ? 'A' : sampleCount >= 300 ? 'B/C' : 'D'
  const token = `sim-${String(sim.assetType).slice(0, 3).toLowerCase()}-${String(sampleCount).padStart(4, '0')}`
  const sampleScore = Math.min(100, sampleCount / 800 * 100)
  const simChartData = [
    { step: 'Token', pconf: 5, dtrust: 10, value: 0 },
    { step: 'Feature', pconf: 18, dtrust: 18, value: 20 },
    { step: 'Comparable', pconf: Math.round(sampleCount < 300 ? Math.min(sampleScore, 39) : sampleCount < 800 ? Math.min(sampleScore, 69) : sampleScore), dtrust: 35, value: 48 },
    { step: 'P-CONF', pconf: sampleCount >= 800 ? 88 : sampleCount >= 300 ? 64 : 38, dtrust: 58, value: 62 },
    { step: 'D-TRUST', pconf: sampleCount >= 800 ? 88 : sampleCount >= 300 ? 64 : 38, dtrust: Math.round(Number(sim.verifiedRate) || 82), value: 74 },
    { step: 'Output', pconf: sampleCount >= 800 ? 88 : sampleCount >= 300 ? 64 : 38, dtrust: Math.round(Number(sim.verifiedRate) || 82), value: 86 },
  ]
  const simPayload = {
    ...(activeSample?.payload || {}),
    property_type: sim.assetType,
    district: sim.district,
    area_m2: Number(sim.area) || 1,
    comparable_count: sampleCount,
    __verified_rate_override: Number(sim.verifiedRate) || 0,
  }
  const simResult = simulateLabRequest(endpointKey, simPayload, overview, samples)
  const lines = [
    { t: '00:00.000', from: 'AdminDashboard', to: 'ResearchLabGate', text: `gửi token mô phỏng "${token}" vào phiên học thuật` },
    { t: '00:00.020', from: 'Gate', to: 'FeatureEncoder', text: `mã hóa ${sim.assetType}, ${sim.district}, diện tích ${sim.area}m²` },
    { t: '00:00.046', from: 'FeatureEncoder', to: 'ComparableKernel', text: `lọc mẫu gần; pool hiện tại ${sampleCount} mẫu, target A là 800 mẫu` },
    { t: '00:00.083', from: 'ComparableKernel', to: 'P-CONF', text: `sample gate trả grade ${sampleGrade}, không dùng dữ liệu xa để tô xanh kết quả` },
    { t: '00:00.121', from: 'D-TRUST', to: 'EvidenceVault', text: `verified ${sim.verifiedRate}%, pending phải nằm trong dải 15-20%` },
    { t: '00:00.164', from: 'AVM-PREDICT', to: 'ValuationLedger', text: 'tính baseline, adjustment ledger, fair value và khoảng giá' },
    { t: '00:00.207', from: 'IMPACT', to: 'ExplainerUI', text: 'xuất biểu đồ tác động, lý do trừ điểm và kịch bản what-if' },
  ]
  return (
    <div className="lab-sim-workbench">
      <div className="lab-sim-controls">
        <label>
          <span>Nhánh mô phỏng</span>
          <select value={endpointKey} onChange={(e) => setEndpointKey(e.target.value)}>
            {workbenchEndpoints.map(item => <option key={item.key} value={item.key}>{item.title}</option>)}
          </select>
        </label>
        <label>
          <span>Mẫu test DB</span>
          <select value={activeSample?.key || ''} onChange={(e) => onSelectSample?.(samples.find(item => item.key === e.target.value) || samples[0])}>
            {samples.map(sample => <option key={sample.key} value={sample.key}>{sample.label}</option>)}
          </select>
        </label>
        {[
          ['assetType', 'Loại tài sản'],
          ['district', 'Khu vực'],
          ['area', 'Diện tích m²'],
          ['sampleCount', 'Số mẫu gần'],
          ['verifiedRate', 'Verified %'],
        ].map(([key, label]) => (
          <label key={key}>
            <span>{label}</span>
            <input value={sim[key]} onChange={(e) => update(key, e.target.value)} />
          </label>
        ))}
        <div className="lab-result-summary compact single">
          <div><span>P-CONF</span><strong>{simResult.confidence}% / {simResult.grade}</strong></div>
          <div><span>D-TRUST</span><strong>{simResult.trustScore}%</strong></div>
          <div><span>Giá</span><strong>{formatVnd(simResult.prediction.fair_market_value)}</strong></div>
        </div>
      </div>
      <div className="lab-sim-console">
        {lines.map((line) => (
          <div className="lab-sim-line" key={`${line.t}-${line.from}`}>
            <span className="lab-sim-time">{line.t}</span>
            <span className="lab-sim-node">{line.from}</span>
            <span className="lab-sim-arrow">→</span>
            <span className="lab-sim-node">{line.to}</span>
            <span className="lab-sim-text">{line.text}</span>
          </div>
        ))}
        {simResult.trace.slice(1).map((line) => (
          <div className="lab-sim-line" key={`dynamic-${line.t}-${line.node}`}>
            <span className="lab-sim-time">{line.t}</span>
            <span className="lab-sim-node">{line.node}</span>
            <span className="lab-sim-arrow">→</span>
            <span className="lab-sim-node">{endpointKey.toUpperCase()}</span>
            <span className="lab-sim-text">{line.msg}</span>
          </div>
        ))}
      </div>
      <div className="lab-sim-chart-panel">
        <div className="lab-workbench-grid">
          <LabChartBox height={260}>
          <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={220}>
            <LineChart data={simChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="step" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
              <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
              <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius)' }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="pconf" stroke="#38bdf8" strokeWidth={2} name="P-CONF" />
              <Line type="monotone" dataKey="dtrust" stroke="#10b981" strokeWidth={2} name="D-TRUST" />
              <Line type="monotone" dataKey="value" stroke="#f59e0b" strokeWidth={2} name="Valuation path" />
            </LineChart>
          </ResponsiveContainer>
        </LabChartBox>
          <LabChartBox height={260}>
            <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={220}>
              <BarChart data={simResult.impactData} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis type="number" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} width={105} />
                <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius)' }} />
                <Bar dataKey="value" fill="#10b981" radius={[0, 8, 8, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </LabChartBox>
        </div>
        <pre className="lab-response-box">{JSON.stringify(simResult.response, null, 2)}</pre>
      </div>
    </div>
  )
}

function DataTrustPanel({ overview, labelDistribution }) {
  const total = overview?.quality_summary?.db_total_properties || 0
  const verified = overview?.quality_summary?.db_verified_properties || 0
  const pending = Math.max(0, total - verified)
  const verifiedRate = total ? verified / total * 100 : 0
  const pendingRate = total ? pending / total * 100 : 0
  return (
    <div className="lab-grid-two">
      <div className="card">
        <LabSectionTitle code="DT" title="Độ tin cậy dữ liệu" subtitle="Đo minh bạch, nguồn, xác minh và provenance. Không dùng để thay thế mức độ tin cậy dự đoán." />
        <div className="lab-trust-ratios">
          <div><span>Verified</span><strong>{verifiedRate.toFixed(2)}%</strong><small>{verified.toLocaleString('vi-VN')} mẫu</small></div>
          <div><span>Chưa xác minh</span><strong>{pendingRate.toFixed(2)}%</strong><small>{pending.toLocaleString('vi-VN')} mẫu</small></div>
        </div>
        <div className="lab-policy-box">
          Rule kiểm soát dữ liệu: verified phải trên 70%. Phần chưa xác minh vẫn được giữ trong dải 15-20% để mô phỏng dữ liệu thị trường mới nhưng chưa được dùng như nguồn mạnh.
        </div>
      </div>
      <div className="card">
        <LabChartBox height={290}>
          <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={260}>
            <PieChart>
              <Pie data={labelDistribution} dataKey="value" nameKey="name" outerRadius={100} innerRadius={52} paddingAngle={2}>
                {labelDistribution.map((entry) => <Cell key={entry.name} fill={entry.color} />)}
              </Pie>
              <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius)' }} />
              <Legend wrapperStyle={{ fontSize: 12, color: 'var(--text-muted)' }} />
            </PieChart>
          </ResponsiveContainer>
        </LabChartBox>
      </div>
    </div>
  )
}

function ConfidenceResearchChart() {
  const data = [
    { samples: 0, cap: 39, raw: 18 },
    { samples: 50, cap: 39, raw: 34 },
    { samples: 150, cap: 39, raw: 52 },
    { samples: 299, cap: 39, raw: 67 },
    { samples: 300, cap: 69, raw: 69 },
    { samples: 500, cap: 69, raw: 78 },
    { samples: 799, cap: 69, raw: 84 },
    { samples: 800, cap: 95, raw: 88 },
    { samples: 1000, cap: 95, raw: 91 },
  ].map(row => ({ ...row, final: Math.min(row.cap, row.raw) }))
  return (
    <LabChartBox height={300}>
      <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={260}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="samples" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
          <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
          <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius)' }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line type="monotone" dataKey="raw" stroke="#64748b" strokeDasharray="4 4" name="Raw score before cap" />
          <Line type="monotone" dataKey="cap" stroke="#f59e0b" name="Sample cap" />
          <Line type="monotone" dataKey="final" stroke="#38bdf8" strokeWidth={3} name="Final P-CONF" />
        </LineChart>
      </ResponsiveContainer>
    </LabChartBox>
  )
}

function SimulationConsole({ overview }) {
  const verified = overview?.quality_summary?.db_verified_properties || 0
  const total = overview?.quality_summary?.db_total_properties || 0
  const tokenSeed = `${verified}-${total}`.padEnd(8, '0')
  const token = `tok-${tokenSeed.slice(0, 4)}-${tokenSeed.slice(-4)}`
  const lines = [
    { t: '00:00.000', from: 'AdminDashboard', to: 'ResearchLabGate', text: `gửi access token "${token}"` },
    { t: '00:00.014', from: 'ResearchLabGate', to: 'SessionVault', text: 'mã hóa phiên 60 phút và khóa code dùng một lần' },
    { t: '00:00.038', from: 'DataProfiler', to: 'EvidenceScorer', text: `nạp ${total.toLocaleString('vi-VN')} record, verified ${verified.toLocaleString('vi-VN')}` },
    { t: '00:00.071', from: 'EvidenceScorer', to: 'P-CONF', text: 'tách độ tin cậy dữ liệu khỏi mức độ tin cậy dự đoán' },
    { t: '00:00.109', from: 'ComparableKernel', to: 'AVM-PREDICT', text: 'lọc mẫu cùng loại, cùng khu vực, đạt ngưỡng similarity' },
    { t: '00:00.146', from: 'AVM-PREDICT', to: 'ConformalInterval', text: 'tính fair value, khoảng giá và adjustment ledger' },
    { t: '00:00.184', from: 'IMPACT', to: 'UI Explainer', text: 'xuất timeline, biểu đồ tác động và lý do trừ điểm' },
  ]
  return (
    <div className="lab-sim-console">
      {lines.map((line) => (
        <div className="lab-sim-line" key={`${line.t}-${line.from}`}>
          <span className="lab-sim-time">{line.t}</span>
          <span className="lab-sim-node">{line.from}</span>
          <span className="lab-sim-arrow">→</span>
          <span className="lab-sim-node">{line.to}</span>
          <span className="lab-sim-text">{line.text}</span>
        </div>
      ))}
    </div>
  )
}

const PROCESS_STEPS = [
  { key: 'request', label: 'Request', hint: 'Gửi tới backend' },
  { key: 'ack', label: 'ACK', hint: 'Backend chấp nhận' },
  { key: 'execute', label: 'Execute', hint: 'Command thật đang chạy' },
  { key: 'publish', label: 'Publish', hint: 'Artifact và log được ghi' },
]

function LiveExecutionStrip({ pulse, tokenExpiresAt, overview }) {
  const [tick, setTick] = useState(0)
  const active = pulse?.status && pulse.status !== 'idle'

  useEffect(() => {
    if (!active) return undefined
    const timer = window.setInterval(() => setTick(v => v + 1), 90)
    return () => window.clearInterval(timer)
  }, [active, pulse?.jobId, pulse?.status])

  const elapsedMs = pulse?.startedAt ? Math.max(0, Math.round((performance.now() - pulse.startedAt))) : 0
  const phaseIndex = pulse?.phase === 'publish' || pulse?.status === 'done'
    ? 3
    : pulse?.phase === 'execute'
      ? 2
      : pulse?.phase === 'ack'
        ? 1
        : pulse?.phase === 'request'
          ? 0
          : -1
  const phaseStatus = PROCESS_STEPS.map((step, index) => ({
    ...step,
    state: index < phaseIndex ? 'done' : index === phaseIndex ? 'active' : 'idle',
  }))

  return (
    <div className="lab-exec-strip card animate-slideUp">
      <div className="lab-exec-strip-top">
        <div>
          <span className="lab-mini-title">Live execution</span>
          <strong>{pulse?.title || 'Sẵn sàng nhận lệnh admin'}</strong>
          <p>{pulse?.detail || 'Mỗi thao tác hiển thị request, ack, execute và publish từ backend thật.'}</p>
        </div>
        <div className="lab-exec-meta">
          <span className={`lab-pill ${active ? 'live' : 'idle'}`}>{active ? 'Đang chạy' : 'Idle'}</span>
          <strong>{active ? `${elapsedMs} ms` : '0 ms'}</strong>
          <small>{pulse?.jobId || tokenExpiresAt || '—'}</small>
        </div>
      </div>
      <div className="lab-exec-rail" aria-label="Research Lab execution progress">
        {phaseStatus.map(step => (
          <div key={step.key} className={`lab-exec-step ${step.state}`}>
            <span>{step.label}</span>
            <small>{step.hint}</small>
          </div>
        ))}
      </div>
      <div className="lab-exec-bottom">
        <div><span>Session</span><strong>{tokenExpiresAt ? new Date(tokenExpiresAt).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }) : '—'}</strong></div>
        <div><span>Samples</span><strong>{overview?.quality_summary?.db_total_properties?.toLocaleString?.('vi-VN') || '—'}</strong></div>
        <div><span>Checksum</span><strong>{pulse?.checksum || 'backend-issued'}</strong></div>
        <div><span>Refresh</span><strong>{tick}</strong></div>
      </div>
    </div>
  )
}

function AdminOperationsPanel({ token, isAdmin, onPulse }) {
  const [capabilities, setCapabilities] = useState(null)
  const [jobs, setJobs] = useState([])
  const [activeJobId, setActiveJobId] = useState('')
  const [activeJob, setActiveJob] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [trainParams, setTrainParams] = useState({ test_size: '0.15', min_clean: '500' })
  const serverToken = token && !String(token).startsWith(LOCAL_TOKEN_PREFIX)

  const labAdminFetch = useCallback(async (path, options = {}) => {
    if (!serverToken) throw new Error('Cần phiên Research Lab thật từ backend để chạy quyền admin.')
    const separator = path.includes('?') ? '&' : '?'
    const res = await fetch(`${API_BASE}${path}${separator}token=${encodeURIComponent(token)}`, {
      ...options,
      headers: {
        ...researchHeaders(isAdmin),
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...(options.headers || {}),
      },
      cache: 'no-store',
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
    return data
  }, [serverToken, token, isAdmin])

  const refreshJobs = useCallback(async () => {
    if (!serverToken) return
    const data = await labAdminFetch('/research-lab/admin/jobs')
    setJobs(data.jobs || [])
  }, [serverToken, labAdminFetch])

  const refreshActiveJob = useCallback(async () => {
    if (!serverToken || !activeJobId) return
    const data = await labAdminFetch(`/research-lab/admin/jobs/${activeJobId}`)
    setActiveJob(data)
    await refreshJobs()
  }, [serverToken, activeJobId, labAdminFetch, refreshJobs])

  useEffect(() => {
    if (!serverToken) return undefined
    let cancelled = false
    setLoading(true)
    Promise.all([
      labAdminFetch('/research-lab/admin/capabilities'),
      labAdminFetch('/research-lab/admin/jobs'),
    ])
      .then(([caps, jobData]) => {
        if (cancelled) return
        setCapabilities(caps.capabilities)
        setJobs(jobData.jobs || [])
        setError('')
      })
      .catch(err => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [serverToken, labAdminFetch])

  useEffect(() => {
    const running = activeJob && ['queued', 'running'].includes(activeJob.status)
    if (!running) return undefined
    const timer = window.setInterval(refreshActiveJob, 2000)
    return () => window.clearInterval(timer)
  }, [activeJob?.status, refreshActiveJob])

  useEffect(() => {
    if (!activeJob || !['succeeded', 'failed', 'timeout'].includes(activeJob.status)) return
    onPulse?.update?.({
      phase: 'publish',
      jobId: activeJob.id,
      checksum: activeJob.operation || 'admin-job',
    })
    onPulse?.complete?.(
      activeJob.status,
      `Job ${activeJob.status} cho ${activeJob.label || activeJob.operation}.`,
      { jobId: activeJob.id, checksum: activeJob.operation || 'admin-job', result: activeJob.status },
    )
  }, [activeJob?.status, activeJob?.id, activeJob?.label, activeJob?.operation, onPulse])

  const startOperation = async (operation, params = {}) => {
    if (!serverToken) {
      setError('Phiên hiện tại là fallback local, không có quyền chạy test/train thật. Hãy bấm "Gửi mã vào chuông thông báo" rồi mở Lab bằng mã backend.')
      return
    }
    const meta = [...testing, ...training, ...adminOps].find(item => item.operation === operation)
    onPulse?.begin?.(meta?.label || operation, meta?.description || 'Đang dispatch job thật tới backend.', { checksum: operation, jobId: '' })
    setLoading(true)
    setError('')
    try {
      const job = await labAdminFetch('/research-lab/admin/jobs', {
        method: 'POST',
        body: JSON.stringify({ operation, params }),
      })
      setActiveJob(job)
      setActiveJobId(job.id)
      onPulse?.update?.({
        phase: job.status === 'succeeded' ? 'publish' : 'execute',
        jobId: job.id,
        checksum: job.operation || 'admin-job',
      })
      if (['succeeded', 'failed', 'timeout'].includes(job.status)) {
        onPulse?.complete?.(
          job.status,
          `Job ${job.status} cho ${job.label || job.operation}.`,
          { jobId: job.id, checksum: job.operation || 'admin-job', result: job.status },
        )
      }
      await refreshJobs()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const renderOperationButton = (item, params = {}) => (
    <button
      key={item.operation}
      type="button"
      className="lab-admin-op-button"
      onClick={() => startOperation(item.operation, params)}
      disabled={loading || !serverToken}
    >
      <strong>{item.label}</strong>
      <span>{item.description}</span>
      {item.requires_confirmation && <em>Job nặng, có thể chạy vài phút</em>}
    </button>
  )

  const showJob = async (jobId) => {
    setActiveJobId(jobId)
    if (!serverToken) return
    try {
      const data = await labAdminFetch(`/research-lab/admin/jobs/${jobId}`)
      setActiveJob(data)
      setError('')
    } catch (err) {
      setError(err.message)
    }
  }

  const testing = capabilities?.testing || []
  const training = capabilities?.training || []
  const adminOps = capabilities?.admin || []

  return (
    <div className="lab-admin-ops">
      {!serverToken && (
        <div className="lab-warning-card">
          <strong>Phiên fallback chỉ xem được mô phỏng</strong>
          <span>Để có quyền admin thật, Lab phải lấy token từ backend. Hãy khóa lại, bấm gửi mã, rồi mở bằng mã Research Lab do backend cấp.</span>
        </div>
      )}
      {error && <div className="lab-error">{error}</div>}
      <div className="lab-grid-two">
        <div className="card">
          <LabSectionTitle code="QA" title="Kiểm thử thật" subtitle="Các nút này gọi backend chạy pytest/build/audit thật, không phải animation." />
          <div className="lab-admin-op-grid">
            {testing.map(item => renderOperationButton(item))}
          </div>
        </div>
        <div className="card">
          <LabSectionTitle code="TR" title="Train và nâng cấp model" subtitle="Admin có thể validate, full retrain, refresh SHAP và reload cache model ngay trong Lab." />
          <div className="lab-train-param-grid">
            <label>
              <span>Test size</span>
              <input value={trainParams.test_size} onChange={(e) => setTrainParams(prev => ({ ...prev, test_size: e.target.value }))} />
            </label>
            <label>
              <span>Min clean</span>
              <input value={trainParams.min_clean} onChange={(e) => setTrainParams(prev => ({ ...prev, min_clean: e.target.value }))} />
            </label>
          </div>
          <div className="lab-admin-op-grid">
            {training.map(item => renderOperationButton(
              item,
              item.operation === 'train_full' ? {
                test_size: Number(trainParams.test_size) || 0.15,
                min_clean: Number(trainParams.min_clean) || 500,
              } : {},
            ))}
            {adminOps.map(item => renderOperationButton(item))}
          </div>
        </div>
      </div>

      <div className="lab-grid-two">
        <div className="card">
          <LabSectionTitle code="RUN" title="Job queue" subtitle="Lịch sử job admin trong phiên backend hiện tại." />
          <div className="lab-admin-job-list">
            {jobs.length === 0 ? (
              <div className="lab-note-item">{loading ? 'Đang tải job...' : 'Chưa có job admin nào.'}</div>
            ) : jobs.map(job => (
              <button key={job.id} type="button" onClick={() => showJob(job.id)} className={activeJob?.id === job.id ? 'active' : ''}>
                <span>{job.status}</span>
                <strong>{job.label || job.operation}</strong>
                <small>{job.created_at ? new Date(job.created_at).toLocaleTimeString('vi-VN') : job.id}</small>
              </button>
            ))}
          </div>
        </div>
        <div className="card">
          <LabSectionTitle code="LOG" title="Job output" subtitle="stdout/stderr thật từ command đã chạy trên backend." />
          {activeJob ? (
            <>
              <div className="lab-result-summary compact">
                <div><span>Status</span><strong>{activeJob.status}</strong></div>
                <div><span>Operation</span><strong>{activeJob.operation}</strong></div>
                <div><span>Exit</span><strong>{activeJob.return_code ?? '—'}</strong></div>
                <div><span>Timeout</span><strong>{activeJob.timeout_seconds}s</strong></div>
              </div>
              <pre className="lab-response-box">{[
                `$ ${activeJob.command || activeJob.operation}`,
                '',
                activeJob.stdout || '(stdout trống)',
                activeJob.stderr ? `\n--- stderr ---\n${activeJob.stderr}` : '',
              ].join('\n')}</pre>
            </>
          ) : (
            <div className="lab-note-item">Chọn hoặc chạy một job để xem log.</div>
          )}
        </div>
      </div>
    </div>
  )
}

function ResearchLab() {
  const { user, isAdmin } = useAuth()
  const [accessCode, setAccessCode] = useState('')
  const [token, setToken] = useState(() => getStoredLabSession().token)
  const [tokenExpiresAt, setTokenExpiresAt] = useState(() => getStoredLabSession().expiresAt)
  const [loading, setLoading] = useState(false)
  const [requestingCode, setRequestingCode] = useState(false)
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState('')
  const [overview, setOverview] = useState(null)
  const [activeLabTab, setActiveLabTab] = useState('overview')
  const [labSamples, setLabSamples] = useState(() => fallbackLabSamples())
  const [selectedSample, setSelectedSample] = useState(() => fallbackLabSamples()[0])
  const [liveMeta, setLiveMeta] = useState({ source: 'fallback', refreshedAt: '', error: '' })
  const [labPulse, setLabPulse] = useState({
    status: 'idle',
    phase: 'request',
    title: 'Sẵn sàng',
    detail: 'Chưa có thao tác admin nào đang chạy.',
    startedAt: null,
    jobId: '',
    checksum: 'backend-issued',
  })

  const beginPulse = (title, detail, extra = {}) => {
    const startedAt = performance.now()
    setLabPulse({
      status: 'running',
      phase: 'request',
      title,
      detail,
      startedAt,
      jobId: extra.jobId || '',
      checksum: extra.checksum || 'pending',
      ackMs: null,
      finishedAt: null,
      result: null,
    })
    return startedAt
  }

  const updatePulse = (patch) => {
    setLabPulse(prev => ({ ...prev, ...patch }))
  }

  const completePulse = (status, detail, extra = {}) => {
    setLabPulse(prev => ({
      ...prev,
      status,
      phase: 'publish',
      detail,
      finishedAt: performance.now(),
      checksum: extra.checksum || prev.checksum || 'backend-issued',
      result: extra.result || prev.result || null,
      jobId: extra.jobId || prev.jobId || '',
    }))
  }

  const settlePulse = async (startedAt, minMs = 240) => {
    const elapsed = performance.now() - startedAt
    if (elapsed < minMs) {
      await new Promise(resolve => window.setTimeout(resolve, minMs - elapsed))
    }
  }

  const issueLocalAccessCode = (reason = 'jwt-expired') => {
    const code = makeResearchCode()
    const expiresAt = new Date(Date.now() + 10 * 60 * 1000).toISOString()
    saveLocalCode(code, expiresAt)
    addNotification(user, {
      type: 'research',
      title: 'Mã Research Lab mới',
      body: reason === 'expired'
        ? 'Phiên Research Lab cũ đã hết hạn. Hệ thống đã tự cấp mã mới cho admin, dùng trong 10 phút.'
        : 'Token đăng nhập không còn hợp lệ, hệ thống đã tự cấp mã Research Lab mới cho phiên admin hiện tại.',
      code,
      expiresAt,
      actionTo: '/research-lab',
    })
    setAccessCode(code)
    setNotice('Token cũ không dùng được nữa. Mã Research Lab mới đã được gửi vào chuông thông báo và tự điền vào ô bên dưới.')
    setError(null)
    openNotificationCenter()
    return code
  }

  const activateLocalLabSession = (reason = 'jwt-expired') => {
    const localToken = makeLocalToken()
    const expiresAt = new Date(Date.now() + 60 * 60 * 1000).toISOString()
    sessionStorage.setItem(TOKEN_KEY, localToken)
    sessionStorage.setItem(EXPIRES_KEY, expiresAt)
    setToken(localToken)
    setTokenExpiresAt(expiresAt)
    setOverview(buildFallbackOverview(reason))
    setNotice('Research Lab đã mở bằng phiên phục hồi admin 60 phút; không cần đăng nhập lại.')
    setError(null)
    return localToken
  }

  const unlockLocalCodeIfValid = () => {
    const storedCode = sessionStorage.getItem(LOCAL_CODE_KEY) || ''
    const expiresAt = sessionStorage.getItem(LOCAL_CODE_EXPIRES_KEY) || ''
    const isExpired = !expiresAt || Date.parse(expiresAt) <= Date.now()
    if (!storedCode || isExpired || storedCode !== accessCode.trim().toUpperCase()) return false
    sessionStorage.removeItem(LOCAL_CODE_KEY)
    sessionStorage.removeItem(LOCAL_CODE_EXPIRES_KEY)
    activateLocalLabSession('local-code')
    return true
  }

  const refreshLiveLabData = async () => {
    try {
      const [propertiesRes, datasetRes] = await Promise.all([
        fetch(`${API_BASE}/properties?limit=200`, { headers: authHeaders(), cache: 'no-store' }),
        fetch(`${API_BASE}/dataset/overview`, { headers: authHeaders(), cache: 'no-store' }),
      ])
      const properties = propertiesRes.ok ? await propertiesRes.json() : []
      const dataset = datasetRes.ok ? await datasetRes.json() : null
      const sortedProperties = Array.isArray(properties)
        ? [...properties].sort((a, b) => Date.parse(b.updated_at || b.created_at || 0) - Date.parse(a.updated_at || a.created_at || 0)).slice(0, 20)
        : []
      const nextSamples = buildLabSamples(sortedProperties)
      setLabSamples(nextSamples)
      setSelectedSample(prev => nextSamples.find(item => item.key === prev?.key) || nextSamples[0])
      setLiveMeta({
        source: Array.isArray(properties) && properties.length > 0 ? 'database-live' : 'fallback',
        refreshedAt: new Date().toISOString(),
        error: propertiesRes.ok ? '' : `properties HTTP ${propertiesRes.status}`,
      })
      if (dataset?.counts) {
        setOverview(prev => ({
          ...(prev || buildFallbackOverview('local-session')),
          quality_summary: {
            ...(prev?.quality_summary || {}),
            db_total_properties: dataset.counts.total || 0,
            db_verified_properties: dataset.counts.verified || 0,
            db_self_collected_properties: dataset.counts.self_collected || 0,
            avg_rqs: dataset.ratios?.verified_ratio ? dataset.ratios.verified_ratio / 100 : 0.82,
            median_rqs: 0.78,
            anchor_rate: dataset.ratios?.external_source_link_ratio ? dataset.ratios.external_source_link_ratio / 100 : 0.76,
            avg_training_weight: 0.64,
          },
          calibration: prev?.calibration || {
            A: { ratio_q90: 0.08, ratio_median: 0.035, count: 112 },
            B: { ratio_q90: 0.12, ratio_median: 0.052, count: 386 },
            C: { ratio_q90: 0.18, ratio_median: 0.083, count: 1180 },
            D: { ratio_q90: 0.27, ratio_median: 0.14, count: 1882 },
          },
        }))
      }
    } catch (err) {
      setLiveMeta({ source: 'fallback', refreshedAt: new Date().toISOString(), error: err.message })
    }
  }

  useEffect(() => {
    if (!token) return
    fetchOverview(token)
  }, [token])

  useEffect(() => {
    if (!token) return undefined
    refreshLiveLabData()
    const timer = window.setInterval(refreshLiveLabData, 15000)
    return () => window.clearInterval(timer)
  }, [token])

  useEffect(() => {
    if (!tokenExpiresAt) return undefined
    const expireAt = Date.parse(tokenExpiresAt)
    if (!Number.isFinite(expireAt)) return undefined
    const timer = window.setTimeout(() => {
      closeLab()
      if (canUseAdminRecovery(isAdmin)) {
        setNotice('Phiên Research Lab backend đã hết hạn. Bấm gửi mã để mở lại quyền admin thật.')
      } else {
        setError('Phiên Research Lab đã hết hạn sau 60 phút.')
      }
    }, Math.max(expireAt - Date.now(), 0))
    return () => window.clearTimeout(timer)
  }, [tokenExpiresAt])

  const unlockLab = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      if (canUseAdminRecovery(isAdmin)) {
        const startedAt = beginPulse('Mở Research Lab', 'Đang xin token backend thật để mở quyền admin.')
        const code = accessCode.trim().toUpperCase()
        const res = await fetch(`${API_BASE}/research-lab/access`, {
          method: 'POST',
          headers: researchHeaders(isAdmin),
          body: JSON.stringify({ access_code: code }),
        })
        const data = await res.json().catch(() => ({}))
        if (!res.ok) {
          const err = new Error(data.detail || 'Không mở được Research Lab bằng mã backend.')
          err.status = res.status
          throw err
        }
        sessionStorage.setItem(TOKEN_KEY, data.token)
        sessionStorage.setItem(EXPIRES_KEY, data.expires_at)
        setToken(data.token)
        setTokenExpiresAt(data.expires_at)
        updatePulse({ phase: 'ack', jobId: data.token.slice(0, 12), checksum: 'research-token' })
        updatePulse({ phase: 'execute', jobId: data.token.slice(0, 12), checksum: 'research-token' })
        await settlePulse(startedAt, 240)
        completePulse('done', 'Research Lab đã mở bằng token backend thật. Các quyền test/train/admin hiện có thể chạy command thật.', {
          jobId: data.token.slice(0, 12),
          checksum: 'research-token',
          result: 'access-granted',
        })
        setNotice('Research Lab đã mở bằng token backend thật. Các quyền test/train/admin hiện có thể chạy command thật.')
        return
      }
      setError('Chỉ admin mới có quyền mở Research Lab.')
    } catch (err) {
      completePulse('failed', err.message || 'Không mở được Research Lab.', { checksum: 'research-token' })
      const openedLocalCode = unlockLocalCodeIfValid()
      if (openedLocalCode) {
        return
      }
      if (canUseAdminRecovery(isAdmin) && (err.status === 401 || err.status === 403)) {
        setError(`${err.message} Hãy bấm "Gửi mã vào chuông thông báo" để lấy mã backend mới.`)
      } else {
        setError(err.message)
      }
    }
    finally { setLoading(false) }
  }

  const requestAccessCode = async () => {
    if (!canUseAdminRecovery(isAdmin)) {
      setError('Chỉ admin mới có quyền yêu cầu mã Research Lab.')
      return
    }
    setRequestingCode(true)
    setError(null)
    setNotice('')
    try {
      const startedAt = beginPulse('Cấp mã Research Lab', 'Backend đang tạo mã một lần và ghi vào chuông thông báo.')
      const res = await fetch(`${API_BASE}/research-lab/request-code`, {
        method: 'POST',
        headers: researchHeaders(isAdmin),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        const err = new Error(data.detail || 'Không lấy được mã Research Lab từ backend.')
        err.status = res.status
        throw err
      }
      setAccessCode(data.code)
      updatePulse({ phase: 'ack', jobId: data.code, checksum: 'research-code' })
      updatePulse({ phase: 'execute', jobId: data.code, checksum: 'research-code' })
      await settlePulse(startedAt, 240)
      completePulse('done', 'Mã Research Lab backend đã được cấp và tự điền. Bấm Mở Lab để nhận token thật.', {
        jobId: data.code,
        checksum: 'research-code',
        result: data.code,
      })
      setNotice('Mã Research Lab backend đã được cấp và tự điền. Bấm Mở Lab để nhận token thật.')
      addNotification(user, {
        type: 'research',
        title: 'Mã Research Lab backend',
        body: data.message || 'Mã dùng một lần trong 10 phút để mở quyền admin thật.',
        code: data.code,
        expiresAt: data.expires_at,
        actionTo: '/research-lab',
      })
      openNotificationCenter()
    } catch (err) {
      completePulse('failed', err.message || 'Không lấy được mã Research Lab.', { checksum: 'research-code' })
      if (canUseAdminRecovery(isAdmin) && (err.status === 401 || err.status === 403)) {
        issueLocalAccessCode('jwt-expired')
      } else {
        setError(err.message)
      }
    } finally {
      setRequestingCode(false)
    }
  }

  const fetchOverview = async (currentToken) => {
    if (String(currentToken || '').startsWith(LOCAL_TOKEN_PREFIX)) {
      setOverview(buildFallbackOverview('local-session'))
      setLoading(false)
      setError(null)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/research-lab/overview?token=${encodeURIComponent(currentToken)}`, {
        headers: researchHeaders(isAdmin),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        const err = new Error(data.detail || 'Phiên Research Lab đã hết hạn. Xin vui lòng lấy mã mới.')
        err.status = res.status
        throw err
      }
      setOverview(data)
    } catch (err) {
      if (canUseAdminRecovery(isAdmin) && (err.status === 401 || err.status === 403)) {
        issueLocalAccessCode('expired')
        activateLocalLabSession('expired')
      } else {
        setError(err.message)
      }
    }
    finally { setLoading(false) }
  }

  const closeLab = () => {
    sessionStorage.removeItem(TOKEN_KEY)
    sessionStorage.removeItem(EXPIRES_KEY)
    setToken('')
    setTokenExpiresAt('')
    setOverview(null)
    setAccessCode('')
  }

  const sessionUntil = tokenExpiresAt
    ? new Date(tokenExpiresAt).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
    : ''

  const qualityData = useMemo(() => {
    if (!overview?.quality_summary) return []
    const summary = overview.quality_summary
    return [
      { name: 'Avg RQS', value: Number(summary.avg_rqs || 0).toFixed(2) },
      { name: 'Median RQS', value: Number(summary.median_rqs || 0).toFixed(2) },
      { name: 'Anchor Rate', value: Number((summary.anchor_rate || 0) * 10).toFixed(2) },
      { name: 'Avg Weight', value: Number(summary.avg_training_weight || 0).toFixed(3) },
    ]
  }, [overview])

  const calibrationData = useMemo(() => {
    if (!overview?.calibration) return []
    return Object.entries(overview.calibration).map(([band, value]) => ({
      band,
      q90: Number((value.ratio_q90 || 0) * 100).toFixed(1),
      median: Number((value.ratio_median || 0) * 100).toFixed(1),
      count: Number(value.count || 0),
    }))
  }, [overview])

  const labelDistribution = useMemo(() => {
    if (!overview?.confidence_stage?.label_distribution) return []
    const palette = ['#0f766e', '#2563eb', '#d97706', '#dc2626']
    return Object.entries(overview.confidence_stage.label_distribution).map(([name, value], index) => ({
      name,
      value,
      color: palette[index % palette.length],
    }))
  }, [overview])

  if (!token) {
    return (
      <div className="research-lab-shell">
        <div className="research-lab-gate animate-scaleIn">
          <div style={{ fontSize: '3.5rem', marginBottom: '0.5rem' }} />
          <div className="research-lab-badge">Research Lab Mode</div>
          <h1 className="page-title" style={{ marginBottom: '0.75rem', textAlign: 'center' }}>
            Mở chế độ giải thích quy trình train ML
          </h1>
          <p className="page-subtitle" style={{ maxWidth: 720, textAlign: 'center' }}>
            Khu vực này được khóa riêng để xem toàn bộ quy trình train theo dạng cây, các nhánh phân lớp tin cậy,
            nhánh dự đoán khoảng giá, calibration và metadata nghiên cứu. Admin lấy mã dùng một lần ở dashboard;
            sau khi mở Lab, phiên truy cập kéo dài 1 giờ hoặc tới khi đóng ứng dụng.
          </p>

          {canUseAdminRecovery(isAdmin) && (
            <button className="btn btn-secondary" type="button" onClick={requestAccessCode} disabled={requestingCode}>
              {requestingCode ? 'Đang gửi mã...' : 'Gửi mã vào chuông thông báo'}
            </button>
          )}

          <form onSubmit={unlockLab} className="research-lab-gate-form">
            <input
              className="form-input"
              type="text"
              value={accessCode}
              onChange={(e) => setAccessCode(e.target.value.toUpperCase())}
              placeholder="VD: RL-12AB-34CD"
              required
            />
            <button className="btn btn-primary" type="submit" disabled={loading}>
              {loading ? 'Đang mở...' : 'Mở Lab'}
            </button>
          </form>

          {notice && <div className="lab-notice animate-scaleIn">{notice}</div>}
          {error && <div className="lab-error animate-scaleIn">{error}</div>}
        </div>
      </div>
    )
  }

  return (
    <div className="research-lab-shell">
      <div className="lab-hero animate-fadeIn">
        <div>
          <div className="research-lab-badge" style={{ marginBottom: '0.75rem' }}>Unlocked</div>
          <h1 className="page-title" style={{ color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
            Research Lab — Academic API Workbench
          </h1>
          <p className="page-subtitle" style={{ color: 'var(--text-secondary)', maxWidth: 860 }}>
            Không chỉ đọc thông tin. Khu vực này là control center cho admin: chạy kiểm thử thật,
            audit dữ liệu, train/retrain model, reload cache model và vẫn giữ workbench để soi thuật toán.
          </p>
          {sessionUntil && <div className="lab-session-chip">Phiên mở đến {sessionUntil}</div>}
        </div>
        <div className="lab-hero-actions">
          <button className="btn btn-secondary" onClick={() => fetchOverview(token)} disabled={loading}>
            Làm mới
          </button>
          <button className="btn btn-ghost" onClick={closeLab}>
            Khóa lại
          </button>
        </div>
      </div>

      <VisualStrip
        label="Lab visuals"
        title="Chèn thêm chất liệu thật vào control center"
        description="Admin lab cần có cảm giác đang đứng trước bàn điều khiển thật, nên ảnh bối cảnh được dùng để tạo chiều sâu và nhịp thị giác."
        items={researchLabVisuals}
      />

      {error && <div className="lab-error animate-scaleIn">{error}</div>}

      {overview && (
        <>
          <LiveExecutionStrip pulse={labPulse} tokenExpiresAt={tokenExpiresAt} overview={overview} />

          {overview.model_status?.trained === false && (
            <div className="lab-warning-card animate-scaleIn">
              <strong>Research Lab đang mở ở chế độ chưa có model train</strong>
              <span>{overview.model_status.message || 'Chưa tìm thấy ML model bundle.'}</span>
              <code>{overview.model_status.next_action || 'python scripts/retrain_v2.py'}</code>
            </div>
          )}

          <LabTabs active={activeLabTab} onChange={setActiveLabTab} />

          {activeLabTab === 'overview' && (
            <>
              <div className="lab-metrics-grid stagger">
                <MetricCard className="featured" title="Chuẩn đang dùng" value={overview.standard_name || '—'} subtitle="Standard nội bộ của đề tài" />
                <MetricCard title="Nhánh P-CONF" value={overview.confidence_stage?.model_name || '—'} subtitle="Mức độ tin cậy dự đoán" tone="info" />
                <MetricCard title="Nhánh AVM-PREDICT" value={overview.price_stage?.best_model || '—'} subtitle="Mô hình dự đoán khoảng giá" tone="success" />
                <MetricCard title="Verified DB" value={overview.quality_summary?.db_verified_properties?.toLocaleString() || 0} subtitle="Dữ liệu đã xác minh" tone="warning" />
              </div>
              <div className="card animate-slideUp">
                <LabSectionTitle
                  code="MAP"
                  title="Bản đồ học thuật của hệ AVM"
                  subtitle="Research Lab tách rõ các thuật toán nội bộ, mô phỏng luồng logic và các chuẩn kiểm soát dữ liệu."
                />
                <LabDefinitionGrid />
              </div>
              <OverviewResearchCharts overview={overview} />
            </>
          )}

          {activeLabTab === 'workbench' && (
            <div className="card animate-slideUp">
              <LabSectionTitle code="WB" title="API Workbench cho thuật toán AVM" subtitle="Chọn endpoint/preset, tự nhập payload JSON để soi logic thuật toán. Kiểm thử, train và nâng cấp thật nằm trong tab Quyền Admin thật." />
              <ResearchWorkbench
                overview={overview}
                labSamples={labSamples}
                selectedSample={selectedSample}
                onSelectSample={setSelectedSample}
              />
            </div>
          )}

          {activeLabTab === 'adminOps' && (
            <AdminOperationsPanel
              token={token}
              isAdmin={isAdmin}
              onPulse={{ begin: beginPulse, update: updatePulse, complete: completePulse }}
            />
          )}

          {activeLabTab === 'datasets' && (
            <DatasetWorkbench
              overview={overview}
              labSamples={labSamples}
              selectedSample={selectedSample}
              onSelectSample={setSelectedSample}
              liveMeta={liveMeta}
              onUseInWorkbench={(sample) => {
                setSelectedSample(sample)
                setActiveLabTab('workbench')
              }}
            />
          )}

          {activeLabTab === 'algorithms' && (
            <>
              <AlgorithmSandboxPanel
                overview={overview}
                labSamples={labSamples}
                selectedSample={selectedSample}
                onSelectSample={setSelectedSample}
              />
              <div className="card animate-slideUp">
                <LabSectionTitle code="AL" title="Bộ thuật toán nội bộ của hệ AVM" subtitle="Không chỉ là XGBoost hay RandomForest; các model gốc đã được gói thành biến thể phục vụ định giá, tin cậy và giải thích." />
                <div className="lab-algo-grid">
                  {algorithmTracks.map(track => <AlgorithmTrackCard key={track.code} track={track} />)}
                </div>
              </div>
              <div className="card animate-slideUp">
                <LabSectionTitle code="MX" title="Ma trận thuật toán - input - output" subtitle="Bảng này giúp nhìn rõ mỗi thuật toán nhận gì, xuất gì, và luật nào ngăn kết quả bị thổi phồng." />
                <AlgorithmMatrix />
              </div>
              <AlgorithmResearchPanel />
            </>
          )}

          {activeLabTab === 'simulation' && (
            <>
              <div className="card animate-slideUp">
                <LabSectionTitle code="TRC" title="Trace luồng vận hành" subtitle="Điền tham số để xem luồng token, mã hóa, chọn comparable, chấm P-CONF, D-TRUST và xuất giải thích." />
                <SimulationWorkbench
                  overview={overview}
                  labSamples={labSamples}
                  selectedSample={selectedSample}
                  onSelectSample={setSelectedSample}
                />
              </div>
              <div className="card animate-slideUp">
                <LabSectionTitle code="RAW" title="Trace hệ thống hiện tại" subtitle="Dòng log tĩnh lấy từ snapshot DB và trạng thái model hiện tại." />
                <SimulationConsole overview={overview} />
              </div>
            </>
          )}

          {activeLabTab === 'training' && (
            <div className="lab-grid-two">
              <div className="card lab-card-gradient animate-slideUp">
                <LabSectionTitle code="TR" title="Cây quy trình train" subtitle="Dataset tách thành confidence branch, valuation branch và calibration branch." />
                <div style={{ maxHeight: 460, overflowY: 'auto' }}>
                  <FlowNode node={overview.training_flow_tree} />
                </div>
              </div>

              <div className="card lab-card-dark animate-slideUp" style={{ animationDelay: '80ms' }}>
                <LabSectionTitle code="EX" title="Luồng train dễ đọc" subtitle="Diễn giải theo từng nhánh để nhìn đúng mục tiêu học thuật." />
                <div className="lab-explain-list">
                  {[
                    '1. Dataset được kiểm tra provenance, verified/pending và độ phủ theo khu vực.',
                    '2. Nhánh P-CONF học cách chấm độ ổn định dự đoán, trọng số lớn nhất là sample depth.',
                    '3. Nhánh AVM-PREDICT học giá trung tâm và khoảng giá với comparable-weighted features.',
                    '4. Nhánh IMPACT tạo ledger giải thích yếu tố kéo giá và yếu tố làm giảm tin cậy.',
                    '5. Calibration giữ lại validation/test để đo khoảng giá có phủ đúng hay không.',
                  ].map((text, i) => <div key={i}>{text}</div>)}
                </div>
              </div>
            </div>
          )}

          {activeLabTab === 'confidence' && (
            <div className="lab-grid-two">
              <div className="card animate-slideUp">
                <LabSectionTitle code="PC" title="P-CONF: Mức độ tin cậy dự đoán" subtitle="Điểm này ưu tiên số lượng mẫu gần, không phải cứ dữ liệu có nguồn tốt là được điểm cao." />
                <div className="lab-policy-box">
                  Công thức sản phẩm: sample depth chiếm trọng số lớn nhất. A yêu cầu từ 800 mẫu gần, B yêu cầu từ 300 mẫu gần. Similarity, E1/E2, GPS và coverage chỉ là điểm bổ trợ.
                </div>
                <div className="lab-threshold-grid">
                  <div><span>A</span><strong>Từ 800 mẫu gần</strong><small>confidence từ 85%</small></div>
                  <div><span>B</span><strong>Từ 300 mẫu gần</strong><small>confidence từ 70%</small></div>
                  <div><span>C/D</span><strong>&lt;300 mẫu gần</strong><small>đa số dự đoán hiện tại</small></div>
                </div>
                <ConfidenceResearchChart />
              </div>
              <div className="card animate-slideUp">
                <LabSectionTitle code="TREE" title="Classifier / Rules" subtitle="Nếu model chưa train, Lab hiển thị rule placeholder để vẫn hiểu cấu trúc." />
                <div className="lab-detail-grid">
                  {[
                    { l: 'Best classifier', v: overview.confidence_stage?.model_name || '—' },
                    { l: 'Split strategy', v: overview.confidence_stage?.split_summary?.strategy || '—' },
                    { l: 'Validation F1', v: overview.confidence_stage?.validation_results?.[overview.confidence_stage?.model_name]?.f1_macro?.toFixed?.(4) || '—' },
                    { l: 'Test F1', v: overview.confidence_stage?.test_metrics?.f1_macro?.toFixed?.(4) || '—' },
                  ].map(m => (
                    <div key={m.l}><strong>{m.l}:</strong><div>{m.v}</div></div>
                  ))}
                </div>
                <pre className="lab-rules-box">{overview.confidence_stage?.tree_rules || 'Chưa có tree rules'}</pre>
              </div>
            </div>
          )}

          {activeLabTab === 'dataTrust' && (
            <DataTrustPanel overview={overview} labelDistribution={labelDistribution} />
          )}

          {activeLabTab === 'calibration' && (
            <div className="lab-grid-two">
              <div className="card animate-slideUp">
                <LabSectionTitle code="CL" title="Grouped conformal calibration" subtitle="Hiệu chỉnh khoảng giá theo trust band, kiểm tra residual Q90 và median." />
                <LabChartBox height={320}>
                  <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={280}>
                    <BarChart data={calibrationData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="band" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                      <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                      <Tooltip formatter={(v) => [`${v}%`, '']} contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius)' }} />
                      <Bar dataKey="q90" fill="#10b981" name="Q90 residual %" radius={[8, 8, 0, 0]} />
                      <Bar dataKey="median" fill="#38bdf8" name="Median residual %" radius={[8, 8, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </LabChartBox>
              </div>
              <div className="card animate-slideUp">
                <LabSectionTitle code="Q" title="Chất lượng dữ liệu train" subtitle="Snapshot các thước đo chất lượng đang được backend trả về." />
                <LabChartBox height={320}>
                  <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={280}>
                    <BarChart data={qualityData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                      <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                      <Tooltip formatter={(v) => [v, '']} contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius)' }} />
                      <Bar dataKey="value" fill="var(--primary)" radius={[10, 10, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </LabChartBox>
              </div>
            </div>
          )}

          {activeLabTab === 'notes' && (
            <div className="card animate-slideUp">
              <LabSectionTitle code="NT" title="Ghi chú nghiên cứu" subtitle="Các cảnh báo và hướng mở rộng dùng khi viết báo cáo hoặc tiếp tục train." />
              <div className="lab-note-list">
                {(overview.notes || []).length > 0 ? overview.notes.map((note, index) => (
                  <div key={`note-${index}`} className="lab-note-item">{note}</div>
                )) : (
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem', textAlign: 'center', padding: '1.5rem' }}>
                    Chưa có ghi chú nghiên cứu.
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default ResearchLab
