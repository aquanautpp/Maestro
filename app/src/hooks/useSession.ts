/**
 * Hook for session management.
 * Handles starting/stopping sessions, tracking events, and generating summaries.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import {
  getCurrentSession,
  saveCurrentSession,
  saveSession,
  addToSyncQueue,
  getDailyStats,
  getTodayTurns,
  getOrCreateDeviceId,
} from '../services/storage';
import { syncSession } from '../services/supabase';
import { showSessionSummaryNotification } from '../services/notifications';
import { Session, SessionSummary, ConversationEvent, DailyStats } from '../types';

interface UseSessionReturn {
  // State
  currentSession: Session | null;
  isActive: boolean;
  todayTurns: number;
  dailyStats: DailyStats[];

  // Actions
  startSession: () => Promise<void>;
  stopSession: () => Promise<SessionSummary | null>;
  addEvent: (event: ConversationEvent) => Promise<void>;
  refreshStats: () => Promise<void>;
}

function generateSessionId(): string {
  return `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

function calculateSummary(session: Session): SessionSummary {
  const totalServes = session.events.filter((e) => e.type === 'serve').length;
  const totalReturns = session.events.filter((e) => e.type === 'return').length;
  const missedOpportunities = session.events.filter(
    (e) => e.type === 'missed_opportunity'
  ).length;

  const durationMinutes = session.endedAt
    ? (session.endedAt.getTime() - session.startedAt.getTime()) / 60000
    : 0;

  return {
    totalServes,
    totalReturns,
    missedOpportunities,
    responseRate: totalServes > 0 ? totalReturns / totalServes : 0,
    durationMinutes,
  };
}

export function useSession(): UseSessionReturn {
  const [currentSession, setCurrentSession] = useState<Session | null>(null);
  const [todayTurns, setTodayTurns] = useState(0);
  const [dailyStats, setDailyStats] = useState<DailyStats[]>([]);

  const sessionRef = useRef<Session | null>(null);

  // Keep ref in sync with state
  useEffect(() => {
    sessionRef.current = currentSession;
  }, [currentSession]);

  // Load persisted session and stats on mount
  useEffect(() => {
    const loadData = async () => {
      const persisted = await getCurrentSession();
      if (persisted) {
        setCurrentSession(persisted);
      }
      await refreshStats();
    };
    loadData();
  }, []);

  // Refresh stats
  const refreshStats = useCallback(async () => {
    const turns = await getTodayTurns();
    setTodayTurns(turns);

    const stats = await getDailyStats(7);
    setDailyStats(stats);
  }, []);

  // Start a new session
  const startSession = useCallback(async () => {
    const deviceId = await getOrCreateDeviceId();

    const newSession: Session = {
      id: generateSessionId(),
      deviceId,
      startedAt: new Date(),
      endedAt: null,
      events: [],
      synced: false,
    };

    setCurrentSession(newSession);
    await saveCurrentSession(newSession);

    // Sync session start to backend
    syncSession(newSession).catch(console.error);
  }, []);

  // Stop current session
  const stopSession = useCallback(async (): Promise<SessionSummary | null> => {
    const session = sessionRef.current;
    if (!session) return null;

    const endedSession: Session = {
      ...session,
      endedAt: new Date(),
    };

    // Calculate summary before clearing session
    const summary = calculateSummary(endedSession);

    // Save completed session
    await saveSession(endedSession);
    await saveCurrentSession(null);
    setCurrentSession(null);

    // Sync to backend
    syncSession(endedSession).catch(console.error);

    // Show notification with summary
    await showSessionSummaryNotification(summary);

    // Refresh stats
    await refreshStats();

    return summary;
  }, [refreshStats]);

  // Add event to current session
  const addEvent = useCallback(async (event: ConversationEvent) => {
    const session = sessionRef.current;
    if (!session) {
      console.warn('No active session, ignoring event');
      return;
    }

    const updatedSession: Session = {
      ...session,
      events: [...session.events, event],
    };

    setCurrentSession(updatedSession);
    await saveCurrentSession(updatedSession);

    // Add to sync queue for backend
    await addToSyncQueue(session.id, event);

    // Update today's turns count
    if (event.type === 'serve' || event.type === 'return') {
      setTodayTurns((prev) => prev + 1);
    }
  }, []);

  return {
    currentSession,
    isActive: currentSession !== null,
    todayTurns,
    dailyStats,
    startSession,
    stopSession,
    addEvent,
    refreshStats,
  };
}
