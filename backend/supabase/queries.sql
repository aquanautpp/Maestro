-- Early Childhood Coach - Ready-to-use SQL Queries
-- ============================================================================
--
-- These queries can be used directly in Supabase Dashboard or via API.
-- Replace placeholder values (e.g., :family_id) with actual values.
--
-- ============================================================================


-- ============================================================================
-- 1. RESUMO DIÁRIO DE UMA FAMÍLIA
-- ============================================================================

-- Query: Get daily summary for a specific family
-- Usage: Replace 'a1111111-1111-1111-1111-111111111111' with actual family_id

SELECT
    DATE(s.started_at) AS data,
    COUNT(DISTINCT s.id) AS total_sessoes,
    COALESCE(SUM(s.duration_seconds) / 60, 0) AS minutos_totais,
    COALESCE(SUM(s.total_serves), 0) AS total_serves,
    COALESCE(SUM(s.total_returns), 0) AS total_returns,
    COALESCE(SUM(s.total_missed), 0) AS oportunidades_perdidas,
    CASE
        WHEN SUM(s.total_serves) > 0
        THEN ROUND(SUM(s.total_returns)::NUMERIC / SUM(s.total_serves) * 100, 1)
        ELSE 0
    END AS taxa_resposta_percent,
    ROUND(AVG(
        CASE WHEN s.total_serves > 0
        THEN (s.total_serves + s.total_returns)::NUMERIC / (s.duration_seconds / 60.0)
        ELSE 0 END
    ), 1) AS turns_por_minuto
FROM sessions s
JOIN devices d ON d.id = s.device_id
WHERE d.family_id = 'a1111111-1111-1111-1111-111111111111'
  AND s.status = 'completed'
  AND s.started_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(s.started_at)
ORDER BY data DESC;


-- Alternative: Using the pre-built view
SELECT *
FROM daily_family_summary
WHERE family_id = 'a1111111-1111-1111-1111-111111111111'
  AND date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY date DESC;


-- ============================================================================
-- 2. MÉDIA DE CONVERSATIONAL TURNS POR FAIXA ETÁRIA
-- ============================================================================

-- Query: Average stats grouped by child age
-- This query is anonymized (no PII) and can be used for research/analytics

SELECT
    get_age_group(f.child_birth_date) AS faixa_etaria,
    COUNT(DISTINCT f.id) AS num_familias,
    COUNT(DISTINCT s.id) AS num_sessoes,
    ROUND(AVG(s.duration_seconds / 60.0), 1) AS duracao_media_minutos,
    ROUND(AVG(s.total_serves + s.total_returns), 1) AS media_turns_por_sessao,
    ROUND(AVG(
        CASE WHEN s.duration_seconds > 0
        THEN (s.total_serves + s.total_returns)::NUMERIC / (s.duration_seconds / 60.0)
        ELSE 0 END
    ), 2) AS media_turns_por_minuto,
    ROUND(AVG(
        CASE WHEN s.total_serves > 0
        THEN s.total_returns::NUMERIC / s.total_serves
        ELSE 0 END
    ) * 100, 1) AS taxa_resposta_media_percent,
    ROUND(AVG(s.total_missed), 1) AS media_oportunidades_perdidas
FROM families f
JOIN devices d ON d.family_id = f.id
JOIN sessions s ON s.device_id = d.id
WHERE s.status = 'completed'
  AND f.child_birth_date IS NOT NULL
GROUP BY get_age_group(f.child_birth_date)
ORDER BY
    CASE get_age_group(f.child_birth_date)
        WHEN '0-12 meses' THEN 1
        WHEN '12-24 meses' THEN 2
        WHEN '24-36 meses' THEN 3
        WHEN '36-48 meses' THEN 4
        ELSE 5
    END;


-- Alternative: Using the pre-built view
SELECT * FROM stats_by_age_group;


-- Detailed breakdown with response latency
SELECT
    get_age_group(f.child_birth_date) AS faixa_etaria,
    COUNT(DISTINCT f.id) AS num_familias,
    ROUND(AVG((e.metadata->>'response_latency')::NUMERIC), 2) AS latencia_media_segundos,
    ROUND(AVG((e.metadata->>'pitch_hz')::NUMERIC), 0) AS pitch_medio_hz
