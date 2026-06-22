const EVENT_NAME = 'avm:notifications-updated'
const OPEN_EVENT_NAME = 'avm:open-notifications'
const STORE_PREFIX = 'avm-notifications'

function keyForUser(user) {
  return `${STORE_PREFIX}:${user?.username || 'guest'}`
}

function parseStored(key) {
  try {
    const value = localStorage.getItem(key)
    const parsed = value ? JSON.parse(value) : []
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function saveStored(key, notifications) {
  localStorage.setItem(key, JSON.stringify(notifications.slice(0, 80)))
  window.dispatchEvent(new CustomEvent(EVENT_NAME, { detail: { key } }))
}

export const notificationEvents = {
  updated: EVENT_NAME,
  open: OPEN_EVENT_NAME,
}

export function readNotifications(user) {
  return parseStored(keyForUser(user))
}

export function addNotification(user, payload) {
  const key = keyForUser(user)
  const notification = {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    title: payload.title || 'Thông báo',
    body: payload.body || '',
    type: payload.type || 'info',
    code: payload.code || '',
    actionTo: payload.actionTo || '',
    expiresAt: payload.expiresAt || '',
    createdAt: new Date().toISOString(),
    read: false,
  }
  saveStored(key, [notification, ...parseStored(key)])
  return notification
}

export function markNotificationRead(user, id) {
  const key = keyForUser(user)
  saveStored(key, parseStored(key).map(item => item.id === id ? { ...item, read: true } : item))
}

export function markAllNotificationsRead(user) {
  const key = keyForUser(user)
  saveStored(key, parseStored(key).map(item => ({ ...item, read: true })))
}

export function clearNotifications(user) {
  saveStored(keyForUser(user), [])
}

export function openNotificationCenter() {
  window.dispatchEvent(new CustomEvent(OPEN_EVENT_NAME))
}
