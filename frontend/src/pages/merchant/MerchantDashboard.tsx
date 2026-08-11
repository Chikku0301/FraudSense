import React, { useState, useEffect } from 'react'
import api from '../../api'
import { useAuth } from '../../context/AuthContext'
import { Shield, TrendingUp, AlertTriangle, CheckCircle, Info, LogOut } from 'lucide-react'

interface Transaction {
  id: number
  merchant_id: number
  time_offset: number
  amount: number
  status: string
  ingested_at: string
  fraud_score: number | null
  model_decision: string | null
}

interface Stats {
  total_transactions: number
  flagged_count: number
  blocked_amount_saved: number
}

export const MerchantDashboard: React.FC = () => {
  const { user, logout } = useAuth()
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [stats, setStats] = useState<Stats>({
    total_transactions: 0,
    flagged_count: 0,
    blocked_amount_saved: 0.0
  })
  const [selectedTxId, setSelectedTxId] = useState<number | null>(null)
  const [selectedTxDetail, setSelectedTxDetail] = useState<any>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [txsRes, statsRes] = await Promise.all([
          api.get('/merchant/transactions'),
          api.get('/merchant/stats')
        ])
        setTransactions(txsRes.data)
        setStats(statsRes.data)
      } catch (err) {
        console.error('[Merchant] Error loading dashboard data:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const handleRowClick = async (txId: number) => {
    setSelectedTxId(txId)
    setDetailLoading(true)
    try {
      const res = await api.get(`/merchant/transactions/${txId}`)
      setSelectedTxDetail(res.data)
    } catch (err) {
      console.error('[Merchant] Error loading transaction details:', err)
    } finally {
      setDetailLoading(false)
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'cleared':
      case 'confirmed_legit':
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">Cleared</span>
      case 'flagged':
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400">Under Review</span>
      case 'confirmed_fraud':
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-red-500/10 border border-red-500/20 text-red-400">Fraud Blocked</span>
      default:
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-slate-500/10 border border-slate-500/20 text-slate-400">{status}</span>
    }
  }

  const getRiskBadge = (score: number | null) => {
    if (score === null) return <span className="text-slate-400 text-sm font-medium">Low</span>
    if (score >= 70) {
      return <span className="text-red-400 text-sm font-bold">High</span>
    } else if (score >= 30) {
      return <span className="text-amber-400 text-sm font-semibold">Medium</span>
    } else {
      return <span className="text-emerald-400 text-sm font-medium">Low</span>
    }
  }

  return (
    <div className="min-h-screen bg-[#070A13] text-slate-100 flex flex-col font-sans">
      {/* Header bar */}
      <header className="border-b border-slate-800 bg-[#0B0F19]/90 backdrop-blur-md px-6 py-4 flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-600/15 border border-blue-500/30 rounded-xl flex items-center justify-center text-blue-500">
            <Shield className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight">FraudSense</h1>
            <p className="text-xs text-slate-400">Merchant Hub: {user?.merchant_name}</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right hidden sm:block">
            <p className="text-sm font-semibold">{user?.full_name}</p>
            <p className="text-xs text-slate-400 capitalize">{user?.role} Portal</p>
          </div>
          <button 
            onClick={logout}
            className="p-2 text-slate-400 hover:text-slate-200 bg-slate-900 border border-slate-800 rounded-xl hover:bg-slate-800 transition-all"
            title="Log Out"
          >
            <LogOut className="w-5 h-5" />
          </button>
        </div>
      </header>

      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <svg className="animate-spin h-10 w-10 text-blue-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <p className="text-slate-400 text-sm">Syncing secure risk ledgers...</p>
          </div>
        </div>
      ) : (
        <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">
          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="glass-panel p-6 rounded-2xl flex items-center gap-5">
              <div className="w-12 h-12 bg-blue-500/10 border border-blue-500/20 text-blue-400 rounded-xl flex items-center justify-center shadow-inner">
                <TrendingUp className="w-6 h-6" />
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Processed Transactions</p>
                <p className="text-2xl font-bold mt-1">{stats.total_transactions}</p>
              </div>
            </div>

            <div className="glass-panel p-6 rounded-2xl flex items-center gap-5">
              <div className="w-12 h-12 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-xl flex items-center justify-center shadow-inner">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Flagged Under Review</p>
                <p className="text-2xl font-bold mt-1 text-amber-400">{stats.flagged_count}</p>
              </div>
            </div>

            <div className="glass-panel p-6 rounded-2xl flex items-center gap-5">
              <div className="w-12 h-12 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-xl flex items-center justify-center shadow-inner">
                <CheckCircle className="w-6 h-6" />
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Blocked Loss Saved</p>
                <p className="text-2xl font-bold mt-1 text-emerald-400">${stats.blocked_amount_saved.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
              </div>
            </div>
          </div>

          {/* Transactions and side details split */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
            <div className="glass-panel rounded-2xl overflow-hidden lg:col-span-2">
              <div className="px-6 py-4 border-b border-slate-800 bg-slate-900/40">
                <h3 className="font-semibold text-slate-200">Transaction Monitoring History</h3>
                <p className="text-xs text-slate-400 mt-1">Real-time ledger of card operations and automated risk outcomes</p>
              </div>

              <div className="overflow-x-auto max-h-[600px] overflow-y-auto custom-scrollbar">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 text-xs font-semibold text-slate-400 uppercase bg-slate-950/20">
                      <th className="px-6 py-4">Transaction ID</th>
                      <th className="px-6 py-4">Ingested At</th>
                      <th className="px-6 py-4">Amount</th>
                      <th className="px-6 py-4">Risk Category</th>
                      <th className="px-6 py-4">Decision Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {transactions.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="text-center py-12 text-slate-500 text-sm">
                          No transactions found on this account.
                        </td>
                      </tr>
                    ) : (
                      transactions.map((tx) => (
                        <tr 
                          key={tx.id} 
                          onClick={() => handleRowClick(tx.id)}
                          className={`hover:bg-slate-800/30 cursor-pointer transition-colors ${
                            selectedTxId === tx.id ? 'bg-slate-800/45' : ''
                          }`}
                        >
                          <td className="px-6 py-4 font-medium text-slate-300 text-sm">TX-{100000 + tx.id}</td>
                          <td className="px-6 py-4 text-xs text-slate-400">
                            {new Date(tx.ingested_at).toLocaleString()}
                          </td>
                          <td className="px-6 py-4 font-semibold text-sm">${tx.amount.toFixed(2)}</td>
                          <td className="px-6 py-4 text-sm">{getRiskBadge(tx.fraud_score)}</td>
                          <td className="px-6 py-4">{getStatusBadge(tx.status)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Sidebar Details Drawer */}
            <div className="glass-panel p-6 rounded-2xl space-y-6">
              <h3 className="font-semibold text-slate-200 border-b border-slate-800 pb-3 flex items-center gap-2">
                <Info className="w-5 h-5 text-blue-500" />
                Security Risk Details
              </h3>

              {selectedTxId === null ? (
                <div className="text-center py-20 text-slate-500 text-sm space-y-2">
                  <Shield className="w-10 h-10 text-slate-600 mx-auto animate-pulse-slow" />
                  <p>Select any transaction to inspect AI safety evaluations.</p>
                </div>
              ) : detailLoading ? (
                <div className="text-center py-20 text-slate-400 text-sm">
                  <svg className="animate-spin h-8 w-8 text-blue-500 mx-auto mb-3" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <p>Retrieving risk assessments...</p>
                </div>
              ) : selectedTxDetail ? (
                <div className="space-y-6 text-sm">
                  <div className="grid grid-cols-2 gap-y-4 gap-x-2 border-b border-slate-800/60 pb-6">
                    <div>
                      <p className="text-xs text-slate-400">Transaction Reference</p>
                      <p className="font-semibold mt-1">TX-{100000 + selectedTxDetail.id}</p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-400">Amount Processed</p>
                      <p className="font-semibold text-slate-200 mt-1">${selectedTxDetail.amount.toFixed(2)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-400">Ingestion Timestamp</p>
                      <p className="font-semibold text-xs mt-1 text-slate-300">
                        {new Date(selectedTxDetail.ingested_at).toLocaleString()}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-400">AI Risk Rating</p>
                      <div className="mt-1 font-semibold">
                        {selectedTxDetail.risk_level === "High" ? (
                          <span className="text-red-400 font-bold">HIGH RISK</span>
                        ) : selectedTxDetail.risk_level === "Medium" ? (
                          <span className="text-amber-400 font-semibold">MEDIUM RISK</span>
                        ) : (
                          <span className="text-emerald-400 font-medium">LOW RISK</span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="bg-slate-950/60 border border-slate-800/60 p-4 rounded-xl space-y-3">
                    <h4 className="font-semibold text-xs text-slate-300 uppercase tracking-wider">Automated Resolution Summary</h4>
                    <p className="text-slate-400 text-xs leading-relaxed">
                      {selectedTxDetail.status === 'cleared' || selectedTxDetail.status === 'confirmed_legit' ? (
                        "FraudSense AI verified this transaction's fingerprint against known behavioral histories. No suspicious anomalies were found; this ledger is cleared."
                      ) : selectedTxDetail.status === 'flagged' ? (
                        "This transaction was held because of potential pattern misalignment. It is being reviewed by bank security. No merchant actions are required at this stage."
                      ) : (
                        "This card transaction was blocked automatically by our real-time security model. The merchant was saved from chargeback liabilities. Cardholder was notified."
                      )}
                    </p>
                  </div>
                  
                  <div className="text-xs text-slate-500 bg-slate-900/30 p-3 rounded-lg border border-slate-800/40">
                    ℹ️ Sensitive PCA variables (V1-V28) and AI SHAP explainability curves are omitted for data privacy of European cardholders. Only authorised credit analysts can access internal SHAP weight values.
                  </div>
                </div>
              ) : (
                <div className="text-center py-20 text-slate-400">
                  <p>Failed to load transaction data.</p>
                </div>
              )}
            </div>
          </div>
        </main>
      )}
    </div>
  )
}
