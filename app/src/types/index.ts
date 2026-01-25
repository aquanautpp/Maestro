// ============================================================================
// BLE Types
// ============================================================================

export interface BLEDevice {
  id: string;
  name: string | null;
  rssi: number | null;
  isConnected: boolean;
}

export type BLEConnectionStatus =
  | 'disconnected'
  | 'scanning'
  | 'connecting'
  | 'connected'
  | 'error';

// ============================================================================
// Event Types (from algorithm)
// ============================================================================

export type EventType = 'serve' | 'return' | 'missed_opportunity';

export interface ConversationEvent {
  id: string;
  type: EventType;
  timestampInSession: number; // seconds from session start
  confidence: number;
  metadata?: {
    pitchHz?: number;
    responseLatency?: number;
    silenceDuration?: number;
  };
  createdAt: Date;
}

// ============================================================================
// Session Types
// ============================================================================

export interface Session {
  id: string;
  deviceId: string;
  startedAt: Date;
  endedAt: Date | null;
  events: ConversationEvent[];
  synced: boolean;
}

export interface SessionSummary {
  totalServes: number;
  totalReturns: number;
  missedOpportunities: number;
  responseRate: number; // 0-1
  durationMinutes: number;
}

// ============================================================================
// Daily Stats
// ============================================================================

export interface DailyStats {
  date: string; // YYYY-MM-DD
  totalSessions: number;
  totalMinutes: number;
  totalServes: number;
  totalReturns: number;
  missedOpportunities: number;
  responseRate: number;
}

export interface WeeklyStats {
  days: DailyStats[];
  totalTurns: number;
  averageResponseRate: number;
}

// ============================================================================
// Settings Types
// ============================================================================

export type DataSharingMode = 'coach_only' | 'coach_and_school';

export interface AppSettings {
  dataSharingMode: DataSharingMode;
  deviceId: string | null;
  familyId: string | null;
  notificationsEnabled: boolean;
  onboardingCompleted: boolean;
}

// ============================================================================
// Sync Queue Types
// ============================================================================

export interface QueuedEvent {
  id: string;
  sessionId: string;
  event: ConversationEvent;
  attempts: number;
  lastAttempt: Date | null;
}

export interface SyncStatus {
  pendingEvents: number;
  lastSyncAt: Date | null;
  isSyncing: boolean;
  error: string | null;
}

// ============================================================================
// Navigation Types
// ============================================================================

export type RootTabParamList = {
  Home: undefined;
  Weekly: undefined;
  Settings: undefined;
};
