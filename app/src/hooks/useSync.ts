/**
 * Hook for background sync management.
 * Processes offline queue when network is available.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import NetInfo from '@react-native-community/netinfo';
import { processSyncQueue, isOnline } from '../services/supabase';
import { getSyncQueue } from '../services/storage';
import { SyncStatus } from '../types';

interface UseSyncReturn {
  status: SyncStatus;
  sync: () => Promise<void>;
}

const SYNC_INTERVAL_MS = 60000; // 1 minute

export function useSync(): UseSyncReturn {
  const [status, setStatus] = useState<SyncStatus>({
    pendingEvents: 0,
    lastSyncAt: null,
    isSyncing: false,
    error: null,
  });

  const syncInProgressRef = useRef(false);

  // Check queue size on mount
  useEffect(() => {
    const checkQueue = async () => {
      const queue = await getSyncQueue();
      setStatus((prev) => ({ ...prev, pendingEvents: queue.length }));
    };
    checkQueue();
  }, []);

  // Sync function
  const sync = useCallback(async () => {
    if (syncInProgressRef.current) {
      return;
    }

    syncInProgressRef.current = true;
    setStatus((prev) => ({ ...prev, isSyncing: true, error: null }));

    try {
      const result = await processSyncQueue();
      setStatus(result);
    } catch (error) {
      setStatus((prev) => ({
        ...prev,
        isSyncing: false,
        error: error instanceof Error ? error.message : 'Sync failed',
      }));
    } finally {
      syncInProgressRef.current = false;
    }
  }, []);

  // Listen for network changes
  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener(async (state) => {
      if (state.isConnected && state.isInternetReachable) {
        // Network came back online, trigger sync
        await sync();
      }
    });

    return () => unsubscribe();
  }, [sync]);

  // Periodic sync when online
  useEffect(() => {
    const interval = setInterval(async () => {
      if (await isOnline()) {
        await sync();
      }
    }, SYNC_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [sync]);

  // Initial sync
  useEffect(() => {
    sync();
  }, [sync]);

  return { status, sync };
}
