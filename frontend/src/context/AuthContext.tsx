import React, { createContext, useContext, useState, useEffect } from 'react'
import api from '../api'

interface User {
  id: number
  email: string
  role: string
  full_name: string
  merchant_name?: string
}

interface AuthContextType {
  user: User | null
  token: string | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName: string, role: string, merchantName?: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'))
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchMe = async () => {
      if (token) {
        try {
          const res = await api.get('/auth/me')
          setUser(res.data)
        } catch (err) {
          console.error('[Auth] Failed to load current user', err)
          logout()
        }
      }
      setLoading(false)
    }
    fetchMe()
  }, [token])

  const login = async (email: string, password: string) => {
    setLoading(true)
    try {
      const res = await api.post('/auth/login', { email, password })
      const jwtToken = res.data.access_token
      localStorage.setItem('token', jwtToken)
      setToken(jwtToken)
      
      // Fetch user profile immediately
      const userRes = await api.get('/auth/me', {
        headers: { Authorization: `Bearer ${jwtToken}` }
      })
      setUser(userRes.data)
    } catch (err) {
      setLoading(false)
      throw err;
    }
  }

  const register = async (
    email: string,
    password: string,
    fullName: string,
    role: string,
    merchantName?: string
  ) => {
    setLoading(true)
    try {
      await api.post('/auth/register', {
        email,
        password,
        full_name: fullName,
        role,
        merchant_name: merchantName || null
      })
      // Auto login after successful registration
      await login(email, password)
    } catch (err) {
      setLoading(false)
      throw err;
    }
  }

  const logout = () => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
    setLoading(false)
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
