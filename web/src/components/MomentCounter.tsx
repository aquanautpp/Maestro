import { useEffect, useState } from 'react'

interface Props {
  moments: number
  pulse: number
}

export function MomentCounter({ moments, pulse }: Props) {
  const [animating, setAnimating] = useState(false)

  useEffect(() => {
    if (pulse > 0) {
      setAnimating(true)
      const timer = setTimeout(() => setAnimating(false), 1000)
      return () => clearTimeout(timer)
    }
  }, [pulse])

  return (
    <div
      className={`flex flex-col items-center justify-center rounded-2xl bg-white p-8 shadow-sm border transition-all duration-300 ${
        animating
          ? 'border-maestro-green shadow-lg shadow-maestro-green/30 animate-pulse-green'
          : 'border-gray-100'
      }`}
    >
      <p className="text-sm text-gray-500 mb-2">Momentos de Conversa</p>
      <p
        className={`text-7xl font-bold tabular-nums transition-colors duration-300 ${
          animating ? 'text-maestro-green-dark' : 'text-gray-800'
        }`}
      >
        {moments}
      </p>
      <div className="mt-3 flex items-center gap-2">
        <span
          className={`inline-block h-3 w-3 rounded-full transition-colors duration-300 ${
            animating ? 'bg-maestro-green' : 'bg-gray-200'
          }`}
        />
        <span className="text-xs text-gray-400">
          {animating ? 'Momento detectado!' : 'Escutando...'}
        </span>
      </div>
    </div>
  )
}
