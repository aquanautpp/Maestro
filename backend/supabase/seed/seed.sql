-- Early Childhood Coach - Seed Data for Development
-- Run with: npx supabase db reset
--
-- Creates:
-- - 3 families (different states, child ages)
-- - 5 devices (some families have 2)
-- - 10 sessions
-- - 100+ events

-- ============================================================================
-- FAMILIES
-- ============================================================================

INSERT INTO families (id, anonymous_id, state, child_birth_date, created_at, metadata)
VALUES
    -- Family 1: São Paulo, child 18 months old
    (
        'a1111111-1111-1111-1111-111111111111',
        'FAM-SP1801',
        'SP',
        CURRENT_DATE - INTERVAL '18 months',
        NOW() - INTERVAL '30 days',
        '{"language": "pt-BR", "enrolled_via": "ivas_program"}'::JSONB
    ),
    -- Family 2: Rio de Janeiro, child 30 months old
    (
        'a2222222-2222-2222-2222-222222222222',
        'FAM-RJ3002',
        'RJ',
        CURRENT_DATE - INTERVAL '30 months',
        NOW() - INTERVAL '45 days',
        '{"language": "pt-BR", "enrolled_via": "ivas_program"}'::JSONB
    ),
    -- Family 3: Minas Gerais, child 12 months old
    (
        'a3333333-3333-3333-3333-333333333333',
        'FAM-MG1203',
        'MG',
        CURRENT_DATE - INTERVAL '12 months',
        NOW() - INTERVAL '15 days',
        '{"language": "pt-BR", "enrolled_via": "pilot"}'::JSONB
    );


-- ============================================================================
-- DEVICES
-- ============================================================================

INSERT INTO devices (id, family_id, name, mac_address, firmware_version, last_seen_at, created_at)
VALUES
    -- Family 1: 2 devices (mom and dad)
    (
        'b1111111-1111-1111-1111-111111111111',
        'a1111111-1111-1111-1111-111111111111',
        'Dispositivo Mãe',
        'AA:BB:CC:DD:EE:01',
        '1.0.3',
        NOW() - INTERVAL '2 hours',
        NOW() - INTERVAL '30 days'
    ),
    (
        'b1111111-1111-1111-1111-111111111112',
        'a1111111-1111-1111-1111-111111111111',
        'Dispositivo Pai',
        'AA:BB:CC:DD:EE:02',
        '1.0.3',
        NOW() - INTERVAL '1 day',
        NOW() - INTERVAL '25 days'
    ),
    -- Family 2: 2 devices
    (
        'b2222222-2222-2222-2222-222222222221',
        'a2222222-2222-2222-2222-222222222222',
        'Dispositivo Mãe',
        'AA:BB:CC:DD:EE:03',
        '1.0.2',
        NOW() - INTERVAL '5 hours',
        NOW() - INTERVAL '45 days'
    ),
    (
        'b2222222-2222-2222-2222-222222222222',
        'a2222222-2222-2222-2222-222222222222',
        'Dispositivo Avó',
        'AA:BB:CC:DD:EE:04',
        '1.0.2',
        NOW() - INTERVAL '3 days',
        NOW() - INTERVAL '40 days'
    ),
    -- Family 3: 1 device
    (
        'b3333333-3333-3333-3333-333333333333',
        'a3333333-3333-3333-3333-333333333333',
        'Dispositivo Família',
        'AA:BB:CC:DD:EE:05',
        '1.0.3',
        NOW() - INTERVAL '30 minutes',
        NOW() - INTERVAL '15 days'
    );


-- ============================================================================
-- SESSIONS
-- ============================================================================

