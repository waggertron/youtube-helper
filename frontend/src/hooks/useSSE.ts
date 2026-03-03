import { useEffect, useRef } from 'react'

export interface SSEEvent {
  type: string
  operation_id?: number
  status?: string
  progress?: number
  message?: string
  error?: string
}

export function useSSE(onEvent: (event: SSEEvent) => void) {
  const onEventRef = useRef(onEvent)
  onEventRef.current = onEvent
  const sourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    const source = new EventSource('/api/events')
    sourceRef.current = source

    source.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as SSEEvent
        onEventRef.current(data)
      } catch {
        // ignore parse errors
      }
    }

    source.onerror = () => {
      // EventSource auto-reconnects
    }

    return () => {
      source.close()
    }
  }, [])

  return sourceRef
}
