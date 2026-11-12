import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { api, refreshSession, setAccessToken } from './api'

const AuthContext = createContext(null)

export function homeFor(user) {
  if (!user) return '/login'
  if (user.account_status !== 'active') return '/access-denied'
  if (user.role === 'admin') return '/admin'
  if (user.role === 'instructor' && user.instructor_status === 'approved') return '/instructor'
  if (user.role === 'instructor') return '/account'
  return '/student'
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const saved = localStorage.getItem('epp-theme')
    document.documentElement.classList.toggle('dark', saved === 'dark')
    refreshSession()
      .then((data) => setUser(data?.user || null))
      .finally(() => setReady(true))
  }, [])

  const value = useMemo(() => ({
    user,
    ready,
    async login(email, password) {
      const data = await api('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }), skipRefresh: true })
      setAccessToken(data.access_token)
      setUser(data.user)
      return data.user
    },
    async register(payload) {
      const data = await api('/auth/register', { method: 'POST', body: JSON.stringify(payload), skipRefresh: true })
      setAccessToken(data.access_token)
      setUser(data.user)
      return data.user
    },
    async logout() {
      await api('/auth/logout', { method: 'POST' }).catch(() => {})
      setAccessToken(null)
      setUser(null)
    },
  }), [user, ready])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