INSERT INTO sessions (id, device_id, started_at, ended_at, status)
VALUES
    -- Family 1, Device 1 (Mom): 3 sessions
    (
        'c1111111-1111-1111-1111-111111111111',
        'b1111111-1111-1111-1111-111111111111',
        NOW() - INTERVAL '7 days' + INTERVAL '9 hours',  -- Morning
        NOW() - INTERVAL '7 days' + INTERVAL '9 hours 25 minutes',
        'completed'
    ),
    (
        'c1111111-1111-1111-1111-111111111112',
        'b1111111-1111-1111-1111-111111111111',
        NOW() - INTERVAL '5 days' + INTERVAL '18 hours',  -- Evening
        NOW() - INTERVAL '5 days' + INTERVAL '18 hours 40 minutes',
        'completed'
    ),
    (
        'c1111111-1111-1111-1111-111111111113',
        'b1111111-1111-1111-1111-111111111111',
        NOW() - INTERVAL '2 days' + INTERVAL '10 hours',
        NOW() - INTERVAL '2 days' + INTERVAL '10 hours 30 minutes',
        'completed'
    ),

    -- Family 1, Device 2 (Dad): 2 sessions
    (
        'c1111111-1111-1111-1111-111111111121',
        'b1111111-1111-1111-1111-111111111112',
        NOW() - INTERVAL '6 days' + INTERVAL '19 hours',
        NOW() - INTERVAL '6 days' + INTERVAL '19 hours 20 minutes',
        'completed'
    ),
    (
        'c1111111-1111-1111-1111-111111111122',
        'b1111111-1111-1111-1111-111111111112',
        NOW() - INTERVAL '3 days' + INTERVAL '20 hours',
        NOW() - INTERVAL '3 days' + INTERVAL '20 hours 15 minutes',
        'completed'
    ),

    -- Family 2, Device 1 (Mom): 2 sessions
    (
        'c2222222-2222-2222-2222-222222222211',
        'b2222222-2222-2222-2222-222222222221',
        NOW() - INTERVAL '4 days' + INTERVAL '8 hours',
        NOW() - INTERVAL '4 days' + INTERVAL '8 hours 35 minutes',
        'completed'
    ),
    (
        'c2222222-2222-2222-2222-222222222212',
        'b2222222-2222-2222-2222-222222222221',
        NOW() - INTERVAL '1 day' + INTERVAL '17 hours',
        NOW() - INTERVAL '1 day' + INTERVAL '17 hours 45 minutes',
        'completed'
    ),

    -- Family 2, Device 2 (Grandma): 1 session
    (
        'c2222222-2222-2222-2222-222222222221',
        'b2222222-2222-2222-2222-222222222222',
        NOW() - INTERVAL '3 days' + INTERVAL '15 hours',
        NOW() - INTERVAL '3 days' + INTERVAL '15 hours 30 minutes',
        'completed'
    ),

    -- Family 3: 2 sessions
    (
        'c3333333-3333-3333-3333-333333333331',
        'b3333333-3333-3333-3333-333333333333',
        NOW() - INTERVAL '2 days' + INTERVAL '9 hours',
        NOW() - INTERVAL '2 days' + INTERVAL '9 hours 20 minutes',
        'completed'
    ),
    (
        'c3333333-3333-3333-3333-333333333332',
        'b3333333-3333-3333-3333-333333333333',
        NOW() - INTERVAL '6 hours',
        NOW() - INTERVAL '5 hours 30 minutes',
        'completed'
    );


-- ============================================================================
-- EVENTS
-- ============================================================================

-- Helper: Generate events for a session
-- We'll create events manually to have 100+ total

-- Session 1 (Family 1, Mom, 25min): Good engagement - 15 events
INSERT INTO events (session_id, event_type, timestamp_in_session, confidence, metadata) VALUES
('c1111111-1111-1111-1111-111111111111', 'serve', 45.2, 0.85, '{"pitch_hz": 312}'),
('c1111111-1111-1111-1111-111111111111', 'return', 46.8, 0.92, '{"pitch_hz": 165, "response_latency": 1.6}'),
('c1111111-1111-1111-1111-111111111111', 'serve', 120.5, 0.78, '{"pitch_hz": 298}'),
('c1111111-1111-1111-1111-111111111111', 'return', 122.1, 0.88, '{"pitch_hz": 158, "response_latency": 1.6}'),
('c1111111-1111-1111-1111-111111111111', 'serve', 245.0, 0.91, '{"pitch_hz": 325}'),
('c1111111-1111-1111-1111-111111111111', 'return', 247.5, 0.85, '{"pitch_hz": 172, "response_latency": 2.5}'),
('c1111111-1111-1111-1111-111111111111', 'serve', 380.2, 0.82, '{"pitch_hz": 308}'),
('c1111111-1111-1111-1111-111111111111', 'missed_opportunity', 385.2, 0.76, '{"silence_duration": 6.2}'),
('c1111111-1111-1111-1111-111111111111', 'serve', 520.8, 0.89, '{"pitch_hz": 315}'),
('c1111111-1111-1111-1111-111111111111', 'return', 522.0, 0.94, '{"pitch_hz": 162, "response_latency": 1.2}'),
('c1111111-1111-1111-1111-111111111111', 'serve', 780.3, 0.87, '{"pitch_hz": 302}'),
('c1111111-1111-1111-1111-111111111111', 'return', 782.8, 0.90, '{"pitch_hz": 168, "response_latency": 2.5}'),
('c1111111-1111-1111-1111-111111111111', 'serve', 1050.0, 0.83, '{"pitch_hz": 295}'),
('c1111111-1111-1111-1111-111111111111', 'return', 1051.5, 0.91, '{"pitch_hz": 155, "response_latency": 1.5}'),
('c1111111-1111-1111-1111-111111111111', 'serve', 1320.5, 0.86, '{"pitch_hz": 318}');

