import React, { useState } from 'react';
import { ProvinceSelector, DistrictSelector } from '../ui/ProvinceSelector';

import {
  ROAD_CLASSES,
  OWNERSHIP_TYPES,
  FLOOD_RISK,
  ASSET_SUBTYPES,
} from '../../constants/vnStrings';
import {
  COMMON_HINTS,
  HintOptions,
  LOCATION_HINTS,
  clearInvalidField,
  displayOption,
  inputToOptionCode,
  mapEntriesToOptions,
  scrollInvalidField,
  submitLabel,
  toFloat,
  toInt,
} from './formHelpers';

/**
 * LandIntakeForm — Asset-specific intake cho ĐẤT ĐÔ THỊ
 *
 * Fields riêng cho đất:
 * - polygon geometry (vẽ trên bản đồ)
 * - đa đỉnh, edge lengths
 * - nở hậu / thóp hậu score
 * - chiều sâu biến thiên
 * - hẻm phụ
 * - frontage/depth ratio
 *
 * Priority factors: LEGAL, ACCESS, GEOMETRY, FLOOD
 */
export default function LandIntakeForm({ onSubmit, loading, isAdmin = false, engineLabel }) {
  const subtypeOptions = mapEntriesToOptions(ASSET_SUBTYPES.LAND_URBAN || {});
  const ownershipOptions = mapEntriesToOptions(OWNERSHIP_TYPES);
  const roadRiskOptions = COMMON_HINTS.riskLevels;
  const floodOptions = mapEntriesToOptions(FLOOD_RISK);
  const [form, setForm] = useState({
    // Asset identity
    asset_type: 'LAND_URBAN',
    asset_subtype: 'LAND_LEGAL_STREET',

    // Location
    province_city: 'Hà Nội',
    district: '',
    ward: '',
    street_or_project: '',
    latitude: '',
    longitude: '',

    // Parcel geometry (CRITICAL — đây là phần mới nhất)
    area_m2: '',
    polygon_json: '',       // JSON array của [{lat, lng}]
    frontage_m: '',
    frontage_road_class: '',
    depth_min_m: '',
    depth_max_m: '',
    taper_type: 'uniform',
    nö_hậu_score: '0.8',  // 0→1, vuông = 1.0
    thóp_hậu_score: '0.0', // 0→1, bị thắt = 1.0
    irregularity_score: '0.0',
    corner_plot: false,
    alley_branch_count: '0',

    // Legal
    ownership_type: 'FULL_OWNERSHIP',
    road_expansion_risk: 'none',
    dispute_flag: false,
    mortgage_flag: false,

    // Environment
    flood_risk: 'unknown',
    cemetery_distance_m: '',
    pollution_score: '',
    river_distance_m: '',
    park_distance_m: '',

    // Spiritual history
    death_history_flag: false,
    stigma_known: false,
    worship_site_distance_m: '',

    // IoT / environmental
    noise_level: '',
  });

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handleSubmit = (e) => {
    e.preventDefault();
    const payload = {
      ...form,
      area_m2: toFloat(form.area_m2, 0),
      latitude: toFloat(form.latitude),
      longitude: toFloat(form.longitude),
      frontage_m: toFloat(form.frontage_m),
      depth_min_m: toFloat(form.depth_min_m),
      depth_max_m: toFloat(form.depth_max_m),
      nö_hậu_score: toFloat(form.nö_hậu_score, 0),
      thóp_hậu_score: toFloat(form.thóp_hậu_score, 0),
      irregularity_score: toFloat(form.irregularity_score, 0),
      alley_branch_count: toInt(form.alley_branch_count, 0),
      cemetery_distance_m: toFloat(form.cemetery_distance_m),
      pollution_score: toFloat(form.pollution_score),
      river_distance_m: toFloat(form.river_distance_m),
      park_distance_m: toFloat(form.park_distance_m),
      worship_site_distance_m: toFloat(form.worship_site_distance_m),
      noise_level: toFloat(form.noise_level),
    };
    onSubmit(payload);
  };

  return (
    <form onSubmit={handleSubmit} onInvalid={scrollInvalidField} onInput={clearInvalidField} className="space-y-4">
      <HintOptions id="land-wards" options={[...LOCATION_HINTS.hanoiWards, ...LOCATION_HINTS.hcmWards]} />
      <HintOptions id="land-streets" options={[...LOCATION_HINTS.streets, ...LOCATION_HINTS.projects]} />
      <HintOptions id="land-subtypes" options={subtypeOptions} />
      <HintOptions id="land-ownership" options={ownershipOptions} />
      <HintOptions id="land-road-risk" options={roadRiskOptions} />
      <HintOptions id="land-flood" options={floodOptions} />
      {/* Section: Vị trí */}
      <div className="card">
        <div className="card-header">
          <span>Vị trí</span>
        </div>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Loại đất</label>
            <input
              className="form-input"
              list="land-subtypes"
              value={displayOption(subtypeOptions, form.asset_subtype)}
              onChange={e => set('asset_subtype', inputToOptionCode(subtypeOptions, e.target.value))}
              placeholder="VD: Đất mặt đường chính" />
          </div>
          <div className="form-group">
            <label className="form-label">Tỉnh / TP</label>
            <ProvinceSelector value={form.province_city} onChange={val => { set('province_city', val); set('district', '') }} className="form-select" />
          </div>
          <div className="form-group">
            <label className="form-label required">Quận / Huyện *</label>
            <DistrictSelector provinceCode={form.province_city} value={form.district} onChange={val => set('district', val)} className="form-select" required />
          </div>
          <div className="form-group">
            <label className="form-label">Phường / Xã</label>
            <input className="form-input" list="land-wards" value={form.ward}
              onChange={e => set('ward', e.target.value)} placeholder="VD: Xuân Thủy" />
          </div>
          <div className="form-group span-2">
            <label className="form-label">Đường / Dự án</label>
            <input className="form-input" list="land-streets" value={form.street_or_project}
              onChange={e => set('street_or_project', e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Vĩ độ (GPS)</label>
            <input type="number" step="0.0001" className="form-input"
              value={form.latitude} onChange={e => set('latitude', e.target.value)}
              placeholder="VD: 21.0285" />
          </div>
          <div className="form-group">
            <label className="form-label">Kinh độ (GPS)</label>
            <input type="number" step="0.0001" className="form-input"
              value={form.longitude} onChange={e => set('longitude', e.target.value)}
              placeholder="VD: 105.8542" />
          </div>
        </div>
      </div>

      {/* Section: Hình dạng & Diện tích — CRITICAL cho đất */}
      <div className="card">
        <div className="card-header">
          <span>Diện tích & Hình dạng đất</span>
        </div>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label required">Diện tích (m²)</label>
            <input type="number" step="0.1" className="form-input" required
              value={form.area_m2}
              onChange={e => set('area_m2', e.target.value)}
              placeholder="VD: 120.5" />
          </div>
          <div className="form-group">
            <label className="form-label">Mặt tiền (m)</label>
            <input type="number" step="0.1" className="form-input"
              value={form.frontage_m}
              onChange={e => set('frontage_m', e.target.value)}
              placeholder="VD: 5.0" />
          </div>
          <div className="form-group">
            <label className="form-label">Chiều sâu tối thiểu (m)</label>
            <input type="number" step="0.1" className="form-input"
              value={form.depth_min_m}
              onChange={e => set('depth_min_m', e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Chiều sâu tối đa (m)</label>
            <input type="number" step="0.1" className="form-input"
              value={form.depth_max_m}
              onChange={e => set('depth_max_m', e.target.value)} />
          </div>
          {/* Nở hậu / thóp hậu slider */}
          <div className="span-2">
            <label className="form-label">
              Hình dạng: Nở hậu → Thóp hậu
            </label>
            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Nở hậu (vuông)</span>
              <input type="range" min="0" max="1" step="0.05"
                value={form.nö_hậu_score}
                onChange={e => {
                  const v = parseFloat(e.target.value);
                  set('nö_hậu_score', String(v));
                  set('thóp_hậu_score', String(Math.max(0, 1 - v)));
                }}
                style={{ flex: 1 }}
              />
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Thóp hậu (bị thắt)</span>
            </div>
            <div style={{ textAlign: 'center', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              Nở hậu: {form.nö_hậu_score} | Thóp hậu: {form.thóp_hậu_score}
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Điểm vuông vắn (0→1)</label>
            <input type="range" min="0" max="1" step="0.05"
              value={form.nö_hậu_score}
              onChange={e => set('nö_hậu_score', e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Điểm méo (0→1)</label>
            <input type="range" min="0" max="1" step="0.05"
              value={form.irregularity_score}
              onChange={e => set('irregularity_score', e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">
              <input type="checkbox" checked={form.corner_plot}
                onChange={e => set('corner_plot', e.target.checked)} />
              {' '}Đất góc (2+ mặt tiền)
            </label>
          </div>
          <div className="form-group">
            <label className="form-label">Số hẻm phụ tách ra</label>
            <input type="number" min="0" className="form-input"
              value={form.alley_branch_count}
              onChange={e => set('alley_branch_count', e.target.value)} />
          </div>
          <div className="form-group span-2">
            <label className="form-label">Tọa độ polygon (JSON — cho map drawing)</label>
            <textarea className="form-input" rows={3}
              value={form.polygon_json}
              onChange={e => set('polygon_json', e.target.value)}
              placeholder='[{"lat": 21.0285, "lng": 105.8542}, ...]' />
          </div>
        </div>
      </div>

      {/* Section: Pháp lý — CRITICAL cho market valuation */}
      <div className="card">
        <div className="card-header">
          <span>Pháp lý & Quy hoạch
            <span className="text-xs text-muted" style={{ marginLeft: 'auto' }}>
              (Impact: ±5-15%)
            </span>
          </span>
        </div>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label required">Pháp lý</label>
            <input className="form-input" list="land-ownership" required
              value={displayOption(ownershipOptions, form.ownership_type)}
              onChange={e => set('ownership_type', inputToOptionCode(ownershipOptions, e.target.value))}
              placeholder="VD: Sổ đỏ/Sổ hồng đầy đủ" />
          </div>
          <div className="form-group">
            <label className="form-label">Quy hoạch mở đường</label>
            <input className="form-input" list="land-road-risk"
              value={displayOption(roadRiskOptions, form.road_expansion_risk)}
              onChange={e => set('road_expansion_risk', inputToOptionCode(roadRiskOptions, e.target.value))}
              placeholder="VD: Thấp / Trung bình / Cao" />
          </div>
          <div className="form-group">
            <label className="form-label">
              <input type="checkbox" checked={form.dispute_flag}
                onChange={e => set('dispute_flag', e.target.checked)} />
              {' '}Đang có tranh chấp
            </label>
          </div>
          <div className="form-group">
            <label className="form-label">
              <input type="checkbox" checked={form.mortgage_flag}
                onChange={e => set('mortgage_flag', e.target.checked)} />
              {' '}Đang thế chấp ngân hàng
            </label>
          </div>
        </div>
      </div>

      {/* Section: Môi trường & Hạ tầng */}
      <div className="card">
        <div className="card-header">
          <span>Môi trường & Hạ tầng
            <span className="text-xs text-muted" style={{ marginLeft: 'auto' }}>
              (Impact: ±3-16%)
            </span>
          </span>
        </div>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Nguy cơ ngập</label>
            <input className="form-input" list="land-flood"
              value={displayOption(floodOptions, form.flood_risk)}
              onChange={e => set('flood_risk', inputToOptionCode(floodOptions, e.target.value))}
              placeholder="VD: Không rõ / Không ngập / Ngập nhẹ" />
          </div>
          <div className="form-group">
            <label className="form-label">Cách nghĩa trang (m)</label>
            <input type="number" className="form-input"
              value={form.cemetery_distance_m}
              onChange={e => set('cemetery_distance_m', e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Cách sông (m)</label>
            <input type="number" className="form-input"
              value={form.river_distance_m}
              onChange={e => set('river_distance_m', e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Cách công viên (m)</label>
            <input type="number" className="form-input"
              value={form.park_distance_m}
              onChange={e => set('park_distance_m', e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Điểm ô nhiễm (0→1)</label>
            <input type="range" min="0" max="1" step="0.1"
              value={form.pollution_score}
              onChange={e => set('pollution_score', e.target.value)} />
            <div className="text-xs text-muted text-right">
              {form.pollution_score || '0'}
            </div>
          </div>
        </div>
      </div>

      {/* Section: Tâm linh (Fit layer, không ảnh hưởng market_value */}
      <div className="card" style={{ borderColor: 'var(--warning-border)' }}>
        <div className="card-header" style={{ color: 'var(--warning-dark)' }}>
          Lịch sử tâm linh
          <span className="text-xs" style={{ marginLeft: 'auto', opacity: 0.7 }}>
            Lớp FIT — không ảnh hưởng giá thị trường
          </span>
        </div>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">
              <input type="checkbox"
                checked={form.death_history_flag}
                onChange={e => set('death_history_flag', e.target.checked)} />
              {' '}Có tử vong trong nhà/đất
            </label>
          </div>
          <div className="form-group">
            <label className="form-label">
              <input type="checkbox"
                checked={form.stigma_known}
                onChange={e => set('stigma_known', e.target.checked)} />
              {' '}Điểm nhạy cảm đã biết trong khu vực
            </label>
          </div>
          <div className="form-group">
            <label className="form-label">Cách nơi thờ cúng (m)</label>
            <input type="number" className="form-input"
              value={form.worship_site_distance_m}
              onChange={e => set('worship_site_distance_m', e.target.value)} />
          </div>
        </div>
      </div>

      <button type="submit" className="btn btn-primary btn-lg btn-full" disabled={loading}>
        {submitLabel(isAdmin, loading, engineLabel)}
      </button>
    </form>
  );
}
