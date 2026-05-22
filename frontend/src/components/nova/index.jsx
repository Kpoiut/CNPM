// NovaAssistant v3 — Production Floating AI Assistant
// single-click = chat + voice | drag (instant, no delay)
// Orbital physics | Surface light sweep

import React, {
  useState, useEffect, useCallback, useRef, useMemo,
} from 'react'
import { icon } from '../ui/icons'

// ─── State ───────────────────────────────────────────────────────────────────
export const NovaState = {
  IDLE: 'idle',
  CHAT_OPEN: 'chat_open',
  PROCESSING: 'processing',
}

// ─── Constants ────────────────────────────────────────────────────────────────
const ORB = 48
const CHAT_W = 360
const CHAT_H_MAX = 520
const CHAT_H_MIN = 380
const SAFE = 20
const MAX_MESSAGES = 80

// Drag sensitivity — very small for instant response
const DRAG_THRESH_PX = 5
const DRAG_THRESH_MS = 60

// ─── Position ─────────────────────────────────────────────────────────────────
// Always start at bottom-right — canonical initial position
// Version 11: validates saved position against current viewport
function savedPos() {
  try {
    const raw = localStorage.getItem('np-v11')
    if (!raw) return null
    const p = JSON.parse(raw)
    if (p == null || p.x == null || p.y == null) return null
    // Validate: must be within current viewport bounds
    const vw = window.innerWidth
    const vh = window.innerHeight
    if (p.x < -ORB || p.y < -ORB || p.x > vw + 100 || p.y > vh + 100) return null
    return p
  } catch { return null }
}
function keepPos(p) { try { localStorage.setItem('np-v11', JSON.stringify(p)) } catch {} }

// ─── Chat panel position relative to orb ──────────────────────────────────────
function chatPos(orbX, orbY, vw, vh) {
  const h = Math.min(CHAT_H_MAX, Math.max(CHAT_H_MIN, vh - SAFE * 2))
  let left = orbX - CHAT_W - 12
  let top = orbY - h / 2 + ORB / 2
  if (left < SAFE) left = orbX + ORB + 12
  if (top < SAFE) top = SAFE
  if (top + h > vh - SAFE) top = vh - h - SAFE
  if (left + CHAT_W > vw - SAFE) left = vw - CHAT_W - SAFE
  return { left, top, height: h }
}

// ─── Color palettes per state ─────────────────────────────────────────────────
const STATE_COLORS = {
  idle:       { ringA: 'rgba(125,211,252,0.88)', ringB: 'rgba(208,98,255,0.88)', ringC: 'rgba(71,146,255,0.88)', core: 'rgba(125,211,252,0.95)', sphereA: 'rgba(125,211,252,0.95)', sphereB: 'rgba(208,98,255,0.9)', glow: 'drop-shadow(0 0 14px rgba(125,211,252,0.3))', pulseScale: 1 },
  chat_open:  { ringA: 'rgba(125,211,252,0.88)', ringB: 'rgba(208,98,255,0.88)', ringC: 'rgba(71,146,255,0.88)', core: 'rgba(125,211,252,0.95)', sphereA: 'rgba(125,211,252,0.95)', sphereB: 'rgba(208,98,255,0.9)', glow: 'drop-shadow(0 0 14px rgba(125,211,252,0.3))', pulseScale: 1.04 },
  processing: { ringA: 'rgba(245,158,11,0.88)', ringB: 'rgba(251,191,36,0.88)', ringC: 'rgba(125,211,252,0.88)', core: 'rgba(251,191,36,0.95)', sphereA: 'rgba(255,230,120,0.95)', sphereB: 'rgba(245,158,11,0.9)', glow: 'drop-shadow(0 0 20px rgba(245,158,11,0.5))', pulseScale: 1.08 },
}

