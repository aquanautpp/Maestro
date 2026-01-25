/**
 * Hook for BLE device management.
 * Handles scanning, connecting, and receiving events from the wearable.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import {
  startScan,
  stopScan,
  connectToDevice,
  disconnectDevice,
  isDeviceConnected,
  getConnectedDevice,
  requestBLEPermissions,
  enableMockMode,
  isMockModeEnabled,
  startMockEvents,
  stopMockEvents,
} from '../services/ble/manager';
import { BLEDevice, BLEConnectionStatus, ConversationEvent } from '../types';

interface UseBLEReturn {
  // State
  status: BLEConnectionStatus;
  device: BLEDevice | null;
  discoveredDevices: BLEDevice[];
  error: string | null;
  isScanning: boolean;

  // Actions
  scan: () => Promise<void>;
  connect: (deviceId: string) => Promise<boolean>;
  disconnect: () => Promise<void>;
  setMockMode: (enabled: boolean) => void;

  // Event callback
  onEvent: (callback: (event: ConversationEvent) => void) => void;
}

export function useBLE(): UseBLEReturn {
  const [status, setStatus] = useState<BLEConnectionStatus>('disconnected');
  const [device, setDevice] = useState<BLEDevice | null>(null);
  const [discoveredDevices, setDiscoveredDevices] = useState<BLEDevice[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isScanning, setIsScanning] = useState(false);

  const eventCallbackRef = useRef<((event: ConversationEvent) => void) | null>(null);

  // Check initial connection state
  useEffect(() => {
    const checkConnection = async () => {
      const connected = await getConnectedDevice();
      if (connected) {
        setDevice(connected);
        setStatus('connected');
      }
    };
    checkConnection();
  }, []);

  // Handle event callback
  const handleEvent = useCallback((event: ConversationEvent) => {
    if (eventCallbackRef.current) {
      eventCallbackRef.current(event);
    }
  }, []);

  // Set event callback
  const onEvent = useCallback((callback: (event: ConversationEvent) => void) => {
    eventCallbackRef.current = callback;
  }, []);

  // Scan for devices
  const scan = useCallback(async () => {
    setError(null);
    setDiscoveredDevices([]);
    setIsScanning(true);

    const hasPermission = await requestBLEPermissions();
    if (!hasPermission) {
      setError('Permissões de Bluetooth necessárias');
      setIsScanning(false);
      return;
    }

    await startScan(
      (foundDevice) => {
        setDiscoveredDevices((prev) => {
          // Avoid duplicates
          if (prev.some((d) => d.id === foundDevice.id)) {
            return prev;
          }
          return [...prev, foundDevice];
        });
      },
      (err) => {
        setError(err);
        setIsScanning(false);
      }
    );

    // Auto-stop after 30s
    setTimeout(() => {
      stopScan();
      setIsScanning(false);
    }, 30000);
  }, []);

  // Connect to device
  const connect = useCallback(
    async (deviceId: string): Promise<boolean> => {
      setError(null);

      // Check for mock mode
      if (isMockModeEnabled()) {
        setStatus('connected');
        setDevice({
          id: 'mock-device',
          name: 'ECC-MOCK',
          rssi: -50,
          isConnected: true,
        });
        startMockEvents(handleEvent);
        return true;
      }

      const success = await connectToDevice(
        deviceId,
        setStatus,
        handleEvent,
        (err) => setError(err)
      );

      if (success) {
        const connected = await getConnectedDevice();
        setDevice(connected);
      }

      return success;
    },
    [handleEvent]
  );

  // Disconnect
  const disconnect = useCallback(async () => {
    if (isMockModeEnabled()) {
      stopMockEvents();
    }
    await disconnectDevice();
    setDevice(null);
    setStatus('disconnected');
  }, []);

  // Set mock mode
  const setMockMode = useCallback((enabled: boolean) => {
    enableMockMode(enabled);
    if (!enabled && isMockModeEnabled()) {
      stopMockEvents();
      setDevice(null);
      setStatus('disconnected');
    }
  }, []);

  return {
    status,
    device,
    discoveredDevices,
    error,
    isScanning,
    scan,
    connect,
    disconnect,
    setMockMode,
    onEvent,
  };
}
