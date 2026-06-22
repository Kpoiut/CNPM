import React, { useState, useEffect } from 'react';
import PrefillBanner from './PrefillBanner';
import { ProvinceSelector, DistrictSelector } from '../ui/ProvinceSelector';
import {
  OWNERSHIP_TYPES,
  FLOOD_RISK,
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
  OpenSection, CollapsibleSection, SelectField, SegmentedField, NumberField, TextField, CheckField, SliderField, FormProgress, IotAutoNote,
} from './SmartFields';

/**
 * LandIntakeForm — ĐẤT ĐÔ THỊ (bản tinh gọn).
 */
const WARD_HINTS = [...LOCATION_HINTS.hanoiWards, ...LOCATION_HINTS.hcmWards];
const STREET_HINTS = [...LOCATION_HINTS.streets, ...LOCATION_HINTS.projects];

export default function LandIntakeForm({ onSubmit, loading, isAdmin = false, engineLabel, prefill, onLiveChange }) {
  const [form, setForm] = useState({
    asset_type: 'LAND_URBAN',
    asset_subtype: 'LAND_LEGAL_STREET',
    province_city: 'Hà Nội',
    district: '',
    ward: '',
    street_or_project: '',
    latitude: '',
    longitude: '',
    area_m2: '',
    polygon_json: '',
    frontage_m: '',
    frontage_road_class: '',
    depth_min_m: '',
    depth_max_m: '',
    taper_type: 'uniform',
    'nö_hậu_score': '0.8',
    'thóp_hậu_score': '0.0',
    irregularity_score: '0.0',
    corner_plot: false,
    alley_branch_count: '0',
    ownership_type: 'FULL_OWNERSHIP',
    road_expansion_risk: 'none',
    dispute_flag: false,
    mortgage_flag: false,
    flood_risk: 'unknown',
    cemetery_distance_m: '',
    pollution_score: '',
    river_distance_m: '',
    park_distance_m: '',
    death_history_flag: false,
    stigma_known: false,
    worship_site_distance_m: '',
    noise_level: '',
  });

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  useFormPrefill(prefill, setForm);
  const iotAuto = useIotAutoFill(form, setForm);

  const buildPayload = () => ({
      ...form,
      area_m2: toFloat(form.area_m2, 0),
      latitude: toFloat(form.latitude),
      longitude: toFloat(form.longitude),
      frontage_m: toFloat(form.frontage_m),
      depth_min_m: toFloat(form.depth_min_m),
      depth_max_m: toFloat(form.depth_max_m),
      'nö_hậu_score': toFloat(form['nö_hậu_score'], 0),
      'thóp_hậu_score': toFloat(form['thóp_hậu_score'], 0),
      irregularity_score: toFloat(form.irregularity_score, 0),
      alley_branch_count: toInt(form.alley_branch_count, 0),
      cemetery_distance_m: toFloat(form.cemetery_distance_m),
      pollution_score: toFloat(form.pollution_score),
      river_distance_m: toFloat(form.river_distance_m),
      park_distance_m: toFloat(form.park_distance_m),
      worship_site_distance_m: toFloat(form.worship_site_distance_m),
      noise_level: toFloat(form.noise_level),
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(buildPayload());
  };

  useEffect(() => { if (onLiveChange) onLiveChange(buildPayload()); }, [form]); // eslint-disable-line react-hooks/exhaustive-deps

  const onNoHau = (v) => {
    set('nö_hậu_score', String(v));
    set('thóp_hậu_score', String(Math.max(0, 1 - parseFloat(v)).toFixed(2)));
  };

  return (
    <form onSubmit={handleSubmit} onInvalid={scrollInvalidField} onInput={clearInvalidField} className="space-y-4">
      <PrefillBanner prefill={prefill} onPick={set} />
      <FormProgress form={form} />
      <IotAutoNote data={iotAuto} />

      <OpenSection title="Vị trí" hint="Mẹo: dùng “Định vị thông minh” để tự điền">
        <SelectField label="Loại đất" value={form.asset_subtype} onChange={v => set('asset_subtype', v)} options={ASSET_SUBTYPES.LAND_URBAN} placeholder="— Chọn loại đất —" />
        <div className="form-group">
          <label className="form-label">Tỉnh / TP</label>
          <ProvinceSelector value={form.province_city} onChange={val => { set('province_city', val); set('district', '') }} className="form-select" />
        </div>
        <div className="form-group">
          <label className="form-label required">Quận / Huyện *</label>
          <DistrictSelector provinceCode={form.province_city} value={form.district} onChange={val => set('district', val)} className="form-select" required />
        </div>
        <TextField label="Phường / Xã" value={form.ward} onChange={v => set('ward', v)} options={WARD_HINTS} placeholder="VD: Xuân Thủy" />
        <TextField label="Đường / Dự án" value={form.street_or_project} onChange={v => set('street_or_project', v)} options={STREET_HINTS} span />
        <NumberField label="Vĩ độ (GPS)" value={form.latitude} onChange={v => set('latitude', v)} step="0.0001" placeholder="Tự điền từ bản đồ" />
        <NumberField label="Kinh độ (GPS)" value={form.longitude} onChange={v => set('longitude', v)} step="0.0001" placeholder="Tự điền từ bản đồ" />
      </OpenSection>

      <OpenSection title="Diện tích & Hình dạng đất">
        <NumberField label="Diện tích (m²)" value={form.area_m2} onChange={v => set('area_m2', v)} required step="0.1" placeholder="VD: 120.5" />
        <NumberField label="Mặt tiền (m)" value={form.frontage_m} onChange={v => set('frontage_m', v)} step="0.1" placeholder="VD: 5.0" suggestions={[4, 5, 6, 8]} />
        <NumberField label="Chiều sâu tối thiểu (m)" value={form.depth_min_m} onChange={v => set('depth_min_m', v)} step="0.1" />
        <NumberField label="Chiều sâu tối đa (m)" value={form.depth_max_m} onChange={v => set('depth_max_m', v)} step="0.1" />
        <SegmentedField span
          label="📐 Hình dạng thửa đất"
          value={form['nö_hậu_score']}
          onChange={onNoHau}
          options={[['0.1', '🔻 Thóp hậu (hẹp dần về sau)'], ['0.6', '⬛ Vuông vắn đều'], ['1', '🔺 Nở hậu (rộng dần về sau)']]}
          hint="Nở hậu = hậu đất rộng hơn mặt tiền (quan niệm tụ tài → giá tốt hơn). Thóp hậu = hẹp dần về sau → thường bị trừ giá."
        />
        <SegmentedField
          label="📏 Độ vuông vức"
          value={form.irregularity_score}
          onChange={v => set('irregularity_score', v)}
          options={[['0', '⬛ Vuông vức'], ['0.5', '◇ Hơi méo'], ['1', '⬡ Méo / đa giác']]}
          hint="Đất méo, nhiều cạnh khó bố trí xây dựng → thường bị trừ giá."
        />
        <NumberField label="Số hẻm phụ tách ra" value={form.alley_branch_count} onChange={v => set('alley_branch_count', v)} min="0" />
        <CheckField label="Đất góc (2+ mặt tiền)" checked={form.corner_plot} onChange={v => set('corner_plot', v)} />
      </OpenSection>

      <OpenSection title="Pháp lý & Quy hoạch" hint="Impact ±5-15%">
        <SelectField label="Pháp lý" value={form.ownership_type} onChange={v => set('ownership_type', v)} options={OWNERSHIP_TYPES} required />
        <SelectField label="Quy hoạch mở đường" value={form.road_expansion_risk} onChange={v => set('road_expansion_risk', v)} options={COMMON_HINTS.riskLevels} />
        <CheckField label="Đang có tranh chấp" checked={form.dispute_flag} onChange={v => set('dispute_flag', v)} />
        <CheckField label="Đang thế chấp ngân hàng" checked={form.mortgage_flag} onChange={v => set('mortgage_flag', v)} />
      </OpenSection>

      <CollapsibleSection title="Môi trường & Hạ tầng" hint="Impact ±3-16%">
        <SelectField label="Nguy cơ ngập" value={form.flood_risk} onChange={v => set('flood_risk', v)} options={FLOOD_RISK} />
        <NumberField label="Cách nghĩa trang (m)" value={form.cemetery_distance_m} onChange={v => set('cemetery_distance_m', v)} />
        <NumberField label="Cách sông (m)" value={form.river_distance_m} onChange={v => set('river_distance_m', v)} />
        <NumberField label="Cách công viên (m)" value={form.park_distance_m} onChange={v => set('park_distance_m', v)} />
        <SegmentedField label="🌫️ Mức ô nhiễm" value={form.pollution_score} onChange={v => set('pollution_score', v)} options={[['0', '🌿 Sạch'], ['0.5', '😐 Trung bình'], ['1', '🏭 Ô nhiễm']]} />
        <NumberField label="Độ ồn môi trường (dB) — IoT" value={form.noise_level} onChange={v => set('noise_level', v)} step="0.1" hint="Tự điền từ bản đồ" />
      </CollapsibleSection>

      <CollapsibleSection title="Lịch sử tâm linh" hint="Lớp FIT — không ảnh hưởng giá thị trường" accent="var(--warning-border)">
        <CheckField label="Có tử vong trong nhà/đất" checked={form.death_history_flag} onChange={v => set('death_history_flag', v)} />
        <CheckField label="Điểm nhạy cảm đã biết trong khu vực" checked={form.stigma_known} onChange={v => set('stigma_known', v)} />
        <NumberField label="Cách nơi thờ cúng (m)" value={form.worship_site_distance_m} onChange={v => set('worship_site_distance_m', v)} />
      </CollapsibleSection>

      <button type="submit" className="btn btn-primary btn-lg btn-full" disabled={loading}>
        {submitLabel(isAdmin, loading, engineLabel)}
      </button>
    </form>
  );
}