// ─── NovaOrb — Core visual ────────────────────────────────────────────────────
function NovaOrb({ state, hovered }) {
  const colors = STATE_COLORS[state] || STATE_COLORS.idle

  // Pulse by state
  const pulseAnim = state === NovaState.PROCESSING
    ? 'orbThink 1.6s ease-in-out infinite'
    : state === NovaState.CHAT_OPEN
    ? 'orbPulse 2s ease-in-out infinite'
    : 'orbBreathe 3s ease-in-out infinite'

  const brightness = hovered ? 'brightness(1.2)' : 'brightness(1)'

  return (
    <div style={{
      width: ORB, height: ORB, position: 'relative',
      flexShrink: 0,
    }}>
      {/* ── Core sphere ── */}
      <div style={{
        position: 'absolute', inset: '20%', borderRadius: '50%',
        background: `radial-gradient(circle at 30% 28%, rgba(255,255,255,1) 0%, rgba(200,240,255,0.98) 14%, ${colors.core} 34%, rgba(56,189,248,0.88) 54%, rgba(168,95,255,0.5) 70%, rgba(30,58,138,0.35) 100%)`,
        boxShadow: 'inset -3px -5px 10px rgba(15,29,67,0.32), inset 2px 3px 5px rgba(255,255,255,0.28), 0 0 5px rgba(125,211,252,0.5)',
        animation: pulseAnim,
        filter: `drop-shadow(0 0 6px rgba(125,211,252,0.4)) ${brightness}`,
        transition: 'filter 80ms ease-out',
      }} />

      {/* ── Specular highlight (top-left) — sits above core ── */}
      <div style={{
        position: 'absolute', inset: '20%', borderRadius: '50%',
        background: 'radial-gradient(circle at 28% 22%, rgba(255,255,255,0.65) 0%, transparent 55%)',
        animation: 'specDrift 5s ease-in-out infinite',
        pointerEvents: 'none',
        zIndex: 2,
      }} />

      {/* ── Surface wave — single band sweeps across sphere surface only ── */}
      {/* One 54° bright band: transparent→light→bright→light→transparent across full 360° */}
      <div style={{
        position: 'absolute', inset: '20%', borderRadius: '50%',
        background: `conic-gradient(
          from 0deg at 50% 50%,
          transparent 0deg,
          transparent 55deg,
          rgba(200,240,255,0.18) 72deg,
          rgba(255,255,255,0.52) 82deg,
          rgba(200,240,255,0.18) 91deg,
          transparent 108deg,
          transparent 360deg
        )`,
        animation: 'surfaceWave 2.5s linear infinite',
        pointerEvents: 'none',
        zIndex: 3,
        mixBlendMode: 'screen',
      }} />

      {/* ── Shell glow ── */}
      <div style={{
        position: 'absolute', inset: '10%', borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(125,211,252,0.12) 0%, transparent 70%)',
        animation: 'shellBreathe 3s ease-in-out infinite',
        pointerEvents: 'none',
        zIndex: 4,
      }} />

      {/* ── Ring A — equatorial ── */}
      <div style={{
        position: 'absolute', inset: '4%', borderRadius: '50%',
        background: `conic-gradient(from 0deg, transparent, ${colors.ringA}, rgba(118,130,255,0.22), transparent)`,
        transform: 'rotateX(72deg) rotateZ(0deg)',
        animation: 'spinA 4s linear infinite',
        mixBlendMode: 'screen',
        zIndex: 5,
      }} />

      {/* ── Ring B — tilted ── */}
      <div style={{
        position: 'absolute', inset: '0%', borderRadius: '50%',
        background: `conic-gradient(from 140deg, transparent, ${colors.ringB}, rgba(255,164,107,0.22), transparent)`,
        transform: 'rotateY(72deg) rotateZ(18deg)',
        animation: 'spinB 5.5s linear infinite reverse',
        mixBlendMode: 'screen',
        zIndex: 5,
      }} />

      {/* ── Ring C — 3D tilt ── */}
      <div style={{
        position: 'absolute', inset: '-6%', borderRadius: '50%',
        background: `conic-gradient(from 220deg, transparent, ${colors.ringC}, rgba(75,255,208,0.25), transparent)`,
        transform: 'rotateX(72deg) rotateY(72deg) rotateZ(-22deg) scale(0.92)',
        animation: 'spinC 6s linear infinite',
        mixBlendMode: 'screen',
        zIndex: 5,
      }} />

      {/* ══════════════════════════════════════════════════════════════════════ */}
      {/* ORBITAL SPHERES — Proper architecture:                                  */}
      {/*   orbitA/B container = top:50% left:50% → transform-origin auto at     */}
      {/*   the orb's center. Sphere child animates ellipse with no overlap.      */}
      {/* ══════════════════════════════════════════════════════════════════════ */}

      {/* ── Orbit A: Rx=6 horizontal, Ry=4 vertical, 1.8s/cw ── */}
      {/*    transform: translate(0,0) establishes transform-origin at orb center */}
      <div style={{
        position: 'absolute',
        top: '50%', left: '50%',
        width: 0, height: 0,
        zIndex: 10,
        transform: 'translate(0, 0)',
      }}>
        <div style={{
          position: 'absolute',
          width: 6, height: 6, borderRadius: '50%',
          transformOrigin: '0 0',
          // x(t) = 6*cos(t), y(t) = 4*sin(t) — parametric ellipse
          // 0%  = 0°   → (6,  0)
          // 25% = 90°  → (0,  4)
          // 50% = 180° → (-6, 0)
          // 75% = 270° → (0, -4)
          animation: 'orbitA 1.8s linear infinite',
          background: `radial-gradient(circle at 30% 30%, rgba(255,255,255,1), ${colors.sphereA} 50%, rgba(56,189,248,0.6))`,
          boxShadow: state === NovaState.PROCESSING
            ? '0 0 10px rgba(255,230,120,0.9), 0 0 20px rgba(245,158,11,0.5)'
            : '0 0 8px rgba(125,211,252,0.9), 0 0 16px rgba(125,211,252,0.4)',
          filter: brightness,
          pointerEvents: 'none',
        }} />
      </div>

      {/* ── Orbit B: Rx=4 horizontal, Ry=6 vertical, 1.4s/ccw ── */}
      {/*    Phase 90° → starts at BOTTOM → NEVER crosses orbitA               */}
      {/*    Same transform-origin trick for correct center-based orbit          */}
      <div style={{
        position: 'absolute',
        top: '50%', left: '50%',
        width: 0, height: 0,
        zIndex: 10,
        transform: 'translate(0, 0)',
      }}>
        <div style={{
          position: 'absolute',
          width: 5, height: 5, borderRadius: '50%',
          transformOrigin: '0 0',
          // x(t) = 4*cos(t+90°), y(t) = 6*sin(t+90°)
          // Parametric ellipse with 90° phase offset from orbitA
          // 0%  = 90°  → (0,  6)
          // 25% = 180° → (-4, 0)
          // 50% = 270° → (0, -6)
          // 75% = 360° → (4,  0)
          animation: 'orbitB 1.4s linear infinite reverse',
          background: `radial-gradient(circle at 30% 30%, rgba(255,255,255,0.95), ${colors.sphereB} 50%, rgba(168,95,255,0.55))`,
          boxShadow: state === NovaState.PROCESSING
            ? '0 0 8px rgba(245,158,11,0.8), 0 0 16px rgba(245,158,11,0.35)'
            : '0 0 7px rgba(208,98,255,0.8), 0 0 14px rgba(208,98,255,0.35)',
          filter: brightness,
          pointerEvents: 'none',
        }} />
      </div>
    </div>
  )
}

