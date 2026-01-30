interface EventItem {
  time: number
  type: string
  speaker?: string
  pitch?: number
  response_time?: number
  note?: string
}

interface Props {
  events: EventItem[]
}

const typeConfig: Record<string, { label: string; color: string }> = {
  moment: { label: 'Momento!', color: 'text-maestro-green-dark bg-maestro-green-bg' },
  child: { label: 'Crianca', color: 'text-blue-700 bg-blue-50' },
  adult: { label: 'Adulto', color: 'text-orange-700 bg-orange-50' },
  sound: { label: 'Som', color: 'text-gray-500 bg-gray-50' },
  window_closed: { label: 'Janela', color: 'text-gray-400 bg-gray-50' },
}

function formatEventTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

export function EventTimeline({ events }: Props) {
  const recent = events.slice(-20).reverse()

  return (
    <div className="rounded-2xl bg-white p-6 shadow-sm border border-gray-100">
      <p className="text-sm text-gray-500 mb-3">Eventos Recentes</p>
      {recent.length === 0 ? (
        <p className="text-gray-300 text-sm">Nenhum evento ainda</p>
      ) : (
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {recent.map((event, i) => {
            const cfg = typeConfig[event.type] || { label: event.type, color: 'text-gray-500 bg-gray-50' }
            return (
              <div key={i} className="flex items-center gap-3 text-sm">
                <span className="text-xs text-gray-400 font-mono w-10 shrink-0">
                  {formatEventTime(event.time)}
                </span>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${cfg.color}`}>
                  {cfg.label}
                </span>
                {event.pitch && (
                  <span className="text-xs text-gray-400">{event.pitch}Hz</span>
                )}
                {event.response_time && (
                  <span className="text-xs text-gray-400">{event.response_time}s</span>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