-- Session 2 (Family 1, Mom, 40min): Very engaged - 18 events
INSERT INTO events (session_id, event_type, timestamp_in_session, confidence, metadata) VALUES
('c1111111-1111-1111-1111-111111111112', 'serve', 30.0, 0.88, '{"pitch_hz": 305}'),
('c1111111-1111-1111-1111-111111111112', 'return', 31.2, 0.93, '{"pitch_hz": 160, "response_latency": 1.2}'),
('c1111111-1111-1111-1111-111111111112', 'serve', 95.5, 0.85, '{"pitch_hz": 312}'),
('c1111111-1111-1111-1111-111111111112', 'return', 97.0, 0.89, '{"pitch_hz": 167, "response_latency": 1.5}'),
('c1111111-1111-1111-1111-111111111112', 'serve', 180.2, 0.91, '{"pitch_hz": 298}'),
('c1111111-1111-1111-1111-111111111112', 'return', 181.0, 0.95, '{"pitch_hz": 155, "response_latency": 0.8}'),
('c1111111-1111-1111-1111-111111111112', 'serve', 320.8, 0.82, '{"pitch_hz": 320}'),
('c1111111-1111-1111-1111-111111111112', 'return', 323.5, 0.87, '{"pitch_hz": 170, "response_latency": 2.7}'),
('c1111111-1111-1111-1111-111111111112', 'serve', 480.0, 0.86, '{"pitch_hz": 308}'),
('c1111111-1111-1111-1111-111111111112', 'return', 481.5, 0.92, '{"pitch_hz": 163, "response_latency": 1.5}'),
('c1111111-1111-1111-1111-111111111112', 'serve', 650.3, 0.89, '{"pitch_hz": 315}'),
('c1111111-1111-1111-1111-111111111112', 'missed_opportunity', 656.3, 0.74, '{"silence_duration": 5.8}'),
('c1111111-1111-1111-1111-111111111112', 'serve', 850.0, 0.84, '{"pitch_hz": 302}'),
('c1111111-1111-1111-1111-111111111112', 'return', 852.2, 0.90, '{"pitch_hz": 158, "response_latency": 2.2}'),
('c1111111-1111-1111-1111-111111111112', 'serve', 1100.5, 0.87, '{"pitch_hz": 295}'),
('c1111111-1111-1111-1111-111111111112', 'return', 1101.8, 0.93, '{"pitch_hz": 165, "response_latency": 1.3}'),
('c1111111-1111-1111-1111-111111111112', 'serve', 1400.2, 0.90, '{"pitch_hz": 310}'),
('c1111111-1111-1111-1111-111111111112', 'return', 1402.0, 0.88, '{"pitch_hz": 172, "response_latency": 1.8}');

