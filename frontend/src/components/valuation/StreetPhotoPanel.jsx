import React, { useState, useEffect } from 'react'

// Default Unsplash images by property type (fallback when API unavailable)
const DEFAULT_PHOTOS = {
  land: [
    'https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=600&h=400&fit=crop',
    'https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=600&h=400&fit=crop',
  ],
  apartment: [
    'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=600&h=400&fit=crop',
    'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=600&h=400&fit=crop',
  ],
  townhouse: [
    'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=600&h=400&fit=crop',
    'https://images.unsplash.com/photo-1568605114967-8130f3a36994?w=600&h=400&fit=crop',
  ],
  villa: [
    'https://images.unsplash.com/photo-1613490493576-7fde63acd811?w=600&h=400&fit=crop',
    'https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=600&h=400&fit=crop',
  ],
  house: [
    'https://images.unsplash.com/photo-1449844908441-8829872d2607?w=600&h=400&fit=crop',
    'https://images.unsplash.com/photo-1464146072230-91cabc968266?w=600&h=400&fit=crop',
  ],
}

// Map frontend property type → API asset_type
const PROPERTY_TO_ASSET = {
  land: 'LAND_URBAN',
  apartment: 'APARTMENT',
  townhouse: 'TOWNHOUSE',
  house: 'HOUSE',
  villa: 'VILLA',
}

