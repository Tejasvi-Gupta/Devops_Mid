const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

let accessToken = null

function cookie(name) {
  const item = document.cookie.split('; ').find((row) => row.startsWith(`${name}=`))
  return item ? decodeURIComponent(item.split('=').slice(1).join('=')) : ''
}

export function setAccessToken(token) {
  accessToken = token
}

export async function refreshSession() {
  const csrf = cookie('epp_csrf')
  const response = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
    method: 'POST',
    credentials: 'include',
    headers: csrf ? { 'X-CSRF-Token': csrf } : {},
  })
  if (!response.ok) {
    accessToken = null
    return null
  }
  const data = await response.json()
  accessToken = data.access_token
  return data
}

export async function api(path, options = {}) {
  const send = () => {
    const headers = { ...(options.headers || {}) }
    if (options.body) headers['Content-Type'] = 'application/json'
    if (accessToken) headers.Authorization = `Bearer ${accessToken}`
    return fetch(`${API_BASE}/api/v1${path}`, { ...options, headers, credentials: 'include' })
  }
  let response = await send()
  if (response.status === 401 && !options.skipRefresh) {
    const refreshed = await refreshSession()
    if (refreshed) response = await send()
  }
  const text = await response.text()
  const body = text ? JSON.parse(text) : null
  if (!response.ok) {
    const error = new Error(body?.error?.message || 'Request failed')
    error.details = body?.error?.details || {}
    error.status = response.status
    throw error
  }
  return body
}