-- Session 3 (Family 1, Mom, 30min): 12 events
INSERT INTO events (session_id, event_type, timestamp_in_session, confidence, metadata) VALUES
('c1111111-1111-1111-1111-111111111113', 'serve', 60.0, 0.86, '{"pitch_hz": 308}'),
('c1111111-1111-1111-1111-111111111113', 'return', 61.5, 0.91, '{"pitch_hz": 162, "response_latency": 1.5}'),
('c1111111-1111-1111-1111-111111111113', 'serve', 200.8, 0.83, '{"pitch_hz": 315}'),
('c1111111-1111-1111-1111-111111111113', 'return', 202.5, 0.88, '{"pitch_hz": 168, "response_latency": 1.7}'),
('c1111111-1111-1111-1111-111111111113', 'serve', 380.0, 0.89, '{"pitch_hz": 298}'),
('c1111111-1111-1111-1111-111111111113', 'missed_opportunity', 386.5, 0.72, '{"silence_duration": 7.1}'),
('c1111111-1111-1111-1111-111111111113', 'serve', 550.2, 0.85, '{"pitch_hz": 305}'),
('c1111111-1111-1111-1111-111111111113', 'return', 551.8, 0.92, '{"pitch_hz": 158, "response_latency": 1.6}'),
('c1111111-1111-1111-1111-111111111113', 'serve', 800.5, 0.87, '{"pitch_hz": 312}'),
('c1111111-1111-1111-1111-111111111113', 'return', 802.0, 0.90, '{"pitch_hz": 165, "response_latency": 1.5}'),
('c1111111-1111-1111-1111-111111111113', 'serve', 1100.0, 0.84, '{"pitch_hz": 320}'),
('c1111111-1111-1111-1111-111111111113', 'return', 1101.2, 0.89, '{"pitch_hz": 170, "response_latency": 1.2}');

-- Session 4 (Family 1, Dad, 20min): 8 events
INSERT INTO events (session_id, event_type, timestamp_in_session, confidence, metadata) VALUES
('c1111111-1111-1111-1111-111111111121', 'serve', 45.0, 0.82, '{"pitch_hz": 310}'),
('c1111111-1111-1111-1111-111111111121', 'return', 47.5, 0.86, '{"pitch_hz": 125, "response_latency": 2.5}'),
('c1111111-1111-1111-1111-111111111121', 'serve', 180.3, 0.85, '{"pitch_hz": 302}'),
('c1111111-1111-1111-1111-111111111121', 'missed_opportunity', 186.8, 0.70, '{"silence_duration": 6.8}'),
('c1111111-1111-1111-1111-111111111121', 'serve', 350.0, 0.88, '{"pitch_hz": 318}'),
('c1111111-1111-1111-1111-111111111121', 'return', 352.2, 0.91, '{"pitch_hz": 130, "response_latency": 2.2}'),
('c1111111-1111-1111-1111-111111111121', 'serve', 600.5, 0.84, '{"pitch_hz": 295}'),
('c1111111-1111-1111-1111-111111111121', 'return', 602.0, 0.87, '{"pitch_hz": 128, "response_latency": 1.5}');

-- Session 5 (Family 1, Dad, 15min): 6 events
INSERT INTO events (session_id, event_type, timestamp_in_session, confidence, metadata) VALUES
('c1111111-1111-1111-1111-111111111122', 'serve', 30.0, 0.86, '{"pitch_hz": 308}'),
('c1111111-1111-1111-1111-111111111122', 'return', 32.5, 0.89, '{"pitch_hz": 132, "response_latency": 2.5}'),
('c1111111-1111-1111-1111-111111111122', 'serve', 200.0, 0.83, '{"pitch_hz": 315}'),
('c1111111-1111-1111-1111-111111111122', 'return', 201.8, 0.90, '{"pitch_hz": 125, "response_latency": 1.8}'),
('c1111111-1111-1111-1111-111111111122', 'serve', 450.2, 0.87, '{"pitch_hz": 305}'),
('c1111111-1111-1111-1111-111111111122', 'missed_opportunity', 456.0, 0.73, '{"silence_duration": 5.5}');