export default function StreetPhotoPanel({ latitude, longitude, propertyType }) {
  const [photos, setPhotos] = useState([])
  const [selectedIdx, setSelectedIdx] = useState(0)
  const [imgError, setImgError] = useState(false)
  const [loading, setLoading] = useState(true)
  const [mode, setMode] = useState('photo') // 'photo' | 'street'

  const apiAssetType = PROPERTY_TO_ASSET[propertyType] || 'LAND_URBAN'
  const hasCoords = latitude && longitude

  // Fetch reference photos from API
  useEffect(() => {
    setLoading(true)
    setImgError(false)
    fetch(`/api/v2/reference-photos?property_type=${apiAssetType}&limit=6`)
      .then(r => r.json())
      .then(data => {
        setPhotos(data.photos || [])
        setLoading(false)
      })
      .catch(() => {
        // Fallback to hardcoded photos
        const key = propertyType || 'land'
        const defaults = DEFAULT_PHOTOS[key] || DEFAULT_PHOTOS.land
        setPhotos(defaults.map((url, i) => ({
          url,
          caption_vi: '',
          photographer: 'Unsplash',
        })))
        setLoading(false)
      })
  }, [propertyType, apiAssetType])

  // Google Maps Street View embed URL (free Embed API, no JS required)
  const streetViewUrl = hasCoords
    ? `https://www.google.com/maps/embed/v1/streetview?key=AIzaSyB9rS&location=${latitude},${longitude}&heading=0&pitch=0&fov=90`
    : null

  // Fallback street view image (Unsplash)
  const streetFallbackImg = photos[selectedIdx]?.url || DEFAULT_PHOTOS[propertyType]?.[0]

  return (
    <div className="card" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header with mode toggle */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: '10px', flexShrink: 0
      }}>
        <h3 style={{ fontSize: '0.85rem', fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
          Ảnh & Street View
        </h3>
        <div style={{ display: 'flex', gap: '0.25rem' }}>
          <button
            onClick={() => setMode('photo')}
            style={{
              padding: '0.25rem 0.5rem', fontSize: '0.7rem',
              border: mode === 'photo' ? '1px solid var(--primary)' : '1px solid var(--border)',
              borderRadius: '4px', cursor: 'pointer',
              background: mode === 'photo' ? 'var(--primary-50)' : 'transparent',
              color: mode === 'photo' ? 'var(--primary)' : 'var(--text-secondary)',
              fontWeight: mode === 'photo' ? 600 : 400,
            }}
          >
            Ảnh ref
          </button>
          {hasCoords && (
            <button
              onClick={() => setMode('street')}
              style={{
                padding: '0.25rem 0.5rem', fontSize: '0.7rem',
                border: mode === 'street' ? '1px solid var(--primary)' : '1px solid var(--border)',
                borderRadius: '4px', cursor: 'pointer',
                background: mode === 'street' ? 'var(--primary-50)' : 'transparent',
                color: mode === 'street' ? 'var(--primary)' : 'var(--text-secondary)',
                fontWeight: mode === 'street' ? 600 : 400,
              }}
            >
              Street View
            </button>
          )}
        </div>
      </div>

      {/* Main content */}
      <div style={{
        flex: 1, borderRadius: '8px', overflow: 'hidden',
        background: '#e2e8f0', minHeight: '160px', position: 'relative'
      }}>
        {mode === 'street' ? (
          // Street View iframe (Google Maps Embed API)
          hasCoords ? (
            <iframe
              src={streetViewUrl}
              width="100%" height="100%"
              style={{ border: 0 }}
              allowFullScreen
              loading="lazy"
              referrerPolicy="no-referrer-when-downgrade"
              title="Street View"
              onError={() => setMode('photo')}
            />
          ) : (
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              height: '100%', color: 'var(--text-muted)', fontSize: '0.85rem'
            }}>
              Cần có tọa độ để hiển thị Street View
            </div>
          )
        ) : loading ? (
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            height: '100%', color: 'var(--text-muted)', fontSize: '0.85rem'
          }}>
            Đang tải ảnh tham chiếu...
          </div>
        ) : imgError || photos.length === 0 ? (
          <img
            src={streetFallbackImg}
            alt="Reference"
            onError={() => setImgError(true)}
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
        ) : (
          <img
            src={photos[selectedIdx]?.url}
            alt={photos[selectedIdx]?.caption_vi || 'Reference photo'}
            onError={() => setImgError(true)}
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
        )}

        {/* Photo counter */}
        {mode === 'photo' && photos.length > 1 && (
          <div style={{
            position: 'absolute', top: '8px', right: '8px',
            background: 'rgba(0,0,0,0.6)', color: 'white',
            fontSize: '0.65rem', padding: '2px 6px', borderRadius: '4px'
          }}>
            {selectedIdx + 1}/{photos.length}
          </div>
        )}

        {/* Overlay info */}
        <div style={{
          position: 'absolute', bottom: 0, left: 0, right: 0,
          padding: '8px 12px',
          background: 'linear-gradient(to top, rgba(0,0,0,0.8), transparent)',
          color: '#fff', fontSize: '0.7rem',
          display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end'
        }}>
          <div>
            {mode === 'photo' && photos[selectedIdx] && (
              <div>
                {photos[selectedIdx].caption_vi && (
                  <div style={{ fontWeight: 500, marginBottom: '2px' }}>
                    {photos[selectedIdx].caption_vi}
                  </div>
                )}
                <div style={{ opacity: 0.7, fontSize: '0.6rem' }}>
                  Nguồn: {photos[selectedIdx].photographer || 'Unsplash'}
                </div>
              </div>
            )}
            {mode === 'street' && (
              <div>
                <div style={{ fontWeight: 500 }}>Google Street View</div>
                <div style={{ opacity: 0.7, fontSize: '0.6rem' }}>
                  {latitude?.toFixed(5)}, {longitude?.toFixed(5)}
                </div>
              </div>
            )}
          </div>
          {mode === 'photo' && !imgError && photos.length > 1 && (
            <span style={{ fontSize: '0.65rem', opacity: 0.8 }}>
              Ảnh tham chiếu — không phải BĐS thực
            </span>
          )}
        </div>
      </div>

      {/* Photo strip */}
      {mode === 'photo' && photos.length > 1 && (
        <div style={{
          display: 'flex', gap: '4px', marginTop: '6px', overflowX: 'auto',
          paddingBottom: '4px', flexShrink: 0
        }}>
          {photos.map((p, i) => (
            <button
              key={i}
              onClick={() => setSelectedIdx(i)}
              style={{
                width: '48px', height: '36px', flexShrink: 0,
                border: selectedIdx === i ? '2px solid var(--primary)' : '1px solid var(--border)',
                borderRadius: '4px', overflow: 'hidden', cursor: 'pointer',
                padding: 0, background: 'none',
              }}
            >
              <img
                src={p.url}
                alt=""
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                onError={(e) => { e.target.style.display = 'none' }}
              />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}