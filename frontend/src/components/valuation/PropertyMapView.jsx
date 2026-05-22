import React, { useEffect, useRef, useState } from 'react';
import { icon as lucideIcon, MapPin, Satellite } from '../../components/ui/icons';

/**
 * PropertyMapView — Hiển thị vị trí BĐS trên bản đồ OpenStreetMap/Leaflet.
 * Hỗ trợ chuyển đổi layer: OSM Map / ESRI Satellite.
 *
 * Props:
 *   latitude, longitude — tọa độ BĐS (required)
 *   label — tên BĐS hiển thị trên popup
 *   area_m2 — diện tích để hiển thị radius
 *   comparables — [{lat, lng, price, district}] — so sánh trên bản đồ
 */

const TILE_OSM = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
const TILE_ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
const ATTRIBUTION_OSM = '&copy; <a href="https://openstreetmap.org">OpenStreetMap</a>';
const ATTRIBUTION_ESRI = 'Satellite: Esri World Imagery';
const DEFAULT_CENTER = [21.0285, 105.8542];

function createMainMarkerIcon(L) {
  return L.divIcon({
    className: 'prop-map-marker-main',
    html: `<div style="width:28px;height:28px;border-radius:50%;background:linear-gradient(135deg,#7c3aed,#4f46e5);border:3px solid white;box-shadow:0 2px 8px rgba(0,0,0,.3);display:flex;align-items:center;justify-content:center;">
      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>
      </svg>
    </div>`,
    iconSize: [28, 28], iconAnchor: [14, 14],
  });
}

function createCompMarkerIcon(L, index) {
  return L.divIcon({
    className: 'prop-map-marker-comp',
    html: `<div style="width:22px;height:22px;border-radius:50%;background:#06d6a0;border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,.2);display:flex;align-items:center;justify-content:center;color:white;font-size:10px;font-weight:bold">${index + 1}</div>`,
    iconSize: [22, 22], iconAnchor: [11, 11],
  });
}

