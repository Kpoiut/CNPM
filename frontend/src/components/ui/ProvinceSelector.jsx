/**
 * ProvinceSelector + DistrictSelector — shared cascade dropdown
 * Replaces 5 independent province/district fetch implementations
 */
import React, { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { API_BASE } from '../../lib'

/** Province dropdown */
export function ProvinceSelector({ value, onChange, className = 'form-select', ...props }) {
  const { data, isLoading } = useQuery({
    queryKey: ['provinces-list'],
    queryFn: async () => {
      const r = await fetch(`${API_BASE}/provinces`)
      if (!r.ok) throw new Error('load failed')
      const d = await r.json()
      return d.data?.provinces || d.provinces || d || []
    },
    staleTime: 10 * 60 * 1000,
  })

  return (
    <select
      className={className}
      value={value || ''}
      onChange={e => onChange(e.target.value)}
      disabled={isLoading}
      {...props}
    >
      <option value="">{isLoading ? 'Đang tải tỉnh/thành...' : '— Chọn tỉnh/TP —'}</option>
      {(data || []).map(p => (
        <option key={p.code || p.name || p} value={p.name || p.code || p}>
          {p.name || p}
        </option>
      ))}
    </select>
  )
}

/** District dropdown — cascades from province */
export function DistrictSelector({ provinceCode, value, onChange, className = 'form-select', ...props }) {
  const { data, isLoading } = useQuery({
    queryKey: ['districts-list', provinceCode],
    queryFn: async () => {
      if (!provinceCode) return []
      const r = await fetch(`${API_BASE}/provinces/${encodeURIComponent(provinceCode)}/districts`)
      if (!r.ok) return []
      const d = await r.json()
      return d.data?.districts || d.districts || d || []
    },
    enabled: !!provinceCode,
    staleTime: 10 * 60 * 1000,
  })

  return (
    <select
      className={className}
      value={value || ''}
      onChange={e => onChange(e.target.value)}
      disabled={!provinceCode || isLoading}
      {...props}
    >
      <option value="">{isLoading ? 'Đang tải quận/huyện...' : provinceCode ? '— Chọn quận/huyện —' : 'Chọn tỉnh trước'}</option>
      {(data || []).map(d => (
        <option key={d.code || d.name || d} value={d.name || d.code || d}>
          {d.name || d}
        </option>
      ))}
    </select>
  )
}

/** Ward dropdown — cascades from district */
export function WardSelector({ districtCode, value, onChange, className = 'form-select', ...props }) {
  const { data, isLoading } = useQuery({
    queryKey: ['wards-list', districtCode],
    queryFn: async () => {
      if (!districtCode) return []
      const r = await fetch(`${API_BASE}/provinces/${encodeURIComponent(districtCode)}/wards`)
      if (!r.ok) return []
      const d = await r.json()
      return d.data?.wards || d.wards || d || []
    },
    enabled: !!districtCode,
    staleTime: 10 * 60 * 1000,
  })

  return (
    <select
      className={className}
      value={value || ''}
      onChange={e => onChange(e.target.value)}
      disabled={!districtCode || isLoading}
      {...props}
    >
      <option value="">{isLoading ? 'Đang tải phường/xã...' : districtCode ? '— Chọn phường/xã —' : 'Chọn quận trước'}</option>
      {(data || []).map(w => (
        <option key={w.code || w.name || w} value={w.name || w.code || w}>
          {w.name || w}
        </option>
      ))}
    </select>
  )
}
