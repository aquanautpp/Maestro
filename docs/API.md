# API do Early Childhood Coach

Base URL: `http://<IP_DO_DISPOSITIVO>:5000`

## Endpoints

### GET /api/status
Retorna estado atual em tempo real.

**Resposta:**
```json
{
  "listening": true,
  "current_speaker": "CHI",
  "current_pitch": 287,
  "seconds_since_last_speech": 2.3
}
```

Valores de `current_speaker`: `"CHI"` (crianca), `"ADT"` (adulto), `null` (silencio)

### GET /api/session
Retorna resumo da sessao atual.

**Resposta:**
```json
{
  "session_id": "abc123",
  "started_at": "2026-01-25T20:30:00Z",
  "duration_seconds": 342,
  "turns": 14,
  "missed": 6,
  "response_rate": 70.0,
  "avg_response_time": 0.8,
  "events": [
    {"time": 31.2, "type": "turn", "response_time": 0.6},
    {"time": 45.8, "type": "missed"}
  ]
}
```

### POST /api/start
Inicia nova sessao de escuta.

**Resposta:**
```json
{
  "session_id": "abc123",
  "status": "started"
}
```

### POST /api/stop
Para sessao atual e retorna resumo.

**Resposta:**
```json
{
  "session_id": "abc123",
  "status": "stopped",
  "summary": {
    "duration_seconds": 342,
    "turns": 14,
    "missed": 6,
    "response_rate": 70.0
  }
}
```

## Codigos de erro

- `400`: Requisicao invalida
- `500`: Erro interno do dispositivo

## Notas

- O app deve fazer polling em `/api/status` a cada 500ms para atualizacao em tempo real
- Sessoes sao salvas automaticamente no Supabase quando finalizadas
