import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { Shield, AlertCircle } from 'lucide-react'

const loginSchema = z.object({
  email: z.string().email({ message: "Invalid email address" }),
  password: z.string().min(6, { message: "Password must be at least 6 characters" }),
})

type LoginFormValues = z.infer<typeof loginSchema>

export const Login: React.FC = () => {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
    }
  })

  const onSubmit = async (data: LoginFormValues) => {
    setError(null)
    setLoading(true)
    try {
      await login(data.email, data.password)
      // Navigate depending on the role. Let's check which user role logged in.
      // We will read it from token or auth state after a split second
      setLoading(false)
      navigate('/')
    } catch (err: any) {
      setLoading(false)
      const errMsg = err.response?.data?.detail || "Invalid email or password."
      setError(errMsg)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#070A13] px-4">
      {/* Background radial glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-blue-500/10 rounded-full blur-[120px] pointer-events-none"></div>

      <div className="w-full max-w-md glass-panel p-8 rounded-2xl shadow-2xl relative z-10">
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 bg-blue-600/20 border border-blue-500/30 rounded-2xl flex items-center justify-center text-blue-500 mb-4 shadow-lg shadow-blue-500/10">
            <Shield className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-bold text-slate-100 font-display">FraudSense</h1>
          <p className="text-slate-400 text-sm mt-1">Transaction Risk & Monitoring Portal</p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-900/20 border border-red-500/30 text-red-400 rounded-xl flex items-start gap-3 text-sm">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Email Address
            </label>
            <input
              type="email"
              placeholder="e.g. analyst1@fraudsense.com"
              {...register('email')}
              className={`w-full px-4 py-3 bg-slate-950 border rounded-xl text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all ${
                errors.email ? 'border-red-500/50' : 'border-slate-800 focus:border-slate-700'
              }`}
            />
            {errors.email && (
              <p className="mt-1 text-xs text-red-500">{errors.email.message}</p>
            )}
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Password
            </label>
            <input
              type="password"
              placeholder="••••••••"
              {...register('password')}
              className={`w-full px-4 py-3 bg-slate-950 border rounded-xl text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all ${
                errors.password ? 'border-red-500/50' : 'border-slate-800 focus:border-slate-700'
              }`}
            />
            {errors.password && (
              <p className="mt-1 text-xs text-red-500">{errors.password.message}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 text-white font-semibold rounded-xl transition-all shadow-lg shadow-blue-500/20 flex items-center justify-center"
          >
            {loading ? (
              <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            ) : (
              "Sign In"
            )}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-sm text-slate-400">
            Don't have an account?{' '}
            <Link to="/register" className="text-blue-500 hover:underline">
              Create an account
            </Link>
          </p>
        </div>

        {/* Demo credentials tip */}
        <div className="mt-8 pt-6 border-t border-slate-900/60 text-xs text-slate-400">
          <p className="font-semibold text-slate-300 mb-2">Seeded Demo Credentials:</p>
          <div className="grid grid-cols-2 gap-2 text-slate-400">
            <div>
              <p className="font-medium text-slate-300">Analyst:</p>
              <p>analyst1@fraudsense.com</p>
              <p>password123</p>
            </div>
            <div>
              <p className="font-medium text-slate-300">Merchant:</p>
              <p>merchant1@fraudsense.com</p>
              <p>password123</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
