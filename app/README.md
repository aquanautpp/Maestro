# App Module

React Native mobile app for the Early Childhood Coach system.

## Screenshots

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│     HOME        │  │     WEEKLY      │  │    SETTINGS     │
├─────────────────┤  ├─────────────────┤  ├─────────────────┤
│                 │  │                 │  │                 │
│  Olá! 👋       │  │  Semana         │  │  Configurações  │
│  Vamos         │  │  Últimos 7 dias │  │                 │
│  conversar?    │  │                 │  │  ○ Modo Coach   │
│                 │  │  ┌───────────┐ │  │  ○ Coach+Escola │
│  ┌───────────┐ │  │  │  📈 Chart │ │  │                 │
│  │ 🔵 Conectado│ │  │  └───────────┘ │  │  ┌───────────┐ │
│  └───────────┘ │  │                 │  │  │ Device ID │ │
│                 │  │  ┌────┐ ┌────┐ │  │  │ ECC-xxx   │ │
│      48        │  │  │ 48 │ │ 12 │ │  │  └───────────┘ │
│     turns      │  │  │turn│ │sess│ │  │                 │
│                 │  │  └────┘ └────┘ │  │  [Sincronizar] │
│  ┌───────────┐ │  │                 │  │                 │
│  │  INICIAR  │ │  │  🌟 Melhor dia │  │                 │
│  │  SESSÃO   │ │  │  Terça: 15     │  │                 │
│  └───────────┘ │  │                 │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## Quick Start

```bash
cd app

# Install dependencies
npm install

# Start Expo dev server
npx expo start

# Run on device/simulator
npx expo run:ios      # iOS
npx expo run:android  # Android
```

## Features

### 1. BLE Connection
- Scans for devices with prefix `ECC-`
- Auto-connects when device found
- Receives real-time events from wearable

### 2. Session Management
- Start/Stop recording sessions
- Track conversational turns in real-time
- Local persistence (works offline)

### 3. Weekly Summary
- Chart showing turns per day (last 7 days)
- Stats: total turns, sessions, response rate
- Highlights best day

### 4. Offline-First Sync
- Events queued locally when offline
- Auto-sync when WiFi available
- Manual sync button in settings

### 5. Local Notifications
- Session summary after each session
- Positive, encouraging messages

## Project Structure

```
app/
├── App.tsx                    # Entry point
├── app.json                   # Expo configuration
├── package.json
├── tsconfig.json
├── assets/                    # Icons, splash screen
└── src/
    ├── components/            # Reusable UI components
    │   ├── Button.tsx
    │   ├── Card.tsx
    │   ├── StatusIndicator.tsx
    │   └── TurnsCounter.tsx
    │
    ├── screens/               # App screens
    │   ├── HomeScreen.tsx     # Main screen with session control
    │   ├── WeeklyScreen.tsx   # Weekly chart and stats
    │   └── SettingsScreen.tsx # Consent and device info
    │
    ├── services/              # Business logic
    │   ├── storage.ts         # AsyncStorage wrapper
    │   ├── supabase.ts        # Backend sync
    │   ├── notifications.ts   # Local notifications
    │   └── ble/
    │       └── manager.ts     # BLE connection management
    │
    ├── hooks/                 # Custom React hooks
    │   ├── useBLE.ts          # BLE state and actions
    │   ├── useSession.ts      # Session management
    │   └── useSync.ts         # Background sync
    │
    ├── navigation/
    │   └── AppNavigator.tsx   # Bottom tab navigation
    │
    ├── theme/
    │   └── index.ts           # Colors, spacing, typography
    │
    └── types/
        └── index.ts           # TypeScript definitions
```

## Design System

### Colors
```
Primary:    #4CAF50 (calming green)
Secondary:  #64B5F6 (soft blue)
Background: #F5F9F5 (light green tint)
Text:       #2E3D2E (dark green-gray)
```

### Principles
- Large, readable fonts
- Minimal text
- Positive, encouraging tone
- Never blame or guilt-trip

## BLE Protocol

### Device Discovery
- Scan for devices with name starting with `ECC-`
- Auto-connect to first found device

### Service UUID
```
Service:      12345678-1234-5678-1234-56789abcdef0
Events:       12345678-1234-5678-1234-56789abcdef1 (notify)
Status:       12345678-1234-5678-1234-56789abcdef2 (read)
Settings:     12345678-1234-5678-1234-56789abcdef3 (read/write)
```

### Event Format (JSON over BLE)
```json
{
  "type": "serve|return|missed_opportunity",
  "timestamp": 45.2,
  "confidence": 0.85,
  "pitch_hz": 312,
  "response_latency": 1.6
}
```

## Mock Mode

For development without hardware:

```typescript
import { enableMockMode } from './src/services/ble/manager';

// Enable mock mode
enableMockMode(true);

// Connect to mock device
const { connect } = useBLE();
await connect('mock-device');
```

Mock mode generates random events every 3-8 seconds.

## Environment Variables

Create `.env`:

```env
EXPO_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
EXPO_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

## Building for Production

```bash
# Install EAS CLI
npm install -g eas-cli

# Configure EAS
eas build:configure

# Build for iOS
eas build --platform ios

# Build for Android
eas build --platform android
```

## Testing

```bash
# Run tests
npm test

# Type check
npm run typecheck

# Lint
npm run lint
```

## Dependencies

| Package | Purpose |
|---------|---------|
| expo | React Native framework |
| react-native-ble-plx | BLE communication |
| @react-navigation/* | Navigation |
| @supabase/supabase-js | Backend sync |
| react-native-chart-kit | Weekly chart |
| expo-notifications | Local notifications |
| @react-native-async-storage/async-storage | Local storage |

## Troubleshooting

### BLE not working in Expo Go
BLE requires a development build, not Expo Go:
```bash
npx expo run:ios  # or run:android
```

### "Bluetooth permissions not granted"
- iOS: Check Info.plist has NSBluetoothAlwaysUsageDescription
- Android: Ensure location permissions granted (required for BLE scan)

### Events not syncing
1. Check internet connection
2. Go to Settings > tap "Sincronizar agora"
3. Check Supabase credentials in .env
