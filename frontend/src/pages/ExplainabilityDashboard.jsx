import React, { useState, useEffect } from 'react'
import { BarChart3, TrendingUp, Target, BarChart, PieChart, Activity } from 'lucide-react'
import FeatureImportanceChart from '../components/explainability/FeatureImportanceChart'
import SHAPWaterfallChart from '../components/explainability/SHAPWaterfallChart'
import CalibrationChart from '../components/explainability/CalibrationChart'
import ResidualAnalysisChart from '../components/explainability/ResidualAnalysisChart'
import ModelComparisonChart from '../components/explainability/ModelComparisonChart'
import PredictionDistributionChart from '../components/explainability/PredictionDistributionChart'
import SHAPBeeswarmChart from '../components/explainability/SHAPBeeswarmChart'

const API_BASE = '/api'

function MetricCard({ label, value, unit, color, sublabel }) {
  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius)',
      padding: '0.875rem 1rem',
      display: 'flex',
      flexDirection: 'column',
      gap: '0.2rem',
    }}>
      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {label}
      </span>
      <span style={{ fontSize: '1.4rem', fontWeight: 700, color: color || 'var(--text-primary)', lineHeight: 1.2 }}>
        {value ?? '—'}
      </span>
      {unit && <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{unit}</span>}
      {sublabel && <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)', opacity: 0.7 }}>{sublabel}</span>}
    </div>
  )
}

function LoadingPanel({ height = 300 }) {
  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius)',
      height,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    }}>
      <div className="spinner" style={{ width: 32, height: 32 }} />
    </div>
  )
}

function ErrorPanel({ message }) {
  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius)',
      height: 300,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      flexDirection: 'column',
      gap: '0.5rem',
      color: 'var(--text-muted)',
      fontSize: '0.875rem',
    }}>
      <Activity size={24} style={{ opacity: 0.5 }} />
      <span>{message || 'No data available'}</span>
    </div>
  )
}

