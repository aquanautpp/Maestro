/**
 * BLE Manager for connecting to ECC wearable devices.
 *
 * Protocol:
 * - Device name prefix: "ECC-"
 * - Service UUID: Custom service for events
 * - Characteristics: Event notifications, status, settings
 */

import { BleManager, Device, Characteristic, BleError } from 'react-native-ble-plx';
import { Platform, PermissionsAndroid } from 'react-native';
import { BLEDevice, BLEConnectionStatus, ConversationEvent, EventType } from '../../types';

// BLE UUIDs (must match ESP32 firmware)
const SERVICE_UUID = '12345678-1234-5678-1234-56789abcdef0';
const EVENT_CHAR_UUID = '12345678-1234-5678-1234-56789abcdef1';
const STATUS_CHAR_UUID = '12345678-1234-5678-1234-56789abcdef2';
const SETTINGS_CHAR_UUID = '12345678-1234-5678-1234-56789abcdef3';

// Device name prefix
const DEVICE_NAME_PREFIX = 'ECC-';

// Singleton BLE manager
let bleManager: BleManager | null = null;

function getManager(): BleManager {
  if (!bleManager) {
    bleManager = new BleManager();
  }
  return bleManager;
}

// ============================================================================
// Permissions
// ============================================================================

export async function requestBLEPermissions(): Promise<boolean> {
  if (Platform.OS === 'android') {
    const apiLevel = Platform.Version;

    if (apiLevel >= 31) {
      // Android 12+
      const results = await PermissionsAndroid.requestMultiple([
        PermissionsAndroid.PERMISSIONS.BLUETOOTH_SCAN,
        PermissionsAndroid.PERMISSIONS.BLUETOOTH_CONNECT,
        PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
      ]);

      return (
        results[PermissionsAndroid.PERMISSIONS.BLUETOOTH_SCAN] === 'granted' &&
        results[PermissionsAndroid.PERMISSIONS.BLUETOOTH_CONNECT] === 'granted' &&
        results[PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION] === 'granted'
      );
    } else {
      // Android 11 and below
      const result = await PermissionsAndroid.request(
        PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION
      );
      return result === 'granted';
    }
  }

  // iOS permissions handled in Info.plist
  return true;
}

// ============================================================================
// Scanning
// ============================================================================

export type ScanCallback = (device: BLEDevice) => void;

let scanSubscription: any = null;

export async function startScan(
  onDeviceFound: ScanCallback,
  onError: (error: string) => void
): Promise<void> {
  const manager = getManager();

  // Check permissions
  const hasPermission = await requestBLEPermissions();
  if (!hasPermission) {
    onError('Bluetooth permissions not granted');
    return;
  }

  // Check if Bluetooth is enabled
  const state = await manager.state();
  if (state !== 'PoweredOn') {
    onError('Bluetooth is not enabled');
    return;
  }

  // Stop any existing scan
  await stopScan();

  // Start scanning for devices with ECC- prefix
  scanSubscription = manager.startDeviceScan(
    null, // Scan for all services
    { allowDuplicates: false },
    (error, device) => {
      if (error) {
        console.error('Scan error:', error);
        onError(error.message);
        return;
      }

      if (device && device.name?.startsWith(DEVICE_NAME_PREFIX)) {
        onDeviceFound({
          id: device.id,
          name: device.name,
          rssi: device.rssi,
          isConnected: false,
        });
      }
    }
  );

  // Auto-stop after 30 seconds
  setTimeout(() => {
    stopScan();
  }, 30000);
}

export async function stopScan(): Promise<void> {
  const manager = getManager();
  manager.stopDeviceScan();
  scanSubscription = null;
}

// ============================================================================
// Connection
// ============================================================================

let connectedDevice: Device | null = null;
let eventSubscription: any = null;

export async function connectToDevice(
  deviceId: string,
  onStatusChange: (status: BLEConnectionStatus) => void,
  onEvent: (event: ConversationEvent) => void,
  onError: (error: string) => void
): Promise<boolean> {
  const manager = getManager();

  try {
    onStatusChange('connecting');

    // Connect to device
    const device = await manager.connectToDevice(deviceId, {
      timeout: 10000,
    });

    // Discover services and characteristics
    await device.discoverAllServicesAndCharacteristics();

    // Store reference
    connectedDevice = device;

    // Set up disconnect listener
    device.onDisconnected((error, disconnectedDevice) => {
      console.log('Device disconnected:', disconnectedDevice?.id);
      connectedDevice = null;
      eventSubscription?.remove();
      eventSubscription = null;
      onStatusChange('disconnected');
    });

    // Subscribe to event notifications
    await subscribeToEvents(device, onEvent, onError);

    onStatusChange('connected');
    return true;
  } catch (error) {
    console.error('Connection error:', error);
    onStatusChange('error');
    onError(error instanceof Error ? error.message : 'Connection failed');
    return false;
  }
}

