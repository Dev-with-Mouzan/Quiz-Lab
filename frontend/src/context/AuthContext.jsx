import { createContext, useContext, useState, useEffect } from 'react'
import { authAPI } from '../services/api'

const AuthContext = createContext(null)

// Only non-sensitive profile fields are cached for the UI (routing, greetings).
// The session itself is an HttpOnly cookie that page scripts cannot read.
const cacheUser = (u) => {
  localStorage.setItem('user', JSON.stringify({
    id: u.id,
    role: u.role,
    first_name: u.first_name,
    last_name: u.last_name,
  }))
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // Ask the server who the session cookie belongs to (none -> logged out)
  useEffect(() => {
    loadUser()
  }, [])

  const loadUser = async () => {
    try {
      const res = await authAPI.getMe()
      cacheUser(res.data)
      setUser(res.data)
    } catch {
      localStorage.removeItem('user')
      setUser(null)
    } finally {
      setLoading(false)
    }
  }

  const login = async (email, password) => {
    const res = await authAPI.login({ email, password })
    localStorage.removeItem('pendingVerification')
    const userData = await fetchFullProfile({ id: res.data.user_id, role: res.data.role, is_verified: res.data.is_verified, email })
    cacheUser(userData)
    setUser(userData)
    return res.data
  }

  const fetchFullProfile = async (fallback) => {
    try {
      const me = await authAPI.getMe()
      if (me.data) return me.data
    } catch {
      // keep working with the minimal login payload if profile fetch fails
    }
    return fallback
  }

  const register = async (data) => {
    const res = await authAPI.register(data)
    // Don't auto-login — store email for the OTP screen
    localStorage.setItem('pendingVerification', JSON.stringify({ email: data.email }))
    return res.data
  }

  const logout = async () => {
    try {
      await authAPI.logout()
    } catch {
      // Even if the request fails, the local state is cleared below
    }
    localStorage.removeItem('user')
    localStorage.removeItem('pendingVerification')
    setUser(null)
  }

  const loginAfterVerify = async (user_id, role, is_verified, email) => {
    const userData = await fetchFullProfile({ id: user_id, role, is_verified, email })
    cacheUser(userData)
    localStorage.removeItem('pendingVerification')
    setUser(userData)
  }

  const value = {
    user,
    setUser,
    loading,
    login,
    register,
    logout,
    loginAfterVerify,
    isAdmin: user?.role === 'admin',
    isTeacher: user?.role === 'teacher',
    isStudent: user?.role === 'student',
    isAuthenticated: !!user,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within an AuthProvider')
  return context
}