export default function PropertyMapView({ latitude, longitude, label, area_m2, comparables = [] }) {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const osmLayerRef = useRef(null);
  const esriLayerRef = useRef(null);
  const [L, setL] = useState(null);
  const [error, setError] = useState(null);
  const [activeLayer, setActiveLayer] = useState('map');

  const hasCoords = latitude && longitude;
  const center = hasCoords ? [latitude, longitude] : DEFAULT_CENTER;

  useEffect(() => {
    Promise.all([
      import('leaflet'),
      import('leaflet/dist/leaflet.css'),
    ]).then(([leafletModule]) => {
      const leaflet = leafletModule.default || leafletModule;
      delete leaflet.Icon.Default.prototype._getIconUrl;
      leaflet.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
        iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
      });
      setL(leaflet);
    }).catch(err => {
      console.error('Leaflet load failed:', err);
      setError('Không thể tải bản đồ');
    });
  }, []);

  // Build map
  useEffect(() => {
    if (!L || !mapRef.current) return;
    if (mapInstanceRef.current) {
      mapInstanceRef.current.remove();
    }

    const map = L.map(mapRef.current, {
      center, zoom: hasCoords ? 16 : 12,
      zoomControl: true, attributionControl: true,
    });

    const osmLayer = L.tileLayer(TILE_OSM, { attribution: ATTRIBUTION_OSM, maxZoom: 19, pane: 'tilePane' });
    const esriLayer = L.tileLayer(TILE_ESRI, { attribution: ATTRIBUTION_ESRI, maxZoom: 19, pane: 'tilePane' });

    osmLayer.addTo(map);
    esriLayer.removeFrom(map);

    osmLayerRef.current = osmLayer;
    esriLayerRef.current = esriLayer;

    // Main property marker
    if (hasCoords) {
      const mainIcon = createMainMarkerIcon(L);
      const marker = L.marker(center, { icon: mainIcon }).addTo(map);
      marker.bindPopup(`<div style="font-family:system-ui;font-size:13px"><strong>${label || 'Bất động sản'}</strong><br/>${latitude.toFixed(6)}, ${longitude.toFixed(6)}<br/>${area_m2 ? `Diện tích: ${area_m2} m²` : ''}</div>`);

      if (area_m2) {
        const radius = Math.sqrt(area_m2 / Math.PI);
        L.circle(center, {
          radius: Math.max(radius, 5) * 3,
          color: '#7c3aed', fillColor: '#7c3aed', fillOpacity: 0.1,
          weight: 2, dashArray: '5,5',
        }).addTo(map);
      }
    }

    // Comparable markers
    comparables.forEach((comp, i) => {
      if (!comp.lat || !comp.lng) return;
      const compIcon = createCompMarkerIcon(L, i);
      const m = L.marker([comp.lat, comp.lng], { icon: compIcon }).addTo(map);
      m.bindPopup(`<div style="font-family:system-ui;font-size:12px"><strong>Comparable #${i + 1}</strong><br/>${comp.district || ''}<br/>${comp.price ? new Intl.NumberFormat('vi-VN').format(comp.price) + ' VND' : ''}</div>`);
    });

    mapInstanceRef.current = map;

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [L, latitude, longitude, area_m2, comparables.length]);

  // Layer toggle
  useEffect(() => {
    if (!osmLayerRef.current || !esriLayerRef.current || !mapInstanceRef.current) return;
    const map = mapInstanceRef.current;
    if (activeLayer === 'map') {
      esriLayerRef.current.removeFrom(map);
      osmLayerRef.current.addTo(map);
    } else {
      osmLayerRef.current.removeFrom(map);
      esriLayerRef.current.addTo(map);
    }
  }, [activeLayer]);

  const svgIcon = (name, size = 16) => {
    const icons = {
      map: `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/><line x1="9" y1="3" x2="9" y2="18"/><line x1="15" y1="6" x2="15" y2="21"/></svg>`,
      satellite: `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>`,
    }
    return icons[name] || ''
  }

  if (error) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', background: 'var(--danger-bg, #fee2e2)', borderRadius: '12px', color: 'var(--danger, #ef233c)' }}>
        <div style={{ marginBottom: '0.5rem' }}>
          <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto', display: 'block' }}>
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
        </div>
        <div>{error}</div>
      </div>
    );
  }

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0.6rem 1rem', borderBottom: '1px solid var(--border, #e5e7eb)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ color: 'var(--primary)' }}>{lucideIcon('map', 16)}</span>
          <span style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--text-primary)' }}>Vị trí bản đồ</span>
        </div>
        {/* Layer switcher */}
        <div style={{ display: 'flex', gap: '0.25rem' }}>
          <button
            onClick={() => setActiveLayer('map')}
            style={{
              padding: '0.3rem 0.75rem', fontSize: '0.72rem',
              border: activeLayer === 'map' ? '1px solid var(--primary)' : '1px solid var(--border)',
              borderRadius: '6px', cursor: 'pointer',
              background: activeLayer === 'map' ? 'var(--primary-50)' : 'transparent',
              color: activeLayer === 'map' ? 'var(--primary)' : 'var(--text-secondary)',
              fontWeight: activeLayer === 'map' ? 600 : 400,
              display: 'flex', alignItems: 'center', gap: '0.3rem',
            }}
          >
            <span>{lucideIcon('map', 11)}</span>
            Bản đồ
          </button>
          <button
            onClick={() => setActiveLayer('satellite')}
            style={{
              padding: '0.3rem 0.75rem', fontSize: '0.72rem',
              border: activeLayer === 'satellite' ? '1px solid var(--primary)' : '1px solid var(--border)',
              borderRadius: '6px', cursor: 'pointer',
              background: activeLayer === 'satellite' ? 'var(--primary-50)' : 'transparent',
              color: activeLayer === 'satellite' ? 'var(--primary)' : 'var(--text-secondary)',
              fontWeight: activeLayer === 'satellite' ? 600 : 400,
              display: 'flex', alignItems: 'center', gap: '0.3rem',
            }}
          >
            <span>{lucideIcon('satellite', 11)}</span>
            Vệ tinh
          </button>
        </div>
      </div>

      {!hasCoords && (
        <div style={{
          fontSize: '0.7rem', color: 'var(--warning, #f59e0b)',
          background: 'var(--warning-bg, #fef3c7)',
          padding: '0.3rem 1rem', borderBottom: '1px solid var(--border)',
        }}>
          Chưa có tọa độ — hiển thị Hà Nội mặc định
        </div>
      )}

      <div ref={mapRef} style={{ height: 300, width: '100%' }} />
    </div>
  );
}