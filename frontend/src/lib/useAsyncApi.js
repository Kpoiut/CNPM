/**
 * useAsyncApi — Production async hook
 * - Loading / error / data state
 * - Abort on unmount
 * - Optimistic update support
 * - Message limit for chat-like patterns
 */
import { useState, useEffect, useCallback, useRef } from 'react'

/**
 * Generic async hook with automatic cleanup.
 * @param {Function} fn — async function returning data
 * @param {Array} deps — re-run when deps change
 * @param {{ timeout?: number, onError?: Function, initialData?: any }} opts
 */
export function useAsyncApi(fn, deps = [], opts = {}) {
  const { timeout = 30_000, onError, initialData = null } = opts
  const [data, setData] = useState(initialData)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const controllerRef = useRef(null)
  const mountedRef = useRef(true)

  const execute = useCallback(async (...args) => {
    if (controllerRef.current) controllerRef.current.abort()
    controllerRef.current = new AbortController()
    setLoading(true)
    setError(null)
    try {
      const timer = setTimeout(() => controllerRef.current?.abort(), timeout)
      const result = await fn(...args, controllerRef.current.signal)
      clearTimeout(timer)
      if (mountedRef.current) {
        setData(result)
        setLoading(false)
      }
    } catch (err) {
      if (err.name === 'AbortError' || err.message === 'Request timeout') {
        if (mountedRef.current) {
          setError('Yêu cầu hết thời gian. Vui lòng thử lại.')
          setLoading(false)
        }
      } else if (mountedRef.current) {
        setError(err.message || 'Đã xảy ra lỗi')
        setLoading(false)
        onError?.(err)
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      controllerRef.current?.abort()
    }
  }, [])

  const reset = useCallback(() => { setData(initialData); setError(null); setLoading(false) }, [initialData])

  return { data, loading, error, execute, setData, reset }
}

/**
 * useChatMessages — message list với optimistic update + limit
 * @param {number} maxMessages — giới hạn messages để tránh leak (default 100)
 */
export function useChatMessages(maxMessages = 100) {
  const [messages, setMessages] = useState([])

  const addMessage = useCallback((msg, optimistic = false) => {
    setMessages(prev => {
      const next = [...prev, { ...msg, optimistic, id: `${Date.now()}-${Math.random()}` }]
      return next.length > maxMessages ? next.slice(-maxMessages) : next
    })
    return msg.id || `${Date.now()}`
  }, [maxMessages])

  const updateMessage = useCallback((id, patch) => {
    setMessages(prev => prev.map(m => m.id === id ? { ...m, ...patch } : m))
  }, [])

  const removeMessage = useCallback((id) => {
    setMessages(prev => prev.filter(m => m.id !== id))
  }, [])

  const clearMessages = useCallback(() => setMessages([]), [])

  return { messages, addMessage, updateMessage, removeMessage, clearMessages }
}

/**
 * useAbortController — lifecycle-safe AbortController
 */
export function useAbortController() {
  const ref = useRef(null)
  const getSignal = useCallback(() => {
    if (ref.current) ref.current.abort()
    ref.current = new AbortController()
    return ref.current.signal
  }, [])
  useEffect(() => () => ref.current?.abort(), [])
  return getSignal
}
