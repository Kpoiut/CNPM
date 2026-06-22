import React, { useState, useEffect } from 'react';
import PrefillBanner from './PrefillBanner';
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
  OpenSection, CollapsibleSection, SelectField, NumberField, TextField, CheckField, SliderField, FormProgress, IotAutoNote,
} from './SmartFields';

/**
 * VillaIntakeForm — BIỆT THỰ (bản tinh gọn).
 */
const WARD_HINTS = [...LOCATION_HINTS.hanoiWards, ...LOCATION_HINTS.hcmWards];
const STRUCTURE_GRADES = {
  PREMIUM: 'A+ - Biệt thự cao cấp (Vinhomes/Riverside)',
  LUXURY: 'A - Xây dựng xa hoa',
  HIGH: 'B+ - Xây dựng tốt, vật liệu cao cấp',
  GOOD: 'B - Xây dựng khung BTCT, bảo trì tốt',
  AVERAGE: 'C - Trung bình, cần cải tạo nhẹ',
};
const DEVELOPERS = {
  VINGROUP: 'Vingroup (Vinhomes)',
  NOVALAND: 'Novaland',
  MASTERI: 'Masteri Holdings',
  SUNWAH: 'Sunwah',
  BRG: 'BRG Group',
  ECOPARK: 'Ecopark',
  DONGTABU: 'Đông Tây Land',
  OTHER: 'Khác',
  NONE: 'Không có thương hiệu',
};

