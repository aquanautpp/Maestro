interface Props {
  active: boolean
  loading: boolean
  elapsed: number
  connected: boolean
  onStart: () => void
  onStop: () => void
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

export function SessionControls({ active, loading, elapsed, connected, onStart, onStop }: Props) {
  return (
    <div className="rounded-2xl bg-white p-6 shadow-sm border border-gray-100">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span
            className={`inline-block h-2 w-2 rounded-full ${
              connected ? 'bg-maestro-green' : 'bg-red-400'
            }`}
          />
          <span className="text-xs text-gray-400">
            {connected ? 'Conectado' : 'Desconectado'}
          </span>
        </div>
        {active && (
          <span className="font-mono text-2xl font-semibold text-gray-700 tabular-nums">
            {formatTime(elapsed)}
          </span>
        )}
      </div>

      {active ? (
        <button
          onClick={onStop}
          disabled={loading}
          className="w-full rounded-xl bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold py-3 px-6 transition-colors disabled:opacity-50"
        >
          {loading ? 'Parando...' : 'Parar Sessao'}
        </button>
      ) : (
        <button
          onClick={onStart}
          disabled={loading || !connected}
          className="w-full rounded-xl bg-maestro-green hover:bg-maestro-green-dark text-white font-semibold py-3 px-6 transition-colors disabled:opacity-50"
        >
          {loading ? 'Iniciando...' : 'Iniciar Sessao'}
        </button>
      )}
    </div>
  )
}
