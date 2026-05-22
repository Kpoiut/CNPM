import React, { useState } from 'react';
import {
  ROAD_CLASSES,
  OWNERSHIP_TYPES,
  FLOOD_RISK,
  FENG_SHUI_SENSITIVITIES,
  ASSET_SUBTYPES,
} from '../../constants/vnStrings';
import { ProvinceSelector, DistrictSelector } from '../ui/ProvinceSelector';
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
 * HouseIntakeForm — Asset-specific intake cho NHÀ RIÊNG
 *
 * Phase 2: Tách riêng khỏi TOWNHOUSE.
 * Nhà riêng = nhà độc lập, thường cấp thấp hơn, nhiều tuổi hơn.
 *
 * Fields: land_area_m2, construction_year, renovation_year, structure_grade thấp,
 * kitchen, garden, car_access, main_facing, death_history, stigma.
 *
 * Priority factors: LEGAL, ACCESS, BUILDING_DEPRECATION, LAND
 */
export default function HouseIntakeForm({ onSubmit, loading, isAdmin = false, engineLabel }) {
  const subtypeOptions = mapEntriesToOptions(ASSET_SUBTYPES.HOUSE || {});
  const structureOptions = mapEntriesToOptions({
    NEW: 'Mới xây dựng (< 5 năm)',
    GOOD: 'Tốt — đã cải tạo gần đây',
    AVERAGE: 'Trung bình — cần bảo trì nhẹ',
    POOR: 'Kém — cần sửa chữa lớn',
    VERY_POOR: 'Rất kém — có thể phá dỡ',
  });
  const fengShuiOptions = mapEntriesToOptions(FENG_SHUI_SENSITIVITIES);
  const roadClassOptions = mapEntriesToOptions(ROAD_CLASSES);
  const ownershipOptions = mapEntriesToOptions(OWNERSHIP_TYPES);
  const floodOptions = mapEntriesToOptions(FLOOD_RISK);
  const [form, setForm] = useState({
    // Identity
    asset_type: 'HOUSE',
    asset_subtype: 'HOUSE_OLD',

    // Location
    province_city: 'Hà Nội',
    district: '',
    ward: '',
    street_or_project: '',
    latitude: '',
    longitude: '',

    // Geometry
    area_m2: '',
    land_area_m2: '',
    built_area_m2: '',
    floor_count: '1',
    bedrooms: '2',
    bathrooms: '1',
    kitchen_count: '1',

    // Building
    construction_year: '',
    renovation_year: '',
    structure_grade: 'POOR',
    main_facing: '',

    // Access
    road_class: '',
    road_width_m: '',
    car_access: false,
    dead_end: false,

    // Legal
    ownership_type: 'FULL_OWNERSHIP',
    dispute_flag: false,
    mortgage_flag: false,

    // Environment
    flood_risk: 'unknown',
    cemetery_distance_m: '',
    park_distance_m: '',

    // Fit layer
    death_history_flag: false,
    worship_site_distance_m: '',
    stigma_known: false,
    feng_shui_sensitivity: 'LOW',
    birth_year: '',
  });

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handleSubmit = (e) => {
    e.preventDefault();
    const payload = {
      ...form,
      area_m2: toFloat(form.area_m2),
      land_area_m2: toFloat(form.land_area_m2, toFloat(form.area_m2)),
      built_area_m2: toFloat(form.built_area_m2),
      floor_count: toInt(form.floor_count, 1),
      bedrooms: toInt(form.bedrooms, 0),
      bathrooms: toInt(form.bathrooms, 0),
      kitchen_count: toInt(form.kitchen_count, 1),
      latitude: toFloat(form.latitude),
      longitude: toFloat(form.longitude),
      road_width_m: toFloat(form.road_width_m),
      construction_year: toInt(form.construction_year),
      renovation_year: toInt(form.renovation_year),
      cemetery_distance_m: toFloat(form.cemetery_distance_m),
      park_distance_m: toFloat(form.park_distance_m),
      worship_site_distance_m: toFloat(form.worship_site_distance_m),
      birth_year: toInt(form.birth_year),
    };
    onSubmit(payload);
  };

  const STRUCTURE_GRADES = {
    NEW: 'Mới xây dựng (< 5 năm)',
    GOOD: 'Tốt — đã cải tạo gần đây',
    AVERAGE: 'Trung bình — cần bảo trì nhẹ',
    POOR: 'Kém — cần sửa chữa lớn',
    VERY_POOR: 'Rất kém — có thể phá dỡ',
  };

  const FACING_OPTIONS = [
    { value: '', label: '— Chọn hướng —' },
    { value: 'Đông', label: 'Đông' },
    { value: 'Tây', label: 'Tây' },
    { value: 'Nam', label: 'Nam' },
    { value: 'Bắc', label: 'Bắc' },
    { value: 'Đông Nam', label: 'Đông Nam' },
    { value: 'Tây Nam', label: 'Tây Nam' },
    { value: 'Đông Bắc', label: 'Đông Bắc' },
    { value: 'Tây Bắc', label: 'Tây Bắc' },
  ];

  return (
    <form onSubmit={handleSubmit} onInvalid={scrollInvalidField} onInput={clearInvalidField} className="space-y-4">
      <HintOptions id="house-wards" options={[...LOCATION_HINTS.hanoiWards, ...LOCATION_HINTS.hcmWards]} />
      <HintOptions id="house-streets" options={LOCATION_HINTS.streets} />
      <HintOptions id="house-subtypes" options={subtypeOptions} />
      <HintOptions id="house-structure" options={structureOptions} />
      <HintOptions id="house-facing" options={COMMON_HINTS.orientations} />
      <HintOptions id="house-feng-shui" options={fengShuiOptions} />
      <HintOptions id="house-road-class" options={roadClassOptions} />
      <HintOptions id="house-ownership" options={ownershipOptions} />
      <HintOptions id="house-flood" options={floodOptions} />
      {/* Vị trí */}
      <div className="card">
        <div className="card-header"><span>Vị trí</span></div>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Loại nhà riêng</label>
            <input className="form-input" list="house-subtypes"
              value={displayOption(subtypeOptions, form.asset_subtype)}
              onChange={e => set('asset_subtype', inputToOptionCode(subtypeOptions, e.target.value))}
              placeholder="VD: Nhà cũ / truyền thống" />
          </div>
          <div className="form-group">
            <label className="form-label">Tỉnh / TP</label>
            <ProvinceSelector
              value={form.province_city}
              onChange={val => { set('province_city', val); set('district', '') }}
              className="form-select" required />
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
            <input className="form-input" list="house-wards"
              value={form.ward}
              onChange={e => set('ward', e.target.value)} />
          </div>
          <div className="form-group span-2">
            <label className="form-label">Đường / Dự án</label>
            <input className="form-input" list="house-streets"
              value={form.street_or_project}
              onChange={e => set('street_or_project', e.target.value)} />
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

      {/* Diện tích & Quy mô */}
      <div className="card">
        <div className="card-header">
          <span>Diện tích & Quy mô nhà riêng</span>
          <span className="text-xs text-muted" style={{ marginLeft: 'auto' }}>
            Nhà riêng: đất + công trình cũ/khấu hao
          </span>
        </div>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label required">Diện tích đất (m²) *</label>
            <input type="number" step="0.1" className="form-input" required
              value={form.area_m2}
              onChange={e => set('area_m2', e.target.value)}
              placeholder="VD: 60.0" />
          </div>
          <div className="form-group">
            <label className="form-label">Diện tích sàn xây dựng (m²)</label>
            <input type="number" step="0.1" className="form-input"
              value={form.built_area_m2}
              onChange={e => set('built_area_m2', e.target.value)}
              placeholder="VD: 120.0" />
          </div>
          <div className="form-group">
            <label className="form-label">Số tầng</label>
            <input type="number" min="1" max="5" className="form-input"
              value={form.floor_count}
              onChange={e => set('floor_count', e.target.value)}
              placeholder="VD: 2" />
          </div>
          <div className="form-group">
            <label className="form-label">Phòng ngủ</label>
            <input type="number" min="0" className="form-input"
              value={form.bedrooms}
              onChange={e => set('bedrooms', e.target.value)}
              placeholder="VD: 3" />
          </div>
          <div className="form-group">
            <label className="form-label">Phòng tắm</label>
            <input type="number" min="0" className="form-input"
              value={form.bathrooms}
              onChange={e => set('bathrooms', e.target.value)}
              placeholder="VD: 2" />
          </div>
          <div className="form-group">
            <label className="form-label">Số bếp</label>
            <input type="number" min="0" className="form-input"
              value={form.kitchen_count}
              onChange={e => set('kitchen_count', e.target.value)}
              placeholder="VD: 1" />
          </div>
        </div>
      </div>

      {/* Tuổi & Cấp công trình */}
      <div className="card">
        <div className="card-header"><span>Tuổi & Cấp công trình</span></div>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Năm xây dựng</label>
            <input type="number" min="1950" max="2026" className="form-input"
              value={form.construction_year}
              onChange={e => set('construction_year', e.target.value)}
              placeholder="VD: 2000" />
          </div>
          <div className="form-group">
            <label className="form-label">Năm cải tạo gần nhất</label>
            <input type="number" min="1950" max="2026" className="form-input"
              value={form.renovation_year}
              onChange={e => set('renovation_year', e.target.value)}
              placeholder="VD: 2020" />
          </div>
          <div className="form-group span-2">
            <label className="form-label">Cấp công trình hiện tại</label>
            <input className="form-input" list="house-structure"
              value={displayOption(structureOptions, form.structure_grade)}
              onChange={e => set('structure_grade', inputToOptionCode(structureOptions, e.target.value))}
              placeholder="VD: Tốt / Trung bình" />
          </div>
        </div>
      </div>

      {/* Hướng nhà */}
      <div className="card">
        <div className="card-header">
          <span>Hướng nhà</span>
          <span className="text-xs text-muted" style={{ marginLeft: 'auto' }}>
            Lớp FIT — ảnh hưởng ±1-5%
          </span>
        </div>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Hướng cửa chính</label>
            <input className="form-input" list="house-facing"
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
            <input className="form-input" list="house-feng-shui"
              value={displayOption(fengShuiOptions, form.feng_shui_sensitivity)}
              onChange={e => set('feng_shui_sensitivity', inputToOptionCode(fengShuiOptions, e.target.value))}
              placeholder="VD: Tham khảo nhẹ / Quan tâm cao" />
          </div>
        </div>
      </div>

      {/* Tiếp cận */}
      <div className="card">
        <div className="card-header"><span>Tiếp cận</span></div>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Hạng đường</label>
            <input className="form-input" list="house-road-class"
              value={displayOption(roadClassOptions, form.road_class)}
              onChange={e => set('road_class', inputToOptionCode(roadClassOptions, e.target.value))}
              placeholder="VD: Hẻm 3-5m / Đường chính" />
          </div>
          <div className="form-group">
            <label className="form-label">Bề rộng đường (m)</label>
            <input type="number" step="0.5" className="form-input"
              value={form.road_width_m}
              onChange={e => set('road_width_m', e.target.value)}
              placeholder="VD: 3.5" />
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
              {' '}Hẻm cụt
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
            <input className="form-input" list="house-ownership" required
              value={displayOption(ownershipOptions, form.ownership_type)}
              onChange={e => set('ownership_type', inputToOptionCode(ownershipOptions, e.target.value))}
              placeholder="VD: Sổ đỏ/Sổ hồng đầy đủ" />
          </div>
          <div className="form-group">
            <label className="form-label">
              <input type="checkbox"
                checked={form.dispute_flag}
                onChange={e => set('dispute_flag', e.target.checked)} />
              {' '}Đang tranh chấp
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
            <input className="form-input" list="house-flood"
              value={displayOption(floodOptions, form.flood_risk)}
              onChange={e => set('flood_risk', inputToOptionCode(floodOptions, e.target.value))}
              placeholder="VD: Không rõ / Không ngập" />
          </div>
          <div className="form-group">
            <label className="form-label">Cách nghĩa trang (m)</label>
            <input type="number" className="form-input"
              value={form.cemetery_distance_m}
              onChange={e => set('cemetery_distance_m', e.target.value)} />
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
              {' '}Có tử vong trong nhà
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