FROM families f
JOIN devices d ON d.family_id = f.id
JOIN sessions s ON s.device_id = d.id
JOIN events e ON e.session_id = s.id
WHERE s.status = 'completed'
  AND f.child_birth_date IS NOT NULL
  AND e.event_type = 'return'
GROUP BY get_age_group(f.child_birth_date)
ORDER BY faixa_etaria;


-- ============================================================================
-- 3. EVOLUÇÃO SEMANAL DE UMA FAMÍLIA
-- ============================================================================

-- Query: Weekly evolution for a family over the last 8 weeks
-- Shows trends in engagement over time

SELECT
    DATE_TRUNC('week', s.started_at)::DATE AS semana_inicio,
    COUNT(DISTINCT s.id) AS sessoes,
    COUNT(DISTINCT DATE(s.started_at)) AS dias_ativos,
    COALESCE(SUM(s.duration_seconds) / 60, 0) AS minutos_totais,
    COALESCE(SUM(s.total_serves), 0) AS total_serves,
    COALESCE(SUM(s.total_returns), 0) AS total_returns,
    COALESCE(SUM(s.total_missed), 0) AS oportunidades_perdidas,
    ROUND(
        CASE WHEN SUM(s.total_serves) > 0
        THEN SUM(s.total_returns)::NUMERIC / SUM(s.total_serves) * 100
        ELSE 0 END
    , 1) AS taxa_resposta_percent,
    -- Week-over-week change (requires window function)
    ROUND(
        (SUM(s.total_serves + s.total_returns) -
         LAG(SUM(s.total_serves + s.total_returns)) OVER (ORDER BY DATE_TRUNC('week', s.started_at)))::NUMERIC /
        NULLIF(LAG(SUM(s.total_serves + s.total_returns)) OVER (ORDER BY DATE_TRUNC('week', s.started_at)), 0) * 100
    , 1) AS variacao_percent
FROM sessions s
JOIN devices d ON d.id = s.device_id
WHERE d.family_id = 'a1111111-1111-1111-1111-111111111111'
  AND s.status = 'completed'
  AND s.started_at >= CURRENT_DATE - INTERVAL '8 weeks'
GROUP BY DATE_TRUNC('week', s.started_at)
ORDER BY semana_inicio DESC;


-- Simplified weekly summary (without week-over-week comparison)
SELECT
    DATE_TRUNC('week', s.started_at)::DATE AS semana,
    COUNT(DISTINCT s.id) AS sessoes,
    SUM(s.total_serves + s.total_returns) AS total_turns,
    ROUND(AVG(s.total_serves + s.total_returns), 1) AS media_turns_por_sessao
FROM sessions s
JOIN devices d ON d.id = s.device_id
WHERE d.family_id = 'a1111111-1111-1111-1111-111111111111'
  AND s.status = 'completed'
GROUP BY DATE_TRUNC('week', s.started_at)
ORDER BY semana DESC
LIMIT 8;


-- ============================================================================
-- BONUS QUERIES
-- ============================================================================

-- 4. TOP FAMILIES BY ENGAGEMENT (for research/leaderboard)
SELECT
    f.anonymous_id,
    f.state,
    get_age_group(f.child_birth_date) AS faixa_etaria,
    COUNT(DISTINCT s.id) AS total_sessoes,
    SUM(s.total_serves + s.total_returns) AS total_turns,
    ROUND(AVG(
        CASE WHEN s.total_serves > 0
        THEN s.total_returns::NUMERIC / s.total_serves * 100
        ELSE 0 END
    ), 1) AS taxa_resposta_media
FROM families f
JOIN devices d ON d.family_id = f.id
JOIN sessions s ON s.device_id = d.id
WHERE s.status = 'completed'
GROUP BY f.id, f.anonymous_id, f.state, f.child_birth_date
ORDER BY total_turns DESC
LIMIT 10;


-- 5. EVENTS TIMELINE FOR A SESSION (debugging/analysis)
SELECT
    e.timestamp_in_session AS tempo_segundos,
    e.event_type AS tipo,
    e.confidence AS confianca,
    e.metadata->>'pitch_hz' AS pitch_hz,
    e.metadata->>'response_latency' AS latencia,
    e.metadata->>'silence_duration' AS duracao_silencio
