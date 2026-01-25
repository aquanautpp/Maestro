-- Early Childhood Coach - Initial Database Schema
-- Run with: npx supabase db push

-- ============================================================================
-- EXTENSIONS
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- CUSTOM TYPES
-- ============================================================================

-- Event types for conversational turn detection
CREATE TYPE event_type AS ENUM ('serve', 'return', 'missed_opportunity');

-- ============================================================================
-- TABLES
-- ============================================================================

-- Families: Core entity representing a family unit
CREATE TABLE families (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Anonymous identifier for privacy (e.g., "FAM-A7B3C9")
    anonymous_id TEXT UNIQUE NOT NULL DEFAULT (
        'FAM-' || UPPER(SUBSTRING(MD5(RANDOM()::TEXT) FROM 1 FOR 6))
    ),

    -- Geographic info (state only, no city for privacy)
    state VARCHAR(2),

    -- Child info (only birth date to calculate age)
    child_birth_date DATE,

    -- Supabase Auth user ID (nullable for anonymous families)
    auth_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,

    -- Metadata for extensibility
    metadata JSONB DEFAULT '{}'::JSONB
);

-- Index for auth user lookup
CREATE INDEX idx_families_auth_user ON families(auth_user_id);


-- Devices: Physical wearable devices
CREATE TABLE devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    family_id UUID NOT NULL REFERENCES families(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Last time device synced with backend
    last_seen_at TIMESTAMPTZ,

    -- Device info
    name VARCHAR(100) DEFAULT 'Meu Dispositivo',
    mac_address VARCHAR(17), -- Format: XX:XX:XX:XX:XX:XX
    firmware_version VARCHAR(20),

    -- Device status
    is_active BOOLEAN DEFAULT TRUE,

    metadata JSONB DEFAULT '{}'::JSONB
);

-- Index for family lookup
CREATE INDEX idx_devices_family ON devices(family_id);
CREATE INDEX idx_devices_last_seen ON devices(last_seen_at);


-- Sessions: Recording sessions from a device
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,

    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,

    -- Computed duration in seconds (updated on session end)
    duration_seconds INTEGER GENERATED ALWAYS AS (
        CASE
            WHEN ended_at IS NOT NULL
            THEN EXTRACT(EPOCH FROM (ended_at - started_at))::INTEGER
            ELSE NULL
        END
    ) STORED,

    -- Summary stats (denormalized for quick access)
    total_serves INTEGER DEFAULT 0,
    total_returns INTEGER DEFAULT 0,
    total_missed INTEGER DEFAULT 0,

    -- Processing status
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'completed', 'processing', 'error')),

    metadata JSONB DEFAULT '{}'::JSONB
);

-- Indexes for common queries
CREATE INDEX idx_sessions_device ON sessions(device_id);
CREATE INDEX idx_sessions_started_at ON sessions(started_at);
CREATE INDEX idx_sessions_status ON sessions(status);


-- Events: Individual conversational events within a session
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

    -- Event classification
    event_type event_type NOT NULL,

    -- Timestamp relative to session start (in seconds)
    timestamp_in_session REAL NOT NULL,

    -- Confidence score from the algorithm (0.0 - 1.0)
    confidence REAL CHECK (confidence >= 0 AND confidence <= 1),

    -- Additional data (pitch_hz, response_latency, etc.)
    metadata JSONB DEFAULT '{}'::JSONB,

    -- Absolute timestamp for time-series queries
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX idx_events_session ON events(session_id);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_timestamp ON events(timestamp_in_session);
CREATE INDEX idx_events_created_at ON events(created_at);


-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Calculate child age in months from birth date
CREATE OR REPLACE FUNCTION get_child_age_months(birth_date DATE)
RETURNS INTEGER AS $$
BEGIN
    RETURN EXTRACT(YEAR FROM AGE(NOW(), birth_date)) * 12 +
           EXTRACT(MONTH FROM AGE(NOW(), birth_date));
