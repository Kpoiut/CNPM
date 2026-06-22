export class AuthSessionError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'AuthSessionError'
    this.status = status
  }
}

export async function fetchCurrentAccount(token, fetchImpl = fetch) {
  const response = await fetchImpl('/api/auth/me', {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new AuthSessionError(
      body.detail || `Không thể đồng bộ tài khoản (HTTP ${response.status})`,
      response.status,
    )
  }
  return response.json()
}