FROM events e
WHERE e.session_id = 'c1111111-1111-1111-1111-111111111111'
ORDER BY e.timestamp_in_session;


-- 6. DEVICE ACTIVITY SUMMARY
SELECT
    d.name AS dispositivo,
    d.firmware_version AS versao,
    d.last_seen_at AS ultimo_acesso,
    COUNT(s.id) AS total_sessoes,
    MAX(s.started_at) AS ultima_sessao,
    SUM(s.duration_seconds) / 3600.0 AS horas_totais
FROM devices d
LEFT JOIN sessions s ON s.device_id = d.id AND s.status = 'completed'
WHERE d.family_id = 'a1111111-1111-1111-1111-111111111111'
GROUP BY d.id, d.name, d.firmware_version, d.last_seen_at
ORDER BY ultima_sessao DESC NULLS LAST;


-- 7. HOURLY DISTRIBUTION OF SESSIONS (when do families use the device?)
SELECT
    EXTRACT(HOUR FROM s.started_at) AS hora,
    COUNT(*) AS total_sessoes,
    ROUND(AVG(s.total_serves + s.total_returns), 1) AS media_turns
FROM sessions s
WHERE s.status = 'completed'
GROUP BY EXTRACT(HOUR FROM s.started_at)
ORDER BY hora;


-- 8. STATS BY STATE (geographic analysis)
SELECT
    f.state AS estado,
    COUNT(DISTINCT f.id) AS familias,
    COUNT(DISTINCT s.id) AS sessoes,
    ROUND(AVG(s.total_serves + s.total_returns), 1) AS media_turns,
    ROUND(AVG(
        CASE WHEN s.total_serves > 0
        THEN s.total_returns::NUMERIC / s.total_serves * 100
        ELSE 0 END
    ), 1) AS taxa_resposta_media
FROM families f
JOIN devices d ON d.family_id = f.id
JOIN sessions s ON s.device_id = d.id
WHERE s.status = 'completed'
  AND f.state IS NOT NULL
GROUP BY f.state
ORDER BY familias DESC;


-- 9. FAMILY PROGRESS OVER TIME (for individual coaching)
WITH weekly_stats AS (
    SELECT
        DATE_TRUNC('week', s.started_at)::DATE AS semana,
        SUM(s.total_serves) AS serves,
        SUM(s.total_returns) AS returns,
        SUM(s.total_missed) AS missed
    FROM sessions s
    JOIN devices d ON d.id = s.device_id
    WHERE d.family_id = 'a1111111-1111-1111-1111-111111111111'
      AND s.status = 'completed'
    GROUP BY DATE_TRUNC('week', s.started_at)
)
SELECT
    semana,
    serves,
    returns,
    missed,
    CASE WHEN serves > 0
        THEN ROUND(returns::NUMERIC / serves * 100, 1)
        ELSE 0
    END AS taxa_resposta,
    -- Rolling 4-week average
    ROUND(AVG(serves + returns) OVER (
        ORDER BY semana
        ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
    ), 1) AS media_movel_4_semanas
FROM weekly_stats
ORDER BY semana DESC;


-- 10. FIND SESSIONS WITH LOW ENGAGEMENT (for intervention)
SELECT
    f.anonymous_id,
    s.id AS session_id,
    s.started_at,
    s.duration_seconds / 60 AS duracao_minutos,
    s.total_serves,
    s.total_returns,
    s.total_missed,
    CASE WHEN s.total_serves > 0
        THEN ROUND(s.total_returns::NUMERIC / s.total_serves * 100, 1)
        ELSE 0
    END AS taxa_resposta
FROM sessions s
JOIN devices d ON d.id = s.device_id
JOIN families f ON f.id = d.family_id
WHERE s.status = 'completed'
  AND s.duration_seconds >= 600  -- At least 10 minutes
  AND (
      s.total_serves < 3  -- Very few child initiations
      OR (s.total_serves > 0 AND s.total_returns::NUMERIC / s.total_serves < 0.5)  -- Low response rate
  )
ORDER BY s.started_at DESC
LIMIT 20;
