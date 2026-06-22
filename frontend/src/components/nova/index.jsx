// NovaAssistant v3 — Production Floating AI Assistant
// single-click = chat + voice | drag (instant, no delay)
// Orbital physics | Surface light sweep

import React, {
  useState, useEffect, useCallback, useRef, useMemo,
} from 'react'
import { icon } from '../ui/icons'
import { getNovaContext } from './novaBus'
import { useNavigate } from 'react-router-dom'

// ─── State ───────────────────────────────────────────────────────────────────
export const NovaState = {
  IDLE: 'idle',
  CHAT_OPEN: 'chat_open',
  PROCESSING: 'processing',
}

// ─── Constants ────────────────────────────────────────────────────────────────
const ORB = 44
const CHAT_W = 405
const CHAT_H_MAX = 520
const CHAT_H_MIN = 380
const SAFE = 16
const MAX_MESSAGES = 80
const HISTORY_KEY = 'nova-chat-archive'
const MAX_HISTORY = 3
const MAX_ATTACHMENTS = 8
const MAX_FOLDER_FILES = 80
const MAX_TEXT_SNIPPET = 1800

// Drag sensitivity — very small for instant response
const DRAG_THRESH_PX = 5
const DRAG_THRESH_MS = 60

// ─── Position ─────────────────────────────────────────────────────────────────
// Always start at bottom-right — canonical initial position
// Version 11: validates saved position against current viewport
function savedPos() { return null }
function keepPos() {}

function archiveChat(messages) {
  if (!messages?.length) return
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    const archive = raw ? JSON.parse(raw) : []
    const cleanMessages = messages.filter(m => m.role !== 'error')
    if (!cleanMessages.length) return
    const title = cleanMessages.find(m => m.role === 'user')?.text || 'Cuộc trò chuyện Nova'
    archive.unshift({
      id: `nova-${Date.now()}`,
      closedAt: new Date().toISOString(),
      title: title.slice(0, 64),
      messages: cleanMessages,
    })
    localStorage.setItem(HISTORY_KEY, JSON.stringify(archive.slice(0, MAX_HISTORY)))
  } catch {}
}

function loadRecentChats() {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    const archive = raw ? JSON.parse(raw) : []
    return Array.isArray(archive) ? archive.slice(0, MAX_HISTORY) : []
  } catch {
    return []
  }
}

function formatBytes(n = 0) {
  if (!n) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = n
  let i = 0
  while (size >= 1024 && i < units.length - 1) { size /= 1024; i += 1 }
  return `${size.toFixed(size >= 10 || i === 0 ? 0 : 1)} ${units[i]}`
}

function summarizeAttachment(a) {
  if (!a) return ''
  const folder = a.relativePath ? `${a.relativePath}` : a.name
  return `${folder} (${a.kind || 'file'}, ${formatBytes(a.size)})`
}

function readFileAsDataURL(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

function readFileAsText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || '').slice(0, MAX_TEXT_SNIPPET))
    reader.onerror = reject
    reader.readAsText(file)
  })
}

