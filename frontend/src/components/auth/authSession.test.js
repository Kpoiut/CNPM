import test from 'node:test'
import assert from 'node:assert/strict'

import { fetchCurrentAccount } from './authSession.js'

test('tái xác thực account lấy role mới nhất từ PostgreSQL qua /api/auth/me', async () => {
  const calls = []
  const account = await fetchCurrentAccount('jwt-token', async (url, options) => {
    calls.push([url, options])
    return {
      ok: true,
      json: async () => ({ id: 57, username: 'google_kbuekpa', role: 'admin', is_active: true }),
    }
  })

  assert.equal(account.role, 'admin')
  assert.equal(calls[0][0], '/api/auth/me')
  assert.equal(calls[0][1].headers.Authorization, 'Bearer jwt-token')
})

test('tái xác thực báo rõ phiên hết hạn để frontend xóa session cũ', async () => {
  await assert.rejects(
    fetchCurrentAccount('expired-token', async () => ({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Token đã hết hạn' }),
    })),
    error => error.status === 401 && error.message === 'Token đã hết hạn',
  )
})
