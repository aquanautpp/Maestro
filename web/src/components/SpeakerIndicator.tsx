interface Props {
  speaker: string | null
}

export function SpeakerIndicator({ speaker }: Props) {
  const config = {
    CHI: {
      label: 'Crianca',
      bg: 'bg-maestro-child-light',
      text: 'text-blue-700',
      dot: 'bg-maestro-child',
      icon: '👶',
    },
    ADT: {
      label: 'Adulto',
      bg: 'bg-maestro-adult-light',
      text: 'text-orange-700',
      dot: 'bg-maestro-adult',
      icon: '🧑',
    },
  }

  const current = speaker && speaker in config ? config[speaker as keyof typeof config] : null

  return (
    <div className="rounded-2xl bg-white p-6 shadow-sm border border-gray-100">
      <p className="text-sm text-gray-500 mb-3">Falante Atual</p>
      {current ? (
        <div className={`flex items-center gap-3 rounded-xl px-4 py-3 ${current.bg}`}>
          <span className={`inline-block h-3 w-3 rounded-full ${current.dot} animate-pulse`} />
          <span className="text-2xl">{current.icon}</span>
          <span className={`text-lg font-semibold ${current.text}`}>{current.label}</span>
        </div>
      ) : (
        <div className="flex items-center gap-3 rounded-xl px-4 py-3 bg-maestro-silence-light">
          <span className="inline-block h-3 w-3 rounded-full bg-maestro-silence" />
          <span className="text-lg text-gray-400">Silencio</span>
        </div>
      )}
    </div>
  )
}