export default function ExplainabilityDashboard() {
  const [globalData, setGlobalData] = useState(null)
  const [residualsData, setResidualsData] = useState(null)
  const [calibrationData, setCalibrationData] = useState(null)
  const [modelCompareData, setModelCompareData] = useState(null)
  const [selectedProperty, setSelectedProperty] = useState(null)
  const [waterfallData, setWaterfallData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('overview')
  const [modelVersion, setModelVersion] = useState('—')

  useEffect(() => {
    const loadData = async () => {
      try {
        const [globalRes, residualsRes, calibRes, compareRes] = await Promise.all([
          fetch(`${API_BASE}/v2/explain/global`),
          fetch(`${API_BASE}/v2/explain/residuals`),
          fetch(`${API_BASE}/v2/explain/calibration`),
          fetch(`${API_BASE}/v2/explain/model-compare`),
        ])

        if (globalRes.ok) {
          const g = await globalRes.json()
          setGlobalData(g)
          setModelVersion(g.model_version?.slice(0, 16) || '—')
        }
        if (residualsRes.ok) setResidualsData(await residualsRes.json())
        if (calibRes.ok) setCalibrationData(await calibRes.json())
        if (compareRes.ok) setModelCompareData(await compareRes.json())
      } catch (e) {
        console.error('Dashboard load error:', e)
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  const loadWaterfall = async (propertyId) => {
    try {
      const res = await fetch(`${API_BASE}/v2/explain/prediction/${propertyId}`)
      if (res.ok) {
        const data = await res.json()
        setWaterfallData(data)
        setSelectedProperty(propertyId)
      }
    } catch (e) {
      console.error('Waterfall load error:', e)
    }
  }

  if (loading) {
    return (
      <div style={{ padding: '2rem', maxWidth: 1400, margin: '0 auto' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
          {[...Array(6)].map((_, i) => <LoadingPanel key={i} height={80} />)}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
          {[...Array(6)].map((_, i) => <LoadingPanel key={i} />)}
        </div>
      </div>
    )
  }

  const r2 = residualsData?.overall_r2
  const mape = residualsData?.overall_mape_pct          // Official MAPE (>= 500M)
  const mapeRaw = residualsData?.raw_mape_pct             // Raw MAPE (all records — debug only)
  const wape = residualsData?.overall_wape_pct            // WAPE
  const mdape = residualsData?.overall_mdape_pct          // MdAPE
  const mae = residualsData?.overall_mae_vnd
  const nOfficial = residualsData?.n_official
  const nRaw = residualsData?.raw_n
  const nOutliers = residualsData?.n_outliers
  const priceBins = residualsData?.price_bins || []

  return (
    <div style={{ padding: '1.5rem', maxWidth: 1600, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
          <BarChart3 size={24} style={{ color: 'var(--primary)' }} />
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, margin: 0 }}>
            Model Explainability Center
          </h1>
          <span style={{
            background: 'var(--primary-bg)',
            color: 'var(--primary)',
            padding: '0.2rem 0.6rem',
            borderRadius: '20px',
            fontSize: '0.75rem',
            fontFamily: 'monospace',
          }}>
            v{modelVersion}
          </span>
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', margin: 0 }}>
          SHAP Transparency Report — Feature attribution, calibration, and model performance analysis
        </p>
      </div>

      {/* Metrics Strip */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '0.75rem', marginBottom: '1.5rem' }}>
        <MetricCard label="MAPE (Official)" value={mape ? `${mape.toFixed(1)}%` : '—'} sublabel={`≥500M · n=${nOfficial}`} color={mape < 15 ? '#22c55e' : mape < 25 ? '#f59e0b' : '#ef4444'} />
        <MetricCard label="WAPE" value={wape ? `${wape.toFixed(1)}%` : '—'} sublabel="weighted" color={wape < 15 ? '#22c55e' : wape < 25 ? '#f59e0b' : '#ef4444'} />
        <MetricCard label="MdAPE" value={mdape ? `${mdape.toFixed(1)}%` : '—'} sublabel="median" color={mdape < 10 ? '#22c55e' : mdape < 20 ? '#f59e0b' : '#ef4444'} />
        <MetricCard label="Test R2" value={r2 ? r2.toFixed(3) : '—'} color={r2 > 0.7 ? '#22c55e' : '#f59e0b'} />
        <MetricCard label="Test MAE" value={mae ? `${(mae / 1e9).toFixed(2)}B` : '—'} unit="VND" />
        <MetricCard label="MAPE (Raw)" value={mapeRaw ? `${mapeRaw.toFixed(1)}%` : '—'} sublabel={`all n=${nRaw} · debug`} color="#64748b" />
      </div>

      {/* Tab Navigation */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', borderBottom: '1px solid var(--border)', paddingBottom: '0.5rem' }}>
        {['overview', 'shap', 'residuals', 'calibration'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '0.4rem 1rem',
              borderRadius: 'var(--radius)',
              border: 'none',
              cursor: 'pointer',
              fontSize: '0.8rem',
              fontWeight: activeTab === tab ? 600 : 400,
              background: activeTab === tab ? 'var(--primary-bg)' : 'transparent',
              color: activeTab === tab ? 'var(--primary)' : 'var(--text-secondary)',
              transition: 'all 150ms',
            }}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <TrendingUp size={16} style={{ color: 'var(--primary)' }} />
                <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: 0 }}>Feature Importance</h3>
              </div>
              {!globalData ? <ErrorPanel message="SHAP data not available" />
                : <FeatureImportanceChart data={globalData.feature_importance} topN={15} height={350} />}
            </div>

            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <Target size={16} style={{ color: 'var(--primary)' }} />
                <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: 0 }}>Calibration by Band</h3>
              </div>
              {!calibrationData ? <ErrorPanel message="Calibration data not available" />
                : <CalibrationChart data={calibrationData.bands} height={350} />}
            </div>

            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <BarChart size={16} style={{ color: 'var(--primary)' }} />
                <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: 0 }}>Model MAPE Comparison</h3>
              </div>
              {!modelCompareData ? <ErrorPanel message="Model compare data not available" />
                : <ModelComparisonChart data={modelCompareData.models} height={350} />}
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <Activity size={16} style={{ color: 'var(--primary)' }} />
                <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: 0 }}>Residual Distribution</h3>
              </div>
              {!residualsData ? <ErrorPanel message="Residuals not available" />
                : <ResidualAnalysisChart data={residualsData} height={280} />}
            </div>

            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <PieChart size={16} style={{ color: 'var(--primary)' }} />
                <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: 0 }}>Prediction Error Distribution</h3>
              </div>
              {!residualsData ? <ErrorPanel message="Residuals not available" />
                : <PredictionDistributionChart data={residualsData} height={280} />}
            </div>
          </div>

          {/* Beeswarm */}
          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <BarChart3 size={16} style={{ color: 'var(--primary)' }} />
              <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: 0 }}>SHAP Beeswarm — Top 15 Features</h3>
            </div>
            {!globalData ? <ErrorPanel message="SHAP data not available" height={200} />
              : <SHAPBeeswarmChart data={globalData.beeswarm_data} height={220} />}
          </div>
        </>
      )}

      {/* SHAP Tab */}
      {activeTab === 'shap' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '1rem' }}>
            <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: '0 0 1rem' }}>Global Feature Importance</h3>
            {!globalData ? <ErrorPanel message="SHAP data not available" />
              : <FeatureImportanceChart data={globalData.feature_importance} topN={20} height={500} showLabels />}
          </div>
          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '1rem' }}>
            <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: '0 0 1rem' }}>Single Prediction Waterfall</h3>
            <div style={{ marginBottom: '1rem' }}>
              <input
                type="number"
                placeholder="Property ID"
                onKeyDown={e => { if (e.key === 'Enter') loadWaterfall(Number(e.target.value)) }}
                style={{
                  width: '100%',
                  padding: '0.5rem 0.75rem',
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius)',
                  color: 'var(--text-primary)',
                  fontSize: '0.875rem',
                  boxSizing: 'border-box',
                }}
              />
            </div>
            {!waterfallData ? (
              <div style={{ height: 450, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                Enter a property ID and press Enter to see SHAP waterfall
              </div>
            ) : (
              <SHAPWaterfallChart data={waterfallData} height={450} />
            )}
          </div>
        </div>
      )}

      {/* Residuals Tab */}
      {activeTab === 'residuals' && (
        <>
          {/* Methodology note */}
          <div style={{
            background: 'rgba(79,70,229,0.05)',
            border: '1px solid rgba(79,70,229,0.15)',
            borderRadius: 'var(--radius)',
            padding: '0.75rem 1rem',
            marginBottom: '1rem',
            fontSize: '0.78rem',
            color: 'var(--text-secondary)',
            lineHeight: 1.6,
          }}>
            <strong style={{ color: 'var(--primary)' }}>Metric Methodology:</strong>{' '}
            <strong>Official MAPE</strong> = computed on records with actual_price ≥ 500M (aligned with ML pipeline).{' '}
            <strong>Raw MAPE</strong> = all records (debug only).{' '}
            <strong>WAPE</strong> = sum(|error|) / sum(actual).{' '}
            <strong>MdAPE</strong> = median(|error|/actual).{' '}
            <strong>Outliers</strong> (|error| &gt; 50%) are shown separately — NOT excluded from Official MAPE.
          </div>

          {/* Outlier alert */}
          {nOutliers > 0 && (
            <div style={{
              background: 'rgba(239,35,60,0.06)',
              border: '1px solid rgba(239,35,60,0.2)',
              borderRadius: 'var(--radius)',
              padding: '0.6rem 1rem',
              marginBottom: '1rem',
              fontSize: '0.78rem',
              color: '#ef233c',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}>
              <span style={{ fontSize: '1rem' }}>⚠</span>
              {nOutliers} high-residual cases (|error| &gt; 50%) — displayed in table below.
            </div>
          )}

          {/* Scatter + Histogram */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '1rem' }}>
              <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: '0 0 1rem' }}>Actual vs Predicted</h3>
              {!residualsData ? <ErrorPanel message="Residuals not available" />
                : <ResidualAnalysisChart data={residualsData} height={380} fullScatter />}
            </div>
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '1rem' }}>
              <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: '0 0 1rem' }}>Error Histogram</h3>
              {!residualsData ? <ErrorPanel message="Residuals not available" />
                : <PredictionDistributionChart data={residualsData} height={380} />}
            </div>
          </div>

          {/* Segmented MAPE by price bin */}
          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '1rem', marginBottom: '1rem' }}>
            <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: '0 0 0.75rem' }}>MAPE by Price Segment</h3>
            {!residualsData ? <ErrorPanel message="—" /> : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border)' }}>
                      {['Price Range', 'Count', 'MAPE', 'WAPE', 'MdAPE', 'MAE'].map(h => (
                        <th key={h} style={{ textAlign: 'right', padding: '0.4rem 0.75rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', fontSize: '0.68rem' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {priceBins.map((bin, i) => {
                      const binColor = bin.mape_pct == null ? 'var(--text-muted)'
                        : bin.mape_pct < 15 ? '#22c55e'
                        : bin.mape_pct < 25 ? '#f59e0b'
                        : '#ef4444'
                      return (
                        <tr key={i} style={{ borderBottom: '1px solid var(--border)', opacity: bin.count === 0 ? 0.4 : 1 }}>
                          <td style={{ padding: '0.4rem 0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>{bin.label}</td>
                          <td style={{ padding: '0.4rem 0.75rem', textAlign: 'right', color: 'var(--text-muted)' }}>{bin.count}</td>
                          <td style={{ padding: '0.4rem 0.75rem', textAlign: 'right', fontWeight: 700, color: binColor }}>
                            {bin.mape_pct != null ? `${bin.mape_pct}%` : '—'}
                          </td>
                          <td style={{ padding: '0.4rem 0.75rem', textAlign: 'right', color: 'var(--text-secondary)' }}>
                            {bin.wape_pct != null ? `${bin.wape_pct}%` : '—'}
                          </td>
                          <td style={{ padding: '0.4rem 0.75rem', textAlign: 'right', color: 'var(--text-secondary)' }}>
                            {bin.median_ape_pct != null ? `${bin.median_ape_pct}%` : '—'}
                          </td>
                          <td style={{ padding: '0.4rem 0.75rem', textAlign: 'right', color: 'var(--text-muted)' }}>
                            {bin.mae_vnd != null ? `${(bin.mae_vnd / 1e9).toFixed(2)}B` : '—'}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Outliers table */}
          {residualsData?.outliers?.length > 0 && (
            <div style={{ background: 'var(--surface)', border: '1px solid rgba(239,35,60,0.2)', borderRadius: 'var(--radius)', padding: '1rem', marginBottom: '1rem' }}>
              <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: '0 0 0.75rem', color: '#ef233c' }}>
                High Residual Cases ({nOutliers}) — NOT excluded from Official MAPE
              </h3>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border)' }}>
                      {['ID', 'District', 'Type', 'Actual', 'Predicted', 'Error', 'Residual %'].map(h => (
                        <th key={h} style={{ textAlign: 'right', padding: '0.35rem 0.6rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', fontSize: '0.65rem' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {residualsData.outliers.map(o => (
                      <tr key={o.id} style={{ borderBottom: '1px solid var(--border)' }}>
                        <td style={{ padding: '0.35rem 0.6rem', fontFamily: 'monospace', color: 'var(--primary)' }}>#{o.id}</td>
                        <td style={{ padding: '0.35rem 0.6rem', textAlign: 'right' }}>{o.district}</td>
                        <td style={{ padding: '0.35rem 0.6rem', textAlign: 'right', color: 'var(--text-secondary)' }}>{o.property_type}</td>
                        <td style={{ padding: '0.35rem 0.6rem', textAlign: 'right', fontWeight: 600 }}>{(o.actual_price / 1e9).toFixed(2)}B</td>
                        <td style={{ padding: '0.35rem 0.6rem', textAlign: 'right' }}>{(o.predicted_price / 1e9).toFixed(2)}B</td>
                        <td style={{ padding: '0.35rem 0.6rem', textAlign: 'right', color: 'var(--text-muted)' }}>{(o.error_vnd / 1e9).toFixed(2)}B</td>
                        <td style={{ padding: '0.35rem 0.6rem', textAlign: 'right', fontWeight: 700, color: '#ef4444' }}>
                          {o.residual_pct > 0 ? '+' : ''}{o.residual_pct}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {/* Calibration Tab */}
      {activeTab === 'calibration' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '1rem' }}>
            <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: '0 0 1rem' }}>ICP by Confidence Band</h3>
            {!calibrationData ? <ErrorPanel message="Calibration data not available" />
              : <CalibrationChart data={calibrationData.bands} height={400} showDetails />}
          </div>
          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '1rem' }}>
            <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: '0 0 1rem' }}>Model Performance Across Versions</h3>
            {!modelCompareData ? <ErrorPanel message="Model compare data not available" />
              : <ModelComparisonChart data={modelCompareData.models} height={400} showAllMetrics />}
          </div>
        </div>
      )}

      {/* Footer */}
      <div style={{ marginTop: '2rem', padding: '1rem', borderTop: '1px solid var(--border)', color: 'var(--text-muted)', fontSize: '0.75rem', display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
        <span>Model Explainability Center — SHAP-based transparency report</span>
        <span>Model: {modelVersion} | Generated: {new Date().toLocaleString('vi-VN')}</span>
      </div>
    </div>
  )
}
