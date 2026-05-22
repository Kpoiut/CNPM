import React, { useState } from 'react';
import { ProvinceSelector, DistrictSelector } from '../ui/ProvinceSelector';

import {
  ROAD_CLASSES,
  OWNERSHIP_TYPES,
  FLOOD_RISK,
  FENG_SHUI_SENSITIVITIES,
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
 * TownhouseIntakeForm — Asset-specific intake cho NHÀ PHỐ LIỀN KỀ
 *
 * Fields riêng cho nhà phố:
 * - floor_count, built_area_m2, facade_count
 * - structure_grade, construction_year
 * - main_facing (hướng nhà)
 * - car_access, dead_end
 * - road_class, road_width_m
 *
 * Priority factors: LEGAL, ACCESS, GEOMETRY, BUILDING_QUALITY, FLOOD
 */
export default function TownhouseIntakeForm({ onSubmit, loading, isAdmin = false, engineLabel }) {
  const subtypeOptions = mapEntriesToOptions(ASSET_SUBTYPES.TOWNHOUSE || {});
  const facadeOptions = [['1', '1 mặt tiền'], ['2', '2 mặt tiền'], ['3', '3 mặt tiền']];
  const structureGradeOptions = mapEntriesToOptions({
    BETTER: 'A+ - Xây dựng tốt, bảo trì tốt',
    GOOD: 'A - Xây dựng tốt',
    AVERAGE: 'B+ - Trung bình khá',
    FAIR: 'B - Cần bảo trì nhẹ',
    POOR: 'C - Cần sửa chữa lớn',
    VERY_POOR: 'D - Cần phá dỡ/xây mới',
  });
  const fengShuiOptions = mapEntriesToOptions(FENG_SHUI_SENSITIVITIES);
  const roadClassOptions = mapEntriesToOptions(ROAD_CLASSES);
  const ownershipOptions = mapEntriesToOptions(OWNERSHIP_TYPES);
  const roadRiskOptions = COMMON_HINTS.riskLevels;
  const floodOptions = mapEntriesToOptions(FLOOD_RISK);
  const [form, setForm] = useState({
    // Identity
    asset_type: 'TOWNHOUSE',
    asset_subtype: 'TH_SINGLE_FACADE',

    // Location
    province_city: 'Hà Nội',
    district: '',
    ward: '',
    street_or_project: '',
    latitude: '',
    longitude: '',

    // Building geometry
    area_m2: '',
    built_area_m2: '',
    floor_count: '3',
    bedrooms: '3',
    bathrooms: '2',
    facade_count: '1',
    structure_grade: '',
    construction_year: '',
    main_facing: '',

    // Access & road
    road_class: '',
    road_width_m: '',
    car_access: true,
    dead_end: false,

    // Legal
    ownership_type: 'FULL_OWNERSHIP',
    planning_zone: '',
    road_expansion_risk: 'none',
    dispute_flag: false,
    mortgage_flag: false,

    // Environment
    flood_risk: 'unknown',
    cemetery_distance_m: '',
    noise_day_db: '',
    noise_night_db: '',
    river_distance_m: '',
    park_distance_m: '',

    // Spiritual / Fit layer
    death_history_flag: false,
    worship_site_distance_m: '',
    stigma_known: false,
    feng_shui_sensitivity: 'NONE',
    birth_year: '',

    // IoT
    noise_level: '',
  });

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handleSubmit = (e) => {
    e.preventDefault();
    const payload = {
      ...form,
      area_m2: toFloat(form.area_m2),
      built_area_m2: toFloat(form.built_area_m2),
      floor_count: toInt(form.floor_count, 1),
      bedrooms: toInt(form.bedrooms, 0),
      bathrooms: toInt(form.bathrooms, 0),
      facade_count: toInt(form.facade_count, 1),
      latitude: toFloat(form.latitude),
      longitude: toFloat(form.longitude),
      road_width_m: toFloat(form.road_width_m),
      construction_year: toInt(form.construction_year),
      cemetery_distance_m: toFloat(form.cemetery_distance_m),
      noise_day_db: toFloat(form.noise_day_db),
      noise_night_db: toFloat(form.noise_night_db),
      river_distance_m: toFloat(form.river_distance_m),
      park_distance_m: toFloat(form.park_distance_m),
      worship_site_distance_m: toFloat(form.worship_site_distance_m),
      noise_level: toFloat(form.noise_level),
      birth_year: toInt(form.birth_year),
    };
    onSubmit(payload);
  };

  return (
    <form onSubmit={handleSubmit} onInvalid={scrollInvalidField} onInput={clearInvalidField} className="space-y-4">
      <HintOptions id="townhouse-wards" options={[...LOCATION_HINTS.hanoiWards, ...LOCATION_HINTS.hcmWards]} />
      <HintOptions id="townhouse-streets" options={LOCATION_HINTS.streets} />
      <HintOptions id="townhouse-subtypes" options={subtypeOptions} />
      <HintOptions id="townhouse-facades" options={facadeOptions} />
      <HintOptions id="townhouse-structure" options={structureGradeOptions} />
      <HintOptions id="townhouse-facing" options={COMMON_HINTS.orientations} />
      <HintOptions id="townhouse-feng-shui" options={fengShuiOptions} />
      <HintOptions id="townhouse-road-class" options={roadClassOptions} />
      <HintOptions id="townhouse-ownership" options={ownershipOptions} />
      <HintOptions id="townhouse-road-risk" options={roadRiskOptions} />
      <HintOptions id="townhouse-flood" options={floodOptions} />
      {/* Vị trí */}
      <div className="card">
        <div className="card-header"><span>Vị trí</span></div>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Loại nhà phố</label>
            <input className="form-input" list="townhouse-subtypes"
              value={displayOption(subtypeOptions, form.asset_subtype)}
              onChange={e => set('asset_subtype', inputToOptionCode(subtypeOptions, e.target.value))}
              placeholder="VD: Nhà phố một mặt tiền" />
          </div>
          <div className="form-group">
            <label className="form-label">Tỉnh / TP</label>
            <ProvinceSelector
              value={form.province_city}
              onChange={val => { set('province_city', val); set('district', '') }}
              className="form-select" />
          </div>
          <div className="form-group">
            <label className="form-label required">Quận / Huyện *</label>
            <DistrictSelector
              provinceCode={form.province_city}
              value={form.district}
              onChange={val => set('district', val)}
              className="form-select" required />
          </div>
          <div className="form-group">
            <label className="form-label">Phường / Xã</label>
            <input className="form-input" list="townhouse-wards"
              value={form.ward}
              onChange={e => set('ward', e.target.value)}
              placeholder="VD: Xuân Thủy" />
          </div>
          <div className="form-group span-2">
            <label className="form-label">Đường / Dự án</label>
            <input className="form-input" list="townhouse-streets"
              value={form.street_or_project}
              onChange={e => set('street_or_project', e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Vĩ độ (GPS)</label>
            <input type="number" step="0.0001" className="form-input"
              value={form.latitude}
              onChange={e => set('latitude', e.target.value)}
              placeholder="VD: 21.0285" />
          </div>
          <div className="form-group">
            <label className="form-label">Kinh độ (GPS)</label>
            <input type="number" step="0.0001" className="form-input"
              value={form.longitude}
              onChange={e => set('longitude', e.target.value)}
              placeholder="VD: 105.8542" />
          </div>
        </div>
      </div>

      {/* Diện tích & Quy mô */}
      <div className="card">
        <div className="card-header">
          <span>Diện tích & Quy mô nhà</span>
        </div>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label required">Diện tích đất (m²)</label>
            <input type="number" step="0.1" className="form-input" required
              value={form.area_m2}
              onChange={e => set('area_m2', e.target.value)}
              placeholder="VD: 52.5" />
          </div>
          <div className="form-group">
            <label className="form-label">Diện tích sàn xây dựng (m²)</label>
            <input type="number" step="0.1" className="form-input"
              value={form.built_area_m2}
              onChange={e => set('built_area_m2', e.target.value)}
              placeholder="VD: 157.5" />
          </div>
          <div className="form-group">
            <label className="form-label required">Số tầng *</label>
            <input type="number" min="1" max="15" className="form-input" required
              value={form.floor_count}
              onChange={e => set('floor_count', e.target.value)}
              placeholder="VD: 4" />
          </div>
          <div className="form-group">
            <label className="form-label">Số mặt tiền</label>
            <input className="form-input" list="townhouse-facades"
              value={displayOption(facadeOptions, form.facade_count)}
              onChange={e => set('facade_count', inputToOptionCode(facadeOptions, e.target.value))}
              placeholder="VD: 1 mặt tiền / 2 mặt tiền" />
          </div>
          <div className="form-group">
            <label className="form-label">Số phòng ngủ</label>
            <input type="number" min="0" className="form-input"
              value={form.bedrooms}
              onChange={e => set('bedrooms', e.target.value)}
              placeholder="VD: 4" />
          </div>
          <div className="form-group">
            <label className="form-label">Số phòng tắm</label>
            <input type="number" min="0" className="form-input"
              value={form.bathrooms}
              onChange={e => set('bathrooms', e.target.value)}
              placeholder="VD: 3" />
          </div>
          <div className="form-group">
            <label className="form-label">Năm xây dựng</label>
            <input type="number" min="1950" max="2030" className="form-input"
              value={form.construction_year}
              onChange={e => set('construction_year', e.target.value)}
              placeholder="VD: 2018" />
          </div>
          <div className="form-group">
            <label className="form-label">Hạng cấp công trình</label>
            <input className="form-input" list="townhouse-structure"
              value={displayOption(structureGradeOptions, form.structure_grade)}
              onChange={e => set('structure_grade', inputToOptionCode(structureGradeOptions, e.target.value))}
              placeholder="VD: Xây dựng tốt / Trung bình khá" />
          </div>
        </div>
      </div>

      {/* Hướng nhà — Feng Shui input */}
      <div className="card" style={{ borderColor: 'var(--primary-200)' }}>
        <div className="card-header" style={{ color: 'var(--primary)' }}>
          Hướng nhà & Phong thủy
          <span className="text-xs text-muted" style={{ marginLeft: 'auto', opacity: 0.7 }}>
            Lớp FIT — ảnh hưởng ±1-10%
          </span>
        </div>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Hướng cửa chính</label>
            <input className="form-input" list="townhouse-facing"
              value={form.main_facing}
              onChange={e => set('main_facing', e.target.value)}
              placeholder="VD: Đông Nam" />
          </div>
          <div className="form-group">
            <label className="form-label">Năm sinh chủ nhà</label>
            <input type="number" min="1920" max="2015" className="form-input"
              value={form.birth_year}
              onChange={e => set('birth_year', e.target.value)}
              placeholder="VD: 1985" />
          </div>
          <div className="form-group">
            <label className="form-label">Mức quan tâm phong thủy</label>
            <input className="form-input" list="townhouse-feng-shui"
              value={displayOption(fengShuiOptions, form.feng_shui_sensitivity)}
              onChange={e => set('feng_shui_sensitivity', inputToOptionCode(fengShuiOptions, e.target.value))}
              placeholder="VD: Không quan tâm / Quan tâm cao" />
          </div>
        </div>
      </div>

      {/* Tiếp cận & Đường */}
      <div className="card">
        <div className="card-header">
          <span>Tiếp cận & Đường</span>
          <span className="text-xs text-muted" style={{ marginLeft: 'auto' }}>
            Impact: ±3-12%
          </span>
        </div>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Bề rộng đường (m)</label>
            <input type="number" step="0.5" className="form-input"
              value={form.road_width_m}
              onChange={e => set('road_width_m', e.target.value)}
              placeholder="VD: 3.5" />
          </div>
          <div className="form-group">
            <label className="form-label">Hạng đường</label>
            <input className="form-input" list="townhouse-road-class"
              value={displayOption(roadClassOptions, form.road_class)}
              onChange={e => set('road_class', inputToOptionCode(roadClassOptions, e.target.value))}
              placeholder="VD: Đường lớn / Hẻm ô tô" />
          </div>
          <div className="form-group">
            <label className="form-label">
              <input type="checkbox"
                checked={form.car_access}
                onChange={e => set('car_access', e.target.checked)} />
              {' '}Ô tô đỗ được vào
            </label>
          </div>
          <div className="form-group">
            <label className="form-label">
              <input type="checkbox"
                checked={form.dead_end}
                onChange={e => set('dead_end', e.target.checked)} />
              {' '}Hẻm cụt (không lối thoát)
            </label>
          </div>
        </div>
      </div>

      {/* Pháp lý */}
      <div className="card">
        <div className="card-header">
          <span>Pháp lý & Quy hoạch
            <span className="text-xs text-muted" style={{ marginLeft: 'auto' }}>
              Impact: ±5-15%
            </span>
          </span>
        </div>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label required">Pháp lý</label>
            <input className="form-input" list="townhouse-ownership" required
              value={displayOption(ownershipOptions, form.ownership_type)}
              onChange={e => set('ownership_type', inputToOptionCode(ownershipOptions, e.target.value))}
              placeholder="VD: Sổ đỏ/Sổ hồng đầy đủ" />
          </div>
          <div className="form-group">
            <label className="form-label">Quy hoạch / Khu vực</label>
            <input className="form-input"
              value={form.planning_zone}
              onChange={e => set('planning_zone', e.target.value)}
              placeholder="VD: Khu đô thị Cầu Giấy" />
          </div>
          <div className="form-group">
            <label className="form-label">Nguy cơ mở đường</label>
            <input className="form-input" list="townhouse-road-risk"
              value={displayOption(roadRiskOptions, form.road_expansion_risk)}
              onChange={e => set('road_expansion_risk', inputToOptionCode(roadRiskOptions, e.target.value))}
              placeholder="VD: Không có / Thấp / Cao" />
          </div>
          <div className="form-group">
            <label className="form-label">
              <input type="checkbox"
                checked={form.dispute_flag}
                onChange={e => set('dispute_flag', e.target.checked)} />
              {' '}Đang có tranh chấp
            </label>
          </div>
          <div className="form-group">
            <label className="form-label">
              <input type="checkbox"
                checked={form.mortgage_flag}
                onChange={e => set('mortgage_flag', e.target.checked)} />
              {' '}Đang thế chấp ngân hàng
            </label>
          </div>
        </div>
      </div>

      {/* Môi trường */}
      <div className="card">
        <div className="card-header">
          <span>Môi trường
            <span className="text-xs text-muted" style={{ marginLeft: 'auto' }}>
              Impact: ±3-16%
            </span>
          </span>
        </div>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Nguy cơ ngập</label>
            <input className="form-input" list="townhouse-flood"
              value={displayOption(floodOptions, form.flood_risk)}
              onChange={e => set('flood_risk', inputToOptionCode(floodOptions, e.target.value))}
              placeholder="VD: Không rõ / Không ngập / Ngập nặng" />
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
            <label className="form-label">Tiếng ồn ngày (dB)</label>
            <input type="number" step="0.1" className="form-input"
              value={form.noise_day_db}
              onChange={e => set('noise_day_db', e.target.value)}
              placeholder="VD: 65" />
          </div>
          <div className="form-group">
            <label className="form-label">Tiếng ồn đêm (dB)</label>
            <input type="number" step="0.1" className="form-input"
              value={form.noise_night_db}
              onChange={e => set('noise_night_db', e.target.value)}
              placeholder="VD: 55" />
          </div>
        </div>
      </div>

      {/* Tâm linh (Fit layer) */}
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
              {' '}Có tử vong trong nhà
            </label>
          </div>
          <div className="form-group">
            <label className="form-label">
              <input type="checkbox"
                checked={form.stigma_known}
                onChange={e => set('stigma_known', e.target.checked)} />
              {' '}Điểm nhạy cảm đã biết
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
