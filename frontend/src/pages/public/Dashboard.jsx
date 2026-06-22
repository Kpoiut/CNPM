import React, { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  PieChart, Pie, Cell, Legend,
} from 'recharts'
import { PROPERTY_TYPES } from '../../constants/vnStrings'
import {
  StatCard,
  Badge,
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  ProgressBar,
  SkeletonStatCard,
  SkeletonChart,
  Skeleton,
} from '../../components/ui'
import ChartWrapper from '../../components/ui/ChartWrapper'
import { LoadingOverlay } from '../../components/ui/skeleton'
import { useAuth } from '../../components/auth'
import { icon } from '../../components/ui/icons'
import { VISUAL_ASSETS } from '../../constants/visuals'
import { addNotification, openNotificationCenter } from '../../lib/notifications'
import { authFetch } from '../../api/client'
import {
  TIER_COLORS, EVIDENCE_LABELS, EVIDENCE_WEIGHTS, PRICE_RANGES,
  PROPERTY_TYPE_COLORS, PIE_CHART_COLORS, API_BASE,
} from '../../lib'

const PIE_COLORS = PIE_CHART_COLORS
const EvidenceColors = TIER_COLORS
const LOCAL_CODE_KEY = 'research_lab_local_code'
const LOCAL_CODE_EXPIRES_KEY = 'research_lab_local_code_expires_at'

function makeResearchCode() {
  const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
  const pick = (length) => Array.from({ length }, () => alphabet[Math.floor(Math.random() * alphabet.length)]).join('')
  return `RL-${pick(4)}-${pick(4)}`
}