export default function VillaIntakeForm({ onSubmit, loading, isAdmin = false, engineLabel, prefill, onLiveChange }) {
  const [form, setForm] = useState({
    asset_type: 'VILLA',
    asset_subtype: 'VILLA_MODERN',
    province_city: 'Hà Nội',
    district: '',
    ward: '',
    street_or_project: '',
    latitude: '',
    longitude: '',
    land_area_m2: '',
    built_area_m2: '',
    garden_area_m2: '',
    floor_count: '2',
    bedrooms: '4',
    bathrooms: '3',
    pool_flag: false,
    compound_flag: false,
    developer_brand: '',
    structure_grade: 'PREMIUM',
    privacy_score: '7',
    road_class: '',
    road_width_m: '',
    dead_end: false,
    ownership_type: 'FULL_OWNERSHIP',
    road_expansion_risk: 'none',
    dispute_flag: false,
    mortgage_flag: false,
    main_facing: '',
    feng_shui_sensitivity: 'MEDIUM',
    birth_year: '',
    flood_risk: 'unknown',
    cemetery_distance_m: '',
    river_distance_m: '',
    park_distance_m: '',
    death_history_flag: false,
    worship_site_distance_m: '',
    stigma_known: false,
  });

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  useFormPrefill(prefill, setForm);
  const iotAuto = useIotAutoFill(form, setForm);

  const buildPayload = () => ({
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
        <SelectField label="Loại biệt thự" value={form.asset_subtype} onChange={v => set('asset_subtype', v)} options={ASSET_SUBTYPES.VILLA} />
        <div className="form-group">
          <label className="form-label">Tỉnh / TP</label>
          <ProvinceSelector value={form.province_city} onChange={val => { set('province_city', val); set('district', '') }} className="form-select" />
        </div>
        <div className="form-group">
          <label className="form-label required">Quận / Huyện *</label>
          <DistrictSelector provinceCode={form.province_city} value={form.district} onChange={val => set('district', val)} className="form-select" required />
        </div>
        <TextField label="Phường / Xã" value={form.ward} onChange={v => set('ward', v)} options={WARD_HINTS} />
        <TextField label="Đường / Dự án" value={form.street_or_project} onChange={v => set('street_or_project', v)} options={LOCATION_HINTS.projects} placeholder="VD: Vinhomes Riverside" span />
        <NumberField label="Vĩ độ (GPS)" value={form.latitude} onChange={v => set('latitude', v)} step="0.0001" placeholder="Tự điền từ bản đồ" />
        <NumberField label="Kinh độ (GPS)" value={form.longitude} onChange={v => set('longitude', v)} step="0.0001" placeholder="Tự điền từ bản đồ" />
      </OpenSection>

      <OpenSection title="Diện tích & Quy mô biệt thự" hint="Đất chiếm ưu thế trong giá trị">
        <NumberField label="Diện tích đất (m²)" value={form.land_area_m2} onChange={v => set('land_area_m2', v)} required step="0.1" placeholder="VD: 250" />
        <NumberField label="Diện tích sàn xây dựng (m²)" value={form.built_area_m2} onChange={v => set('built_area_m2', v)} step="0.1" placeholder="VD: 350" />
        <NumberField label="Diện tích vườn/sân (m²)" value={form.garden_area_m2} onChange={v => set('garden_area_m2', v)} step="0.1" placeholder="VD: 100" />
        <NumberField label="Số tầng" value={form.floor_count} onChange={v => set('floor_count', v)} min="1" max="5" suggestions={[2, 3]} />
        <NumberField label="Phòng ngủ" value={form.bedrooms} onChange={v => set('bedrooms', v)} min="0" suggestions={[4, 5, 6]} />
        <NumberField label="Phòng tắm" value={form.bathrooms} onChange={v => set('bathrooms', v)} min="0" suggestions={[3, 4]} />
        <SelectField label="Hạng cấp công trình" value={form.structure_grade} onChange={v => set('structure_grade', v)} options={STRUCTURE_GRADES} />
        <SelectField label="Thương hiệu chủ đầu tư" value={form.developer_brand} onChange={v => set('developer_brand', v)} options={DEVELOPERS} />
        <SliderField label="Điểm riêng tư" value={form.privacy_score} onChange={v => set('privacy_score', v)} min={1} max={10} step={1} format={v => `${v}/10`} />
        <CheckField label="Có hồ bơi riêng" checked={form.pool_flag} onChange={v => set('pool_flag', v)} />
        <CheckField label="Biệt thự compound (khu an ninh riêng)" checked={form.compound_flag} onChange={v => set('compound_flag', v)} />
      </OpenSection>

      <OpenSection title="Pháp lý" hint="Impact ±5-15%">
        <SelectField label="Pháp lý" value={form.ownership_type} onChange={v => set('ownership_type', v)} options={OWNERSHIP_TYPES} required />
        <CheckField label="Đang có tranh chấp" checked={form.dispute_flag} onChange={v => set('dispute_flag', v)} />
        <CheckField label="Đang thế chấp ngân hàng" checked={form.mortgage_flag} onChange={v => set('mortgage_flag', v)} />
      </OpenSection>

      <CollapsibleSection title="Hướng & Phong thủy biệt thự" hint="Lớp FIT ±3-5%" accent="var(--primary-200)">
        <SelectField label="Hướng cửa chính" value={form.main_facing} onChange={v => set('main_facing', v)} options={COMMON_HINTS.orientations} />
        <NumberField label="Năm sinh chủ nhà" value={form.birth_year} onChange={v => set('birth_year', v)} min="1920" max="2015" placeholder="VD: 1985" />
        <SelectField label="Mức quan tâm phong thủy" value={form.feng_shui_sensitivity} onChange={v => set('feng_shui_sensitivity', v)} options={FENG_SHUI_SENSITIVITIES} />
      </CollapsibleSection>

      <CollapsibleSection title="Tiếp cận & Đường">
        <NumberField label="Bề rộng đường (m)" value={form.road_width_m} onChange={v => set('road_width_m', v)} step="0.5" placeholder="VD: 8.0" />
        <SelectField label="Hạng đường" value={form.road_class} onChange={v => set('road_class', v)} options={ROAD_CLASSES} />
        <SelectField label="Nguy cơ mở đường" value={form.road_expansion_risk} onChange={v => set('road_expansion_risk', v)} options={COMMON_HINTS.riskLevels} />
        <CheckField label="Hẻm cụt (compound riêng tư)" checked={form.dead_end} onChange={v => set('dead_end', v)} />
      </CollapsibleSection>

      <CollapsibleSection title="Môi trường">
        <SelectField label="Nguy cơ ngập" value={form.flood_risk} onChange={v => set('flood_risk', v)} options={FLOOD_RISK} />
        <NumberField label="Cách nghĩa trang (m)" value={form.cemetery_distance_m} onChange={v => set('cemetery_distance_m', v)} />
        <NumberField label="Cách sông (m)" value={form.river_distance_m} onChange={v => set('river_distance_m', v)} />
        <NumberField label="Cách công viên (m)" value={form.park_distance_m} onChange={v => set('park_distance_m', v)} />
      </CollapsibleSection>

      <CollapsibleSection title="Lịch sử tâm linh" hint="Lớp FIT — không ảnh hưởng giá thị trường" accent="var(--warning-border)">
        <CheckField label="Có tử vong trong tài sản" checked={form.death_history_flag} onChange={v => set('death_history_flag', v)} />
        <CheckField label="Điểm nhạy cảm đã biết trong khu vực" checked={form.stigma_known} onChange={v => set('stigma_known', v)} />
        <NumberField label="Cách nơi thờ cúng (m)" value={form.worship_site_distance_m} onChange={v => set('worship_site_distance_m', v)} />
      </CollapsibleSection>

      <button type="submit" className="btn btn-primary btn-lg btn-full" disabled={loading}>
        {submitLabel(isAdmin, loading, engineLabel)}
      </button>
    </form>
  );
}
