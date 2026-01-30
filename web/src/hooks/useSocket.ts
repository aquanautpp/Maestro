import { useEffect, useRef, useState, useCallback } from 'react'
import { io, Socket } from 'socket.io-client'

export interface SpeechEvent {
  speaker: 'CHI' | 'ADT'
  pitch: number | null
  duration_ms: number
  time: number
}

export interface MomentEvent {
  moments: number
  response_time: number
  time: number
}

export interface StatusEvent {
  listening: boolean
  moments: number
  child_speech: number
  adult_speech: number
  duration_seconds: number
  current_speaker: string | null
}

export function useSocket() {
  const socketRef = useRef<Socket | null>(null)
  const [connected, setConnected] = useState(false)
  const [lastSpeech, setLastSpeech] = useState<SpeechEvent | null>(null)
  const [lastMoment, setLastMoment] = useState<MomentEvent | null>(null)
  const [status, setStatus] = useState<StatusEvent | null>(null)
  const [momentPulse, setMomentPulse] = useState(0)
  const [currentSpeaker, setCurrentSpeaker] = useState<string | null>(null)

  useEffect(() => {
    const socket = io('http://localhost:5000', { transports: ['websocket', 'polling'] })
    socketRef.current = socket

    socket.on('connect', () => setConnected(true))
    socket.on('disconnect', () => setConnected(false))

    socket.on('speech', (data: SpeechEvent) => {
      setLastSpeech(data)
      setCurrentSpeaker(data.speaker)
    })

    socket.on('moment', (data: MomentEvent) => {
      setLastMoment(data)
      setMomentPulse((p) => p + 1)
    })

    socket.on('status', (data: StatusEvent) => {
      setStatus(data)
      setCurrentSpeaker(data.current_speaker)
    })

    socket.on('silence', () => {
      setCurrentSpeaker(null)
    })

    return () => {
      socket.disconnect()
    }
  }, [])

  const disconnect = useCallback(() => {
    socketRef.current?.disconnect()
  }, [])

  return {
    connected,
    lastSpeech,
    lastMoment,
    status,
    momentPulse,
    currentSpeaker,
    disconnect,
  }
}