function ResearchLabAccessPanel() {
  const { isAdmin, user } = useAuth()
  const [labCode, setLabCode] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  if (!isAdmin) return null

  const requestCode = async () => {
    setLoading(true)
    setError('')
    try {
      const code = makeResearchCode()
      const expiresAt = new Date(Date.now() + 10 * 60 * 1000).toISOString()
      sessionStorage.setItem(LOCAL_CODE_KEY, code)
      sessionStorage.setItem(LOCAL_CODE_EXPIRES_KEY, expiresAt)
      const data = { code, expires_at: expiresAt, local: true }
      setLabCode(data)
      addNotification(user, {
        type: 'research',
        title: 'Mã Research Lab mới',
        body: 'Admin session đã được xác thực trong dashboard. Mã dùng một lần và hết hạn sau 10 phút.',
        code: data.code,
        expiresAt: data.expires_at,
        actionTo: '/research-lab',
      })
      openNotificationCenter()
    } catch (err) {
      if (/401|403|Unauthorized|Token/i.test(err.message)) {
        const code = makeResearchCode()
        const expiresAt = new Date(Date.now() + 10 * 60 * 1000).toISOString()
        sessionStorage.setItem(LOCAL_CODE_KEY, code)
        sessionStorage.setItem(LOCAL_CODE_EXPIRES_KEY, expiresAt)
        const localCode = { code, expires_at: expiresAt, local: true }
        setLabCode(localCode)
        addNotification(user, {
          type: 'research',
          title: 'Mã Research Lab mới',
          body: 'Token đăng nhập đã hết hạn nên hệ thống tự cấp mã phục hồi cho admin. Mã dùng một lần trong 10 phút.',
          code,
          expiresAt,
          actionTo: '/research-lab',
        })
        openNotificationCenter()
      } else {
        setError(err.message)
      }
    } finally {
      setLoading(false)
    }
  }

  const expiresText = labCode?.expires_at
    ? new Date(labCode.expires_at).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
    : ''

  return (
    <Card style={{ marginBottom: '1.5rem', borderColor: 'var(--primary-200)', background: 'var(--gradient-hero)' }}>
      <CardHeader>
        <CardTitle style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {icon('unlock', 16)} Mã truy cập Research Lab
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', gap: '1rem', alignItems: 'center' }}>
          <div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '0.75rem' }}>
              Admin yêu cầu mã tại đây, hệ thống sẽ gửi vào chuông thông báo như một tin nhắn. Mã chỉ dùng một lần;
              sau khi mở Lab sẽ bị hủy, còn phiên Research Lab kéo dài 1 giờ hoặc tới khi đóng ứng dụng.
            </div>
            {labCode && (
              <div className="lab-code-message">
                <div>
                  <div className="lab-code-label">Đã gửi vào chuông thông báo</div>
                  <div className="lab-code-value">Mã Research Lab đã được lưu</div>
                </div>
                <div className="lab-code-meta">Hết hạn lúc {expiresText}</div>
              </div>
            )}
            {error && <div className="lab-error" style={{ marginTop: '0.75rem' }}>{error}</div>}
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
            <button className="btn btn-primary" type="button" onClick={requestCode} disabled={loading}>
              {loading ? 'Đang tạo...' : 'Yêu cầu mã'}
            </button>
            {labCode?.code && (
              <button className="btn btn-secondary" type="button" onClick={openNotificationCenter}>
                Mở chuông
              </button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function Dashboard() {
  const {
    data: stats,
    dataUpdatedAt: statsUpdatedAt,
    isLoading: statsLoading,
    error: statsError,
    refetch: refetchStats,
  } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      const res = await authFetch(`${API_BASE}/dashboard/stats`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      return res.json()
    },
    staleTime: 20_000,
    refetchInterval: 30_000,
    retry: 2,
  })

  const { data: propertiesData, isLoading: chartsLoading, error: chartsError, refetch: refetchProperties } = useQuery({
    queryKey: ['dashboard-properties'],
    queryFn: async () => {
      const res = await authFetch(`${API_BASE}/properties?limit=5000`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      return res.json()
    },
    staleTime: 45_000,
    refetchInterval: 60_000,
    retry: 2,
  })

  const { data: scopesData } = useQuery({
    queryKey: ['provinces'],
    queryFn: async () => {
      const res = await fetch('/api/provinces')
      if (!res.ok) return null
      return res.json()
    },
    staleTime: 10 * 60 * 1000,
  })

  const servingModel = stats?.serving_model || stats?.latest_model

  const {
    typeData, provinceData, priceData, evidenceData, dbEmpty,
    totalDistrictCount,
  } = useMemo(() => {
    const data = Array.isArray(propertiesData) ? propertiesData : []
    if (data.length === 0) {
      return { typeData: [], provinceData: [], priceData: [], evidenceData: [], dbEmpty: Array.isArray(propertiesData), totalDistrictCount: 0 }
    }

    const typeCounts = {}
    data.forEach(p => { typeCounts[p.property_type] = (typeCounts[p.property_type] || 0) + 1 })

    const provinceCounts = {}
    data.forEach(p => { provinceCounts[p.province_city] = (provinceCounts[p.province_city] || 0) + 1 })

    const evCounts = {}
    data.forEach(p => { evCounts[p.evidence_tier || 'E5'] = (evCounts[p.evidence_tier || 'E5'] || 0) + 1 })

    const scopeList = scopesData?.data?.scopes || scopesData?.provinces || []
    const districtCount = scopeList.length
      ? scopeList.reduce((sum, s) => sum + (s.district_count || s.districts?.length || 0), 0)
      : 0

    const evidenceRows = Object.keys(EVIDENCE_LABELS).map(k => ({
      name: EVIDENCE_LABELS[k],
      key: k,
      value: evCounts[k] || 0,
      fill: EvidenceColors[k],
      weight: EVIDENCE_WEIGHTS[k],
    }))
    const evidenceRankMap = [...evidenceRows]
      .sort((a, b) => b.value - a.value)
      .reduce((acc, item, index) => {
        acc[item.key] = item.value > 0 ? index + 1 : null
        return acc
      }, {})

    return {
      typeData: Object.entries(typeCounts).map(([name, value]) => ({
        name: PROPERTY_TYPES[name] || name,
        value,
        key: name,
        fill: PROPERTY_TYPE_COLORS[name] || PIE_COLORS[Object.keys(typeCounts).indexOf(name) % PIE_COLORS.length],
      })),
      provinceData: Object.entries(provinceCounts).sort((a, b) => b[1] - a[1]).slice(0, 8)
        .map(([name, value]) => ({ name, value })),
      priceData: PRICE_RANGES.map(r => ({
        name: r.name,
        count: data.filter(p => p.price >= r.min && p.price < r.max).length,
      })),
      evidenceData: evidenceRows.map(item => ({
        ...item,
        countRank: evidenceRankMap[item.key],
        share: data.length ? (item.value / data.length) * 100 : 0,
      })),
      dbEmpty: false,
      totalDistrictCount: districtCount,
    }
  }, [propertiesData, scopesData])

  const confidenceCounts = useMemo(() => {
    const serverCounts = stats?.confidence_distribution || null
    const fromServer = {
      confidence_a: Number(stats?.confidence_a ?? serverCounts?.A ?? 0),
      confidence_b: Number(stats?.confidence_b ?? serverCounts?.B ?? 0),
      confidence_c: Number(stats?.confidence_c ?? serverCounts?.C ?? 0),
      confidence_d: Number(stats?.confidence_d ?? serverCounts?.D ?? 0),
    }
    if (Object.values(fromServer).some(v => v > 0)) return { ...fromServer, source: stats?.confidence_source || 'server' }

    const rows = Array.isArray(propertiesData) ? propertiesData : []
    const groupCounts = rows.reduce((acc, row) => {
      const key = [row.property_type || 'unknown', row.province_city || row.city || '', row.district || ''].join('|')
      acc[key] = (acc[key] || 0) + 1
      return acc
    }, {})
    const fallback = { confidence_a: 0, confidence_b: 0, confidence_c: 0, confidence_d: 0, source: 'client p-conf sample-depth gate' }
    rows.forEach(row => {
      const key = [row.property_type || 'unknown', row.province_city || row.city || '', row.district || ''].join('|')
      const closeCount = groupCounts[key] || 0
      if (closeCount >= 800) fallback.confidence_a += 1
      else if (closeCount >= 300) fallback.confidence_b += 1
      else if (closeCount >= 100) fallback.confidence_c += 1
      else fallback.confidence_d += 1
    })
    return fallback
  }, [stats, propertiesData])

  const fmt = (n) => n >= 1e9 ? `${(n/1e9).toFixed(1)}B` : n >= 1e6 ? `${(n/1e6).toFixed(0)}M` : String(n)
  const fmtPrice = (n) => new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(n || 0)

  const isLoading = statsLoading || chartsLoading
  if (isLoading && !stats) return <LoadingOverlay message="Đang tải dữ liệu thống kê..." />

  if (statsError && !stats) return (
    <div className="card" style={{ margin: '1rem', background: 'var(--danger-bg)', border: '1px solid var(--danger-border)' }}>
      {icon('alertTriangle', 18)} <strong>Lỗi tải dữ liệu:</strong> {statsError.message}
    </div>
  )

  if (!stats) return null

  const scRatio = stats.self_collected_ratio || 0

  return (
    <div>
      <div className="dashboard-hero animate-fadeIn">
        <div className="dashboard-hero-copy">
          <div className="dashboard-hero-eyebrow">Bảng điều hành dữ liệu</div>
          <h1 className="dashboard-hero-title">Thống kê dữ liệu nghiên cứu</h1>
          <p className="dashboard-hero-description">
            Tổng quan đọc trực tiếp từ database: bản ghi, provenance, evidence tier, và trạng thái model hiện tại.
          </p>
          <div className="dashboard-hero-points">
            <span className="dashboard-hero-chip">{fmt(stats.total_records || 0)} bản ghi</span>
            <span className="dashboard-hero-chip">{Math.round(((stats.by_verification?.verified || 0) / (stats.total_records || 1)) * 100)}% verified</span>
            <span className="dashboard-hero-chip">Self-collected {scRatio.toFixed(1)}%</span>
            <span className="dashboard-hero-chip">{String(totalDistrictCount || 0)} quận trong scope</span>
          </div>
          <div className="dashboard-hero-meta">
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => { refetchStats(); refetchProperties() }}
              disabled={isLoading}
              style={{ padding: '0.55rem 0.85rem' }}
            >
              {icon('refreshCw', 14)} Làm mới
            </button>
            <div className="dashboard-hero-meta-item">
              <strong>Source</strong>
              <span>Đọc từ database thật · cache 5 phút</span>
            </div>
            <div className="dashboard-hero-meta-item">
              <strong>Model</strong>
              <span>{servingModel?.model_name || 'Chưa có model train'}</span>
            </div>
          </div>
        </div>

        <div className="dashboard-hero-media">
          <div className="dashboard-hero-shot">
            <img src={VISUAL_ASSETS.citySkyline} alt="Đường chân trời thị trường BĐS" />
            <div className="dashboard-hero-shot-label">
              <span className="dashboard-hero-shot-kicker">Market pulse</span>
              <strong>Đọc bức tranh thị trường theo vùng</strong>
              <span>Top tỉnh / thành, phân bố loại tài sản và nhịp truy vấn model.</span>
            </div>
          </div>
          <div className="dashboard-hero-mini-stack">
            <div className="dashboard-hero-mini">
              <img src={VISUAL_ASSETS.houseExterior} alt="Nguồn cung bản ghi nhà ở" />
              <div className="dashboard-hero-mini-label">
                <span className="dashboard-hero-shot-kicker">Supply</span>
                <strong>Nguồn bản ghi thật</strong>
                <span className="dashboard-hero-mini-caption">Độ phủ verified / provenance.</span>
              </div>
            </div>
            <div className="dashboard-hero-mini">
              <img src={VISUAL_ASSETS.officeInterior} alt="Khu vận hành Research Lab" />
              <div className="dashboard-hero-mini-label">
                <span className="dashboard-hero-shot-kicker">Ops</span>
                <strong>Research Lab / Train</strong>
                <span className="dashboard-hero-mini-caption">Luồng kiểm thử và training admin.</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="dashboard-live-strip">
        <div className="dashboard-live-chip">
          {icon('database', 16)}
          <span>Dữ liệu thống kê đang đọc trực tiếp từ database</span>
        </div>
        <div className="dashboard-live-chip">
          {icon('barChart3', 16)}
          <span>{(Array.isArray(propertiesData) ? propertiesData.length : 0).toLocaleString('vi-VN')} record dùng cho biểu đồ</span>
        </div>
        <div className="dashboard-live-chip">
          {icon('shieldCheck', 16)}
          <span>{confidenceCounts.source || 'server'} confidence gate</span>
        </div>
        <div className="dashboard-live-chip">
          {icon('clock', 16)}
          <span>
            Cập nhật {statsUpdatedAt
              ? new Date(statsUpdatedAt).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
              : 'đang đồng bộ'}
          </span>
        </div>
      </div>

      <ResearchLabAccessPanel />

      {chartsError && (
        <div className="card mb-6" style={{ background: 'var(--danger-bg)', border: '1px solid var(--danger-border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: 'var(--danger)' }}>
            {icon('alertTriangle', 18)}
            <strong>Lỗi tải dữ liệu biểu đồ:</strong>
            <span>{chartsError.message}</span>
          </div>
        </div>
      )}

      {/* DB Empty Warning */}
      {dbEmpty && (
        <div className="card mb-6" style={{ background: 'var(--warning-bg)', border: '1px solid var(--warning-border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            {icon('alertTriangle', 18, '')}
            <div>
              <div style={{ fontWeight: 600, color: 'var(--warning)' }}>Cơ sở dữ liệu trống</div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Không có bản ghi thật trong database nên dashboard chưa thể vẽ biểu đồ.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Stat Cards Grid */}
      <div className="dashboard-kpi-grid" style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
        gap: '0.75rem',
        marginBottom: '1.5rem',
      }}>
        <StatCard
          icon={icon('database', 20)}
          label="Tổng bản ghi"
          value={stats.total_records?.toLocaleString() || '0'}
          sub={`+${stats.added_this_week || 0} tuần này`}
          delta="up"
          color="primary"
        />
        <StatCard
          icon={icon('checkCircle', 20)}
          label="Đã xác minh"
          value={stats.by_verification?.verified?.toLocaleString() || '0'}
          sub={`${Math.round((stats.by_verification?.verified || 0) / (stats.total_records || 1) * 100)}% verified`}
          delta={stats.by_verification?.verified > 0 ? 'up' : null}
          color="success"
        />
        <StatCard
          icon={icon('activity', 20)}
          label="Dữ liệu IoT"
          value={stats.iot_records?.toLocaleString() || '0'}
          sub={stats.iot_records > 0 ? 'IoT Active' : 'Không có IoT'}
          color="info"
        />
        <StatCard
          icon={icon('flask', 20)}
          label="Tự thu thập"
          value={`${scRatio.toFixed(1)}%`}
          sub={scRatio >= 3 ? `${icon('check', 12)} Đạt yêu cầu` : `${icon('alertTriangle', 12)} Cần thêm`}
          delta={scRatio >= 3 ? 'up' : 'down'}
          color={scRatio >= 3 ? 'success' : 'warning'}
        />
        <StatCard
          icon={icon('shieldCheck', 20)}
          label="Provenance"
          value={`${Math.round((stats.provenance_coverage || 0) * 100)}%`}
          sub="Full chain coverage"
          color="info"
        />
        <StatCard
          icon={icon('mapPin', 20)}
          label="Quận trong scope"
          value={String(totalDistrictCount || 0)}
          sub={scopesData?.data?.scopes
            ? scopesData.data.scopes.map(s => `${s.province}:${s.districts?.length || 0}`).join(' | ')
            : 'Đang tải...'}
          color="primary"
        />
      </div>

      {/* Charts Row 1 */}
      <div className="dashboard-grid-two" style={{ marginBottom: '1.25rem' }}>
        {/* Property Type Pie */}
        <Card>
          <CardHeader>
            <CardTitle style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              {icon('pieChart', 14)} Phân bố loại bất động sản
            </CardTitle>
          </CardHeader>
          <CardContent>
            {typeData.length > 0 ? (
              <ChartWrapper height={220}>
                <PieChart>
                  <Pie
                    data={typeData}
                    cx="50%" cy="50%"
                    innerRadius={55} outerRadius={90}
                    paddingAngle={2} dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {typeData.map((entry, idx) => (
                      <Cell key={idx} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v) => [v.toLocaleString(), 'Bản ghi']} />
                  <Legend wrapperStyle={{ fontSize: 12, color: 'var(--text-muted)' }} />
                </PieChart>
              </ChartWrapper>
            ) : (
              <div style={{ height: 220, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <SkeletonChart height={200} />
              </div>
            )}
          </CardContent>
        </Card>

        {/* Province Bar */}
        <Card>
          <CardHeader>
            <CardTitle style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              {icon('globe', 14)} Phân bố theo tỉnh / TP
            </CardTitle>
          </CardHeader>
          <CardContent>
            {provinceData.length > 0 ? (
              <ChartWrapper height={220}>
                <BarChart data={provinceData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis type="number" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                  <YAxis
                    dataKey="name" type="category" width={120}
                    tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
                  />
                  <Tooltip formatter={(v) => [v.toLocaleString(), 'Bản ghi']} />
                  <Bar dataKey="value" fill="var(--primary)" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ChartWrapper>
            ) : (
              <SkeletonChart height={220} />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Price Distribution */}
      <Card className="dashboard-panel" style={{ marginBottom: '1.25rem' }}>
        <CardHeader>
          <CardTitle style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            {icon('trendingUp', 14)} Phân bố giá bất động sản
          </CardTitle>
        </CardHeader>
        <CardContent>
          {priceData.length > 0 ? (
            <ChartWrapper height={200}>
              <BarChart data={priceData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                <Tooltip formatter={(v) => [v.toLocaleString(), 'Số lượng']} />
                <Bar dataKey="count" fill="#06d6a0" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ChartWrapper>
          ) : <SkeletonChart height={200} />}
        </CardContent>
      </Card>

      {/* Verification + Origin */}
      <div className="dashboard-grid-split" style={{ marginBottom: '1.25rem' }}>
        <Card>
          <CardHeader>
            <CardTitle style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              {icon('checkCircle', 14)} Trạng thái xác minh
            </CardTitle>
          </CardHeader>
          <CardContent>
            {stats.by_verification ? (
              <ChartWrapper height={180}>
                <PieChart>
                  <Pie
                    data={[
                      { name: 'Đã xác minh', value: stats.by_verification.verified || 0, fill: 'var(--success)' },
                      { name: 'Chờ xác minh', value: stats.by_verification.pending || 0, fill: 'var(--warning)' },
                      { name: 'Bị từ chối', value: stats.by_verification.rejected || 0, fill: 'var(--danger)' },
                    ]}
                    cx="50%" cy="50%" outerRadius={75} dataKey="value"
                  >
                    {[
                      { fill: 'var(--success)' },
                      { fill: 'var(--warning)' },
                      { fill: 'var(--danger)' },
                    ].map((c, i) => <Cell key={i} fill={c.fill} />)}
                  </Pie>
                  <Tooltip />
                  <Legend wrapperStyle={{ fontSize: 12, color: 'var(--text-muted)' }} />
                </PieChart>
              </ChartWrapper>
            ) : <SkeletonChart height={180} />}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              {icon('database', 14)} Theo nguồn gốc dữ liệu
            </CardTitle>
          </CardHeader>
          <CardContent>
            {stats.by_origin ? (
              <ChartWrapper height={180}>
                <PieChart>
                  <Pie
                    data={[
                      { name: 'Tự thu thập', value: stats.by_origin.self_collected || 0, fill: 'var(--success)' },
                      { name: 'Công khai', value: stats.by_origin.public_collected || 0, fill: 'var(--primary)' },
                      { name: 'Demo hệ thống', value: stats.by_origin.system_demo || 0, fill: 'var(--warning)' },
                    ]}
                    cx="50%" cy="50%" outerRadius={75} dataKey="value"
                  >
                    {[
                      { fill: 'var(--success)' },
                      { fill: 'var(--primary)' },
                      { fill: 'var(--warning)' },
                    ].map((c, i) => <Cell key={i} fill={c.fill} />)}
                  </Pie>
                  <Tooltip />
                  <Legend wrapperStyle={{ fontSize: 12, color: 'var(--text-muted)' }} />
                </PieChart>
              </ChartWrapper>
            ) : <SkeletonChart height={180} />}
          </CardContent>
        </Card>
      </div>

      {/* Evidence Tier Distribution */}
      <Card style={{ marginBottom: '1.5rem' }}>
        <CardHeader>
          <CardTitle style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            {icon('barChart3', 14)} Evidence Tier Distribution (CVX-BDS/IoT 1.1-VN)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
            {evidenceData.map((item) => (
              <Badge key={item.key} variant={item.key.toLowerCase()} size="md">
                {item.name}: {item.value.toLocaleString()} mẫu
                {item.countRank ? ` · hạng ${item.countRank}` : ''}
              </Badge>
            ))}
          </div>
          <div style={{ marginBottom: '0.75rem', color: 'var(--text-muted)', fontSize: '0.78rem' }}>
            Evidence Tier là cấp chất lượng bằng chứng. Hạng số mẫu được tính riêng theo số lượng thực tế trong database,
            nên E2/E3 có thể đứng hạng cao hơn E1 nếu có nhiều bản ghi hơn.
          </div>
          {evidenceData.length > 0 ? (
            <ChartWrapper height={180}>
              <BarChart data={evidenceData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="key" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                <Tooltip
                  formatter={(v, _name, item) => [
                    `${v.toLocaleString()} mẫu · hạng ${item?.payload?.countRank || '—'} · ${item?.payload?.share?.toFixed?.(1) || 0}%`,
                    item?.payload?.name || 'Evidence Tier',
                  ]}
                />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {evidenceData.map((entry, idx) => (
                    <Cell key={idx} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ChartWrapper>
          ) : <SkeletonChart height={180} />}
        </CardContent>
      </Card>

      {/* Confidence Distribution + District Price Ranking */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: '1.25rem', marginBottom: '1.25rem' }}>

        {/* Confidence Gauge */}
        <Card>
          <CardHeader>
            <CardTitle style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              {icon('target', 14)} Độ tin cậy dự đoán
            </CardTitle>
          </CardHeader>
          <CardContent>
            {(() => {
              const confData = [
                { label: 'Cao (A)', key: 'confidence_a', color: '#06d6a0', threshold: 0.8 },
                { label: 'Trung bình (B)', key: 'confidence_b', color: '#0099ff', threshold: 0.6 },
                { label: 'Thấp (C)', key: 'confidence_c', color: '#f59e0b', threshold: 0.4 },
                { label: 'Kém (D)', key: 'confidence_d', color: '#ef233c', threshold: 0 },
              ]
              const total = confData.reduce((s, d) => s + (confidenceCounts[d.key] || 0), 0)
              return (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {confData.map(d => {
                    const count = confidenceCounts[d.key] || 0
                    const pct = total > 0 ? (count / total) * 100 : 0
                    return (
                      <div key={d.key}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '4px' }}>
                          <span style={{ color: d.color, fontWeight: 600 }}>{d.label}</span>
                          <span style={{ color: 'var(--text-muted)' }}>{count.toLocaleString()} ({pct.toFixed(1)}%)</span>
                        </div>
                        <div style={{ height: '10px', background: 'var(--border)', borderRadius: '5px', overflow: 'hidden' }}>
                          <div style={{
                            width: `${pct}%`, height: '100%',
                            background: d.color, borderRadius: '5px',
                            transition: 'width 0.5s ease',
                          }} />
                        </div>
                      </div>
                    )
                  })}
                  {total === 0 && (
                    <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem', padding: '1rem' }}>
                      Chưa có dữ liệu confidence
                    </div>
                  )}
                  {total > 0 && (
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.72rem', paddingTop: '0.25rem' }}>
                      Nguồn: {confidenceCounts.source}. A chỉ mở khi nhóm mẫu gần đạt từ 800 bản ghi.
                    </div>
                  )}
                </div>
              )
            })()}
          </CardContent>
        </Card>

        {/* District Price Ranking */}
        <Card>
          <CardHeader>
            <CardTitle style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              {icon('mapPin', 14)} Giá trung bình theo quận (Top 8)
            </CardTitle>
          </CardHeader>
          <CardContent>
            {(() => {
              const data = Array.isArray(propertiesData) ? propertiesData : []
              if (data.length === 0) return <SkeletonChart height={180} />
              const districtPrices = {}
              data.forEach(p => {
                if (!p.district || !p.price) return
                if (!districtPrices[p.district]) districtPrices[p.district] = []
                districtPrices[p.district].push(p.price)
              })
              const avgPrices = Object.entries(districtPrices)
                .map(([name, prices]) => ({
                  name,
                  avg: prices.reduce((a, b) => a + b, 0) / prices.length,
                  count: prices.length,
                }))
                .filter(d => d.count >= 3)
                .sort((a, b) => b.avg - a.avg)
                .slice(0, 8)

              if (avgPrices.length === 0) {
                return <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textAlign: 'center', padding: '1rem' }}>Cần dữ liệu giá để hiển thị</div>
              }
              const maxAvg = avgPrices[0].avg
              return (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {avgPrices.map((d, i) => (
                    <div key={d.name} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ width: '16px', fontSize: '0.7rem', color: 'var(--text-muted)', textAlign: 'right', flexShrink: 0 }}>{i + 1}</span>
                      <span style={{ fontSize: '0.8rem', minWidth: '100px', color: 'var(--text-secondary)' }}>{d.name}</span>
                      <div style={{ flex: 1, height: '12px', background: 'var(--border)', borderRadius: '6px', overflow: 'hidden' }}>
                        <div style={{
                          width: `${(d.avg / maxAvg) * 100}%`, height: '100%',
                          background: `hsl(${200 - i * 20}, 70%, 50%)`,
                          borderRadius: '6px', transition: 'width 0.5s ease',
                        }} />
                      </div>
                      <span style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--text-muted)', minWidth: '70px', textAlign: 'right', flexShrink: 0 }}>
                        {d.count} rec
                      </span>
                    </div>
                  ))}
                </div>
              )
            })()}
          </CardContent>
        </Card>
      </div>

      {/* Model Performance */}
      {servingModel && (
        <Card className="dashboard-panel" style={{ borderLeft: '4px solid var(--primary)', marginBottom: '1.5rem' }}>
          <CardHeader>
            <CardTitle style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              {icon('bot', 14)} Hiệu suất model đang phục vụ
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr)', gap: '0.75rem', marginBottom: '1.25rem' }}>
              {[
                { label: 'Mô hình', value: servingModel.model_name, color: 'var(--primary)' },
                { label: 'Phiên bản', value: servingModel.version, color: 'var(--text-primary)' },
                { label: 'Mẫu train', value: (servingModel.dataset_record_count || servingModel.train_record_count)?.toLocaleString(), color: 'var(--text-primary)' },
                { label: 'MAPE', value: servingModel.mape != null ? `${Number(servingModel.mape).toFixed(2)}%` : '—', color: 'var(--danger)' },
                { label: 'MAE', value: fmtPrice(servingModel.mae), color: 'var(--danger)' },
                { label: 'R² Score', value: (servingModel.r2 || 0).toFixed(4), color: 'var(--success)' },
              ].map((m, i) => (
                <div key={i} style={{
                  padding: '0.875rem', textAlign: 'center',
                  background: 'var(--bg-elevated)',
                  borderRadius: '10px',
                  border: '1px solid var(--border)',
                }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>{m.label}</div>
                  <div style={{
                    fontFamily: "'Space Grotesk', monospace",
                    fontWeight: 700, fontSize: '1.1rem', color: m.color,
                  }}>
                    {m.value || '—'}
                  </div>
                </div>
              ))}
            </div>

            {/* Metrics bars */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
              {[
                {
                  label: 'MAE', value: servingModel.mae,
                  max: 15e6,
                  color: 'var(--danger)',
                  fmt: fmtPrice,
                },
                {
                  label: 'RMSE', value: servingModel.rmse || 0,
                  max: 25e6,
                  color: 'var(--warning)',
                  fmt: fmtPrice,
                  skip: !servingModel.rmse,
                },
                {
                  label: 'R² Score', value: servingModel.r2 || 0,
                  max: 1,
                  color: 'var(--success)',
                  fmt: (v) => (v * 100).toFixed(1) + '%',
                },
              ].filter(m => !m.skip).map((m) => (
                <div key={m.label}>
                  <ProgressBar
                    label={m.label}
                    value={m.value || 0}
                    max={m.max}
                    showValue
                    color={m.color}
                    size="lg"
                  />
                </div>
              ))}
            </div>

            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
              <Badge variant={stats.model_needs_retrain ? 'warning' : 'success'} size="sm">
                {icon(stats.model_needs_retrain ? 'alertTriangle' : 'checkCircle', 10)}
                {stats.model_needs_retrain ? 'Cần retrain theo DB mới' : 'Model đã khớp tập train hiện tại'}
              </Badge>
              <Badge variant="primary" size="sm">
                {icon('database', 10)} {servingModel.dataset_record_count || servingModel.train_record_count} samples
              </Badge>
              <Badge variant="info" size="sm">
                Metric: {servingModel.metric_source || 'ACTIVE_MODEL/metadata'}
              </Badge>
              <Badge variant="info" size="sm">
                P-CONF: {stats.confidence_source || '—'}
              </Badge>
            </div>
          </CardContent>
        </Card>
      )}

      {!servingModel && (
        <Card className="dashboard-panel" style={{ background: 'var(--warning-bg)', border: '1px solid var(--warning-border)' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
            {icon('flask', 18, '')}
            <div>
              <div style={{ fontWeight: 600, color: 'var(--warning)', marginBottom: '0.25rem' }}>
                Chưa có mô hình được train
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Vui lòng chạy retrain để tạo mô hình dự đoán
              </div>
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}

export default Dashboard
