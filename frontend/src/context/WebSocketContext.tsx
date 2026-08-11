import React, { createContext, useContext, useState, useEffect, useRef } from 'react'
import { useAuth } from './AuthContext'

export interface SimulatedTransaction {
  id: number
  merchant_id: number
  merchant_name: string
  time_offset: number
  amount: number
  status: string
  ingested_at: string
  fraud_score: number
  model_decision: string
  case_id?: number
}

interface WebSocketContextType {
  liveTransactions: SimulatedTransaction[]
  isConnected: boolean
  clearFeed: () => void
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined)

export const WebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, token } = useAuth()
  const [liveTransactions, setLiveTransactions] = useState<SimulatedTransaction[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const socketRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    // Only connect WebSocket if the user is logged in as an analyst or admin
    if (!token || !user || !["analyst", "admin"].includes(user.role)) {
      if (socketRef.current) {
        socketRef.current.close()
      }
      setIsConnected(false)
      return
    }

    const connectWebSocket = () => {
      // Connect to the Live Feed WebSocket
      const wsUrl = `ws://localhost:8000/api/v1/analyst/live-feed`
      console.log(`[WebSocket] Connecting to ${wsUrl}`)
      const ws = new WebSocket(wsUrl)
      socketRef.current = ws

      ws.onopen = () => {
        console.log('[WebSocket] Live Feed connection established.')
        setIsConnected(true)
      }

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data)
          if (payload.event === "transaction_ingested") {
            console.log('[WebSocket] Received transaction:', payload.data)
            setLiveTransactions((prev) => [payload.data, ...prev])
          }
        } catch (err) {
          console.error('[WebSocket] Error parsing socket message:', err)
        }
      }

      ws.onclose = () => {
        console.log('[WebSocket] Connection closed.')
        setIsConnected(false)
        // Auto-reconnect after 3 seconds if the user is still logged in
        if (token) {
          setTimeout(() => {
            if (socketRef.current === null || socketRef.current.readyState === WebSocket.CLOSED) {
              connectWebSocket()
            }
          }, 3000)
        }
      }

      ws.onerror = (err) => {
        console.error('[WebSocket] Error:', err)
        ws.close()
      }
    }

    connectWebSocket()

    return () => {
      if (socketRef.current) {
        socketRef.current.close()
      }
    }
  }, [user, token])

  const clearFeed = () => {
    setLiveTransactions([])
  }

  return (
    <WebSocketContext.Provider value={{ liveTransactions, isConnected, clearFeed }}>
      {children}
    </WebSocketContext.Provider>
  )
}

export const useWebSocket = () => {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider')
  }
  return context
}