-- Session 6 (Family 2, Mom, 35min): Child 30 months - 14 events
INSERT INTO events (session_id, event_type, timestamp_in_session, confidence, metadata) VALUES
('c2222222-2222-2222-2222-222222222211', 'serve', 25.0, 0.90, '{"pitch_hz": 285}'),
('c2222222-2222-2222-2222-222222222211', 'return', 26.2, 0.94, '{"pitch_hz": 175, "response_latency": 1.2}'),
('c2222222-2222-2222-2222-222222222211', 'serve', 100.5, 0.87, '{"pitch_hz": 278}'),
('c2222222-2222-2222-2222-222222222211', 'return', 102.0, 0.91, '{"pitch_hz": 168, "response_latency": 1.5}'),
('c2222222-2222-2222-2222-222222222211', 'serve', 220.0, 0.85, '{"pitch_hz": 290}'),
('c2222222-2222-2222-2222-222222222211', 'return', 221.5, 0.89, '{"pitch_hz": 172, "response_latency": 1.5}'),
('c2222222-2222-2222-2222-222222222211', 'serve', 400.3, 0.88, '{"pitch_hz": 282}'),
('c2222222-2222-2222-2222-222222222211', 'return', 401.8, 0.92, '{"pitch_hz": 165, "response_latency": 1.5}'),
('c2222222-2222-2222-2222-222222222211', 'serve', 650.0, 0.84, '{"pitch_hz": 275}'),
('c2222222-2222-2222-2222-222222222211', 'missed_opportunity', 656.2, 0.71, '{"silence_duration": 6.5}'),
('c2222222-2222-2222-2222-222222222211', 'serve', 900.5, 0.89, '{"pitch_hz": 288}'),
('c2222222-2222-2222-2222-222222222211', 'return', 902.0, 0.93, '{"pitch_hz": 170, "response_latency": 1.5}'),
('c2222222-2222-2222-2222-222222222211', 'serve', 1200.0, 0.86, '{"pitch_hz": 280}'),
('c2222222-2222-2222-2222-222222222211', 'return', 1201.5, 0.90, '{"pitch_hz": 168, "response_latency": 1.5}');

-- Session 7 (Family 2, Mom, 45min): 16 events
INSERT INTO events (session_id, event_type, timestamp_in_session, confidence, metadata) VALUES
('c2222222-2222-2222-2222-222222222212', 'serve', 40.0, 0.88, '{"pitch_hz": 282}'),
('c2222222-2222-2222-2222-222222222212', 'return', 41.5, 0.92, '{"pitch_hz": 172, "response_latency": 1.5}'),
('c2222222-2222-2222-2222-222222222212', 'serve', 150.2, 0.85, '{"pitch_hz": 290}'),
('c2222222-2222-2222-2222-222222222212', 'return', 152.0, 0.89, '{"pitch_hz": 165, "response_latency": 1.8}'),
('c2222222-2222-2222-2222-222222222212', 'serve', 280.0, 0.91, '{"pitch_hz": 278}'),
('c2222222-2222-2222-2222-222222222212', 'return', 281.2, 0.95, '{"pitch_hz": 170, "response_latency": 1.2}'),
('c2222222-2222-2222-2222-222222222212', 'serve', 450.5, 0.84, '{"pitch_hz": 285}'),
('c2222222-2222-2222-2222-222222222212', 'return', 453.0, 0.88, '{"pitch_hz": 175, "response_latency": 2.5}'),
('c2222222-2222-2222-2222-222222222212', 'serve', 700.0, 0.87, '{"pitch_hz": 280}'),
('c2222222-2222-2222-2222-222222222212', 'return', 701.5, 0.91, '{"pitch_hz": 168, "response_latency": 1.5}'),
('c2222222-2222-2222-2222-222222222212', 'serve', 950.3, 0.89, '{"pitch_hz": 288}'),
('c2222222-2222-2222-2222-222222222212', 'return', 951.8, 0.93, '{"pitch_hz": 172, "response_latency": 1.5}'),
('c2222222-2222-2222-2222-222222222212', 'serve', 1250.0, 0.83, '{"pitch_hz": 275}'),
('c2222222-2222-2222-2222-222222222212', 'missed_opportunity', 1256.5, 0.70, '{"silence_duration": 6.2}'),
('c2222222-2222-2222-2222-222222222212', 'serve', 1500.5, 0.86, '{"pitch_hz": 282}'),
('c2222222-2222-2222-2222-222222222212', 'return', 1502.0, 0.90, '{"pitch_hz": 165, "response_latency": 1.5}');

-- Session 8 (Family 2, Grandma, 30min): 10 events
INSERT INTO events (session_id, event_type, timestamp_in_session, confidence, metadata) VALUES
('c2222222-2222-2222-2222-222222222221', 'serve', 50.0, 0.84, '{"pitch_hz": 280}'),
('c2222222-2222-2222-2222-222222222221', 'return', 52.5, 0.87, '{"pitch_hz": 195, "response_latency": 2.5}'),
('c2222222-2222-2222-2222-222222222221', 'serve', 180.0, 0.82, '{"pitch_hz": 288}'),
('c2222222-2222-2222-2222-222222222221', 'missed_opportunity', 186.0, 0.68, '{"silence_duration": 6.8}'),
('c2222222-2222-2222-2222-222222222221', 'serve', 400.5, 0.86, '{"pitch_hz": 275}'),
('c2222222-2222-2222-2222-222222222221', 'return', 403.0, 0.89, '{"pitch_hz": 200, "response_latency": 2.5}'),
('c2222222-2222-2222-2222-222222222221', 'serve', 700.0, 0.85, '{"pitch_hz": 282}'),
('c2222222-2222-2222-2222-222222222221', 'return', 702.5, 0.88, '{"pitch_hz": 192, "response_latency": 2.5}'),
('c2222222-2222-2222-2222-222222222221', 'serve', 1000.2, 0.83, '{"pitch_hz": 278}'),
('c2222222-2222-2222-2222-222222222221', 'missed_opportunity', 1006.5, 0.69, '{"silence_duration": 5.8}');

