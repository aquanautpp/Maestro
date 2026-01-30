import { AreaChart, Area, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts'

interface Props {
  events: Array<{
    time: number
    type: string
  }>
}

export function TrendChart({ events }: Props) {
  // Build cumulative moments over time
  const data: Array<{ time: string; momentos: number }> = []
  let cumulative = 0

  // Start at 0
  data.push({ time: '0:00', momentos: 0 })

  for (const event of events) {
    if (event.type === 'moment') {
      cumulative++
      const m = Math.floor(event.time / 60)
      const s = Math.floor(event.time % 60)
      data.push({
        time: `${m}:${s.toString().padStart(2, '0')}`,
        momentos: cumulative,
      })
    }
  }

  if (data.length <= 1) {
    return (
      <div className="rounded-2xl bg-white p-6 shadow-sm border border-gray-100">
        <p className="text-sm text-gray-500 mb-3">Momentos ao Longo do Tempo</p>
        <div className="flex items-center justify-center h-40 text-gray-300 text-sm">
          Os momentos aparecerao aqui
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-2xl bg-white p-6 shadow-sm border border-gray-100">
      <p className="text-sm text-gray-500 mb-3">Momentos ao Longo do Tempo</p>
      <ResponsiveContainer width="100%" height={180}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="greenGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#4ade80" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#4ade80" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="time" tick={{ fontSize: 11 }} stroke="#d1d5db" />
          <YAxis allowDecimals={false} tick={{ fontSize: 11 }} stroke="#d1d5db" />
          <Tooltip />
          <Area
            type="monotone"
            dataKey="momentos"
            stroke="#16a34a"
            strokeWidth={2}
            fill="url(#greenGrad)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
