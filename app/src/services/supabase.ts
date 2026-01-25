/**
 * Supabase client and sync service.
 * Handles backend communication with offline queue support.
 */

import { createClient } from '@supabase/supabase-js';
import NetInfo from '@react-native-community/netinfo';
import {
  getSyncQueue,
  removeFromSyncQueue,
  updateSyncQueueItem,
  getSettings,
} from './storage';
import { ConversationEvent, Session, SyncStatus } from '../types';

// Supabase configuration
// In production, these would come from environment variables
const SUPABASE_URL = process.env.EXPO_PUBLIC_SUPABASE_URL || 'https://your-project.supabase.co';
const SUPABASE_ANON_KEY = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY || 'your-anon-key';

// Create Supabase client
export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: {
    persistSession: false, // We use device ID, not auth
  },
});

// ============================================================================
// Connectivity Check
// ============================================================================

export async function isOnline(): Promise<boolean> {
  try {
    const state = await NetInfo.fetch();
    return state.isConnected === true && state.isInternetReachable === true;
  } catch {
    return false;
  }
}

// ============================================================================
// Session Sync
// ============================================================================

export async function syncSession(session: Session): Promise<boolean> {
  if (!(await isOnline())) {
    console.log('Offline, skipping sync');
    return false;
  }

  const settings = await getSettings();
  if (!settings.deviceId) {
    console.error('No device ID, cannot sync');
    return false;
  }

  try {
    // First, ensure session exists in backend
    const { data: existingSession, error: fetchError } = await supabase
      .from('sessions')
      .select('id')
      .eq('id', session.id)
      .single();

    if (fetchError && fetchError.code !== 'PGRST116') {
      // PGRST116 = not found, which is fine
      console.error('Error checking session:', fetchError);
      return false;
    }

    if (!existingSession) {
      // Create session
      const { error: createError } = await supabase.from('sessions').insert({
        id: session.id,
        device_id: settings.deviceId,
        started_at: session.startedAt.toISOString(),
        ended_at: session.endedAt?.toISOString() || null,
        status: session.endedAt ? 'completed' : 'active',
      });

      if (createError) {
        console.error('Error creating session:', createError);
        return false;
      }
    } else if (session.endedAt) {
      // Update session end time
      const { error: updateError } = await supabase
        .from('sessions')
        .update({
          ended_at: session.endedAt.toISOString(),
          status: 'completed',
        })
        .eq('id', session.id);

      if (updateError) {
        console.error('Error updating session:', updateError);
        return false;
      }
    }

    return true;
  } catch (error) {
    console.error('Error syncing session:', error);
    return false;
  }
}

// ============================================================================
// Event Sync
// ============================================================================

export async function syncEvent(
  sessionId: string,
  event: ConversationEvent
): Promise<boolean> {
  if (!(await isOnline())) {
    return false;
  }

  try {
    const { error } = await supabase.from('events').insert({
      id: event.id,
      session_id: sessionId,
      event_type: event.type,
      timestamp_in_session: event.timestampInSession,
      confidence: event.confidence,
      metadata: event.metadata || {},
      created_at: event.createdAt.toISOString(),
    });

    if (error) {
      // Ignore duplicate errors
      if (error.code === '23505') {
        return true;
      }
      console.error('Error syncing event:', error);
      return false;
    }

    return true;
  } catch (error) {
    console.error('Error syncing event:', error);
    return false;
  }
}

// ============================================================================
// Queue Processing
// ============================================================================

const MAX_RETRY_ATTEMPTS = 5;

export async function processSyncQueue(): Promise<SyncStatus> {
  const queue = await getSyncQueue();
  const status: SyncStatus = {
    pendingEvents: queue.length,
    lastSyncAt: null,
    isSyncing: true,
    error: null,
  };

  if (queue.length === 0) {
    return { ...status, isSyncing: false };
  }

  if (!(await isOnline())) {
    return { ...status, isSyncing: false, error: 'Offline' };
  }

  const successfulIds: string[] = [];
  const now = new Date();

  for (const item of queue) {
    // Skip items that have been retried too many times
    if (item.attempts >= MAX_RETRY_ATTEMPTS) {
      successfulIds.push(item.id); // Remove from queue
      continue;
    }

    try {
      const success = await syncEvent(item.sessionId, item.event);
      if (success) {
        successfulIds.push(item.id);
      } else {
        await updateSyncQueueItem(item.id, {
          attempts: item.attempts + 1,
          lastAttempt: now,
        });
      }
    } catch (error) {
      console.error('Error processing queue item:', error);
      await updateSyncQueueItem(item.id, {
        attempts: item.attempts + 1,
        lastAttempt: now,
      });
    }
  }

  // Remove successfully synced items
  if (successfulIds.length > 0) {
    await removeFromSyncQueue(successfulIds);
  }

  return {
    pendingEvents: queue.length - successfulIds.length,
    lastSyncAt: now,
    isSyncing: false,
    error: null,
  };
}

// ============================================================================
// Fetch Data from Backend
// ============================================================================

export async function fetchWeeklyStats(deviceId: string) {
  if (!(await isOnline())) {
    return null;
  }

  try {
    const sevenDaysAgo = new Date();
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

    const { data, error } = await supabase
      .from('sessions')
      .select(`
        id,
        started_at,
        ended_at,
        total_serves,
        total_returns,
        total_missed
      `)
      .eq('device_id', deviceId)
      .eq('status', 'completed')
      .gte('started_at', sevenDaysAgo.toISOString())
      .order('started_at', { ascending: true });

    if (error) {
      console.error('Error fetching weekly stats:', error);
      return null;
    }

    return data;
  } catch (error) {
    console.error('Error fetching weekly stats:', error);
    return null;
  }
}
