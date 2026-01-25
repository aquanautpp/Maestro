# Backend Module

Supabase backend for the Early Childhood Coach system.

## Quick Start

```bash
cd backend
npm install

# Start local Supabase (requires Docker)
npx supabase start

# Apply migrations
npx supabase db push

# Seed with test data
psql -h localhost -p 54322 -U postgres -d postgres -f supabase/seed/seed.sql

# Open Supabase Studio
# Visit: http://localhost:54323
```

## Database Schema

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              FAMILIES                                    │
│  id, anonymous_id, state, child_birth_date, auth_user_id                │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ 1:N
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              DEVICES                                     │
│  id, family_id, name, mac_address, firmware_version, last_seen_at       │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ 1:N
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              SESSIONS                                    │
│  id, device_id, started_at, ended_at, duration_seconds (computed)       │
│  total_serves, total_returns, total_missed (denormalized)               │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ 1:N
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              EVENTS                                      │
│  id, session_id, event_type (enum), timestamp_in_session, confidence    │
│  metadata (jsonb: pitch_hz, response_latency, silence_duration)         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Event Types

| Type | Description |
|------|-------------|
| `serve` | Child initiated (spoke) |
| `return` | Adult responded within threshold |
| `missed_opportunity` | Silence >5s after child without adult response |

## Files

```
backend/
├── package.json
├── supabase/
│   ├── config.toml              # Local Supabase config
│   ├── migrations/
│   │   └── 00001_initial_schema.sql  # Tables, types, functions, RLS
│   ├── seed/
│   │   └── seed.sql             # 3 families, 10 sessions, 100+ events
│   └── queries.sql              # Ready-to-use SQL queries
```

## Row Level Security (RLS)

All tables have RLS enabled:

| Table | Policy |
|-------|--------|
| `families` | Users see only their own family (via `auth_user_id`) |
| `devices` | Users see devices in their family |
| `sessions` | Users see sessions from their devices |
| `events` | Users see events in their sessions |

**Anonymous access**: The `stats_by_age_group` view is accessible to anonymous users for aggregated research data (no PII).

## Helper Functions

```sql
-- Get child age in months
SELECT get_child_age_months('2024-06-15'::DATE);  -- Returns: 19

-- Get age group label
SELECT get_age_group('2024-06-15'::DATE);  -- Returns: '12-24 meses'
```

## Pre-built Views

### `daily_family_summary`
Daily aggregated stats per family.

```sql
SELECT * FROM daily_family_summary
WHERE family_id = 'xxx'
ORDER BY date DESC;
```

### `stats_by_age_group`
Anonymized stats grouped by child age (accessible to all).

```sql
SELECT * FROM stats_by_age_group;
```

## Example Queries

### 1. Resumo diário de uma família

```sql
SELECT
    DATE(s.started_at) AS data,
    SUM(s.total_serves) AS serves,
    SUM(s.total_returns) AS returns,
    ROUND(SUM(s.total_returns)::NUMERIC / NULLIF(SUM(s.total_serves), 0) * 100, 1) AS taxa_resposta
FROM sessions s
JOIN devices d ON d.id = s.device_id
WHERE d.family_id = 'a1111111-1111-1111-1111-111111111111'
GROUP BY DATE(s.started_at)
ORDER BY data DESC;
```

### 2. Média de turns por faixa etária

```sql
SELECT
    get_age_group(f.child_birth_date) AS faixa_etaria,
    ROUND(AVG(s.total_serves + s.total_returns), 1) AS media_turns
FROM families f
JOIN devices d ON d.family_id = f.id
JOIN sessions s ON s.device_id = d.id
WHERE s.status = 'completed'
GROUP BY get_age_group(f.child_birth_date);
```

### 3. Evolução semanal de uma família

```sql
SELECT
    DATE_TRUNC('week', s.started_at)::DATE AS semana,
    COUNT(s.id) AS sessoes,
    SUM(s.total_serves + s.total_returns) AS total_turns
FROM sessions s
JOIN devices d ON d.id = s.device_id
WHERE d.family_id = 'a1111111-1111-1111-1111-111111111111'
GROUP BY DATE_TRUNC('week', s.started_at)
ORDER BY semana DESC;
```

See `supabase/queries.sql` for more examples.

## Seed Data

The seed file creates:
- **3 families**: SP (18mo), RJ (30mo), MG (12mo)
- **5 devices**: Some families have multiple caregivers
- **10 sessions**: Varied durations and times
- **117 events**: Realistic distribution of serves/returns/missed

```bash
# Reset database and apply seed
npx supabase db reset
```

## API Usage (from App)

### Insert a session with events

```typescript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

// Create session
const { data: session } = await supabase
  .from('sessions')
  .insert({ device_id: deviceId })
  .select()
  .single()

// Insert events
await supabase.from('events').insert([
  {
    session_id: session.id,
    event_type: 'serve',
    timestamp_in_session: 45.2,
    confidence: 0.85,
    metadata: { pitch_hz: 312 }
  },
  {
    session_id: session.id,
    event_type: 'return',
    timestamp_in_session: 46.8,
    confidence: 0.92,
    metadata: { pitch_hz: 165, response_latency: 1.6 }
  }
])

// End session
await supabase
  .from('sessions')
  .update({ ended_at: new Date().toISOString(), status: 'completed' })
  .eq('id', session.id)
```

### Fetch family summary

```typescript
const { data } = await supabase
  .from('daily_family_summary')
  .select('*')
  .eq('family_id', familyId)
  .gte('date', thirtyDaysAgo)
  .order('date', { ascending: false })
```

## Deployment

```bash
# Link to Supabase project
npx supabase link --project-ref your-project-ref

# Push schema
npx supabase db push

# Deploy edge functions (when created)
npx supabase functions deploy
```

## Environment Variables

```env
# .env.local
SUPABASE_URL=http://localhost:54321
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```
