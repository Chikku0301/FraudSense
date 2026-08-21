import React, { useState, useEffect } from 'react'
import api from '../../api'
import { useAuth } from '../../context/AuthContext'
import { useWebSocket } from '../../context/WebSocketContext'
import { 
  Shield, 
  Activity, 
  FolderLock, 
  UploadCloud, 
  BarChart3, 
  Check, 
  X, 
  AlertTriangle, 
  CheckCircle2, 
  TrendingUp, 
  Zap, 
  LogOut,
  Calendar,
  Layers,
  Database
} from 'lucide-react'
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell
} from 'recharts'

export const AnalystDashboard: React.FC = () => {
  const { user, logout } = useAuth()
  const { liveTransactions, isConnected } = useWebSocket()
  
  // Navigation tabs: 'feed' | 'cases' | 'upload' | 'analytics'
  const [activeTab, setActiveTab] = useState<'feed' | 'cases' | 'upload' | 'analytics'>('feed')

  // Shared state
  const [allTransactions, setAllTransactions] = useState<any[]>([])
  const [activeCases, setActiveCases] = useState<any[]>([])
  const [selectedTxId, setSelectedTxId] = useState<number | null>(null)
  const [txDetails, setTxDetails] = useState<any>(null)
  const [loadingDetails, setLoadingDetails] = useState(false)
  const [loadingData, setLoadingData] = useState(true)

  // Simulation state
  const [simulating, setSimulating] = useState(false)

  // Ingestion state
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadLoading, setUploadLoading] = useState(false)
  const [uploadResult, setUploadResult] = useState<any>(null)

  // Resolution inputs
  const [notes, setNotes] = useState('')
  const [resolutionSubmitting, setResolutionSubmitting] = useState(false)

  // Analytics state
  const [analytics, setAnalytics] = useState<any>(null)
  const [loadingAnalytics, setLoadingAnalytics] = useState(true)

  // Load Transactions & Cases
  const fetchData = async () => {
    try {
      const [txsRes, casesRes] = await Promise.all([
        api.get('/analyst/transactions'),
        api.get('/analyst/transactions?status_filter=flagged')
      ])
      setAllTransactions(txsRes.data)
      // Extract case info from flagged items
      setActiveCases(casesRes.data)
    } catch (err) {
      console.error('[Analyst] Error loading transactions/cases', err)
    } finally {
      setLoadingData(false)
    }
  }

  // Load Analytics specifically when analytics tab is clicked
  const fetchAnalytics = async () => {
    setLoadingAnalytics(true)
    try {
      const res = await api.get('/analyst/portfolio/stats')
      setAnalytics(res.data)
    } catch (err) {
      console.error('[Analyst] Error loading analytics', err)
    } finally {
      setLoadingAnalytics(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  useEffect(() => {
    if (activeTab === 'analytics') {
      fetchAnalytics()
    }
  }, [activeTab])

  // Select a transaction to inspect details
  const handleSelectTx = async (txId: number) => {
    setSelectedTxId(txId)
    setLoadingDetails(true)
    setNotes('')
    try {
      const res = await api.get(`/analyst/transactions/${txId}`)
      setTxDetails(res.data)
    } catch (err) {
      console.error('[Analyst] Error fetching details:', err)
    } finally {
      setLoadingDetails(false)
    }
  }

  // Simulate a transaction
  const triggerSimulation = async () => {
    setSimulating(true)
    try {
      await api.post('/analyst/simulate-live')
      // Refresh transactions ledger
      await fetchData()
    } catch (err) {
      console.error('[Analyst] Error simulating transaction', err)
    } finally {
      setSimulating(false)
    }
  }

  // Resolve a Case
  const handleResolveCase = async (caseId: number, resolution: 'fraud_confirmed' | 'false_positive') => {
    setResolutionSubmitting(true)
    try {
      await api.post(`/analyst/cases/${caseId}/resolve`, {
        resolution,
        notes: notes.trim() ? notes : undefined
      })
      // Refresh details and transaction list
      if (selectedTxId) {
        await handleSelectTx(selectedTxId)
      }
      await fetchData()
      setNotes('')
      // If we are looking at analytics, refresh it too
      if (activeTab === 'analytics') {
        await fetchAnalytics()
      }
    } catch (err) {
      console.error('[Analyst] Error resolving case', err)
    } finally {
      setResolutionSubmitting(false)
    }
  }

  // Handle CSV batch upload
  const handleBatchUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!uploadFile) return

    setUploadLoading(true)
    setUploadProgress(10)
    setUploadResult(null)
    
    const formData = new FormData()
    formData.append('file', uploadFile)

    try {
      // Simulate progress bar movement
      const interval = setInterval(() => {
        setUploadProgress((prev) => (prev < 90 ? prev + 15 : prev))
      }, 300)

      const res = await api.post('/analyst/ingest/batch', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      clearInterval(interval)
      setUploadProgress(100)
      setUploadResult(res.data)
      setUploadFile(null)
      await fetchData()
    } catch (err: any) {
      console.error('[Analyst] Batch upload failed', err)
      alert(err.response?.data?.detail || 'CSV Ingestion failed. Check columns.')
    } finally {
      setUploadLoading(false)
    }
  }

  // Helper styles
  const getDecisionStyles = (decision: string) => {
    switch (decision) {
      case 'clear':
        return { text: 'Clear', badge: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' }
      case 'flag_for_review':
        return { text: 'Review', badge: 'bg-amber-500/10 border-amber-500/20 text-amber-400' }
      case 'block':
        return { text: 'Block', badge: 'bg-red-500/10 border-red-500/20 text-red-400' }
      default:
        return { text: decision, badge: 'bg-slate-500/10 border-slate-500/20 text-slate-400' }
    }
  }

  return (
    <div className="min-h-screen bg-[#070A13] text-slate-100 flex flex-col md:flex-row font-sans">
      
      {/* SIDEBAR */}
      <aside className="w-full md:w-64 bg-[#0B0F19] border-r border-slate-800 flex flex-col justify-between p-6 shrink-0">
        <div className="space-y-8">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-600/15 border border-blue-500/30 rounded-xl flex items-center justify-center text-blue-500 shadow-md">
              <Shield className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">FraudSense</h1>
              <span className="text-[10px] uppercase font-semibold tracking-widest text-blue-500">AI Risk System</span>
            </div>
          </div>

          {/* Connection status */}
          <div className="flex items-center gap-2 px-3 py-2 bg-slate-950/45 rounded-xl border border-slate-900">
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`}></span>
            <span className="text-xs font-medium text-slate-300">
              {isConnected ? 'Live WS Feed Linked' : 'WS Reconnecting...'}
            </span>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-1.5">
            <button
              onClick={() => setActiveTab('feed')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all text-left ${
                activeTab === 'feed'
                  ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/15'
                  : 'text-slate-400 hover:bg-slate-800/40 hover:text-slate-200'
              }`}
            >
              <Activity className="w-5 h-5" />
              Live Operations
              {liveTransactions.length > 0 && (
                <span className="ml-auto bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                  {liveTransactions.length}
                </span>
              )}
            </button>

            <button
              onClick={() => {
                setActiveTab('cases');
                // Auto-inspect first case if available
                if (activeCases.length > 0 && !selectedTxId) {
                  handleSelectTx(activeCases[0].id)
                }
              }}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all text-left ${
                activeTab === 'cases'
                  ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/15'
                  : 'text-slate-400 hover:bg-slate-800/40 hover:text-slate-200'
              }`}
            >
              <FolderLock className="w-5 h-5" />
              Cases Review
              {activeCases.length > 0 && (
                <span className="ml-auto bg-amber-500/20 text-amber-400 text-xs font-semibold px-2 py-0.5 rounded-lg border border-amber-500/20">
                  {activeCases.length}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('upload')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all text-left ${
                activeTab === 'upload'
                  ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/15'
                  : 'text-slate-400 hover:bg-slate-800/40 hover:text-slate-200'
              }`}
            >
              <UploadCloud className="w-5 h-5" />
              Ingest Batch
            </button>

            <button
              onClick={() => setActiveTab('analytics')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all text-left ${
                activeTab === 'analytics'
                  ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/15'
                  : 'text-slate-400 hover:bg-slate-800/40 hover:text-slate-200'
              }`}
            >
              <BarChart3 className="w-5 h-5" />
              Portfolio Analytics
            </button>
          </nav>
        </div>

        {/* User Card & Logout */}
        <div className="pt-6 border-t border-slate-800 space-y-4">
          <div className="flex flex-col">
            <span className="text-sm font-bold text-slate-200">{user?.full_name}</span>
            <span className="text-xs text-slate-400 capitalize">{user?.role} Profile</span>
          </div>
          <button
            onClick={logout}
            className="w-full flex items-center justify-between px-4 py-2.5 bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-400 hover:text-slate-200 rounded-xl transition-all text-xs font-semibold"
          >
            Sign Out
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </aside>

      {/* MAIN VIEW AREA */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        
        {/* --- VIEW 1: LIVE OPERATIONS (FEED + LEDGER) --- */}
        {activeTab === 'feed' && (
          <div className="flex-1 flex flex-col lg:flex-row items-stretch">
            
            {/* Live Feed Feed List */}
            <div className="flex-1 p-6 flex flex-col space-y-6">
              
              {/* Header block with Simulation CTA */}
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-900 pb-6">
                <div>
                  <h2 className="text-xl font-bold font-display">Real-Time Transaction Stream</h2>
                  <p className="text-xs text-slate-400 mt-1">Live payments pipeline scored by FraudSense models</p>
                </div>

                <button
                  onClick={triggerSimulation}
                  disabled={simulating}
                  className="px-5 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 text-white rounded-xl text-sm font-semibold transition-all shadow-lg shadow-blue-500/15 flex items-center justify-center gap-2 self-start sm:self-center"
                >
                  {simulating ? (
                    <>
                      <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      Simulating payment...
                    </>
                  ) : (
                    <>
                      <Zap className="w-4 h-4 fill-current text-yellow-300 animate-pulse" />
                      Simulate Live Transaction
                    </>
                  )}
                </button>
              </div>

              {/* Live WebSocket Event Stream Box */}
              {liveTransactions.length > 0 && (
                <div className="space-y-3">
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-ping"></span>
                    Recent Live Simulations ({liveTransactions.length})
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {liveTransactions.map((tx) => {
                      const dec = getDecisionStyles(tx.model_decision)
                      return (
                        <div 
                          key={tx.id}
                          onClick={() => handleSelectTx(tx.id)}
                          className="glass-panel p-4 rounded-xl border-l-4 border-l-blue-500 flex flex-col justify-between hover:border-l-blue-400 cursor-pointer glass-panel-hover transition-all"
                        >
                          <div className="flex justify-between items-start">
                            <div>
                              <p className="text-xs font-bold text-slate-400">TX-{100000 + tx.id}</p>
                              <p className="text-[10px] text-slate-500 mt-0.5">{tx.merchant_name}</p>
                            </div>
                            <span className={`px-2 py-0.5 text-[10px] font-bold rounded-md border ${dec.badge}`}>
                              {dec.text} ({tx.fraud_score}%)
                            </span>
                          </div>
                          <div className="flex justify-between items-end mt-4">
                            <p className="text-lg font-bold">${tx.amount.toFixed(2)}</p>
                            <span className="text-[10px] text-slate-500">
                              {new Date(tx.ingested_at).toLocaleTimeString()}
                            </span>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}

              {/* Base Transactions Ledger */}
              <div className="glass-panel rounded-2xl overflow-hidden flex-1 flex flex-col">
                <div className="px-6 py-4 border-b border-slate-800 bg-slate-900/35 flex items-center justify-between">
                  <h3 className="font-semibold text-slate-200">Historical Ingestion History</h3>
                  <span className="text-xs text-slate-400">{allTransactions.length} txs total</span>
                </div>
                
                <div className="overflow-x-auto overflow-y-auto max-h-[500px] flex-1 custom-scrollbar">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-slate-800 text-xs font-semibold text-slate-400 uppercase bg-slate-950/20">
                        <th className="px-6 py-4">Transaction ID</th>
                        <th className="px-6 py-4">Ingested At</th>
                        <th className="px-6 py-4">Amount</th>
                        <th className="px-6 py-4">Score</th>
                        <th className="px-6 py-4">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/50">
                      {loadingData ? (
                        <tr>
                          <td colSpan={5} className="text-center py-8 text-slate-500 text-xs">
                            Syncing ledgers...
                          </td>
                        </tr>
                      ) : allTransactions.length === 0 ? (
                        <tr>
                          <td colSpan={5} className="text-center py-12 text-slate-500 text-sm">
                            No transactions ingested. Click "Simulate Live" above or upload a batch CSV.
                          </td>
                        </tr>
                      ) : (
                        allTransactions.map((tx) => {
                          const dec = getDecisionStyles(tx.model_decision || 'clear')
                          return (
                            <tr
                              key={tx.id}
                              onClick={() => handleSelectTx(tx.id)}
                              className={`hover:bg-slate-800/20 cursor-pointer transition-colors ${
                                selectedTxId === tx.id ? 'bg-slate-800/40' : ''
                              }`}
                            >
                              <td className="px-6 py-3.5 font-medium text-slate-300 text-sm">TX-{100000 + tx.id}</td>
                              <td className="px-6 py-3.5 text-xs text-slate-400">
                                {new Date(tx.ingested_at).toLocaleString()}
                              </td>
                              <td className="px-6 py-3.5 font-bold text-sm">${tx.amount.toFixed(2)}</td>
                              <td className="px-6 py-3.5">
                                <span className={`text-xs font-semibold ${
                                  tx.fraud_score >= 70 ? 'text-red-400' : tx.fraud_score >= 30 ? 'text-amber-400' : 'text-emerald-400'
                                }`}>
                                  {tx.fraud_score !== null ? `${tx.fraud_score}%` : 'N/A'}
                                </span>
                              </td>
                              <td className="px-6 py-3.5">
                                <span className={`px-2 py-0.5 text-[10px] font-bold rounded-md border ${dec.badge}`}>
                                  {dec.text}
                                </span>
                              </td>
                            </tr>
                          )
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* Live Inspector Panel */}
            <div className="w-full lg:w-96 bg-[#0B0F19]/40 border-t lg:border-t-0 lg:border-l border-slate-800 p-6 flex flex-col justify-start shrink-0">
              <InspectorSubPanel 
                selectedTxId={selectedTxId} 
                txDetails={txDetails} 
                loadingDetails={loadingDetails}
                notes={notes}
                setNotes={setNotes}
                submitting={resolutionSubmitting}
                onResolve={handleResolveCase}
              />
            </div>
          </div>
        )}

        {/* --- VIEW 2: CASES REVIEW --- */}
        {activeTab === 'cases' && (
          <div className="flex-1 flex flex-col lg:flex-row items-stretch">
            
            {/* Open Cases List */}
            <div className="flex-1 p-6 flex flex-col space-y-6">
              <div>
                <h2 className="text-xl font-bold font-display">Investigation Cases</h2>
                <p className="text-xs text-slate-400 mt-1">Review flagged payments requiring analyst feedback or manual block resolutions</p>
              </div>

              <div className="glass-panel rounded-2xl overflow-hidden flex-1">
                <div className="px-6 py-4 border-b border-slate-800 bg-slate-900/35">
                  <h3 className="font-semibold text-slate-200">Active Pipeline Cases ({activeCases.length})</h3>
                </div>

                <div className="overflow-x-auto overflow-y-auto max-h-[600px] custom-scrollbar">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-slate-800 text-xs font-semibold text-slate-400 uppercase bg-slate-950/20">
                        <th className="px-6 py-4">Case Ref</th>
                        <th className="px-6 py-4">Date Flagged</th>
                        <th className="px-6 py-4">Transaction Amount</th>
                        <th className="px-6 py-4">Threat Score</th>
                        <th className="px-6 py-4">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/40">
                      {activeCases.length === 0 ? (
                        <tr>
                          <td colSpan={5} className="text-center py-16 text-slate-500 text-sm">
                            🎉 No open pipeline cases. Excellent model health!
                          </td>
                        </tr>
                      ) : (
                        activeCases.map((tx) => (
                          <tr
                            key={tx.id}
                            onClick={() => handleSelectTx(tx.id)}
                            className={`hover:bg-slate-800/20 cursor-pointer transition-colors ${
                              selectedTxId === tx.id ? 'bg-slate-800/40' : ''
                            }`}
                          >
                            <td className="px-6 py-4 font-semibold text-sm text-slate-300">TX-{100000 + tx.id}</td>
                            <td className="px-6 py-4 text-xs text-slate-400">
                              {new Date(tx.ingested_at).toLocaleString()}
                            </td>
                            <td className="px-6 py-4 font-bold text-sm">${tx.amount.toFixed(2)}</td>
                            <td className="px-6 py-4 text-sm font-semibold text-amber-400">
                              {tx.fraud_score}%
                            </td>
                            <td className="px-6 py-4">
                              <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-amber-500/10 border border-amber-500/20 text-amber-400">
                                Open review
                              </span>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* Cases Inspector Panel */}
            <div className="w-full lg:w-96 bg-[#0B0F19]/40 border-t lg:border-t-0 lg:border-l border-slate-800 p-6 flex flex-col justify-start shrink-0">
              <InspectorSubPanel 
                selectedTxId={selectedTxId} 
                txDetails={txDetails} 
                loadingDetails={loadingDetails}
                notes={notes}
                setNotes={setNotes}
                submitting={resolutionSubmitting}
                onResolve={handleResolveCase}
              />
            </div>
          </div>
        )}

        {/* --- VIEW 3: BATCH UPLOAD --- */}
        {activeTab === 'upload' && (
          <div className="p-6 max-w-4xl w-full mx-auto space-y-6">
            <div>
              <h2 className="text-xl font-bold font-display">Partner Ingestion Port</h2>
              <p className="text-xs text-slate-400 mt-1">Ingest batch transactions from partner card networks or upload CSV files from incoming pools</p>
            </div>

            <div className="glass-panel p-8 rounded-2xl border border-slate-800/80 space-y-8">
              <div className="flex flex-col items-center justify-center p-8 bg-slate-950/40 border border-dashed border-slate-800 rounded-xl text-center space-y-4">
                <div className="w-14 h-14 bg-slate-900 border border-slate-800 rounded-2xl flex items-center justify-center text-slate-400 shadow-md">
                  <UploadCloud className="w-8 h-8" />
                </div>
                <div>
                  <p className="font-semibold text-slate-200">Upload Transaction Batch File</p>
                  <p className="text-xs text-slate-500 mt-1">Supports CSV tables matching creditcard.csv columns</p>
                </div>

                <form onSubmit={handleBatchUpload} className="w-full max-w-xs space-y-4">
                  <input
                    type="file"
                    accept=".csv"
                    onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                    className="block w-full text-xs text-slate-400 file:mr-4 file:py-2.5 file:px-4 file:rounded-xl file:border file:border-slate-800 file:text-xs file:font-semibold file:bg-slate-900 file:text-slate-300 hover:file:bg-slate-800 cursor-pointer"
                  />
                  
                  <button
                    type="submit"
                    disabled={!uploadFile || uploadLoading}
                    className="w-full py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 text-white rounded-xl text-xs font-bold transition-all shadow-md shadow-blue-500/10 flex items-center justify-center gap-2"
                  >
                    {uploadLoading ? "Analyzing Fingerprints..." : "Upload & Score Batch"}
                  </button>
                </form>
              </div>

              {uploadLoading && (
                <div className="space-y-2">
                  <div className="flex justify-between text-xs font-semibold text-slate-400">
                    <span>Batch scoring pipeline active...</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <div className="w-full bg-slate-950 rounded-full h-2">
                    <div 
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    ></div>
                  </div>
                </div>
              )}

              {uploadResult && (
                <div className="bg-slate-950/50 border border-slate-800 rounded-xl p-6 space-y-4">
                  <h4 className="font-semibold text-sm text-slate-200 flex items-center gap-2">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    Ingestion Pipeline Outcomes
                  </h4>
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div className="bg-slate-900/60 p-4 rounded-lg border border-slate-800/40">
                      <p className="text-2xl font-bold text-slate-200">{uploadResult.message.match(/\d+/)?.[0] || 0}</p>
                      <p className="text-[10px] text-slate-400 uppercase tracking-widest mt-1">Processed</p>
                    </div>
                    <div className="bg-slate-900/60 p-4 rounded-lg border border-slate-800/40">
                      <p className="text-2xl font-bold text-amber-400">{uploadResult.flagged}</p>
                      <p className="text-[10px] text-slate-400 uppercase tracking-widest mt-1">Flagged Review</p>
                    </div>
                    <div className="bg-slate-900/60 p-4 rounded-lg border border-slate-800/40">
                      <p className="text-2xl font-bold text-red-400">{uploadResult.blocked}</p>
                      <p className="text-[10px] text-slate-400 uppercase tracking-widest mt-1">Blocked Loss</p>
                    </div>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed pt-2">
                    All processed payments have been catalogued and risk assessments generated with complete SHAP explanations for top-contributing features. Fraud rates and score distributions have updated in Portfolio Analytics.
                  </p>
                </div>
              )}
            </div>
            
            {/* Guide to get a file */}
            <div className="glass-panel p-6 rounded-2xl border border-slate-800/50 space-y-3">
              <h4 className="font-semibold text-sm text-slate-300 flex items-center gap-2">
                <Database className="w-5 h-5 text-blue-500" />
                Where is the incoming pool data?
              </h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                The splitting step created the live simulation dataset at:
                <code className="bg-slate-950 border border-slate-900 px-1.5 py-0.5 rounded text-blue-400 ml-1">
                  backend/models_store/incoming_pool.csv
                </code>
              </p>
              <p className="text-xs text-slate-400 leading-relaxed">
                You can copy a few rows from that file to a new CSV (including headers) to simulate bank processing batch uploads!
              </p>
            </div>
          </div>
        )}

        {/* --- VIEW 4: PORTFOLIO ANALYTICS --- */}
        {activeTab === 'analytics' && (
          <div className="p-6 max-w-7xl w-full mx-auto space-y-6">
            <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4">
              <div>
                <h2 className="text-xl font-bold font-display">System Portfolio & Performance</h2>
                <p className="text-xs text-slate-400 mt-1">Human feedback loops compared against ML automated decisions</p>
              </div>
              
              <button 
                onClick={fetchAnalytics}
                className="px-4 py-2 bg-slate-900 border border-slate-800 text-slate-300 text-xs font-semibold rounded-xl hover:bg-slate-800 hover:text-white transition-all flex items-center gap-1.5"
              >
                Sync Metrics
              </button>
            </div>

            {loadingAnalytics || !analytics ? (
              <div className="py-32 text-center text-slate-400 text-sm">
                <svg className="animate-spin h-8 w-8 text-blue-500 mx-auto mb-3" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                <p>Computing live system precision & recall coefficients...</p>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Analytics Stats Row */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                  <div className="glass-panel p-5 rounded-2xl flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Active Flagged Volume</p>
                      <p className="text-2xl font-bold text-slate-200 mt-1">${analytics.total_flagged_volume.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
                    </div>
                    <div className="w-10 h-10 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-lg flex items-center justify-center">
                      <AlertTriangle className="w-5 h-5" />
                    </div>
                  </div>

                  <div className="glass-panel p-5 rounded-2xl flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Model Precision</p>
                      <p className="text-2xl font-bold text-slate-200 mt-1">{(analytics.model_precision * 100).toFixed(1)}%</p>
                    </div>
                    <div className="w-10 h-10 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg flex items-center justify-center">
                      <CheckCircle2 className="w-5 h-5" />
                    </div>
                  </div>

                  <div className="glass-panel p-5 rounded-2xl flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Model Recall</p>
                      <p className="text-2xl font-bold text-slate-200 mt-1">{(analytics.model_recall * 100).toFixed(1)}%</p>
                    </div>
                    <div className="w-10 h-10 bg-blue-500/10 border border-blue-500/20 text-blue-400 rounded-lg flex items-center justify-center">
                      <TrendingUp className="w-5 h-5" />
                    </div>
                  </div>

                  <div className="glass-panel p-5 rounded-2xl flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">System F1-Score</p>
                      <p className="text-2xl font-bold text-slate-200 mt-1">
                        {((2 * analytics.model_precision * analytics.model_recall) / (analytics.model_precision + analytics.model_recall || 1) * 100).toFixed(1)}%
                      </p>
                    </div>
                    <div className="w-10 h-10 bg-purple-500/10 border border-purple-500/20 text-purple-400 rounded-lg flex items-center justify-center">
                      <Layers className="w-5 h-5" />
                    </div>
                  </div>
                </div>

                {/* Graphs Section */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Fraud Rate Trend */}
                  <div className="glass-panel p-6 rounded-2xl space-y-4">
                    <div>
                      <h3 className="font-semibold text-slate-200">Model Fraud Detection Rate Trend</h3>
                      <p className="text-xs text-slate-500 mt-0.5">Ratio of fraud cases flagged over daily transaction totals</p>
                    </div>
                    
                    <div className="h-[280px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={analytics.fraud_rate_trend}>
                          <defs>
                            <linearGradient id="colorRate" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.2}/>
                              <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
                          <XAxis dataKey="date" stroke="#64748B" fontSize={10} tickLine={false} />
                          <YAxis 
                            stroke="#64748B" 
                            fontSize={10} 
                            tickLine={false} 
                            tickFormatter={(v) => `${(v * 100).toFixed(1)}%`}
                          />
                          <Tooltip 
                            contentStyle={{ backgroundColor: '#0F172A', border: '1px solid #334155', borderRadius: '12px' }}
                            labelStyle={{ color: '#F1F5F9', fontWeight: 'bold' }}
                            formatter={(v: any) => [`${(v * 100).toFixed(2)}%`, 'Fraud Detection Rate']}
                          />
                          <Area type="monotone" dataKey="rate" stroke="#ef4444" strokeWidth={2} fillOpacity={1} fill="url(#colorRate)" />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Score Distribution */}
                  <div className="glass-panel p-6 rounded-2xl space-y-4">
                    <div>
                      <h3 className="font-semibold text-slate-200">Fingerprint Fraud Score Distribution</h3>
                      <p className="text-xs text-slate-500 mt-0.5">Count of payments bucketed by composite risk probability scores</p>
                    </div>
                    
                    <div className="h-[280px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={analytics.score_distribution}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
                          <XAxis dataKey="bucket" stroke="#64748B" fontSize={10} tickLine={false} />
                          <YAxis stroke="#64748B" fontSize={10} tickLine={false} />
                          <Tooltip 
                            contentStyle={{ backgroundColor: '#0F172A', border: '1px solid #334155', borderRadius: '12px' }}
                            labelStyle={{ color: '#F1F5F9', fontWeight: 'bold' }}
                            formatter={(v: any) => [v, 'Transactions']}
                          />
                          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                            {analytics.score_distribution.map((entry: any, index: number) => {
                              // color code buckets based on risk thresholds: >=70 (red), 30-70 (amber), <30 (green)
                              const limit = parseInt(entry.bucket.split('-')[0])
                              let fill = '#10b981'
                              if (limit >= 70) fill = '#ef4444'
                              else if (limit >= 30) fill = '#f59e0b'
                              return <Cell key={`cell-${index}`} fill={fill} />
                            })}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>

                <div className="glass-panel p-6 rounded-2xl flex flex-col md:flex-row items-center gap-6">
                  <div className="w-12 h-12 bg-blue-500/10 border border-blue-500/20 text-blue-400 rounded-xl flex items-center justify-center shrink-0 shadow-inner">
                    <Calendar className="w-6 h-6" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-slate-200 text-sm">Human-in-the-Loop Performance Calibration</h4>
                    <p className="text-xs text-slate-400 leading-relaxed mt-1">
                      Model precision is calculated dynamically using cases resolved by credit analysts (TP / [TP+FP] resolutions). Recall metrics are calculated utilizing true labels of the incoming pool, tracing the ratio of correctly flagged items against total actual frauds (TP / [TP+FN]). Use Case Resolution to calibrate weights.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}

// INSPECTOR SUB-PANEL COMPONENT (REUSABLE DETAILED SIDE DRAWER)
interface InspectorProps {
  selectedTxId: number | null
  txDetails: any
  loadingDetails: boolean
  notes: string
  setNotes: (v: string) => void
  submitting: boolean
  onResolve: (caseId: number, resolution: 'fraud_confirmed' | 'false_positive') => Promise<void>
}

const InspectorSubPanel: React.FC<InspectorProps> = ({
  selectedTxId,
  txDetails,
  loadingDetails,
  notes,
  setNotes,
  submitting,
  onResolve
}) => {
  if (selectedTxId === null) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center text-slate-500 py-32">
        <Shield className="w-12 h-12 text-slate-700 mb-3 animate-pulse-slow" />
        <p className="text-sm font-semibold">Risk Investigator</p>
        <p className="text-xs text-slate-600 mt-1 max-w-[200px]">Select a transaction row to pull ML explains and case logs</p>
      </div>
    )
  }

  if (loadingDetails) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center text-slate-400 py-32">
        <svg className="animate-spin h-8 w-8 text-blue-500 mb-3" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
        <p className="text-xs">Computing feature explanations...</p>
      </div>
    )
  }

  if (!txDetails) {
    return (
      <div className="py-20 text-center text-slate-400">
        <p>Could not fetch details.</p>
      </div>
    )
  }

  const assessment = txDetails.fraud_assessment
  const hasCase = txDetails.case
  const maxShap = assessment ? Math.max(...assessment.shap_explanation.map((s: any) => Math.abs(s.shap_contribution)), 0.1) : 1

  return (
    <div className="space-y-6 flex-1 flex flex-col justify-start">
      
      {/* Basic Tx Header Info */}
      <div className="border-b border-slate-800/80 pb-4">
        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest bg-slate-900 border border-slate-800 px-2 py-0.5 rounded">
          Reference: TX-{100000 + txDetails.id}
        </span>
        <div className="flex justify-between items-end mt-3">
          <p className="text-2xl font-bold">${txDetails.amount.toFixed(2)}</p>
          <span className="text-xs text-slate-400">Time offset: {txDetails.time_offset.toFixed(1)}s</span>
        </div>
        <p className="text-[10px] text-slate-500 mt-1">Ingested: {new Date(txDetails.ingested_at).toLocaleString()}</p>
      </div>

      {/* Model Decision Block */}
      {assessment ? (
        <div className="bg-slate-950/60 border border-slate-800/70 p-4 rounded-xl space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Model Decision</span>
            <span className={`px-2 py-0.5 text-[10px] font-bold rounded border ${
              assessment.model_decision === 'clear' 
                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' 
                : assessment.model_decision === 'flag_for_review'
                ? 'bg-amber-500/10 border-amber-500/20 text-amber-400'
                : 'bg-red-500/10 border-red-500/20 text-red-400'
            }`}>
              {assessment.model_decision.replace(/_/g, ' ').toUpperCase()}
            </span>
          </div>

          <div className="flex justify-between items-baseline pt-1">
            <span className="text-xs text-slate-400">Calculated Fraud Probability</span>
            <span className="text-lg font-bold text-slate-200">
              {assessment.fraud_score}%
            </span>
          </div>
          
          <div className="w-full bg-slate-900 rounded-full h-1.5 mt-2">
            <div 
              className={`h-1.5 rounded-full ${
                assessment.fraud_score >= 70 ? 'bg-red-500' : assessment.fraud_score >= 30 ? 'bg-amber-500' : 'bg-emerald-500'
              }`}
              style={{ width: `${assessment.fraud_score}%` }}
            ></div>
          </div>
        </div>
      ) : (
        <div className="bg-slate-950 border border-slate-900 p-4 rounded-xl text-center text-slate-500 text-xs">
          No automated assessment attached.
        </div>
      )}

      {/* SHAP Explanation Horizontal Bar Chart */}
      {assessment && (
        <div className="space-y-3.5">
          <div>
            <h4 className="font-semibold text-xs text-slate-300 uppercase tracking-wider">Explainability Breakdown (SHAP)</h4>
            <p className="text-[10px] text-slate-500 mt-0.5">Top 6 variables contributing to log-odds of risk rating</p>
          </div>

          <div className="space-y-3">
            {assessment.shap_explanation.map((item: any, idx: number) => {
              const widthPct = Math.min((Math.abs(item.shap_contribution) / maxShap) * 100, 100)
              const isPositive = item.shap_contribution >= 0
              return (
                <div key={idx} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-300 font-medium truncate max-w-[170px]" title={item.feature}>
                      {item.feature}
                    </span>
                    <span className="text-slate-500 font-mono text-[10px]">
                      val={item.value > 1000 ? item.value.toFixed(0) : item.value.toFixed(3)}
                    </span>
                  </div>
                  
                  {/* Custom horizontal SHAP scale bar */}
                  <div className="flex items-center w-full h-2.5 bg-slate-950 rounded-full relative overflow-hidden border border-slate-900">
                    <div className="absolute left-1/2 w-[1px] h-full bg-slate-800 z-10"></div>
                    {isPositive ? (
                      <div 
                        className="absolute left-1/2 h-full bg-red-500/80 rounded-r"
                        style={{ width: `${widthPct / 2}%` }}
                      ></div>
                    ) : (
                      <div 
                        className="absolute right-1/2 h-full bg-emerald-500/80 rounded-l"
                        style={{ width: `${widthPct / 2}%` }}
                      ></div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          <div className="flex justify-between text-[8px] text-slate-500 font-mono pt-1">
            <span>← Decreases Risk</span>
            <span>Increases Risk →</span>
          </div>
        </div>
      )}

      {/* Case Resolution Actions block */}
      {hasCase && (
        <div className="border-t border-slate-800/80 pt-5 space-y-4">
          <div>
            <h4 className="font-semibold text-xs text-slate-300 uppercase tracking-wider">Manual Investigation Review</h4>
            <p className="text-[10px] text-slate-500 mt-0.5">Determine case resolution and update security databases</p>
          </div>

          {hasCase.status === 'resolved' ? (
            <div className="bg-slate-950/40 border border-slate-800 p-4 rounded-xl space-y-2 text-xs">
              <div className="flex justify-between text-slate-400">
                <span>Case Status</span>
                <span className="font-bold text-slate-200">RESOLVED</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Resolution Decision</span>
                <span className={`font-bold ${hasCase.resolution === 'fraud_confirmed' ? 'text-red-400' : 'text-emerald-400'}`}>
                  {hasCase.resolution === 'fraud_confirmed' ? 'Fraud Confirmed' : 'False Positive'}
                </span>
              </div>
              {hasCase.notes && (
                <div className="mt-2 pt-2 border-t border-slate-900 text-slate-400 leading-relaxed">
                  <span className="font-semibold text-slate-300">Notes:</span> {hasCase.notes}
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-3.5">
              <textarea
                placeholder="Enter investigation notes (e.g. Cardholder confirmed block, pattern verification...)"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-850 rounded-xl text-slate-300 focus:outline-none focus:ring-1 focus:ring-blue-500 text-xs resize-none"
              />
              
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => onResolve(hasCase.id, 'false_positive')}
                  disabled={submitting}
                  className="py-2.5 bg-slate-900 hover:bg-slate-800 disabled:bg-slate-950 border border-slate-850 text-slate-300 hover:text-white rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all"
                >
                  <X className="w-3.5 h-3.5 text-slate-400" />
                  False Positive
                </button>
                <button
                  type="button"
                  onClick={() => onResolve(hasCase.id, 'fraud_confirmed')}
                  disabled={submitting}
                  className="py-2.5 bg-red-600 hover:bg-red-500 disabled:bg-red-900 text-white rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all shadow-md shadow-red-600/10"
                >
                  <Check className="w-3.5 h-3.5 text-red-200" />
                  Confirm Fraud
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