async function fileToAttachment(file, source = 'file') {
  const isImage = file.type?.startsWith('image/')
  const isText = /^text\/|json|csv|xml|markdown|javascript|typescript|python/i.test(file.type || file.name)
  const attachment = {
    id: `att-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    kind: isImage ? 'image' : source,
    name: file.name,
    relativePath: file.webkitRelativePath || '',
    mime: file.type || 'application/octet-stream',
    size: file.size,
  }
  if (isImage) attachment.dataUrl = await readFileAsDataURL(file)
  else if (isText && file.size <= 256 * 1024) attachment.textPreview = await readFileAsText(file)
  return attachment
}

function novaContext(history = []) {
  let authUser = null
  try {
    const stored = localStorage.getItem('avm-user')
    authUser = stored ? JSON.parse(stored) : null
  } catch {}
  const role = authUser?.role === 'admin' ? 'admin' : 'user'
  const moduleCtx = (() => { try { return getNovaContext() } catch { return {} } })()
  return {
    page: window.location.pathname,
    title: document.title,
    page_context: moduleCtx,
    locale: navigator.language,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    auth_user: authUser ? {
      username: authUser.username,
      role,
    } : { role: 'guest' },
    nova_mode: role === 'admin' ? 'collaborator' : 'advisor',
    recent_messages: history.slice(-6).map(m => ({
      role: m.role,
      text: m.text,
      attachments: (m.attachments || []).map(a => ({
        kind: a.kind,
        name: a.name,
        relativePath: a.relativePath,
        mime: a.mime,
        size: a.size,
      })),
    })),
  }
}

async function readNovaResponse(res) {
  let data = {}
  try { data = await res.json() } catch {}
  if (!res.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : `HTTP ${res.status}`
    throw new Error(detail)
  }
  if (!data.text) {
    throw new Error('Nova không trả về nội dung. Kiểm tra /api/nova/chat và API key backend.')
  }
  return data
}

function renderMessageText(text) {
  const parts = String(text || '').split(/(\*\*[^*]+\*\*)/g)
  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={idx}>{part.slice(2, -2)}</strong>
    }
    return <React.Fragment key={idx}>{part}</React.Fragment>
  })
}

// ─── Chat panel position relative to orb ──────────────────────────────────────
function chatPos(orbX, orbY, vw, vh) {
  const width = Math.min(CHAT_W, Math.max(300, vw - SAFE * 2))
  const height = Math.min(CHAT_H_MAX, Math.max(CHAT_H_MIN, vh - SAFE * 2 - ORB - 14))
  return { right: SAFE, bottom: SAFE + ORB + 12, width, height }
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
        zIndex: 6,
      }} />

      {/* ── Specular highlight (top-left) — sits above core ── */}
      <div style={{
        position: 'absolute', inset: '20%', borderRadius: '50%',
        background: 'radial-gradient(circle at 28% 22%, rgba(255,255,255,0.65) 0%, transparent 55%)',
        animation: 'specDrift 5s ease-in-out infinite',
        pointerEvents: 'none',
        zIndex: 7,
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
        zIndex: 8,
        mixBlendMode: 'screen',
      }} />

      {/* ── Shell glow ── */}
      <div style={{
        position: 'absolute', inset: '10%', borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(125,211,252,0.12) 0%, transparent 70%)',
        animation: 'shellBreathe 3s ease-in-out infinite',
        pointerEvents: 'none',
        zIndex: 7,
      }} />

      {/* ── Ring A — equatorial ── */}
      <div style={{
        position: 'absolute', inset: '4%', borderRadius: '50%',
        background: `conic-gradient(from 0deg, transparent, ${colors.ringA}, rgba(118,130,255,0.22), transparent)`,
        transform: 'rotateX(72deg) rotateZ(0deg)',
        animation: 'spinA 4s linear infinite',
        mixBlendMode: 'screen',
        zIndex: 9,
      }} />

      {/* ── Ring B — tilted ── */}
      <div style={{
        position: 'absolute', inset: '0%', borderRadius: '50%',
        background: `conic-gradient(from 140deg, transparent, ${colors.ringB}, rgba(255,164,107,0.22), transparent)`,
        transform: 'rotateY(72deg) rotateZ(18deg)',
        animation: 'spinB 5.5s linear infinite reverse',
        mixBlendMode: 'screen',
        zIndex: 9,
      }} />

      {/* ── Ring C — 3D tilt ── */}
      <div style={{
        position: 'absolute', inset: '-6%', borderRadius: '50%',
        background: `conic-gradient(from 220deg, transparent, ${colors.ringC}, rgba(75,255,208,0.25), transparent)`,
        transform: 'rotateX(72deg) rotateY(72deg) rotateZ(-22deg) scale(0.92)',
        animation: 'spinC 6s linear infinite',
        mixBlendMode: 'screen',
        zIndex: 9,
      }} />

    </div>
  )
}

function SiriSphere({ listening = false, size = 48 }) {
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%', position: 'relative',
      overflow: 'hidden',
      background: 'radial-gradient(circle at 32% 24%, #ffffff 0%, #a7ecff 24%, #38bdf8 48%, #8b5cf6 78%, #0f172a 100%)',
      boxShadow: listening
        ? '0 0 18px rgba(56,189,248,0.55), 0 0 34px rgba(168,85,247,0.34), inset -5px -8px 16px rgba(15,23,42,0.28)'
        : '0 5px 16px rgba(56,189,248,0.34), inset -4px -7px 14px rgba(15,23,42,0.22)',
      animation: listening ? 'siriFloat 1.7s ease-in-out infinite' : 'none',
    }}>
      <div style={{
        position: 'absolute', inset: '-18%',
        background: 'conic-gradient(from 0deg, rgba(255,255,255,0), rgba(34,211,238,0.75), rgba(168,85,247,0.48), rgba(52,211,153,0.56), rgba(255,255,255,0))',
        animation: listening ? 'siriSpin 2.6s linear infinite' : 'none',
        mixBlendMode: 'screen',
      }} />
      <div style={{
        position: 'absolute', inset: '11%', borderRadius: '50%',
        background: 'radial-gradient(circle at 35% 30%, rgba(255,255,255,0.82), rgba(125,211,252,0.2) 42%, transparent 72%)',
        animation: listening ? 'siriPulse 1.8s ease-in-out infinite' : 'none',
      }} />
      <div style={{
        position: 'absolute', inset: '21%', borderRadius: '50%',
        border: '1px solid rgba(255,255,255,0.55)',
        transform: 'rotateX(68deg) rotateZ(18deg)',
        animation: listening ? 'siriRing 2.1s linear infinite' : 'none',
      }} />
    </div>
  )
}

// ─── Chatbox panel ─────────────────────────────────────────────────────────────
function Chatbox({ messages, onSend, onClose, onRestoreChat, recentChats, orbX, orbY, sending, voiceTranscript, voiceListening, onStartVoice, onStopVoice, onRunAction, novaStatus }) {
  const [input, setInput] = useState('')
  const [attachments, setAttachments] = useState([])
  const [showHistory, setShowHistory] = useState(false)
  const [typing, setTyping] = useState(false)
  const endRef = useRef(null)
  const inRef = useRef(null)
  const boxRef = useRef(null)
  const imageInputRef = useRef(null)
  const folderInputRef = useRef(null)

  const vw = window.innerWidth
  const vh = window.innerHeight
  const pos = useMemo(() => chatPos(orbX, orbY, vw, vh), [orbX, orbY, vw, vh])
  const statusText = voiceListening
    ? 'Đang nghe...'
    : novaStatus?.provider === 'offline'
    ? 'Ngữ cảnh dự án'
    : novaStatus?.provider
    ? 'AI trực tuyến'
    : 'Đang kiểm tra'

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

  const addAttachments = useCallback(async (files, source = 'file') => {
    const selected = Array.from(files || []).slice(0, source === 'folder' ? MAX_FOLDER_FILES : MAX_ATTACHMENTS)
    if (!selected.length) return
    const converted = []
    for (const file of selected) converted.push(await fileToAttachment(file, source))
    setAttachments(prev => [...prev, ...converted].slice(0, source === 'folder' ? MAX_FOLDER_FILES : MAX_ATTACHMENTS))
    inRef.current?.focus()
  }, [])

  const handlePaste = useCallback(async (e) => {
    const items = Array.from(e.clipboardData?.items || [])
    const imageItems = items.filter(item => item.kind === 'file' && item.type?.startsWith('image/'))
    if (!imageItems.length) return
    e.preventDefault()
    const stamp = new Date().toISOString().replace(/[:.]/g, '-')
    const files = imageItems
      .map((item, index) => {
        const file = item.getAsFile()
        if (!file) return null
        const ext = (file.type || 'image/png').split('/')[1] || 'png'
        const name = file.name || `clipboard-${stamp}-${index + 1}.${ext}`
        return new File([file], name, { type: file.type || 'image/png', lastModified: Date.now() })
      })
      .filter(Boolean)
    await addAttachments(files, 'clipboard')
    if (!input.trim()) setInput('Phân tích ảnh này')
  }, [addAttachments, input])

  const send = () => {
    if (!input.trim() && !attachments.length) return
    const text = input.trim() || 'Phân tích các tệp tôi vừa gửi.'
    onSend(text, attachments)
    setInput('')
    setAttachments([])
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
        position: 'fixed', right: pos.right, bottom: pos.bottom, width: pos.width, height: pos.height,
        display: 'flex', flexDirection: 'column',
        background: 'linear-gradient(180deg, rgba(247,252,255,0.99), rgba(229,244,255,0.98))',
        border: '1px solid rgba(125,211,252,0.28)',
        borderRadius: 12,
        boxShadow: '0 18px 42px rgba(3, 7, 18, 0.34), 0 0 0 1px rgba(14,165,233,0.14)',
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
        background: 'linear-gradient(135deg, rgba(218,242,255,0.98), rgba(239,247,255,0.96))',
        gap: 9, flexShrink: 0,
      }}>
        <div style={{ flexShrink: 0 }}>
          <SiriSphere listening={voiceListening || sending} size={30} />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: '0.92rem', fontWeight: 800, color: '#082f49' }}>Nova</div>
          <div style={{ fontSize: '0.7rem', color: '#0369a1', display: 'flex', alignItems: 'center', gap: 3 }}>
            <div style={{
              width: 5, height: 5, borderRadius: '50%',
              background: voiceListening ? '#f59e0b' : '#06d6a0',
              boxShadow: `0 0 3px ${voiceListening ? '#f59e0b' : '#06d6a0'}`,
              animation: voiceListening ? 'dotBlink 0.85s ease-in-out infinite' : 'none',
            }} />
            {statusText}
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
        <button
          onClick={voiceListening ? onStopVoice : onStartVoice}
          title={voiceListening ? 'Tắt nghe' : 'Bật nghe Hey Nova'}
          style={{
            height: 24, minWidth: 30, borderRadius: 6,
            border: '1px solid rgba(14,165,233,0.22)',
            background: voiceListening ? 'rgba(245,158,11,0.16)' : 'rgba(14,165,233,0.08)',
            color: voiceListening ? '#b45309' : '#0c4a6e',
            cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          {icon('mic', 13)}
        </button>
        <button
          onClick={() => setShowHistory(v => !v)}
          title="3 cuộc trò chuyện gần nhất"
          style={{
            height: 24, minWidth: 30, borderRadius: 6,
            border: '1px solid rgba(14,165,233,0.22)',
            background: showHistory ? 'rgba(14,165,233,0.16)' : 'rgba(14,165,233,0.08)',
            color: '#0c4a6e', cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '0.72rem', gap: 4, flexShrink: 0,
          }}
        >
          {icon('clock', 13)} {recentChats.length}
        </button>
        <div style={{
          fontSize: '0.68rem', color: '#0f6e93',
          background: 'rgba(14,165,233,0.12)', borderRadius: 4,
          padding: '1px 5px', border: '1px solid rgba(14,165,233,0.22)',
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

      {showHistory && (
        <div style={{
          padding: '8px 12px', borderBottom: '1px solid rgba(125,211,252,0.16)',
          background: 'rgba(240,249,255,0.96)', display: 'grid', gap: 6,
        }}>
          {recentChats.length ? recentChats.map(chat => (
            <button
              key={chat.id}
              onClick={() => { onRestoreChat(chat); setShowHistory(false) }}
              style={{
                textAlign: 'left', border: '1px solid rgba(125,211,252,0.24)',
                background: '#fff', borderRadius: 8, padding: '6px 8px',
                cursor: 'pointer', color: '#0f172a',
              }}
            >
              <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#075985' }}>
                {chat.title || 'Cuộc trò chuyện Nova'}
              </div>
              <div style={{ fontSize: '0.64rem', color: '#64748b', marginTop: 2 }}>
                {new Date(chat.closedAt).toLocaleString('vi-VN')} · {chat.messages?.length || 0} tin
              </div>
            </button>
          )) : (
            <div style={{ fontSize: '0.72rem', color: '#64748b', padding: '4px 0' }}>
              Chưa có cuộc trò chuyện đã đóng.
            </div>
          )}
        </div>
      )}

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
            <SiriSphere listening={voiceListening || sending} size={48} />
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
                    padding: '3px 9px', borderRadius: 12,
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
          const isPending = m.pending
          return (
          <div key={m.id || i} style={{
            display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start',
            animation: 'msgIn 180ms ease-out',
            opacity: m.optimistic ? 0.6 : 1,
          }}>
            {/* Avatar for assistant */}
            {m.role !== 'user' && !isFailed && (
              <div style={{ flexShrink: 0, marginRight: 5, alignSelf: 'flex-end' }}>
                <SiriSphere listening={sending || voiceListening} size={22} />
              </div>
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
                : isPending
                ? 'rgba(255,255,255,0.86)'
                : m.role === 'user'
                ? 'linear-gradient(135deg, #0ea5e9, #2563eb)'
                : 'rgba(255,255,255,0.98)',
              color: isFailed ? '#b91c1c' : m.role === 'user' ? '#ffffff' : '#0f172a',
              fontSize: '0.8rem', lineHeight: 1.45,
              boxShadow: m.role === 'user'
                ? '0 1px 5px rgba(56,189,248,0.22)'
                : '0 1px 3px rgba(0,0,0,0.06)',
              wordBreak: 'break-word',
              whiteSpace: 'pre-wrap',
            }}>
              {isVoiceMsg && (
                <div style={{
                  fontSize: '0.62rem', color: 'rgba(56,189,248,0.6)',
                  marginBottom: 2, display: 'flex', alignItems: 'center', gap: 3,
                }}>
                  <span style={{ fontStyle: 'normal' }}>🎤</span> giọng nói
                </div>
              )}
              {isPending ? (
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7, color: '#075985' }}>
                  Nova đang suy nghĩ
                  <span style={{ display: 'inline-flex', gap: 3 }}>
                    {[0, 1, 2].map(d => (
                      <span key={d} style={{
                        width: 4, height: 4, borderRadius: '50%', background: '#38bdf8',
                        animation: `tdot 1.1s ease-in-out ${d * 0.16}s infinite`,
                      }} />
                    ))}
                  </span>
                </span>
              ) : (m.text ? renderMessageText(m.text) : (isFailed ? 'Gửi thất bại. Nhấn để thử lại.' : ''))}
              {!!m.attachments?.length && (
                <div style={{ display: 'grid', gap: 5, marginTop: 7 }}>
                  {m.attachments.slice(0, 6).map(a => (
                    <div key={a.id || a.name} style={{
                      display: 'flex', alignItems: 'center', gap: 6,
                      padding: '5px 6px', borderRadius: 7,
                      background: m.role === 'user' ? 'rgba(255,255,255,0.16)' : 'rgba(14,165,233,0.06)',
                      border: m.role === 'user' ? '1px solid rgba(255,255,255,0.22)' : '1px solid rgba(14,165,233,0.12)',
                    }}>
                      {a.dataUrl ? (
                        <img src={a.dataUrl} alt="" style={{ width: 32, height: 32, borderRadius: 6, objectFit: 'cover' }} />
                      ) : (
                        <span style={{ display: 'flex', color: m.role === 'user' ? '#e0f2fe' : '#0284c7' }}>
                          {icon(a.kind === 'folder' ? 'package' : 'fileText', 15)}
                        </span>
                      )}
                      <span style={{ fontSize: '0.68rem', lineHeight: 1.25 }}>
                        {a.relativePath || a.name}
                      </span>
                    </div>
                  ))}
                  {m.attachments.length > 6 && (
                    <div style={{ fontSize: '0.65rem', opacity: 0.8 }}>
                      +{m.attachments.length - 6} tệp khác
                    </div>
                  )}
                </div>
              )}
              {m.action && !isPending && m.role === 'assistant' && (
                <button
                  type="button"
                  onClick={() => onRunAction?.(m.action, m.id)}
                  disabled={m.actionDone}
                  style={{
                    marginTop: 8, width: '100%', cursor: m.actionDone ? 'default' : 'pointer',
                    padding: '7px 10px', borderRadius: 9, border: '1px solid rgba(14,165,233,0.35)',
                    background: m.actionDone ? 'rgba(148,163,184,0.18)' : 'linear-gradient(135deg, #0ea5e9, #2563eb)',
                    color: m.actionDone ? '#475569' : '#fff', fontSize: '0.74rem', fontWeight: 700,
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                  }}
                >
                  {icon(m.action.type === 'navigate' ? 'arrowRight' : 'play', 14)}
                  {m.actionDone ? 'Đã thực hiện' : (m.action.label || 'Thực hiện')}
                </button>
              )}
            </div>
          </div>
          )
        })}

        {/* Typing indicator */}
        {typing && !messages.some(m => m.pending) && (
          <div style={{ display: 'flex', justifyContent: 'flex-start', gap: 5, alignItems: 'center' }}>
            <SiriSphere listening size={22} />
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
        background: 'rgba(241,248,255,0.94)', flexShrink: 0,
      }}>
        {!!attachments.length && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, marginBottom: 6 }}>
            {attachments.slice(0, 8).map(a => (
              <div key={a.id} style={{
                display: 'flex', alignItems: 'center', gap: 5,
                maxWidth: '100%', padding: '4px 6px', borderRadius: 8,
                background: '#fff', border: '1px solid rgba(125,211,252,0.24)',
                color: '#0f172a', fontSize: '0.66rem',
              }}>
                {a.dataUrl ? <img src={a.dataUrl} alt="" style={{ width: 22, height: 22, borderRadius: 5, objectFit: 'cover' }} /> : icon(a.kind === 'folder' ? 'package' : 'fileText', 13)}
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 170 }}>
                  {a.relativePath || a.name}
                </span>
                <button
                  onClick={() => setAttachments(prev => prev.filter(x => x.id !== a.id))}
                  title="Bỏ tệp"
                  style={{ border: 'none', background: 'transparent', color: '#64748b', cursor: 'pointer', padding: 0 }}
                >
                  {icon('close', 12)}
                </button>
              </div>
            ))}
          </div>
        )}
        <div style={{ display: 'flex', gap: 6, alignItems: 'flex-end' }}>
          <input
            ref={imageInputRef}
            type="file"
            accept="image/*"
            multiple
            style={{ display: 'none' }}
            onChange={e => { addAttachments(e.target.files, 'image'); e.target.value = '' }}
          />
          <input
            ref={folderInputRef}
            type="file"
            multiple
            webkitdirectory=""
            directory=""
            style={{ display: 'none' }}
            onChange={e => { addAttachments(e.target.files, 'folder'); e.target.value = '' }}
          />
          <button
            onClick={() => imageInputRef.current?.click()}
            style={{
              width: 30, height: 32, borderRadius: 8,
              border: '1px solid rgba(125,211,252,0.22)',
              background: '#fff', cursor: 'pointer',
              color: '#0284c7', display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}
            title="Gửi ảnh"
          >
            {icon('cloudUp', 15)}
          </button>
          <button
            onClick={() => folderInputRef.current?.click()}
            style={{
              width: 30, height: 32, borderRadius: 8,
              border: '1px solid rgba(125,211,252,0.22)',
              background: '#fff', cursor: 'pointer',
              color: '#0284c7', display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}
            title="Gửi thư mục"
          >
            {icon('package', 15)}
          </button>

          <textarea
            ref={inRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onPaste={handlePaste}
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
            disabled={(!input.trim() && !attachments.length) || sending}
            style={{
              width: 32, height: 32, borderRadius: 8, border: 'none',
              background: sending
                ? 'rgba(125,211,252,0.3)'
                : input.trim() || attachments.length
                ? 'linear-gradient(135deg, #38bdf8, #0ea5e9)'
                : 'rgba(125,211,252,0.12)',
              color: sending ? '#94a3b8' : (input.trim() || attachments.length) ? '#fff' : 'rgba(125,211,252,0.35)',
              cursor: (!input.trim() && !attachments.length) || sending ? 'default' : 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '0.85rem',
              boxShadow: (input.trim() || attachments.length) && !sending ? '0 1px 5px rgba(56,189,248,0.28)' : 'none',
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
  const [recentChats, setRecentChats] = useState(() => loadRecentChats())
  const [voiceListening, setVoiceListening] = useState(false)
  const [voiceTranscript, setVoiceTranscript] = useState('')
  const [sending, setSending] = useState(false)
  const [novaStatus, setNovaStatus] = useState(null)
  
  // Orb position — canonical: always start at bottom-right
  const [orbPos, setOrbPos] = useState(() => ({
    x: window.innerWidth - ORB - SAFE,
    y: window.innerHeight - ORB - SAFE,
  }))

  // Refs for drag/voice without causing re-renders
  const recogRef = useRef(null)
  const voiceTimeout = useRef(null)

  const orbX = orbPos.x
  const orbY = orbPos.y

  const navigate = useNavigate()

  useEffect(() => {
    let cancelled = false
    fetch('/api/nova/status', { cache: 'no-store' })
      .then(res => res.ok ? res.json() : null)
      .then(data => { if (!cancelled) setNovaStatus(data) })
      .catch(() => { if (!cancelled) setNovaStatus({ provider: 'offline' }) })
    return () => { cancelled = true }
  }, [])

  // ─── Agentic action: thực thi tác vụ hệ thống do người dùng xác nhận ─────────
  const runNovaAction = useCallback(async (action, msgId) => {
    if (!action) return
    // Đánh dấu nút đã bấm để không gọi lại
    setMsgs(prev => prev.map(m => (m.id === msgId ? { ...m, actionDone: true } : m)))

    if (action.type === 'navigate' && action.to) {
      try { navigate(action.to) } catch { window.location.assign(action.to) }
      return
    }

    if (action.type === 'execute' && action.op) {
      const pendingId = `act-${Date.now()}`
      setMsgs(prev => [...prev, { id: pendingId, role: 'assistant', text: '', pending: true }])
      try {
        const token = localStorage.getItem('avm-token')
        const res = await fetch('/api/nova/execute', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ action: action.op, params: action.params || {} }),
        })
        const data = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
        setMsgs(prev => prev.map(m =>
          m.id === pendingId
            ? { id: `asst-${Date.now()}`, role: 'assistant', text: data.text || 'Đã chạy xong.' }
            : m,
        ))
      } catch (err) {
        const detail = err?.message || 'Không thực thi được.'
        const friendly = /403|quyền|admin/i.test(detail)
          ? 'Tác vụ này cần quyền admin. Hãy đăng nhập tài khoản admin rồi thử lại.'
          : `Không thực thi được: ${detail}`
        setMsgs(prev => prev.map(m =>
          m.id === pendingId ? { id: `err-${Date.now()}`, role: 'error', text: friendly } : m,
        ))
      }
    }
  }, [navigate])

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
  const closeChat = useCallback(() => {
    stopVoice()
    archiveChat(msgs)
    setRecentChats(loadRecentChats())
    setMsgs([])
    setState(NovaState.IDLE)
  }, [msgs, stopVoice])

  const restoreChat = useCallback((chat) => {
    stopVoice()
    setMsgs(Array.isArray(chat?.messages) ? chat.messages : [])
  }, [stopVoice])

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
        body: JSON.stringify({ message: text, context: novaContext() }),
      })
      const d = await readNovaResponse(res)
      const reply = d.text
      speakResponse(reply)
    } catch {
      speakResponse('Xin lỗi, Nova chưa kết nối được backend. Hãy kiểm tra RUN_BACKEND.bat đang chạy ở cổng 8000.')
    }
    setState(NovaState.CHAT_OPEN)
    stopVoice()
  }, [stopVoice])

  // ─── Chat send (text input) ─────────────────────────────────────────────────
  const chatSend = useCallback(async (text, attachments = []) => {
    const optimisticId = `opt-${Date.now()}`
    const pendingId = `pending-${Date.now()}`
    const wantsPreviousAttachment = /ảnh|hình|file|tệp|giải|bài toán|đọc|phân tích|tóm tắt/i.test(text || '')
    const recentAttachments = wantsPreviousAttachment
      ? [...msgs].reverse().find(m => Array.isArray(m.attachments) && m.attachments.length)?.attachments || []
      : []
    const effectiveAttachments = attachments.length ? attachments : recentAttachments
    const attachmentSummary = effectiveAttachments.length
      ? `\n\n[Tệp gửi kèm]\n${effectiveAttachments.map(summarizeAttachment).join('\n')}`
      : ''
    setMsgs(prev => {
      const next = [
        ...prev,
        { id: optimisticId, role: 'user', text, attachments },
        { id: pendingId, role: 'assistant', text: '', pending: true },
      ]
      return next.length > MAX_MESSAGES ? next.slice(-MAX_MESSAGES) : next
    })
    setSending(true)
    try {
      const res = await fetch('/api/nova/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text + attachmentSummary,
          context: novaContext(msgs),
          attachments: effectiveAttachments,
        }),
      })
      const d = await readNovaResponse(res)
      setMsgs(prev => {
        const next = prev.map(m =>
          m.id === pendingId
            ? { id: `asst-${Date.now()}`, role: 'assistant', text: d.text, action: d.action || null }
            : m
        )
        return next.length > MAX_MESSAGES ? next.slice(-MAX_MESSAGES) : next
      })
    } catch (err) {
      setMsgs(prev => {
        const updated = prev.map(m =>
          m.id === optimisticId
            ? { ...m, optimistic: false, error: true }
            : m.id === pendingId
            ? { id: `err-${Date.now()}`, role: 'error', text: err?.message || 'Nova chưa nhận được phản hồi. Bạn thử gửi lại câu này nhé.' }
            : m
        )
        return updated.slice(-MAX_MESSAGES)
      })
    } finally {
      setSending(false)
    }
  }, [msgs])

  // ─── ESC to close ───────────────────────────────────────────────────────────
  useEffect(() => {
    const h = (e) => {
      if (e.key === 'Escape' && state === NovaState.CHAT_OPEN) {
        closeChat()
      }
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [state, closeChat])

  // ─── Window resize: keep Nova pinned to the outer bottom-right corner ─────
  useEffect(() => {
    const pin = () => setOrbPos({
      x: window.innerWidth - ORB - SAFE,
      y: window.innerHeight - ORB - SAFE,
    })
    pin()
    window.addEventListener('resize', pin)
    return () => window.removeEventListener('resize', pin)
  }, [])

  // ─── Click only: Nova is pinned, not draggable ─────────────────────────────
  const onPointerDown = useCallback((e) => {
    if (e.button != null && e.button !== 0) return
    e.preventDefault()
    if (state === NovaState.IDLE) {
      setMsgs([])
      setState(NovaState.CHAT_OPEN)
    } else if (state === NovaState.CHAT_OPEN) {
      closeChat()
    }
  }, [state, closeChat])

  const onMouseEnter = useCallback(() => {
    document.body.style.cursor = 'pointer'
  }, [])

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

        @keyframes siriFloat { 0%,100%{transform:translateY(0) scale(1)} 50%{transform:translateY(-2px) scale(1.035)} }
        @keyframes siriSpin { from{transform:rotate(0deg) scale(1)} to{transform:rotate(360deg) scale(1)} }
        @keyframes siriPulse { 0%,100%{opacity:0.58; transform:scale(0.95)} 50%{opacity:0.95; transform:scale(1.12)} }
        @keyframes siriRing { from{transform:rotateX(68deg) rotateZ(18deg)} to{transform:rotateX(68deg) rotateZ(378deg)} }

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
          onClose={closeChat}
          onRestoreChat={restoreChat}
          recentChats={recentChats}
          orbX={orbX}
          orbY={orbY}
          sending={sending}
          voiceTranscript={voiceTranscript}
          voiceListening={voiceListening}
          onStartVoice={startVoice}
          onStopVoice={stopVoice}
          onRunAction={runNovaAction}
          novaStatus={novaStatus}
        />
      )}

      {/* Orb container — canonical: always starts at bottom-right */}
      <div
        id="nova-orb-container"
        onMouseDown={onPointerDown}
        onTouchStart={onPointerDown}
        onMouseEnter={onMouseEnter}
        onMouseLeave={onMouseLeave}
        title={state === NovaState.CHAT_OPEN ? 'Click để đóng chat' : 'Click để mở chat'}
        style={{
          position: 'fixed',
          left: orbX,
          top: orbY,
          zIndex: state === NovaState.CHAT_OPEN ? 9999 : 9998,
          cursor: 'pointer',
          userSelect: 'none',
          WebkitUserSelect: 'none',
          display: 'flex',
          alignItems: 'center',
        }}
      >
        {/* Drag ring indicator */}
        <NovaOrb
          state={state}
          hovered={false}
        />
      </div>
    </>
  )
}
