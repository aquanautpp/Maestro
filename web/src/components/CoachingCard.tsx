import { useState } from 'react'

export function CoachingCard() {
  const [coaching, setCoaching] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchCoaching = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/coaching', { method: 'POST' })
      const data = await res.json()
      if (data.error) {
        setError(data.error)
      } else {
        setCoaching(data.coaching)
      }
    } catch {
      setError('Erro ao conectar com o servidor')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="rounded-2xl bg-white p-6 shadow-sm border border-gray-100">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm text-gray-500">Dica do Maestro</p>
        <button
          onClick={fetchCoaching}
          disabled={loading}
          className="text-sm text-maestro-green-dark hover:text-maestro-green font-medium disabled:opacity-50 transition-colors"
        >
          {loading ? 'Pensando...' : coaching ? 'Nova dica' : 'Pedir dica'}
        </button>
      </div>

      {error && (
        <p className="text-sm text-orange-600 bg-orange-50 rounded-lg p-3">{error}</p>
      )}

      {coaching && !error && (
        <p className="text-gray-700 leading-relaxed">{coaching}</p>
      )}

      {!coaching && !error && !loading && (
        <p className="text-gray-300 text-sm">
          Clique em "Pedir dica" para receber coaching personalizado
        </p>
      )}
    </div>
  )
}
