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
 * VillaIntakeForm — Asset-specific intake cho BIỆT THỰ
 *
 * Fields riêng cho biệt thự:
 * - land_area_m2, built_area_m2 (LAND > BUILDING)
 * - garden_area_m2, pool_flag, compound_flag
 * - privacy_score, developer_brand
 * - structure_grade cao cấp
 *
 * Priority factors: LEGAL, PRIVACY, LAND_RATIO, DEVELOPMENT, FLOOD
 */
export default function VillaIntakeForm({ onSubmit, loading, isAdmin = false, engineLabel }) {
  const subtypeOptions = mapEntriesToOptions(ASSET_SUBTYPES.VILLA || {});
  const structureOptions = mapEntriesToOptions({
    PREMIUM: 'A+ - Biệt thự cao cấp (Vinhomes/Riverside)',
    LUXURY: 'A - Xây dựng xa hoa',
    HIGH: 'B+ - Xây dựng tốt, vật liệu cao cấp',
    GOOD: 'B - Xây dựng khung BTCT, bảo trì tốt',
    AVERAGE: 'C - Trung bình, cần cải tạo nhẹ',
  });
  const developerOptions = mapEntriesToOptions({
    VINGROUP: 'Vingroup (Vinhomes)',
    NOVALAND: 'Novaland',
    MASTERI: 'Masteri Holdings',
    SUNWAH: 'Sunwah',
    BRG: 'BRG Group',
    ECOPARK: 'Ecopark',
    DONGTABU: 'Đông Tây Land',
    OTHER: 'Khác',
    NONE: 'Không có thương hiệu',
  });
  const fengShuiOptions = mapEntriesToOptions(FENG_SHUI_SENSITIVITIES);
  const roadClassOptions = mapEntriesToOptions(ROAD_CLASSES);
  const ownershipOptions = mapEntriesToOptions(OWNERSHIP_TYPES);
  const floodOptions = mapEntriesToOptions(FLOOD_RISK);
  const [form, setForm] = useState({
    // Identity
    asset_type: 'VILLA',
    asset_subtype: 'VILLA_MODERN',

    // Location
    province_city: 'Hà Nội',
    district: '',
    ward: '',
    street_or_project: '',
    latitude: '',
    longitude: '',

    // Land & Building (LAND dominant)
    land_area_m2: '',
    built_area_m2: '',
    garden_area_m2: '',
    floor_count: '2',
    bedrooms: '4',
    bathrooms: '3',

    // Villa-specific
    pool_flag: false,
    compound_flag: false,
    developer_brand: '',
    structure_grade: 'PREMIUM',
    privacy_score: '7',

    // Access & road
    road_class: '',
    road_width_m: '',
    dead_end: false,

    // Legal
    ownership_type: 'FULL_OWNERSHIP',
    road_expansion_risk: 'none',
    dispute_flag: false,
    mortgage_flag: false,

    // Feng shui
    main_facing: '',
    feng_shui_sensitivity: 'MEDIUM',
    birth_year: '',

    // Environment
    flood_risk: 'unknown',
    cemetery_distance_m: '',
    river_distance_m: '',
    park_distance_m: '',

    // Spiritual / Fit layer
    death_history_flag: false,
    worship_site_distance_m: '',
    stigma_known: false,
  });

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handleSubmit = (e) => {
    e.preventDefault();
    const payload = {
      ...form,
      area_m2: toFloat(form.land_area_m2),
      land_area_m2: toFloat(form.land_area_m2),
      built_area_m2: toFloat(form.built_area_m2),
      garden_area_m2: toFloat(form.garden_area_m2),
      floor_count: toInt(form.floor_count, 2),
      bedrooms: toInt(form.bedrooms, 0),
      bathrooms: toInt(form.bathrooms, 0),
      latitude: toFloat(form.latitude),
      longitude: toFloat(form.longitude),
      road_width_m: toFloat(form.road_width_m),
      cemetery_distance_m: toFloat(form.cemetery_distance_m),
      river_distance_m: toFloat(form.river_distance_m),
      park_distance_m: toFloat(form.park_distance_m),
      worship_site_distance_m: toFloat(form.worship_site_distance_m),
      birth_year: toInt(form.birth_year),
      privacy_score: toInt(form.privacy_score, 5),
    };
    onSubmit(payload);
  };

  return (
    <form onSubmit={handleSubmit} onInvalid={scrollInvalidField} onInput={clearInvalidField} className="space-y-4">
      <HintOptions id="villa-wards" options={[...LOCATION_HINTS.hanoiWards, ...LOCATION_HINTS.hcmWards]} />
      <HintOptions id="villa-projects" options={LOCATION_HINTS.projects} />
      <HintOptions id="villa-subtypes" options={subtypeOptions} />
      <HintOptions id="villa-structure" options={structureOptions} />
      <HintOptions id="villa-developers" options={developerOptions} />
      <HintOptions id="villa-facing" options={COMMON_HINTS.orientations} />
      <HintOptions id="villa-feng-shui" options={fengShuiOptions} />
      <HintOptions id="villa-road-class" options={roadClassOptions} />
      <HintOptions id="villa-ownership" options={ownershipOptions} />
      <HintOptions id="villa-flood" options={floodOptions} />
      {/* Vị trí */}
      <div className="card">
        <div className="card-header"><span>Vị trí</span></div>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Loại biệt thự</label>
            <input className="form-input" list="villa-subtypes"
              value={displayOption(subtypeOptions, form.asset_subtype)}
              onChange={e => set('asset_subtype', inputToOptionCode(subtypeOptions, e.target.value))}
              placeholder="VD: Biệt thự hiện đại" />
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
            <input className="form-input" list="villa-wards"
              value={form.ward}
              onChange={e => set('ward', e.target.value)} />
          </div>
          <div className="form-group span-2">
            <label className="form-label">Đường / Dự án</label>
            <input className="form-input" list="villa-projects"
              value={form.street_or_project}
              onChange={e => set('street_or_project', e.target.value)}
              placeholder="VD: Vinhomes Riverside" />
          </div>
          <div className="form-group">
            <label className="form-label">Vĩ độ (GPS)</label>
            <input type="number" step="0.0001" className="form-input"
              value={form.latitude}
              onChange={e => set('latitude', e.target.value)}
              placeholder="21.0285" />
          </div>
          <div className="form-group">
            <label className="form-label">Kinh độ (GPS)</label>
            <input type="number" step="0.0001" className="form-input"
              value={form.longitude}
              onChange={e => set('longitude', e.target.value)}
              placeholder="105.8542" />
          </div>
        </div>
      </div>

      {/* Diện tích & Quy mô — LAND dominant */}
      <div className="card">
        <div className="card-header">
          <span>Diện tích & Quy mô biệt thự</span>
          <span className="text-xs text-muted" style={{ marginLeft: 'auto' }}>
            Đất chiếm ưu thế trong giá trị biệt thự
          </span>
        </div>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label required">Diện tích đất (m²) *</label>
            <input type="number" step="0.1" className="form-input" required
              value={form.land_area_m2}
              onChange={e => set('land_area_m2', e.target.value)}
              placeholder="VD: 250.0" />
          </div>
          <div className="form-group">
            <label className="form-label">Diện tích sàn xây dựng (m²)</label>
            <input type="number" step="0.1" className="form-input"
              value={form.built_area_m2}
              onChange={e => set('built_area_m2', e.target.value)}
              placeholder="VD: 350.0" />
          </div>
          <div className="form-group">
            <label className="form-label">Diện tích vườn/sân (m²)</label>
            <input type="number" step="0.1" className="form-input"
              value={form.garden_area_m2}
              onChange={e => set('garden_area_m2', e.target.value)}
              placeholder="VD: 100.0" />
          </div>
          <div className="form-group">
            <label className="form-label">Số tầng</label>
            <input type="number" min="1" max="5" className="form-input"
              value={form.floor_count}
              onChange={e => set('floor_count', e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Phòng ngủ</label>
            <input type="number" min="0" className="form-input"
              value={form.bedrooms}
              onChange={e => set('bedrooms', e.target.value)}
              placeholder="VD: 5" />
          </div>
          <div className="form-group">
            <label className="form-label">Phòng tắm</label>
            <input type="number" min="0" className="form-input"
              value={form.bathrooms}
              onChange={e => set('bathrooms', e.target.value)}
              placeholder="VD: 4" />
          </div>
          <div className="form-group">
            <label className="form-label">Hạng cấp công trình</label>
            <input className="form-input" list="villa-structure"
              value={displayOption(structureOptions, form.structure_grade)}
              onChange={e => set('structure_grade', inputToOptionCode(structureOptions, e.target.value))}
              placeholder="VD: Biệt thự cao cấp / Xây dựng tốt" />
          </div>
          <div className="form-group">
            <label className="form-label">Thương hiệu chủ đầu tư</label>
            <input className="form-input" list="villa-developers"
              value={displayOption(developerOptions, form.developer_brand)}
              onChange={e => set('developer_brand', inputToOptionCode(developerOptions, e.target.value))}
              placeholder="VD: Vingroup / Ecopark / Khác" />
          </div>
          <div className="form-group">
            <label className="form-label">Điểm riêng tư (1-10)</label>
            <input type="number" min="1" max="10" className="form-input"
              value={form.privacy_score}
              onChange={e => set('privacy_score', e.target.value)}
              placeholder="7" />
          </div>
          <div className="form-group">
            <label className="form-label">
              <input type="checkbox"
                checked={form.pool_flag}
                onChange={e => set('pool_flag', e.target.checked)} />
              {' '}Có hồ bơi riêng
            </label>
          </div>
          <div className="form-group">
            <label className="form-label">
              <input type="checkbox"
                checked={form.compound_flag}
                onChange={e => set('compound_flag', e.target.checked)} />
              {' '}Biệt thự compound (khu an ninh riêng)
            </label>
          </div>
        </div>
      </div>

      {/* Hướng & Phong thủy */}
      <div className="card" style={{ borderColor: 'var(--primary-200)' }}>
        <div className="card-header" style={{ color: 'var(--primary)' }}>
          Hướng & Phong thủy biệt thự
          <span className="text-xs text-muted" style={{ marginLeft: 'auto', opacity: 0.7 }}>
            Lớp FIT — ảnh hưởng ±3-5%
          </span>
        </div>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Hướng cửa chính</label>
            <input className="form-input" list="villa-facing"
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
            <input className="form-input" list="villa-feng-shui"
              value={displayOption(fengShuiOptions, form.feng_shui_sensitivity)}
              onChange={e => set('feng_shui_sensitivity', inputToOptionCode(fengShuiOptions, e.target.value))}
              placeholder="VD: Trung bình / Quan tâm cao" />
          </div>
        </div>
      </div>

      {/* Tiếp cận */}
      <div className="card">
        <div className="card-header"><span>Tiếp cận & Đường</span></div>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Bề rộng đường (m)</label>
            <input type="number" step="0.5" className="form-input"
              value={form.road_width_m}
              onChange={e => set('road_width_m', e.target.value)}
              placeholder="VD: 8.0" />
          </div>
          <div className="form-group">
            <label className="form-label">Hạng đường</label>
            <input className="form-input" list="villa-road-class"
              value={displayOption(roadClassOptions, form.road_class)}
              onChange={e => set('road_class', inputToOptionCode(roadClassOptions, e.target.value))}
              placeholder="VD: Đường lớn / Đường nội khu" />
          </div>
          <div className="form-group">
            <label className="form-label">
              <input type="checkbox"
                checked={form.dead_end}
                onChange={e => set('dead_end', e.target.checked)} />
              {' '}Hẻm cụt (compound riêng tư)
            </label>
          </div>
        </div>
      </div>

      {/* Pháp lý */}
      <div className="card">
        <div className="card-header">
          <span>Pháp lý</span>
          <span className="text-xs text-muted" style={{ marginLeft: 'auto' }}>Impact: ±5-15%</span>
        </div>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label required">Pháp lý</label>
            <input className="form-input" list="villa-ownership" required
              value={displayOption(ownershipOptions, form.ownership_type)}
              onChange={e => set('ownership_type', inputToOptionCode(ownershipOptions, e.target.value))}
              placeholder="VD: Sổ đỏ/Sổ hồng đầy đủ" />
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
        <div className="card-header"><span>Môi trường</span></div>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Nguy cơ ngập</label>
            <input className="form-input" list="villa-flood"
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
              {' '}Có tử vong trong tài sản
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