-- Session 9 (Family 3, 20min): Child 12 months - higher pitch, fewer turns - 8 events
INSERT INTO events (session_id, event_type, timestamp_in_session, confidence, metadata) VALUES
('c3333333-3333-3333-3333-333333333331', 'serve', 60.0, 0.78, '{"pitch_hz": 350}'),
('c3333333-3333-3333-3333-333333333331', 'return', 62.5, 0.85, '{"pitch_hz": 170, "response_latency": 2.5}'),
('c3333333-3333-3333-3333-333333333331', 'serve', 200.0, 0.75, '{"pitch_hz": 365}'),
('c3333333-3333-3333-3333-333333333331', 'missed_opportunity', 207.0, 0.65, '{"silence_duration": 7.5}'),
('c3333333-3333-3333-3333-333333333331', 'serve', 450.5, 0.80, '{"pitch_hz": 355}'),
('c3333333-3333-3333-3333-333333333331', 'return', 453.5, 0.87, '{"pitch_hz": 165, "response_latency": 3.0}'),
('c3333333-3333-3333-3333-333333333331', 'serve', 750.0, 0.76, '{"pitch_hz": 360}'),
('c3333333-3333-3333-3333-333333333331', 'missed_opportunity', 756.5, 0.62, '{"silence_duration": 6.0}');

-- Session 10 (Family 3, 30min): 10 events
INSERT INTO events (session_id, event_type, timestamp_in_session, confidence, metadata) VALUES
('c3333333-3333-3333-3333-333333333332', 'serve', 45.0, 0.80, '{"pitch_hz": 352}'),
('c3333333-3333-3333-3333-333333333332', 'return', 47.0, 0.86, '{"pitch_hz": 168, "response_latency": 2.0}'),
('c3333333-3333-3333-3333-333333333332', 'serve', 180.5, 0.77, '{"pitch_hz": 360}'),
('c3333333-3333-3333-3333-333333333332', 'return', 183.5, 0.84, '{"pitch_hz": 172, "response_latency": 3.0}'),
('c3333333-3333-3333-3333-333333333332', 'serve', 350.0, 0.82, '{"pitch_hz": 348}'),
('c3333333-3333-3333-3333-333333333332', 'missed_opportunity', 356.5, 0.66, '{"silence_duration": 6.8}'),
('c3333333-3333-3333-3333-333333333332', 'serve', 600.0, 0.79, '{"pitch_hz": 355}'),
('c3333333-3333-3333-3333-333333333332', 'return', 602.5, 0.88, '{"pitch_hz": 165, "response_latency": 2.5}'),
('c3333333-3333-3333-3333-333333333332', 'serve', 900.2, 0.81, '{"pitch_hz": 362}'),
('c3333333-3333-3333-3333-333333333332', 'return', 902.0, 0.85, '{"pitch_hz": 170, "response_latency": 1.8}');


-- ============================================================================
-- VERIFY SEED DATA
-- ============================================================================

-- Output summary
DO $$
DECLARE
    family_count INTEGER;
    device_count INTEGER;
    session_count INTEGER;
    event_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO family_count FROM families;
    SELECT COUNT(*) INTO device_count FROM devices;
    SELECT COUNT(*) INTO session_count FROM sessions;
    SELECT COUNT(*) INTO event_count FROM events;

    RAISE NOTICE '=== Seed Data Summary ===';
    RAISE NOTICE 'Families: %', family_count;
    RAISE NOTICE 'Devices: %', device_count;
    RAISE NOTICE 'Sessions: %', session_count;
    RAISE NOTICE 'Events: %', event_count;
END $$;
