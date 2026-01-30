import { useEffect, useState } from 'react'
import { useSocket } from '../hooks/useSocket'
import { useSession } from '../hooks/useSession'
import { MomentCounter } from './MomentCounter'
import { SpeakerIndicator } from './SpeakerIndicator'
import { SessionControls } from './SessionControls'
import { TrendChart } from './TrendChart'
import { CoachingCard } from './CoachingCard'
import { WeeklyTip } from './WeeklyTip'
import { EventTimeline } from './EventTimeline'

export function Dashboard() {
  const socket = useSocket()
  const session = useSession()
  const [moments, setMoments] = useState(0)
  const [events, setEvents] = useState<Array<{ time: number; type: string }>>([])

  // Sync moments from status heartbeat
  useEffect(() => {
    if (socket.status) {
      setMoments(socket.status.moments)
    }
  }, [socket.status])

  // Update moments on moment event
  useEffect(() => {
    if (socket.lastMoment) {
      setMoments(socket.lastMoment.moments)
    }
  }, [socket.lastMoment])

  // Fetch session data periodically to get events
  useEffect(() => {
    if (!session.active) return
    const interval = setInterval(async () => {
      const data = await session.fetchSession()
      if (data?.events) setEvents(data.events)
    }, 3000)
    return () => clearInterval(interval)
  }, [session.active, session.fetchSession])

  // Check if already listening on mount
  useEffect(() => {
    session.fetchSession().then((data) => {
      if (data?.session_id && data.started_at) {
        setMoments(data.moments)
        setEvents(data.events || [])
      }
    })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleStart = async () => {
    await session.startSession()
    setMoments(0)
    setEvents([])
  }

  const handleStop = async () => {
    await session.stopSession()
    // Keep moments and events visible after stopping
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-100 px-4 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-800">Maestro</h1>
            <p className="text-xs text-gray-400">Momentos de conversa</p>
          </div>
          {session.active && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-maestro-green-bg text-maestro-green-dark text-xs font-medium">
              <span className="h-1.5 w-1.5 rounded-full bg-maestro-green animate-pulse" />
              Escutando
            </span>
          )}
        </div>
      </header>

      {/* Main grid */}
      <main className="max-w-4xl mx-auto p-4 space-y-4">
        {/* Top row: Controls + Counter */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <SessionControls
            active={session.active}
            loading={session.loading}
            elapsed={session.elapsed}
            connected={socket.connected}
            onStart={handleStart}
            onStop={handleStop}
          />
          <MomentCounter moments={moments} pulse={socket.momentPulse} />
        </div>

        {/* Middle row: Speaker + Chart */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <SpeakerIndicator speaker={socket.currentSpeaker} />
          <TrendChart events={events} />
        </div>

        {/* Bottom row: Coaching + Weekly + Timeline */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-4">
            <CoachingCard />
            <WeeklyTip />
          </div>
          <EventTimeline events={events} />
        </div>
      </main>

      {/* Footer */}
      <footer className="text-center py-6 text-xs text-gray-300">
        Maestro - Cada conversa importa
      </footer>
    </div>
  )
}
