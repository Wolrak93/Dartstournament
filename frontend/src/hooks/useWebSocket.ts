import { useEffect, useRef, useState } from 'react'
import { WS_BASE } from '../api/client'

export interface WsEvent {
  type: string
  data: unknown
}

/**
 * Connects to a WebSocket channel and returns the latest event plus connection
 * state. Automatically reconnects after 3 s on unexpected disconnect.
 *
 * @param channel - 'match' or 'tournament'
 * @param id      - match_id or tournament_id to subscribe to
 */
export function useWebSocket(
  channel: 'match' | 'tournament',
  id: number,
): { lastEvent: WsEvent | null; isConnected: boolean } {
  const [lastEvent, setLastEvent] = useState<WsEvent | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    let cancelled = false

    const connect = () => {
      if (cancelled) return
      const ws = new WebSocket(`${WS_BASE}/ws/${channel}/${id}`)
      wsRef.current = ws

      ws.onopen = () => {
        if (!cancelled) setIsConnected(true)
      }

      ws.onmessage = (ev: MessageEvent<string>) => {
        if (!cancelled) {
          const event = JSON.parse(ev.data) as WsEvent
          setLastEvent(event)
        }
      }

      ws.onclose = () => {
        if (!cancelled) {
          setIsConnected(false)
          reconnectTimer.current = setTimeout(connect, 3000)
        }
      }

      ws.onerror = () => {
        ws.close()
      }
    }

    connect()

    return () => {
      cancelled = true
      if (reconnectTimer.current !== null) clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [channel, id])

  return { lastEvent, isConnected }
}
