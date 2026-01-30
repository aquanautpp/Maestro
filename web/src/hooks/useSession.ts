import { useState, useCallback, useRef, useEffect } from 'react'

export interface SessionData {
  session_id: string | null
  started_at: string | null
  duration_minutes: number
  moments: number
  child_speech: number
  adult_speech: number
  moments_per_hour: number
  events: Array<{
    time: number
    type: string
    speaker?: string
    pitch?: number
    response_time?: number
    note?: string
  }>
}

export function useSession() {
  const [active, setActive] = useState(false)
  const [loading, setLoading] = useState(false)
  const [sessionData, setSessionData] = useState<SessionData | null>(null)
  const [elapsed, setElapsed] = useState(0)
  const startTimeRef = useRef<number | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const startSession = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/start', { method: 'POST' })
      const data = await res.json()
      if (data.session_id) {
        setActive(true)
        startTimeRef.current = Date.now()
        setElapsed(0)
      }
    } finally {
      setLoading(false)
    }
  }, [])

  const stopSession = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/stop', { method: 'POST' })
      const data = await res.json()
      setActive(false)
      startTimeRef.current = null
      setElapsed(0)
      return data
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchSession = useCallback(async () => {
    try {
      const res = await fetch('/api/session')
      const data: SessionData = await res.json()
      setSessionData(data)
      if (data.session_id && data.started_at) {
        setActive(true)
      }
      return data
    } catch {
      return null
    }
  }, [])

  // Timer for elapsed seconds
  useEffect(() => {
    if (active) {
      if (!startTimeRef.current) startTimeRef.current = Date.now()
      timerRef.current = setInterval(() => {
        if (startTimeRef.current) {
          setElapsed(Math.floor((Date.now() - startTimeRef.current) / 1000))
        }
      }, 1000)
    } else {
      if (timerRef.current) clearInterval(timerRef.current)
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [active])

  return {
    active,
    loading,
    sessionData,
    elapsed,
    startSession,
    stopSession,
    fetchSession,
  }
}
