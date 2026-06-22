import React, { useState, useEffect } from 'react';
import PrefillBanner from './PrefillBanner';
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
 * ApartmentIntakeForm — CĂN HỘ (bản tinh gọn, đầy đủ hơn: thêm tiện ích toà nhà + IoT).
 */
const WARD_HINTS = [...LOCATION_HINTS.hanoiWards, ...LOCATION_HINTS.hcmWards];
const BUILDING_QUALITY = {
  LUXURY: 'Hạng sang', PREMIUM: 'Cao cấp', STANDARD: 'Tiêu chuẩn', ECONOMY: 'Bình dân',
};
const DISTANCE_OPTS = COMMON_HINTS.distances;

export default function ApartmentIntakeForm({ onSubmit, loading, isAdmin = false, engineLabel, prefill, onLiveChange }) {
  const [form, setForm] = useState({
    asset_type: 'APARTMENT',
    province_city: 'TP. Hồ Chí Minh',
    district: '',
    ward: '',
    area_m2: '',
    latitude: '',
    longitude: '',
    block_name: '',
    apt_floor: '',
    unit_position: 'middle',
    door_orientation: '',
    balcony_orientation: '',
    main_facing: '',
    view_type: '',
    view_obstruction_pct: '0',
    elevator_distance: 'medium',
    trash_room_distance: 'medium',
    core_distance: 'far',
    stair_distance: 'medium',
    layout_score: '0.7',
    bedrooms: '',
    bathrooms: '',
    has_utilities_room: false,
    sunlight_exposure: 'FAIR',
    ventilation_score: '0.7',
    noise_inside_db: '',
    building_quality: 'STANDARD',
    building_age_years: '',
    has_concierge: false,
    has_pool: false,
    has_gym: false,
    ownership_type: 'FULL_OWNERSHIP',
    flood_risk: 'unknown',
    feng_shui_sensitivity: 'NONE',
    noise_tolerance: 'NEUTRAL',
    noise_level: '',
    temperature: '',
    humidity: '',
    gps_lat: '',
    gps_lng: '',
  });

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  useFormPrefill(prefill, setForm);
  const iotAuto = useIotAutoFill(form, setForm);

  const buildPayload = () => ({
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

      <OpenSection title="Vị trí & Căn hộ" hint="Mẹo: dùng “Định vị thông minh” để tự điền">
        <div className="form-group">
          <label className="form-label">Tỉnh / TP</label>
          <ProvinceSelector value={form.province_city} onChange={val => { set('province_city', val); set('district', '') }} className="form-select" />
        </div>
        <div className="form-group">
          <label className="form-label required">Quận / Huyện *</label>
          <DistrictSelector provinceCode={form.province_city} value={form.district} onChange={val => set('district', val)} className="form-select" required />
        </div>
        <TextField label="Phường / Xã" value={form.ward} onChange={v => set('ward', v)} options={WARD_HINTS} />
        <NumberField label="Diện tích căn hộ (m²)" value={form.area_m2} onChange={v => set('area_m2', v)} required step="0.1" placeholder="VD: 72.5" />
        <TextField label="Block / Tower" value={form.block_name} onChange={v => set('block_name', v)} options={LOCATION_HINTS.blocks} placeholder="VD: Tower A" />
        <NumberField label="Tầng" value={form.apt_floor} onChange={v => set('apt_floor', v)} required placeholder="VD: 15" />
        <SelectField label="Vị trí trong block" value={form.unit_position} onChange={v => set('unit_position', v)} options={COMMON_HINTS.unitPositions} />
        <NumberField label="Vĩ độ (GPS)" value={form.latitude} onChange={v => set('latitude', v)} step="0.0001" placeholder="Tự điền từ bản đồ" />
        <NumberField label="Kinh độ (GPS)" value={form.longitude} onChange={v => set('longitude', v)} step="0.0001" placeholder="Tự điền từ bản đồ" />
      </OpenSection>

      <OpenSection title="Pháp lý" hint="Impact ±5-15%">
        <SelectField label="Pháp lý" value={form.ownership_type} onChange={v => set('ownership_type', v)} options={OWNERSHIP_TYPES} required span />
      </OpenSection>

      <CollapsibleSection title="View & Hướng nhìn" hint="Impact ±10%">
        <SelectField label="Loại view" value={form.view_type} onChange={v => set('view_type', v)} options={APT_VIEW_TYPES} />
        <SliderField label="Độ che chắn view (%)" value={form.view_obstruction_pct} onChange={v => set('view_obstruction_pct', v)} min={0} max={100} step={5} format={v => `${v}% bị che`} />
        <SelectField label="Hướng cửa chính" value={form.door_orientation} onChange={v => set('door_orientation', v)} options={COMMON_HINTS.orientations} />
        <SelectField label="Hướng ban công" value={form.balcony_orientation} onChange={v => set('balcony_orientation', v)} options={COMMON_HINTS.orientations} />
        <SelectField label="Nắng Tây chiều" value={form.sunlight_exposure} onChange={v => set('sunlight_exposure', v)} options={COMMON_HINTS.sunlight} />
      </CollapsibleSection>

      <CollapsibleSection title="Khoảng cách tiện ích">
        <SelectField label="Thang máy" value={form.elevator_distance} onChange={v => set('elevator_distance', v)} options={DISTANCE_OPTS} />
        <SelectField label="Phòng rác" value={form.trash_room_distance} onChange={v => set('trash_room_distance', v)} options={DISTANCE_OPTS} />
        <SelectField label="Lõi kỹ thuật" value={form.core_distance} onChange={v => set('core_distance', v)} options={DISTANCE_OPTS} />
        <SelectField label="Cầu thang bộ" value={form.stair_distance} onChange={v => set('stair_distance', v)} options={DISTANCE_OPTS} />
      </CollapsibleSection>

      <CollapsibleSection title="Bố cục & Chất lượng sống">
        <NumberField label="Số phòng ngủ" value={form.bedrooms} onChange={v => set('bedrooms', v)} min="0" suggestions={[1, 2, 3]} />
        <NumberField label="Số phòng tắm" value={form.bathrooms} onChange={v => set('bathrooms', v)} min="0" suggestions={[1, 2]} />
        <SliderField label="Bố cục hợp lý (0→1)" value={form.layout_score} onChange={v => set('layout_score', v)} format={v => Number(v).toFixed(1)} />
        <SliderField label="Thông thoáng (0→1)" value={form.ventilation_score} onChange={v => set('ventilation_score', v)} step={0.1} format={v => Number(v).toFixed(1)} />
        <CheckField label="Có phòng đa năng / kho" checked={form.has_utilities_room} onChange={v => set('has_utilities_room', v)} />
      </CollapsibleSection>

      <CollapsibleSection title="Toà nhà & Tiện ích">
        <SelectField label="Chất lượng toà nhà" value={form.building_quality} onChange={v => set('building_quality', v)} options={BUILDING_QUALITY} />
        <NumberField label="Tuổi toà nhà (năm)" value={form.building_age_years} onChange={v => set('building_age_years', v)} min="0" placeholder="VD: 5" />
        <CheckField label="Có lễ tân / bảo vệ 24/7" checked={form.has_concierge} onChange={v => set('has_concierge', v)} />
        <CheckField label="Có hồ bơi" checked={form.has_pool} onChange={v => set('has_pool', v)} />
        <CheckField label="Có phòng gym" checked={form.has_gym} onChange={v => set('has_gym', v)} />
      </CollapsibleSection>

      <CollapsibleSection title="Môi trường & Cảm biến IoT" hint="Tự điền từ bản đồ">
        <SelectField label="Nguy cơ ngập" value={form.flood_risk} onChange={v => set('flood_risk', v)} options={FLOOD_RISK} />
        <NumberField label="Tiếng ồn trong căn (dB)" value={form.noise_inside_db} onChange={v => set('noise_inside_db', v)} step="0.1" placeholder="VD: 42.5" />
        <NumberField label="Độ ồn môi trường (dB) — IoT" value={form.noise_level} onChange={v => set('noise_level', v)} step="0.1" />
        <NumberField label="Nhiệt độ (°C) — IoT" value={form.temperature} onChange={v => set('temperature', v)} step="0.1" />
        <NumberField label="Độ ẩm (%) — IoT" value={form.humidity} onChange={v => set('humidity', v)} step="0.1" />
      </CollapsibleSection>

      <CollapsibleSection title="Gợi ý phù hợp người mua" hint="Lớp FIT — không ảnh hưởng giá thị trường" accent="var(--warning-border)">
        <SelectField label="Mức quan tâm phong thủy" value={form.feng_shui_sensitivity} onChange={v => set('feng_shui_sensitivity', v)} options={FENG_SHUI_SENSITIVITIES} />
        <SelectField label="Mức chịu ồn" value={form.noise_tolerance} onChange={v => set('noise_tolerance', v)} options={NOISE_TOLERANCES} />
      </CollapsibleSection>

      <button type="submit" className="btn btn-primary btn-lg btn-full" disabled={loading}>
        {submitLabel(isAdmin, loading, engineLabel)}
      </button>
    </form>
  );
}
