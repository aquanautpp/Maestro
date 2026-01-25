/**
 * Local storage service using AsyncStorage.
 * Handles offline data persistence and sync queue.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  AppSettings,
  Session,
  DailyStats,
  ConversationEvent,
  QueuedEvent,
} from '../types';

// Storage keys
const KEYS = {
  SETTINGS: '@ecc/settings',
  CURRENT_SESSION: '@ecc/current_session',
  SESSIONS: '@ecc/sessions',
  DAILY_STATS: '@ecc/daily_stats',
  SYNC_QUEUE: '@ecc/sync_queue',
  DEVICE_ID: '@ecc/device_id',
};

// ============================================================================
// Settings
// ============================================================================

const DEFAULT_SETTINGS: AppSettings = {
  dataSharingMode: 'coach_only',
  deviceId: null,
  familyId: null,
  notificationsEnabled: true,
  onboardingCompleted: false,
};

export async function getSettings(): Promise<AppSettings> {
  try {
    const json = await AsyncStorage.getItem(KEYS.SETTINGS);
    if (json) {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(json) };
    }
    return DEFAULT_SETTINGS;
  } catch (error) {
    console.error('Error reading settings:', error);
    return DEFAULT_SETTINGS;
  }
}

export async function saveSettings(settings: Partial<AppSettings>): Promise<void> {
  try {
    const current = await getSettings();
    const updated = { ...current, ...settings };
    await AsyncStorage.setItem(KEYS.SETTINGS, JSON.stringify(updated));
  } catch (error) {
    console.error('Error saving settings:', error);
  }
}

// ============================================================================
// Device ID (persistent identifier)
// ============================================================================

export async function getOrCreateDeviceId(): Promise<string> {
  try {
    let deviceId = await AsyncStorage.getItem(KEYS.DEVICE_ID);
    if (!deviceId) {
      // Generate a simple unique ID
      deviceId = `ECC-${Date.now().toString(36)}-${Math.random().toString(36).substr(2, 9)}`;
      await AsyncStorage.setItem(KEYS.DEVICE_ID, deviceId);
    }
    return deviceId;
  } catch (error) {
    console.error('Error with device ID:', error);
    return `ECC-${Date.now().toString(36)}`;
  }
}

// ============================================================================
// Sessions
// ============================================================================

export async function getCurrentSession(): Promise<Session | null> {
  try {
    const json = await AsyncStorage.getItem(KEYS.CURRENT_SESSION);
    if (json) {
      const session = JSON.parse(json);
      return {
        ...session,
        startedAt: new Date(session.startedAt),
        endedAt: session.endedAt ? new Date(session.endedAt) : null,
      };
    }
    return null;
  } catch (error) {
    console.error('Error reading current session:', error);
    return null;
  }
}

export async function saveCurrentSession(session: Session | null): Promise<void> {
  try {
    if (session) {
      await AsyncStorage.setItem(KEYS.CURRENT_SESSION, JSON.stringify(session));
    } else {
      await AsyncStorage.removeItem(KEYS.CURRENT_SESSION);
    }
  } catch (error) {
    console.error('Error saving current session:', error);
  }
}

export async function getSessions(): Promise<Session[]> {
  try {
    const json = await AsyncStorage.getItem(KEYS.SESSIONS);
    if (json) {
      const sessions = JSON.parse(json);
      return sessions.map((s: any) => ({
        ...s,
        startedAt: new Date(s.startedAt),
        endedAt: s.endedAt ? new Date(s.endedAt) : null,
      }));
    }
    return [];
  } catch (error) {
    console.error('Error reading sessions:', error);
    return [];
  }
}

export async function saveSession(session: Session): Promise<void> {
  try {
    const sessions = await getSessions();
    const index = sessions.findIndex((s) => s.id === session.id);
    if (index >= 0) {
      sessions[index] = session;
    } else {
      sessions.push(session);
    }
    // Keep only last 100 sessions
    const trimmed = sessions.slice(-100);
    await AsyncStorage.setItem(KEYS.SESSIONS, JSON.stringify(trimmed));
  } catch (error) {
    console.error('Error saving session:', error);
  }
}

// ============================================================================
// Daily Stats (cached)
// ============================================================================

export async function getDailyStats(days: number = 7): Promise<DailyStats[]> {
  try {
    const sessions = await getSessions();
    const now = new Date();
    const stats: Map<string, DailyStats> = new Map();

    // Initialize last N days
    for (let i = 0; i < days; i++) {
      const date = new Date(now);
      date.setDate(date.getDate() - i);
      const dateStr = date.toISOString().split('T')[0];
      stats.set(dateStr, {
        date: dateStr,
        totalSessions: 0,
        totalMinutes: 0,
        totalServes: 0,
        totalReturns: 0,
        missedOpportunities: 0,
        responseRate: 0,
      });
    }

    // Aggregate from sessions
    for (const session of sessions) {
      const dateStr = session.startedAt.toISOString().split('T')[0];
      const dayStat = stats.get(dateStr);
      if (dayStat && session.endedAt) {
        dayStat.totalSessions++;
        dayStat.totalMinutes +=
          (session.endedAt.getTime() - session.startedAt.getTime()) / 60000;

        for (const event of session.events) {
          if (event.type === 'serve') dayStat.totalServes++;
          if (event.type === 'return') dayStat.totalReturns++;
          if (event.type === 'missed_opportunity') dayStat.missedOpportunities++;
        }

        dayStat.responseRate =
          dayStat.totalServes > 0
            ? dayStat.totalReturns / dayStat.totalServes
            : 0;
      }
    }

    return Array.from(stats.values()).sort((a, b) => a.date.localeCompare(b.date));
  } catch (error) {
    console.error('Error calculating daily stats:', error);
    return [];
  }
}

export async function getTodayTurns(): Promise<number> {
  const stats = await getDailyStats(1);
  if (stats.length > 0) {
    return stats[0].totalServes + stats[0].totalReturns;
  }
  return 0;
}

// ============================================================================
// Sync Queue (offline-first)
// ============================================================================

export async function addToSyncQueue(
  sessionId: string,
  event: ConversationEvent
): Promise<void> {
  try {
    const queue = await getSyncQueue();
    const queuedEvent: QueuedEvent = {
      id: `${sessionId}-${event.id}`,
      sessionId,
      event,
      attempts: 0,
      lastAttempt: null,
    };
    queue.push(queuedEvent);
    await AsyncStorage.setItem(KEYS.SYNC_QUEUE, JSON.stringify(queue));
  } catch (error) {
    console.error('Error adding to sync queue:', error);
  }
}

export async function getSyncQueue(): Promise<QueuedEvent[]> {
  try {
    const json = await AsyncStorage.getItem(KEYS.SYNC_QUEUE);
    if (json) {
      return JSON.parse(json);
    }
    return [];
  } catch (error) {
    console.error('Error reading sync queue:', error);
    return [];
  }
}

export async function removeFromSyncQueue(ids: string[]): Promise<void> {
  try {
    const queue = await getSyncQueue();
    const filtered = queue.filter((item) => !ids.includes(item.id));
    await AsyncStorage.setItem(KEYS.SYNC_QUEUE, JSON.stringify(filtered));
  } catch (error) {
    console.error('Error removing from sync queue:', error);
  }
}

export async function updateSyncQueueItem(
  id: string,
  updates: Partial<QueuedEvent>
): Promise<void> {
  try {
    const queue = await getSyncQueue();
    const index = queue.findIndex((item) => item.id === id);
    if (index >= 0) {
      queue[index] = { ...queue[index], ...updates };
      await AsyncStorage.setItem(KEYS.SYNC_QUEUE, JSON.stringify(queue));
    }
  } catch (error) {
    console.error('Error updating sync queue item:', error);
  }
}

// ============================================================================
// Clear all data (for testing/reset)
// ============================================================================

export async function clearAllData(): Promise<void> {
  try {
    await AsyncStorage.multiRemove(Object.values(KEYS));
  } catch (error) {
    console.error('Error clearing data:', error);
  }
}
