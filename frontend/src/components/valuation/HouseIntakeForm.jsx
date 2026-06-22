import React, { useState, useEffect } from 'react';
import PrefillBanner from './PrefillBanner';
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
  LOCATION_HINTS,
  clearInvalidField,
  scrollInvalidField,
  submitLabel,
  toFloat,
  toInt,
  useFormPrefill,
  useIotAutoFill,
} from './formHelpers';
import {
  OpenSection, CollapsibleSection, SelectField, NumberField, TextField, CheckField, FormProgress, IotAutoNote,
} from './SmartFields';

/**
 * HouseIntakeForm — NHÀ RIÊNG (bản tinh gọn: chọn 1 chạm, gập phần nâng cao).
 */
const STRUCTURE_GRADES = {
  NEW: 'Mới xây dựng (< 5 năm)',
  GOOD: 'Tốt — đã cải tạo gần đây',
  AVERAGE: 'Trung bình — cần bảo trì nhẹ',
  POOR: 'Kém — cần sửa chữa lớn',
  VERY_POOR: 'Rất kém — có thể phá dỡ',
};
const WARD_HINTS = [...LOCATION_HINTS.hanoiWards, ...LOCATION_HINTS.hcmWards];

export default function HouseIntakeForm({ onSubmit, loading, isAdmin = false, engineLabel, prefill, onLiveChange }) {
  const [form, setForm] = useState({
    asset_type: 'HOUSE',
    asset_subtype: 'HOUSE_OLD',
    province_city: 'Hà Nội',
    district: '',
    ward: '',
    street_or_project: '',
    latitude: '',
    longitude: '',
    area_m2: '',
    land_area_m2: '',
    built_area_m2: '',
    floor_count: '1',
    bedrooms: '2',
    bathrooms: '1',
    kitchen_count: '1',
    construction_year: '',
    renovation_year: '',
    structure_grade: 'POOR',
    main_facing: '',
    road_class: '',
    road_width_m: '',
    car_access: false,
    dead_end: false,
    ownership_type: 'FULL_OWNERSHIP',
    dispute_flag: false,
    mortgage_flag: false,
    flood_risk: 'unknown',
    cemetery_distance_m: '',
    park_distance_m: '',
    death_history_flag: false,
    worship_site_distance_m: '',
    stigma_known: false,
    feng_shui_sensitivity: 'LOW',
    birth_year: '',
  });

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  useFormPrefill(prefill, setForm);
  const iotAuto = useIotAutoFill(form, setForm);

  const buildPayload = () => ({
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
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(buildPayload());
  };

  useEffect(() => { if (onLiveChange) onLiveChange(buildPayload()); }, [form]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <form onSubmit={handleSubmit} onInvalid={scrollInvalidField} onInput={clearInvalidField} className="space-y-4">
      <PrefillBanner prefill={prefill} onPick={set} />
      <FormProgress form={form} />
      <IotAutoNote data={iotAuto} />

      <OpenSection title="Vị trí" hint="Mẹo: dùng “Định vị thông minh” để tự điền">
        <SelectField label="Loại nhà riêng" value={form.asset_subtype} onChange={v => set('asset_subtype', v)} options={ASSET_SUBTYPES.HOUSE} placeholder="— Chọn loại —" />
        <div className="form-group">
          <label className="form-label">Tỉnh / TP</label>
          <ProvinceSelector value={form.province_city} onChange={val => { set('province_city', val); set('district', '') }} className="form-select" required />
        </div>
        <div className="form-group">
          <label className="form-label required">Quận / Huyện *</label>
          <DistrictSelector provinceCode={form.province_city} value={form.district} onChange={val => set('district', val)} className="form-select" required />
        </div>
        <TextField label="Phường / Xã" value={form.ward} onChange={v => set('ward', v)} options={WARD_HINTS} />
        <TextField label="Đường / Dự án" value={form.street_or_project} onChange={v => set('street_or_project', v)} options={LOCATION_HINTS.streets} span />
        <NumberField label="Vĩ độ (GPS)" value={form.latitude} onChange={v => set('latitude', v)} step="0.0001" placeholder="Tự điền từ bản đồ" />
        <NumberField label="Kinh độ (GPS)" value={form.longitude} onChange={v => set('longitude', v)} step="0.0001" placeholder="Tự điền từ bản đồ" />
      </OpenSection>

      <OpenSection title="Diện tích & Quy mô">
        <NumberField label="Diện tích đất (m²)" value={form.area_m2} onChange={v => set('area_m2', v)} required step="0.1" placeholder="VD: 60" />
        <NumberField label="Diện tích sàn xây dựng (m²)" value={form.built_area_m2} onChange={v => set('built_area_m2', v)} step="0.1" placeholder="VD: 120" />
        <NumberField label="Số tầng" value={form.floor_count} onChange={v => set('floor_count', v)} min="1" max="5" suggestions={[1, 2, 3, 4]} />
        <NumberField label="Phòng ngủ" value={form.bedrooms} onChange={v => set('bedrooms', v)} min="0" suggestions={[2, 3, 4]} />
        <NumberField label="Phòng tắm" value={form.bathrooms} onChange={v => set('bathrooms', v)} min="0" suggestions={[1, 2, 3]} />
        <NumberField label="Số bếp" value={form.kitchen_count} onChange={v => set('kitchen_count', v)} min="0" suggestions={[1, 2]} />
      </OpenSection>

      <OpenSection title="Pháp lý" hint="Impact ±5-15%">
        <SelectField label="Pháp lý" value={form.ownership_type} onChange={v => set('ownership_type', v)} options={OWNERSHIP_TYPES} required />
        <CheckField label="Đang tranh chấp" checked={form.dispute_flag} onChange={v => set('dispute_flag', v)} />
        <CheckField label="Đang thế chấp ngân hàng" checked={form.mortgage_flag} onChange={v => set('mortgage_flag', v)} />
      </OpenSection>

      <CollapsibleSection title="Tuổi & Cấp công trình">
        <NumberField label="Năm xây dựng" value={form.construction_year} onChange={v => set('construction_year', v)} min="1950" max="2026" placeholder="VD: 2000" />
        <NumberField label="Năm cải tạo gần nhất" value={form.renovation_year} onChange={v => set('renovation_year', v)} min="1950" max="2026" placeholder="VD: 2020" />
        <SelectField label="Cấp công trình hiện tại" value={form.structure_grade} onChange={v => set('structure_grade', v)} options={STRUCTURE_GRADES} span />
      </CollapsibleSection>

      <CollapsibleSection title="Hướng nhà & Phong thủy" hint="Lớp FIT ±1-5%" accent="var(--primary-200)">
        <SelectField label="Hướng cửa chính" value={form.main_facing} onChange={v => set('main_facing', v)} options={COMMON_HINTS.orientations} placeholder="— Chọn hướng —" />
        <NumberField label="Năm sinh chủ nhà" value={form.birth_year} onChange={v => set('birth_year', v)} min="1920" max="2015" placeholder="VD: 1985" />
        <SelectField label="Mức quan tâm phong thủy" value={form.feng_shui_sensitivity} onChange={v => set('feng_shui_sensitivity', v)} options={FENG_SHUI_SENSITIVITIES} />
      </CollapsibleSection>

      <CollapsibleSection title="Tiếp cận">
        <SelectField label="Hạng đường" value={form.road_class} onChange={v => set('road_class', v)} options={ROAD_CLASSES} />
        <NumberField label="Bề rộng đường (m)" value={form.road_width_m} onChange={v => set('road_width_m', v)} step="0.5" placeholder="VD: 3.5" />
        <CheckField label="Ô tô đỗ được vào" checked={form.car_access} onChange={v => set('car_access', v)} />
        <CheckField label="Hẻm cụt" checked={form.dead_end} onChange={v => set('dead_end', v)} />
      </CollapsibleSection>

      <CollapsibleSection title="Môi trường">
        <SelectField label="Nguy cơ ngập" value={form.flood_risk} onChange={v => set('flood_risk', v)} options={FLOOD_RISK} />
        <NumberField label="Cách nghĩa trang (m)" value={form.cemetery_distance_m} onChange={v => set('cemetery_distance_m', v)} />
        <NumberField label="Cách công viên (m)" value={form.park_distance_m} onChange={v => set('park_distance_m', v)} />
      </CollapsibleSection>

      <CollapsibleSection title="Lịch sử tâm linh" hint="Lớp FIT — không ảnh hưởng giá thị trường" accent="var(--warning-border)">
        <CheckField label="Có tử vong trong nhà" checked={form.death_history_flag} onChange={v => set('death_history_flag', v)} />
        <CheckField label="Điểm nhạy cảm đã biết trong khu vực" checked={form.stigma_known} onChange={v => set('stigma_known', v)} />
        <NumberField label="Cách nơi thờ cúng (m)" value={form.worship_site_distance_m} onChange={v => set('worship_site_distance_m', v)} />
      </CollapsibleSection>

      <button type="submit" className="btn btn-primary btn-lg btn-full" disabled={loading}>
        {submitLabel(isAdmin, loading, engineLabel)}
      </button>
    </form>
  );
}
