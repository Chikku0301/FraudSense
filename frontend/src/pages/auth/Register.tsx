import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { Shield, AlertCircle } from 'lucide-react'

const registerSchema = z.object({
  email: z.string().email({ message: "Invalid email address" }),
  password: z.string().min(6, { message: "Password must be at least 6 characters" }),
  fullName: z.string().min(2, { message: "Full name is required" }),
  role: z.string().refine(val => ["merchant", "analyst"].includes(val), {
    message: "Select either Merchant or Analyst role."
  }),
  merchantName: z.string().optional()
}).refine(data => {
  if (data.role === "merchant" && (!data.merchantName || data.merchantName.trim() === "")) {
    return false
  }
  return true
}, {
  message: "Merchant organization name is required.",
  path: ["merchantName"]
})

type RegisterFormValues = z.infer<typeof registerSchema>

export const Register: React.FC = () => {
  const { register: signup } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [selectedRole, setSelectedRole] = useState("merchant")

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      email: '',
      password: '',
      fullName: '',
      role: 'merchant',
      merchantName: ''
    }
  })

  const onSubmit = async (data: RegisterFormValues) => {
    setError(null)
    setLoading(true)
    try {
      await signup(
        data.email,
        data.password,
        data.fullName,
        data.role,
        data.role === "merchant" ? data.merchantName : undefined
      )
      setLoading(false)
      navigate('/')
    } catch (err: any) {
      setLoading(false)
      const errMsg = err.response?.data?.detail || "Registration failed. Try again."
      setError(errMsg)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#070A13] px-4 py-12">
      {/* Background radial glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-blue-500/10 rounded-full blur-[120px] pointer-events-none"></div>

      <div className="w-full max-w-md glass-panel p-8 rounded-2xl shadow-2xl relative z-10">
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 bg-blue-600/20 border border-blue-500/30 rounded-2xl flex items-center justify-center text-blue-500 mb-4 shadow-lg shadow-blue-500/10">
            <Shield className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-bold text-slate-100 font-display">Create Account</h1>
          <p className="text-slate-400 text-sm mt-1">Register for the FraudSense platform</p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-900/20 border border-red-500/30 text-red-400 rounded-xl flex items-start gap-3 text-sm">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Full Name
            </label>
            <input
              type="text"
              placeholder="e.g. Alice Vance"
              {...register('fullName')}
              className={`w-full px-4 py-3 bg-slate-950 border rounded-xl text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all ${
                errors.fullName ? 'border-red-500/50' : 'border-slate-800 focus:border-slate-700'
              }`}
            />
            {errors.fullName && (
              <p className="mt-1 text-xs text-red-500">{errors.fullName.message}</p>
            )}
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Email Address
            </label>
            <input
              type="email"
              placeholder="e.g. alice@example.com"
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

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Account Role / Type
            </label>
            <select
              {...register('role')}
              onChange={(e) => {
                setSelectedRole(e.target.value)
                setValue('role', e.target.value)
              }}
              className="w-full px-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all focus:border-slate-700"
            >
              <option value="merchant">Merchant (View own transactions, sanitized risk labels)</option>
              <option value="analyst">Analyst (Full analytics, cases review, raw explainability)</option>
            </select>
            {errors.role && (
              <p className="mt-1 text-xs text-red-500">{errors.role.message}</p>
            )}
          </div>

          {selectedRole === "merchant" && (
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Merchant Business/Org Name
              </label>
              <input
                type="text"
                placeholder="e.g. Nova Payments Inc"
                {...register('merchantName')}
                className={`w-full px-4 py-3 bg-slate-950 border rounded-xl text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all ${
                  errors.merchantName ? 'border-red-500/50' : 'border-slate-800 focus:border-slate-700'
                }`}
              />
              {errors.merchantName && (
                <p className="mt-1 text-xs text-red-500">{errors.merchantName.message}</p>
              )}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 text-white font-semibold rounded-xl transition-all shadow-lg shadow-blue-500/20 flex items-center justify-center mt-2"
          >
            {loading ? (
              <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            ) : (
              "Sign Up"
            )}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-sm text-slate-400">
            Already have an account?{' '}
            <Link to="/login" className="text-blue-500 hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