// ─── Chatbox panel ─────────────────────────────────────────────────────────────
function Chatbox({ messages, onSend, onClose, orbX, orbY, sending, voiceTranscript, voiceListening }) {
  const [input, setInput] = useState('')
  const [typing, setTyping] = useState(false)
  const endRef = useRef(null)
  const inRef = useRef(null)
  const boxRef = useRef(null)

  const vw = window.innerWidth
  const vh = window.innerHeight
  const pos = useMemo(() => chatPos(orbX, orbY, vw, vh), [orbX, orbY, vw, vh])

  // Auto-focus input
  useEffect(() => {
    const t = setTimeout(() => inRef.current?.focus(), 80)
    return () => clearTimeout(t)
  }, [])

  // Auto-scroll on new messages
  useEffect(() => {
    if (messages.length) endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Typing indicator
  useEffect(() => {
    const last = messages[messages.length - 1]
    if (sending || last?.role === 'user') {
      setTyping(true)
      const t = setTimeout(() => setTyping(false), sending ? 3000 : 2200)
      return () => clearTimeout(t)
    }
    setTyping(false)
  }, [messages, sending])

  // Close on outside click
  useEffect(() => {
    const handler = (e) => {
      if (boxRef.current && !boxRef.current.contains(e.target)) {
        const orbEl = document.getElementById('nova-orb-container')
        if (orbEl && orbEl.contains(e.target)) return
        onClose()
      }
    }
    const t = setTimeout(() => document.addEventListener('mousedown', handler), 150)
    return () => { clearTimeout(t); document.removeEventListener('mousedown', handler) }
  }, [onClose])

  const send = () => {
    if (!input.trim()) return
    onSend(input.trim())
    setInput('')
  }

  // When voice transcript updates, show it in the input field
  useEffect(() => {
    if (voiceTranscript && voiceListening) {
      setInput(voiceTranscript)
    }
  }, [voiceTranscript, voiceListening])

  return (
    <div
      ref={boxRef}
      style={{
        position: 'fixed', left: pos.left, top: pos.top, width: CHAT_W, height: pos.height,
        display: 'flex', flexDirection: 'column',
        background: 'rgba(240,249,255,0.98)',
        border: '1px solid rgba(125,211,252,0.28)',
        borderRadius: 14,
        boxShadow: '0 8px 40px rgba(56,189,248,0.16), 0 2px 8px rgba(56,189,248,0.1)',
        backdropFilter: 'blur(18px)',
        WebkitBackdropFilter: 'blur(18px)',
        zIndex: 9998, overflow: 'hidden',
        animation: 'chatIn 220ms cubic-bezier(0.34, 1.4, 0.64, 1)',
      }}
    >
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', padding: '9px 12px',
        borderBottom: '1px solid rgba(125,211,252,0.12)',
        background: 'linear-gradient(135deg, rgba(125,211,252,0.1) 0%, transparent 100%)',
        gap: 9, flexShrink: 0,
      }}>
        <div style={{
          width: 28, height: 28, borderRadius: '50%',
          background: 'radial-gradient(circle at 30% 28%, rgba(255,255,255,0.95), rgba(125,211,252,0.9) 45%, rgba(56,189,248,0.85))',
          boxShadow: '0 1px 6px rgba(125,211,252,0.35)', flexShrink: 0,
        }} />
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#0c4a6e' }}>Nova</div>
          <div style={{ fontSize: '0.62rem', color: '#0284c7', display: 'flex', alignItems: 'center', gap: 3 }}>
            <div style={{
              width: 5, height: 5, borderRadius: '50%',
              background: voiceListening ? '#f59e0b' : '#06d6a0',
              boxShadow: `0 0 3px ${voiceListening ? '#f59e0b' : '#06d6a0'}`,
              animation: voiceListening ? 'dotBlink 0.85s ease-in-out infinite' : 'none',
            }} />
            {voiceListening ? 'Đang nghe...' : 'Trực tuyến'}
          </div>
        </div>
        {voiceListening && (
          <div style={{
            fontSize: '0.6rem', color: 'rgba(245,158,11,0.65)',
            background: 'rgba(245,158,11,0.08)', borderRadius: 4,
            padding: '1px 5px', border: '1px solid rgba(245,158,11,0.18)',
          }}>
            Hey Nova...
          </div>
        )}
        <div style={{
          fontSize: '0.6rem', color: 'rgba(125,211,252,0.45)',
          background: 'rgba(125,211,252,0.06)', borderRadius: 4,
          padding: '1px 5px', border: '1px solid rgba(125,211,252,0.12)',
        }}>
          ESC để đóng
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); onClose() }}
          style={{
            width: 24, height: 24, borderRadius: 6, border: 'none',
            background: 'rgba(125,211,252,0.08)', color: '#0c4a6e',
            cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '0.8rem', flexShrink: 0,
          }}
        >
          ✕
        </button>
      </div>

      {/* Message area */}
      <div style={{
        flex: 1, overflowY: 'auto', padding: '8px 11px',
        display: 'flex', flexDirection: 'column', gap: 6,
        scrollBehavior: 'smooth',
      }}>
        {/* Empty state */}
        {!messages.length && (
          <div style={{
            flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
            justifyContent: 'center', gap: 10, padding: '16px 0',
          }}>
            <div style={{
              width: 40, height: 40, borderRadius: '50%',
              background: 'radial-gradient(circle at 30% 28%, rgba(255,255,255,0.95), rgba(125,211,252,0.9) 45%, rgba(56,189,248,0.85))',
              boxShadow: '0 3px 12px rgba(125,211,252,0.3)',
              animation: 'orbBreathe 3.5s ease-in-out infinite',
            }} />
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '0.88rem', fontWeight: 700, color: '#0c4a6e' }}>
                Xin chào! Tôi là Nova
              </div>
              <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: 3, lineHeight: 1.5 }}>
                Trợ lý BĐS thông minh<br />Hỗ trợ 6 khu vực Hà Nội & HCM
              </div>
              {voiceListening && (
                <div style={{
                  marginTop: 8, fontSize: '0.72rem', color: '#f59e0b',
                  display: 'flex', alignItems: 'center', gap: 4,
                }}>
                  <div style={{ display: 'flex', gap: 2 }}>
                    {[0,1,2].map(i => (
                      <div key={i} style={{
                        width: 3, height: 4 + Math.sin((Date.now() % 700) / 100 + i * 1.2) * 6,
                        borderRadius: 1.5, background: '#f59e0b',
                        animation: `wBar ${380 + i * 45}ms ease-in-out ${i * 30}ms infinite alternate`,
                      }} />
                    ))}
                  </div>
                  Đang nghe...
                </div>
              )}
            </div>

            {/* Quick actions */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, justifyContent: 'center', marginTop: 4 }}>
              {[
                { label: 'Định giá Q7', iconKey: 'house' },
                { label: 'So sánh thị trường', iconKey: 'table' },
                { label: 'Xu hướng giá', iconKey: 'trendingUp' },
                { label: 'Hỏi về pháp lý', iconKey: 'shieldCheck' },
              ].map(s => (
                <button
                  key={s.label}
                  onClick={() => { setInput(s.label); inRef.current?.focus() }}
                  style={{
                    padding: '3px 9px', borderRadius: 14,
                    border: '1px solid rgba(125,211,252,0.3)',
                    background: 'rgba(125,211,252,0.05)', color: '#0284c7',
                    fontSize: '0.68rem', cursor: 'pointer',
                    display: 'flex', alignItems: 'center', gap: 4,
                  }}
                >
                  <span>{icon(s.iconKey, 12)}</span>{s.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
        {messages.map((m, i) => {
          const isFailed = m.error || m.role === 'error'
          const isVoiceMsg = m.isVoice
          return (
          <div key={m.id || i} style={{
            display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start',
            animation: 'msgIn 180ms ease-out',
            opacity: m.optimistic ? 0.6 : 1,
          }}>
            {/* Avatar for assistant */}
            {m.role !== 'user' && !isFailed && (
              <div style={{
                width: 20, height: 20, borderRadius: '50%',
                background: 'radial-gradient(circle, rgba(255,255,255), rgba(125,211,252,0.9))',
                flexShrink: 0, marginRight: 5, alignSelf: 'flex-end',
                boxShadow: '0 1px 3px rgba(125,211,252,0.3)',
              }} />
            )}
            {isFailed && (
              <div style={{
                width: 20, height: 20, borderRadius: '50%', background: 'rgba(239,68,68,0.15)',
                flexShrink: 0, marginRight: 5, alignSelf: 'flex-end',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '0.7rem',
              }}>
              </div>
            )}
            <div style={{
              maxWidth: '76%', padding: '6px 10px',
              borderRadius: m.role === 'user' ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
              background: isFailed
                ? 'rgba(239,68,68,0.08)'
                : m.role === 'user'
                ? 'linear-gradient(135deg, #7dd3fc, #38bdf8)'
                : 'rgba(255,255,255,0.95)',
              color: isFailed ? '#ef233c' : m.role === 'user' ? '#0c4a6e' : '#1e293b',
              fontSize: '0.8rem', lineHeight: 1.45,
              boxShadow: m.role === 'user'
                ? '0 1px 5px rgba(56,189,248,0.22)'
                : '0 1px 3px rgba(0,0,0,0.06)',
              wordBreak: 'break-word',
            }}>
              {isVoiceMsg && (
                <div style={{
                  fontSize: '0.62rem', color: 'rgba(56,189,248,0.6)',
                  marginBottom: 2, display: 'flex', alignItems: 'center', gap: 3,
                }}>
                  <span style={{ fontStyle: 'normal' }}>🎤</span> giọng nói
                </div>
              )}
              {m.text || (isFailed ? 'Gửi thất bại. Nhấn để thử lại.' : '')}
            </div>
          </div>
          )
        })}

        {/* Typing indicator */}
        {typing && (
          <div style={{ display: 'flex', justifyContent: 'flex-start', gap: 5, alignItems: 'center' }}>
            <div style={{
              width: 20, height: 20, borderRadius: '50%',
              background: 'radial-gradient(circle, rgba(255,255,255), rgba(125,211,252,0.9))',
              boxShadow: '0 1px 3px rgba(125,211,252,0.3)',
            }} />
            <div style={{
              padding: '6px 11px', borderRadius: '12px 12px 12px 2px',
              background: 'rgba(255,255,255,0.95)',
              display: 'flex', gap: 3, alignItems: 'center',
            }}>
              {[0, 1, 2].map(d => (
                <div key={d} style={{
                  width: 5, height: 5, borderRadius: '50%', background: '#38bdf8',
                  animation: `tdot 1.2s ease-in-out ${d * 0.18}s infinite`,
                }} />
              ))}
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input area */}
      <div style={{
        padding: '7px 10px', borderTop: '1px solid rgba(125,211,252,0.1)',
        background: 'rgba(255,255,255,0.65)', flexShrink: 0,
      }}>
        <div style={{ display: 'flex', gap: 6, alignItems: 'flex-end' }}>
          <button
            style={{
              border: 'none', background: 'none', cursor: 'pointer',
              fontSize: '0.95rem', padding: '2px 4px', color: '#94a3b8',
            }}
            title="Đính kèm file"
          >
          </button>

          <textarea
            ref={inRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                send()
              }
            }}
            placeholder={sending ? 'Đang xử lý...' : 'Nhắn cho Nova...'}
            rows={1}
            disabled={sending}
            style={{
              flex: 1, border: '1px solid rgba(125,211,252,0.28)',
              borderRadius: 9, padding: '6px 9px', fontSize: '0.8rem',
              resize: 'none', outline: 'none',
              background: sending ? 'rgba(255,255,255,0.7)' : 'rgba(255,255,255,0.9)',
              color: '#1e293b', fontFamily: 'inherit', lineHeight: 1.4,
              maxHeight: 80, overflowY: 'auto',
              transition: 'border-color 150ms ease, background 150ms ease',
              opacity: sending ? 0.7 : 1,
            }}
          />

          <button
            onClick={send}
            disabled={!input.trim() || sending}
            style={{
              width: 32, height: 32, borderRadius: 8, border: 'none',
              background: sending
                ? 'rgba(125,211,252,0.3)'
                : input.trim()
                ? 'linear-gradient(135deg, #38bdf8, #0ea5e9)'
                : 'rgba(125,211,252,0.12)',
              color: sending ? '#94a3b8' : input.trim() ? '#fff' : 'rgba(125,211,252,0.35)',
              cursor: !input.trim() || sending ? 'default' : 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '0.85rem',
              boxShadow: input.trim() && !sending ? '0 1px 5px rgba(56,189,248,0.28)' : 'none',
              flexShrink: 0,
              transition: 'background 150ms ease, box-shadow 150ms ease',
            }}
          >
            {sending ? (
              <div style={{
                width: 14, height: 14, border: '2px solid rgba(125,211,252,0.3)',
                borderTopColor: '#38bdf8', borderRadius: '50%',
                animation: 'spinA 0.6s linear infinite',
              }} />
            ) : '↑'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Main NovaAssistant ────────────────────────────────────────────────────────
export default function NovaAssistant() {
  const [state, setState] = useState(NovaState.IDLE)
  const [msgs, setMsgs] = useState([])
  const [voiceListening, setVoiceListening] = useState(false)
  const [voiceTranscript, setVoiceTranscript] = useState('')
  const [sending, setSending] = useState(false)
  const [isDragging, setIsDragging] = useState(false)

  // Orb position — canonical: always start at bottom-right
  const [orbPos, setOrbPos] = useState(() => {
    const saved = savedPos()
    if (saved && saved.x != null) return saved
    return { x: window.innerWidth - ORB - SAFE, y: window.innerHeight - ORB - SAFE }
  })

  // Refs for drag/voice without causing re-renders
  const dragging = useRef(false)
  const dragStartX = useRef(0)
  const dragStartY = useRef(0)
  const dragOrbX = useRef(0)
  const dragOrbY = useRef(0)
  const lastMoveX = useRef(0)
  const lastMoveY = useRef(0)
  const rafId = useRef(null)
  const recogRef = useRef(null)
  const voiceTimeout = useRef(null)
  const clickTimer = useRef(null)

  const orbX = orbPos.x
  const orbY = orbPos.y

  // ─── Voice: start speech recognition ──────────────────────────────────────
  const startVoice = useCallback(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) return
    if (recogRef.current) { try { recogRef.current.stop() } catch {} }

    const r = new SR()
    r.continuous = true
    r.interimResults = true
    r.lang = 'vi-VN'
    recogRef.current = r

    setVoiceListening(true)
    setVoiceTranscript('')

    r.onresult = (ev) => {
      let fin = '', tmp = ''
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        const t = ev.results[i][0].transcript
        if (ev.results[i].isFinal) fin += t; else tmp += t
      }
      const text = fin || tmp
      setVoiceTranscript(text)

      // Wake word detection
      if (fin) {
        const lower = fin.toLowerCase()
        if (lower.includes('hey nova') || lower.includes('nê ova') || lower.includes('nao va')) {
          setVoiceTranscript('')
          setVoiceListening(false)
          if (voiceTimeout.current) clearTimeout(voiceTimeout.current)
          // Process the command (what comes after "hey nova")
          const cmd = fin.replace(/hey nova|nê ova|nao va/gi, '').trim()
          if (cmd) {
            processVoiceCommand(cmd)
          } else {
            setVoiceListening(true)
            setTimeout(() => startVoice(), 100)
          }
        }
      }
    }

    r.onerror = () => {
      setVoiceListening(false)
    }

    r.onend = () => {
      if (voiceListening) {
        try { r.start() } catch {}
      }
    }

    try { r.start() } catch {}

    // Auto-stop after 15s
    if (voiceTimeout.current) clearTimeout(voiceTimeout.current)
    voiceTimeout.current = setTimeout(() => {
      stopVoice()
    }, 15000)
  }, []) // eslint-disable-line

  // ─── Voice: stop speech recognition ────────────────────────────────────────
  const stopVoice = useCallback(() => {
    if (voiceTimeout.current) { clearTimeout(voiceTimeout.current); voiceTimeout.current = null }
    setVoiceListening(false)
    setVoiceTranscript('')
    if (recogRef.current) { try { recogRef.current.stop() } catch {} }
  }, [])

  // ─── Process voice command ──────────────────────────────────────────────────
  const processVoiceCommand = useCallback(async (text) => {
    setState(NovaState.PROCESSING)
    setMsgs(m => [...m, { role: 'user', text, isVoice: true }])

    // Speak agent response back
    const speakResponse = (ssmlText) => {
      const utt = new SpeechSynthesisUtterance(ssmlText)
      utt.lang = 'vi-VN'
      utt.rate = 0.95
      utt.pitch = 1.0
      window.speechSynthesis.cancel()
      window.speechSynthesis.speak(utt)
      // Also display in chat
      setMsgs(prev => {
        const filtered = prev.filter(x => x.text !== ssmlText || x.role !== 'assistant')
        return [...filtered, { role: 'assistant', text: ssmlText, isVoice: true }]
      })
    }

    try {
      const res = await fetch('/api/nova/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      })
      const d = await res.json()
      const reply = d.text || 'Đã nhận yêu cầu.'
      speakResponse(reply)
    } catch {
      speakResponse('Xin lỗi, gặp lỗi kết nối.')
    }
    setState(NovaState.CHAT_OPEN)
    // Resume listening after processing
    setTimeout(() => startVoice(), 800)
  }, [startVoice])

  // ─── Chat send (text input) ─────────────────────────────────────────────────
  const chatSend = useCallback(async (text) => {
    const optimisticId = `opt-${Date.now()}`
    setMsgs(prev => {
      const next = [...prev, { id: optimisticId, role: 'user', text }]
      return next.length > MAX_MESSAGES ? next.slice(-MAX_MESSAGES) : next
    })
    setSending(true)
    try {
      const res = await fetch('/api/nova/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      })
      const d = await res.json()
      setMsgs(prev => {
        const filtered = prev.filter(m => m.id !== optimisticId)
        const userConfirmed = [...filtered, { id: optimisticId, role: 'user', text }]
        const next = [...userConfirmed, { id: `asst-${Date.now()}`, role: 'assistant', text: d.text || 'Đã nhận yêu cầu.' }]
        return next.length > MAX_MESSAGES ? next.slice(-MAX_MESSAGES) : next
      })
    } catch (err) {
      setMsgs(prev => {
        const updated = prev.map(m =>
          m.id === optimisticId ? { ...m, optimistic: false, error: true } : m
        )
        return [...updated, { id: `err-${Date.now()}`, role: 'error', text: 'Xin lỗi, gặp lỗi kết nối.' }]
          .slice(-MAX_MESSAGES)
      })
    } finally {
      setSending(false)
    }
  }, [])

  // ─── ESC to close ───────────────────────────────────────────────────────────
  useEffect(() => {
    const h = (e) => {
      if (e.key === 'Escape' && state === NovaState.CHAT_OPEN) {
        stopVoice()
        setState(NovaState.IDLE)
      }
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [state, stopVoice])

  // ─── Window resize: keep orb in bounds ────────────────────────────────────
  useEffect(() => {
    const onResize = () => {
      setOrbPos(prev => ({
        ...prev,
        x: Math.min(prev.x, window.innerWidth - ORB),
        y: Math.min(prev.y, window.innerHeight - ORB),
      }))
    }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  // ─── Click vs drag (instant, no delay) ────────────────────────────────────
  const onPointerDown = useCallback((e) => {
    if (e.button !== 0) return
    dragStartX.current = e.clientX
    dragStartY.current = e.clientY
    dragOrbX.current = orbX
    dragOrbY.current = orbY
    dragging.current = false

    const onMove = (me) => {
      const dx = me.clientX - dragStartX.current
      const dy = me.clientY - dragStartY.current
      const dist = Math.sqrt(dx * dx + dy * dy)
      if (!dragging.current && dist > DRAG_THRESH_PX) {
        dragging.current = true
        setIsDragging(true)
        document.body.style.cursor = 'grabbing'
        clickTimer.current && clearTimeout(clickTimer.current)
      }
      if (dragging.current) {
        lastMoveX.current = me.clientX
        lastMoveY.current = me.clientY
        if (rafId.current) cancelAnimationFrame(rafId.current)
        rafId.current = requestAnimationFrame(() => {
          const nx = Math.max(0, Math.min(window.innerWidth - ORB, dragOrbX.current + me.clientX - dragStartX.current))
          const ny = Math.max(0, Math.min(window.innerHeight - ORB, dragOrbY.current + me.clientY - dragStartY.current))
          setOrbPos({ x: nx, y: ny })
        })
      }
    }

    const onUp = () => {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
      if (rafId.current) cancelAnimationFrame(rafId.current)
      document.body.style.cursor = ''

      if (dragging.current) {
        dragging.current = false
        setIsDragging(false)
        // Capture final position at drag end (not stale closure)
        const finalX = dragOrbX.current + (lastMoveX.current - dragStartX.current)
        const finalY = dragOrbY.current + (lastMoveY.current - dragStartY.current)
        const finalPos = {
          x: Math.max(0, Math.min(window.innerWidth - ORB, finalX)),
          y: Math.max(0, Math.min(window.innerHeight - ORB, finalY)),
        }
        setOrbPos(finalPos)
        keepPos(finalPos)
        return
      }

      // Not a drag — it's a click
      dragging.current = false
      setIsDragging(false)

      if (state === NovaState.IDLE) {
        setState(NovaState.CHAT_OPEN)
        setTimeout(() => startVoice(), 100)
      } else if (state === NovaState.CHAT_OPEN) {
        stopVoice()
        setState(NovaState.IDLE)
      }
    }

    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }, [orbX, orbY, state, startVoice, stopVoice])

  const onMouseEnter = useCallback(() => {
    document.body.style.cursor = isDragging ? 'grabbing' : 'pointer'
  }, [isDragging])

  const onMouseLeave = () => {
    document.body.style.cursor = ''
  }

  return (
    <>
      <style>{`
        @keyframes orbBreathe { 0%,100%{transform:scale(1)} 50%{transform:scale(1.03)} }
        @keyframes orbPulse  { 0%,100%{transform:scale(1)} 50%{transform:scale(1.06)} }
        @keyframes orbThink  { 0%,100%{transform:scale(1.04)} 50%{transform:scale(1.09)} }

        /* ── Surface wave: single 54° band sweeps across sphere surface only ──
           One conic-gradient band: transparent→light→bright→light→transparent.
           Rotates 360° in 2.5s. No cross pattern — only one band exists. */
        @keyframes surfaceWave {
          from { transform: rotate(0deg) }
          to   { transform: rotate(360deg) }
        }

        @keyframes specDrift { 0%{transform:translate(0,0); opacity:0.5} 25%{transform:translate(2px,-1px); opacity:0.65} 50%{transform:translate(-1px,-2px); opacity:0.5} 75%{transform:translate(-2px,1px); opacity:0.6} 100%{transform:translate(0,0); opacity:0.5} }
        @keyframes shellBreathe { 0%,100%{opacity:0.6;transform:scale(1)} 50%{opacity:0.9;transform:scale(1.04)} }

        /* 3D ring spins — faster for snappier feel */
        @keyframes spinA { from{transform:rotateX(72deg) rotateZ(0deg)} to{transform:rotateX(72deg) rotateZ(360deg)} }
        @keyframes spinB { from{transform:rotateY(72deg) rotateZ(18deg)} to{transform:rotateY(72deg) rotateZ(378deg)} }
        @keyframes spinC { from{transform:rotateX(72deg) rotateY(72deg) rotateZ(-22deg) scale(0.92)} to{transform:rotateX(72deg) rotateY(72deg) rotateZ(338deg) scale(0.92)} }

        /* ── Orbit A: Rx=6, Ry=4 horizontal ellipse, 1.8s clockwise ──
           Parametric: x(t)=6*cos(t), y(t)=4*sin(t)
           Phase 0° → starts at right-most point. zIndex=10 above sphere. */
        @keyframes orbitA {
          0%   { transform: translate( 6px,  0px); }
          25%  { transform: translate( 0px,  4px); }
          50%  { transform: translate(-6px,  0px); }
          75%  { transform: translate( 0px, -4px); }
          100% { transform: translate( 6px,  0px); }
        }

        /* ── Orbit B: Rx=4, Ry=6 vertical ellipse, 1.4s counter-clockwise ──
           Parametric: x(t)=4*cos(t+90°), y(t)=6*sin(t+90°)
           Phase 90° → starts at bottom (0,6). NEVER meets orbitA — orthogonal axes.
           Speed: 1.4s = 1.29× faster than orbitA. zIndex=10 above sphere. */
        @keyframes orbitB {
          0%   { transform: translate( 0px,  6px); }
          25%  { transform: translate(-4px,  0px); }
          50%  { transform: translate( 0px, -6px); }
          75%  { transform: translate( 4px,  0px); }
          100% { transform: translate( 0px,  6px); }
        }

        @keyframes dotBlink  { 0%,100%{transform:scale(1); opacity:1} 50%{transform:scale(1.5); opacity:0.6} }
        @keyframes wBar      { from{transform:scaleY(0.15)} to{transform:scaleY(1)} }
        @keyframes pillIn    { from{opacity:0; transform:translateX(8px) scale(0.95)} to{opacity:1; transform:translateX(0) scale(1)} }
        @keyframes chatIn    { from{opacity:0; transform:scale(0.94) translateY(6px)} to{opacity:1; transform:scale(1) translateY(0)} }
        @keyframes msgIn     { from{opacity:0; transform:translateY(4px)} to{opacity:1; transform:translateY(0)} }
        @keyframes tdot      { 0%,100%{transform:translateY(0); opacity:0.3} 50%{transform:translateY(-2.5px); opacity:1} }
        @keyframes dragRing  { 0%{transform:scale(1); opacity:0.7} 50%{transform:scale(1.15); opacity:0.3} 100%{transform:scale(1); opacity:0.7} }
        @keyframes tapRipple  { 0%{transform:scale(0.9); opacity:0.6; border-color:rgba(125,211,252,0.4)} 100%{transform:scale(1.3); opacity:0; border-color:rgba(125,211,252,0)} }
      `}</style>

      {/* Chatbox panel */}
      {state === NovaState.CHAT_OPEN && (
        <Chatbox
          messages={msgs}
          onSend={chatSend}
          onClose={() => { stopVoice(); setState(NovaState.IDLE) }}
          orbX={orbX}
          orbY={orbY}
          sending={sending}
          voiceTranscript={voiceTranscript}
          voiceListening={voiceListening}
        />
      )}

      {/* Orb container — canonical: always starts at bottom-right */}
      <div
        id="nova-orb-container"
        onMouseDown={onPointerDown}
        onTouchStart={onPointerDown}
        onMouseEnter={onMouseEnter}
        onMouseLeave={onMouseLeave}
        title={state === NovaState.CHAT_OPEN ? 'Click để đóng chat · Kéo để di chuyển' : 'Click để mở chat · Kéo để di chuyển'}
        style={{
          position: 'fixed',
          left: orbX,
          top: orbY,
          zIndex: state === NovaState.CHAT_OPEN ? 9999 : 9998,
          cursor: isDragging ? 'grabbing' : 'pointer',
          userSelect: 'none',
          WebkitUserSelect: 'none',
          display: 'flex',
          alignItems: 'center',
        }}
      >
        {/* Drag ring indicator */}
        {isDragging && (
          <div style={{
            position: 'absolute', inset: '-8px', borderRadius: '50%',
            border: '2px solid rgba(125,211,252,0.55)',
            animation: 'dragRing 0.6s ease-out infinite',
            pointerEvents: 'none',
          }} />
        )}

        <NovaOrb
          state={state}
          hovered={false}
        />
      </div>
    </>
  )
}