export async function disconnectDevice(): Promise<void> {
  if (connectedDevice) {
    try {
      eventSubscription?.remove();
      eventSubscription = null;
      await connectedDevice.cancelConnection();
      connectedDevice = null;
    } catch (error) {
      console.error('Disconnect error:', error);
    }
  }
}

export function isDeviceConnected(): boolean {
  return connectedDevice !== null;
}

export async function getConnectedDevice(): Promise<BLEDevice | null> {
  if (!connectedDevice) return null;

  return {
    id: connectedDevice.id,
    name: connectedDevice.name,
    rssi: connectedDevice.rssi,
    isConnected: true,
  };
}

// ============================================================================
// Event Subscription
// ============================================================================

async function subscribeToEvents(
  device: Device,
  onEvent: (event: ConversationEvent) => void,
  onError: (error: string) => void
): Promise<void> {
  try {
    eventSubscription = device.monitorCharacteristicForService(
      SERVICE_UUID,
      EVENT_CHAR_UUID,
      (error, characteristic) => {
        if (error) {
          console.error('Event notification error:', error);
          onError(error.message);
          return;
        }

        if (characteristic?.value) {
          try {
            const event = parseEventData(characteristic.value);
            if (event) {
              onEvent(event);
            }
          } catch (e) {
            console.error('Error parsing event:', e);
          }
        }
      }
    );
  } catch (error) {
    console.error('Subscribe error:', error);
    onError(error instanceof Error ? error.message : 'Subscribe failed');
  }
}

// ============================================================================
// Data Parsing
// ============================================================================

function parseEventData(base64Data: string): ConversationEvent | null {
  try {
    // Decode base64 to string
    const jsonString = atob(base64Data);
    const data = JSON.parse(jsonString);

    // Validate required fields
    if (!data.type || data.timestamp === undefined) {
      return null;
    }

    // Map to our event type
    const eventType: EventType = data.type;
    if (!['serve', 'return', 'missed_opportunity'].includes(eventType)) {
      return null;
    }

    return {
      id: data.id || `evt-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type: eventType,
      timestampInSession: data.timestamp,
      confidence: data.confidence || 0.8,
      metadata: {
        pitchHz: data.pitch_hz,
        responseLatency: data.response_latency,
        silenceDuration: data.silence_duration,
      },
      createdAt: new Date(),
    };
  } catch (error) {
    console.error('Error parsing event data:', error);
    return null;
  }
}

// ============================================================================
// Mock Mode (for development without hardware)
// ============================================================================

let mockMode = false;
let mockInterval: NodeJS.Timeout | null = null;

export function enableMockMode(enabled: boolean): void {
  mockMode = enabled;
}

export function isMockModeEnabled(): boolean {
  return mockMode;
}

export function startMockEvents(onEvent: (event: ConversationEvent) => void): void {
  if (!mockMode) return;

  let timestampCounter = 0;

  mockInterval = setInterval(() => {
    // Randomly generate events
    const rand = Math.random();
    let type: EventType;
    let metadata: ConversationEvent['metadata'] = {};

    if (rand < 0.4) {
      type = 'serve';
      metadata = { pitchHz: 280 + Math.random() * 80 };
    } else if (rand < 0.85) {
      type = 'return';
      metadata = {
        pitchHz: 120 + Math.random() * 80,
        responseLatency: 0.5 + Math.random() * 2,
      };
    } else {
      type = 'missed_opportunity';
      metadata = { silenceDuration: 5 + Math.random() * 3 };
    }

    timestampCounter += 5 + Math.random() * 20;

    const event: ConversationEvent = {
      id: `mock-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type,
      timestampInSession: timestampCounter,
      confidence: 0.7 + Math.random() * 0.3,
      metadata,
      createdAt: new Date(),
    };

    onEvent(event);
  }, 3000 + Math.random() * 5000); // Random interval 3-8 seconds
}

export function stopMockEvents(): void {
  if (mockInterval) {
    clearInterval(mockInterval);
    mockInterval = null;
  }
}

// ============================================================================
// Cleanup
// ============================================================================

export function destroy(): void {
  stopScan();
  stopMockEvents();
  disconnectDevice();
  if (bleManager) {
    bleManager.destroy();
    bleManager = null;
  }
}
