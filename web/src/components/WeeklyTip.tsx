import { useEffect, useState } from 'react'

interface WeeklyData {
  tip: {
    title: string
    text: string
    example?: string
  }
  encouragement: string
  week: {
    moments: number
    sessions: number
  }
  trend_message: string
  activity?: {
    area: string
    title: string
    description: string
    why: string
    ages: string
  }
}

export function WeeklyTip() {
  const [data, setData] = useState<WeeklyData | null>(null)

  useEffect(() => {
    fetch('/api/weekly')
      .then((r) => r.json())
      .then(setData)
      .catch(() => {})
  }, [])

  if (!data) return null

  return (
    <div className="rounded-2xl bg-maestro-green-bg p-6 shadow-sm border border-maestro-green-light">
      <p className="text-xs font-semibold text-maestro-green-dark uppercase tracking-wide mb-1">
        Dica da Semana
      </p>
      <p className="text-lg font-semibold text-gray-800 mb-1">{data.tip.title}</p>
      <p className="text-gray-600 text-sm mb-2">{data.tip.text}</p>
      {data.tip.example && (
        <p className="text-xs text-gray-400 italic mb-3">Ex: {data.tip.example}</p>
      )}

      {data.activity && (
        <div className="bg-white/60 rounded-xl p-3 mt-3">
          <p className="text-xs font-semibold text-maestro-green-dark uppercase tracking-wide mb-1">
            Atividade Sugerida
          </p>
          <p className="text-sm font-semibold text-gray-800">{data.activity.title}</p>
          <p className="text-xs text-gray-600 mt-1">{data.activity.description}</p>
          <p className="text-xs text-gray-400 mt-1 italic">
            Por que funciona: {data.activity.why}
          </p>
          <p className="text-xs text-maestro-green-dark mt-1">
            Idades: {data.activity.ages}
          </p>
        </div>
      )}

      <div className="border-t border-maestro-green-light pt-3 mt-3">
        <p className="text-sm text-maestro-green-dark">{data.trend_message}</p>
        <p className="text-xs text-gray-400 mt-1">
          Esta semana: {data.week.moments} momentos em {data.week.sessions} sessoes
        </p>
      </div>
    </div>
  )
}
