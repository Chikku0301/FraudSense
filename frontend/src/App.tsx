import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { WebSocketProvider } from './context/WebSocketContext'
import { Login } from './pages/auth/Login'
import { Register } from './pages/auth/Register'
import { MerchantDashboard } from './pages/merchant/MerchantDashboard'
import { AnalystDashboard } from './pages/analyst/AnalystDashboard'

const DashboardRedirector: React.FC = () => {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen bg-[#070A13] flex items-center justify-center text-slate-400">
        <div className="text-center">
          <svg className="animate-spin h-10 w-10 text-blue-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <p className="text-sm font-semibold">Bootstrapping security consoles...</p>
        </div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  if (user.role === 'merchant') {
    return <MerchantDashboard />
  } else if (user.role === 'analyst' || user.role === 'admin') {
    return (
      <WebSocketProvider>
        <AnalystDashboard />
      </WebSocketProvider>
    )
  }

  return <Navigate to="/login" replace />
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/*" element={<DashboardRedirector />} />
        </Routes>
      </AuthProvider>
    </Router>
  )
}

export default App
