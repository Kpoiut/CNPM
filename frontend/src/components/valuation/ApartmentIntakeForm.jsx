import React, { useState } from 'react';
import { ProvinceSelector, DistrictSelector } from '../ui/ProvinceSelector';

import {
  OWNERSHIP_TYPES,
  FLOOD_RISK,
  FENG_SHUI_SENSITIVITIES,
  APT_VIEW_TYPES,
  NOISE_TOLERANCES,
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
 * ApartmentIntakeForm — Asset-specific intake cho CĂN HỘ CHUNG CƯ
 *
 * Fields riêng cho căn hộ:
 * - Hướng cửa / ban công / view
 * - Tầng (số thực)
 * - Khoảng cách thang máy, phòng rác, lõi kỹ thuật
 * - Bố cục cửa-bếp-toilet-ban công
 * - Độ thoáng, tiếng ồn
 *
 * Priority factors: VIEW, FLOOR, NOISE, LEGAL
 */
export default function ApartmentIntakeForm({ onSubmit, loading, isAdmin = false, engineLabel }) {
  const viewOptions = mapEntriesToOptions(APT_VIEW_TYPES);
  const ownershipOptions = mapEntriesToOptions(OWNERSHIP_TYPES);
  const floodOptions = mapEntriesToOptions(FLOOD_RISK);
  const fengShuiOptions = mapEntriesToOptions(FENG_SHUI_SENSITIVITIES);
  const noiseToleranceOptions = mapEntriesToOptions(NOISE_TOLERANCES);
  const unitPositionOptions = COMMON_HINTS.unitPositions;
  const sunlightOptions = COMMON_HINTS.sunlight;
  const distanceOptions = COMMON_HINTS.distances;
  const [form, setForm] = useState({
    // Identity
    asset_type: 'APARTMENT',

    // Location
    province_city: 'TP. Hồ Chí Minh',
    district: '',
    ward: '',
    area_m2: '',
    latitude: '',
    longitude: '',

    // Building location
    block_name: '',
    apt_floor: '',
    unit_position: 'middle',

    // Orientations (CRITICAL)
    door_orientation: '',
    balcony_orientation: '',
    main_facing: '',

    // View (CRITICAL — ±5-10%)
    view_type: '',
    view_obstruction_pct: '0',

    // Proximity distances
    elevator_distance: 'medium',
    trash_room_distance: 'medium',
    core_distance: 'far',
    stair_distance: 'medium',

    // Layout quality
    layout_score: '0.7',
    bedrooms: '',
    bathrooms: '',
    has_utilities_room: false,

    // Environment
    sunlight_exposure: 'FAIR',
    ventilation_score: '0.7',
    noise_inside_db: '',

    // Building
    building_quality: 'STANDARD',
    building_age_years: '',
    has_concierge: false,
    has_pool: false,
    has_gym: false,

    // Legal
    ownership_type: 'FULL_OWNERSHIP',

    // Environment
    flood_risk: 'unknown',

    // Persona hints (fit layer)
    feng_shui_sensitivity: 'NONE',
    noise_tolerance: 'NEUTRAL',

    // IoT
    noise_level: '',
    temperature: '',
    humidity: '',
    gps_lat: '',
    gps_lng: '',
  });

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handleSubmit = (e) => {
    e.preventDefault();
    const payload = {
      ...form,
      area_m2: toFloat(form.area_m2),
      apt_floor: toInt(form.apt_floor),
      bedrooms: toInt(form.bedrooms, 0),
      bathrooms: toInt(form.bathrooms, 0),
      latitude: toFloat(form.latitude),
      longitude: toFloat(form.longitude),
      noise_inside_db: toFloat(form.noise_inside_db),
      ventilation_score: toFloat(form.ventilation_score, 0.7),
      building_age_years: toInt(form.building_age_years),
      layout_score: toFloat(form.layout_score, 0.7),
      noise_level: toFloat(form.noise_level),
      temperature: toFloat(form.temperature),
      humidity: toFloat(form.humidity),
      gps_lat: toFloat(form.gps_lat),
      gps_lng: toFloat(form.gps_lng),
    };
    onSubmit(payload);
  };

  return (
    <form onSubmit={handleSubmit} onInvalid={scrollInvalidField} onInput={clearInvalidField} className="space-y-4">
      <HintOptions id="apt-wards" options={[...LOCATION_HINTS.hanoiWards, ...LOCATION_HINTS.hcmWards]} />
      <HintOptions id="apt-blocks" options={LOCATION_HINTS.blocks} />
      <HintOptions id="apt-unit-position" options={unitPositionOptions} />
      <HintOptions id="apt-view-types" options={viewOptions} />
      <HintOptions id="apt-orientations" options={COMMON_HINTS.orientations} />
      <HintOptions id="apt-sunlight" options={sunlightOptions} />
      <HintOptions id="apt-distances" options={distanceOptions} />
      <HintOptions id="apt-ownership" options={ownershipOptions} />
      <HintOptions id="apt-flood" options={floodOptions} />
      <HintOptions id="apt-feng-shui" options={fengShuiOptions} />
      <HintOptions id="apt-noise-tolerance" options={noiseToleranceOptions} />
      {/* Vị trí */}
      <div className="card">
        <div className="card-header"><span>Vị trí</span></div>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Tỉnh / TP</label>
            <ProvinceSelector value={form.province_city} onChange={val => { set('province_city', val); set('district', '') }} className="form-select" />
          </div>
          <div className="form-group">
            <label className="form-label required">Quận / Huyện</label>
            <DistrictSelector provinceCode={form.province_city} value={form.district} onChange={val => set('district', val)} className="form-select" required />
          </div>
          <div className="form-group">
            <label className="form-label required">Diện tích căn hộ (m²) *</label>
            <input type="number" step="0.1" className="form-input" required
              value={form.area_m2}
              onChange={e => set('area_m2', e.target.value)}
              placeholder="VD: 72.5" />
          </div>
          <div className="form-group">
            <label className="form-label">Block/Tower</label>
            <input className="form-input" list="apt-blocks"
              value={form.block_name}
              onChange={e => set('block_name', e.target.value)}
              placeholder="VD: Tower A, Block B2" />
          </div>
          <div className="form-group">
            <label className="form-label required">Tầng *</label>
            <input type="number" className="form-input" required
              value={form.apt_floor}
              onChange={e => set('apt_floor', e.target.value)}
              placeholder="VD: 15" />
          </div>
          <div className="form-group">
            <label className="form-label">Vị trí trong block</label>
            <input className="form-input" list="apt-unit-position"
              value={displayOption(unitPositionOptions, form.unit_position)}
              onChange={e => set('unit_position', inputToOptionCode(unitPositionOptions, e.target.value))}
              placeholder="VD: Ở giữa / Căn góc" />
          </div>
        </div>
      </div>

      {/* View & Hướng (CRITICAL ±10%) */}
      <div className="card">
        <div className="card-header">
          <span>View & Hướng nhìn
            <span className="text-xs text-muted" style={{ marginLeft: 'auto' }}>
              Impact ±10%
            </span>
          </span>
        </div>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Loại view</label>
            <input className="form-input" list="apt-view-types"
              value={displayOption(viewOptions, form.view_type)}
              onChange={e => set('view_type', inputToOptionCode(viewOptions, e.target.value))}
              placeholder="VD: View sông / View công viên" />
          </div>
          <div className="form-group">
            <label className="form-label">Độ che chắn view (%)</label>
            <input type="range" min="0" max="100" step="5"
              value={form.view_obstruction_pct}
              onChange={e => set('view_obstruction_pct', e.target.value)} />
            <div className="text-xs text-muted text-right">
              {form.view_obstruction_pct}% bị che
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Hướng cửa chính</label>
            <input className="form-input" list="apt-orientations"
              value={form.door_orientation}
              onChange={e => set('door_orientation', e.target.value)}
              placeholder="VD: Đông Nam" />
          </div>
          <div className="form-group">
            <label className="form-label">Hướng ban công</label>
            <input className="form-input" list="apt-orientations"
              value={form.balcony_orientation}
              onChange={e => set('balcony_orientation', e.target.value)}
              placeholder="VD: Nam" />
          </div>
          <div className="form-group">
            <label className="form-label">Nắng Tây chiều</label>
            <input className="form-input" list="apt-sunlight"
              value={displayOption(sunlightOptions, form.sunlight_exposure)}
              onChange={e => set('sunlight_exposure', inputToOptionCode(sunlightOptions, e.target.value))}
              placeholder="VD: Nắng đẹp / Trung bình / Nắng gắt" />
          </div>
        </div>
      </div>

      {/* Khoảng cách tiện ích */}
      <div className="card">
        <div className="card-header">Khoảng cách tiện ích</div>
        <div className="form-grid">
          {[
            { field: 'elevator_distance', label: 'Thang máy', options: [
              ['very_close','Rất gần (≤5m)'],
              ['close','Gần (5-10m)'], ['medium','Trung bình (10-20m)'],
              ['far','Xa (>20m)'], ['very_far','Rất xa'],
            ]},
            { field: 'trash_room_distance', label: 'Phòng rác', options: [
              ['close','Gần (<10m)'], ['medium','10-30m'],
              ['far','Xa (>30m)'],
            ]},
            { field: 'core_distance', label: 'Lõi kỹ thuật', options: [
              ['adjacent','Liền kề lõi KT'],
              ['close','Gần (5-15m)'], ['medium','15-30m'], ['far','Xa (>30m)'],
            ]},
          ].map(({ field, label, options }) => (
            <div className="form-group" key={field}>
              <label className="form-label">{label}</label>
              <input className="form-input" list="apt-distances"
                value={displayOption(distanceOptions, form[field])}
                onChange={e => set(field, inputToOptionCode(distanceOptions, e.target.value))}
                placeholder={options[0]?.[1] || 'Trung bình'} />
            </div>
          ))}
        </div>
      </div>

      {/* Bố cục & Chất lượng sống */}
      <div className="card">
        <div className="card-header">Bố cục & Chất lượng sống</div>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Số phòng ngủ</label>
            <input type="number" min="0" className="form-input"
              value={form.bedrooms}
              onChange={e => set('bedrooms', e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Số phòng tắm</label>
            <input type="number" min="0" className="form-input"
              value={form.bathrooms}
              onChange={e => set('bathrooms', e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Thông thoáng (0→1)</label>
            <input type="range" min="0" max="1" step="0.1"
              value={form.ventilation_score}
              onChange={e => set('ventilation_score', e.target.value)} />
            <div className="text-xs text-muted text-right">
              {form.ventilation_score}
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Tiếng ồn trong căn (dB) — đo bằng cảm biến</label>
            <input type="number" step="0.1" className="form-input"
              value={form.noise_inside_db}
              onChange={e => set('noise_inside_db', e.target.value)}
              placeholder="VD: 42.5" />
          </div>
        </div>
      </div>

      {/* Pháp lý */}
      <div className="card">
        <div className="card-header">Pháp lý</div>
        <div className="form-group">
          <label className="form-label required">Pháp lý</label>
          <input className="form-input" list="apt-ownership" required
            value={displayOption(ownershipOptions, form.ownership_type)}
            onChange={e => set('ownership_type', inputToOptionCode(ownershipOptions, e.target.value))}
            placeholder="VD: Sổ đỏ/Sổ hồng đầy đủ" />
        </div>
      </div>

      {/* Ngập + Tiếng ồn môi trường */}
      <div className="card">
        <div className="card-header">Ngập & Môi trường</div>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Nguy cơ ngập</label>
            <input className="form-input" list="apt-flood"
              value={displayOption(floodOptions, form.flood_risk)}
              onChange={e => set('flood_risk', inputToOptionCode(floodOptions, e.target.value))}
              placeholder="VD: Không rõ / Không ngập" />
          </div>
          <div className="form-group">
            <label className="form-label">Độ ồn môi trường (dB) — IoT</label>
            <input type="number" step="0.1" className="form-input"
              value={form.noise_level}
              onChange={e => set('noise_level', e.target.value)} />
          </div>
        </div>
      </div>

      {/* Persona hints — Fit layer */}
      <div className="card" style={{ borderColor: 'var(--warning-border)' }}>
        <div className="card-header" style={{ color: 'var(--warning-dark)' }}>
          Gợi ý phù hợp người mua
          <span className="text-xs" style={{ marginLeft: 'auto', opacity: 0.7 }}>
            Lớp FIT — không ảnh hưởng giá thị trường
          </span>
        </div>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Mức quan tâm phong thủy</label>
            <input className="form-input" list="apt-feng-shui"
              value={displayOption(fengShuiOptions, form.feng_shui_sensitivity)}
              onChange={e => set('feng_shui_sensitivity', inputToOptionCode(fengShuiOptions, e.target.value))}
              placeholder="VD: Không quan tâm / Quan tâm cao" />
          </div>
          <div className="form-group">
            <label className="form-label">Mức chịu ồn</label>
            <input className="form-input" list="apt-noise-tolerance"
              value={displayOption(noiseToleranceOptions, form.noise_tolerance)}
              onChange={e => set('noise_tolerance', inputToOptionCode(noiseToleranceOptions, e.target.value))}
              placeholder="VD: Bình thường / Nhạy cảm" />
          </div>
        </div>
      </div>

      <button type="submit" className="btn btn-primary btn-lg btn-full" disabled={loading}>
        {submitLabel(isAdmin, loading, engineLabel)}
      </button>
    </form>
  );
}