END;
$$ LANGUAGE plpgsql IMMUTABLE;


-- Get age group label
CREATE OR REPLACE FUNCTION get_age_group(birth_date DATE)
RETURNS TEXT AS $$
DECLARE
    months INTEGER;
BEGIN
    months := get_child_age_months(birth_date);
    RETURN CASE
        WHEN months < 12 THEN '0-12 meses'
        WHEN months < 24 THEN '12-24 meses'
        WHEN months < 36 THEN '24-36 meses'
        WHEN months < 48 THEN '36-48 meses'
        ELSE '48+ meses'
    END;
END;
$$ LANGUAGE plpgsql IMMUTABLE;


-- Update session summary stats (called via trigger)
CREATE OR REPLACE FUNCTION update_session_stats()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE sessions SET
        total_serves = (
            SELECT COUNT(*) FROM events
            WHERE session_id = COALESCE(NEW.session_id, OLD.session_id)
            AND event_type = 'serve'
        ),
        total_returns = (
            SELECT COUNT(*) FROM events
            WHERE session_id = COALESCE(NEW.session_id, OLD.session_id)
            AND event_type = 'return'
        ),
        total_missed = (
            SELECT COUNT(*) FROM events
            WHERE session_id = COALESCE(NEW.session_id, OLD.session_id)
            AND event_type = 'missed_opportunity'
        )
    WHERE id = COALESCE(NEW.session_id, OLD.session_id);

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;


-- Trigger to update session stats on event changes
CREATE TRIGGER trigger_update_session_stats
AFTER INSERT OR UPDATE OR DELETE ON events
FOR EACH ROW EXECUTE FUNCTION update_session_stats();


-- ============================================================================
-- VIEWS
-- ============================================================================

-- Daily summary view per family
CREATE OR REPLACE VIEW daily_family_summary AS
SELECT
    f.id AS family_id,
    f.anonymous_id,
    DATE(s.started_at) AS date,
    COUNT(DISTINCT s.id) AS total_sessions,
    SUM(s.duration_seconds) / 60 AS total_minutes,
    SUM(s.total_serves) AS total_serves,
    SUM(s.total_returns) AS total_returns,
    SUM(s.total_missed) AS total_missed,
    CASE
        WHEN SUM(s.total_serves) > 0
        THEN ROUND(SUM(s.total_returns)::NUMERIC / SUM(s.total_serves), 2)
        ELSE 0
    END AS return_rate
FROM families f
JOIN devices d ON d.family_id = f.id
JOIN sessions s ON s.device_id = d.id
WHERE s.status = 'completed'
GROUP BY f.id, f.anonymous_id, DATE(s.started_at);


-- Aggregated stats by age group (anonymized)
CREATE OR REPLACE VIEW stats_by_age_group AS
SELECT
    get_age_group(f.child_birth_date) AS age_group,
    COUNT(DISTINCT f.id) AS family_count,
    COUNT(DISTINCT s.id) AS session_count,
    ROUND(AVG(s.total_serves + s.total_returns)::NUMERIC, 1) AS avg_turns_per_session,
    ROUND(AVG(
        CASE WHEN s.total_serves > 0
        THEN s.total_returns::NUMERIC / s.total_serves
        ELSE 0 END
    ), 2) AS avg_return_rate
FROM families f
JOIN devices d ON d.family_id = f.id
JOIN sessions s ON s.device_id = d.id
WHERE s.status = 'completed'
  AND f.child_birth_date IS NOT NULL
GROUP BY get_age_group(f.child_birth_date)
ORDER BY age_group;


-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE families ENABLE ROW LEVEL SECURITY;
ALTER TABLE devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;

-- ----------------------------------------------------------------------------
-- FAMILIES POLICIES
-- ----------------------------------------------------------------------------

-- Users can view their own family
CREATE POLICY "Users can view own family"
ON families FOR SELECT
USING (auth.uid() = auth_user_id);

-- Users can update their own family
CREATE POLICY "Users can update own family"
ON families FOR UPDATE
USING (auth.uid() = auth_user_id);

-- Users can insert a family for themselves
CREATE POLICY "Users can create own family"
ON families FOR INSERT
WITH CHECK (auth.uid() = auth_user_id OR auth_user_id IS NULL);

-- Service role can do anything (for backend operations)
CREATE POLICY "Service role full access to families"
ON families FOR ALL
USING (auth.role() = 'service_role');

-- ----------------------------------------------------------------------------
-- DEVICES POLICIES
-- ----------------------------------------------------------------------------

-- Users can view devices belonging to their family
CREATE POLICY "Users can view own devices"
ON devices FOR SELECT
USING (
    family_id IN (
        SELECT id FROM families WHERE auth_user_id = auth.uid()
    )
);

-- Users can manage devices in their family
CREATE POLICY "Users can manage own devices"
ON devices FOR ALL
USING (
    family_id IN (
        SELECT id FROM families WHERE auth_user_id = auth.uid()
    )
);

-- Service role full access
CREATE POLICY "Service role full access to devices"
ON devices FOR ALL
USING (auth.role() = 'service_role');

-- ----------------------------------------------------------------------------
-- SESSIONS POLICIES
-- ----------------------------------------------------------------------------

-- Users can view sessions from their devices
CREATE POLICY "Users can view own sessions"
ON sessions FOR SELECT
USING (
    device_id IN (
        SELECT d.id FROM devices d
        JOIN families f ON f.id = d.family_id
        WHERE f.auth_user_id = auth.uid()
    )
);

-- Users can create sessions for their devices
CREATE POLICY "Users can create own sessions"
ON sessions FOR INSERT
WITH CHECK (
    device_id IN (
        SELECT d.id FROM devices d
        JOIN families f ON f.id = d.family_id
        WHERE f.auth_user_id = auth.uid()
    )
);

-- Users can update their own sessions
CREATE POLICY "Users can update own sessions"
ON sessions FOR UPDATE
USING (
    device_id IN (
        SELECT d.id FROM devices d
        JOIN families f ON f.id = d.family_id
        WHERE f.auth_user_id = auth.uid()
    )
);

-- Service role full access
CREATE POLICY "Service role full access to sessions"
ON sessions FOR ALL
USING (auth.role() = 'service_role');

-- ----------------------------------------------------------------------------
-- EVENTS POLICIES
-- ----------------------------------------------------------------------------

-- Users can view events from their sessions
CREATE POLICY "Users can view own events"
ON events FOR SELECT
USING (
    session_id IN (
        SELECT s.id FROM sessions s
        JOIN devices d ON d.id = s.device_id
        JOIN families f ON f.id = d.family_id
        WHERE f.auth_user_id = auth.uid()
    )
);

-- Users can create events in their sessions
CREATE POLICY "Users can create own events"
ON events FOR INSERT
WITH CHECK (
    session_id IN (
        SELECT s.id FROM sessions s
        JOIN devices d ON d.id = s.device_id
        JOIN families f ON f.id = d.family_id
        WHERE f.auth_user_id = auth.uid()
    )
);

-- Service role full access
CREATE POLICY "Service role full access to events"
ON events FOR ALL
USING (auth.role() = 'service_role');

-- ----------------------------------------------------------------------------
-- ANONYMOUS ACCESS TO AGGREGATED DATA
-- ----------------------------------------------------------------------------

-- Allow anonymous read access to aggregated views (no PII)
-- These views don't expose individual family data

GRANT SELECT ON stats_by_age_group TO anon;
GRANT SELECT ON stats_by_age_group TO authenticated;


-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Composite index for time-range queries
CREATE INDEX idx_sessions_device_time ON sessions(device_id, started_at DESC);

-- Index for age-based queries
CREATE INDEX idx_families_birth_date ON families(child_birth_date);

-- Index for state-based aggregations
CREATE INDEX idx_families_state ON families(state);
