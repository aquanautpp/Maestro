# Firmware Module

ESP32-S3 firmware for the Early Childhood Coach wearable device.

## Hardware Requirements

| Component | Part | Connection |
|-----------|------|------------|
| MCU | ESP32-S3-DevKitC-1 | - |
| Microphone | INMP441 I2S MEMS | SD→GPIO4, SCK→GPIO5, WS→GPIO6 |
| Haptic Motor | ERM 3V | GPIO7 (via 2N2222 + resistor) |
| LED | RGB common cathode | R→GPIO38, G→GPIO39, B→GPIO40 |
| Battery | 3.7V LiPo 800mAh | Via TP4056 charger |

## Pin Configuration

```
ESP32-S3 DevKitC-1
┌─────────────────────────────────────┐
│                USB                  │
├─────────────────────────────────────┤
│ GPIO4  ← I2S SD (mic data)          │
│ GPIO5  ← I2S SCK (clock)            │
│ GPIO6  ← I2S WS (word select)       │
│ GPIO7  → Haptic motor (PWM)         │
│ GPIO38 → LED Red (PWM)              │
│ GPIO39 → LED Green (PWM)            │
│ GPIO40 → LED Blue (PWM)             │
│ 3.3V   → INMP441 VDD                │
│ GND    → INMP441 GND, LED cathode   │
└─────────────────────────────────────┘
```

## Quick Start

```bash
# Install PlatformIO (if not installed)
pip install platformio

# Build
cd firmware
pio run

# Upload
pio run --target upload

# Monitor serial
pio device monitor
```

## Project Structure

```
firmware/
├── platformio.ini          # PlatformIO configuration
├── scripts/
│   └── version.py          # Build script for version injection
└── src/
    ├── main.cpp            # Entry point, main loop
    ├── audio_capture.h/cpp # I2S microphone capture
    ├── vad_detector.h/cpp  # Voice Activity Detection
    ├── ble_service.h/cpp   # BLE GATT server
    └── feedback.h/cpp      # LED + haptic control
```

## Module Overview

### audio_capture
- Configures ESP32 I2S peripheral for INMP441
- Maintains 10-second circular buffer
- Provides 30ms audio frames for processing
- 16kHz sample rate, 16-bit mono

### vad_detector
- Energy-based Voice Activity Detection
- Adaptive threshold (learns noise floor)
- State machine: SILENCE → SPEECH → HANGOVER
- Reports speech segments with timing

### ble_service
- BLE GATT server with custom service
- Characteristics:
  - `session_control` (write): "start"/"stop"
  - `event_stream` (notify): JSON events
  - `device_status` (read): battery, uptime

### feedback
- RGB LED control with PWM
- Haptic motor patterns
- Predefined feedback types:
  - Session start/end
  - Successful turn
  - Missed opportunity
  - Connection status

## BLE Protocol

### Service UUID
```
12345678-1234-5678-1234-56789abcdef0
```

### Characteristics

| Name | UUID | Properties | Description |
|------|------|------------|-------------|
| session_control | ...def1 | Write | "start" or "stop" |
| event_stream | ...def2 | Notify | JSON events |
| device_status | ...def3 | Read | JSON status |

### Event Format (JSON)
```json
{
  "type": "serve|return|missed_opportunity",
  "timestamp": 45.2,
  "confidence": 0.85,
  "pitch_hz": 312,
  "response_latency": 1.6,
  "silence_duration": 5.5
}
```

### Status Format (JSON)
```json
{
  "battery": 85,
  "charging": false,
  "uptime": 3600,
  "session_active": true,
  "events": 42
}
```

## Conversation Detection Logic

```
┌─────────────────────────────────────────────────────────┐
│                    STATE MACHINE                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  IDLE ──(child speaks)──► WAITING_FOR_RESPONSE          │
│    │                            │                        │
│    │                            ├──(adult <3s)──► RETURN │
│    │                            │                        │
│    │                            └──(silence >5s)──► MISS │
│    │                                                     │
│    └──(adult speaks)──► (ignore, no serve)              │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Detection Thresholds

| Parameter | Default | Description |
|-----------|---------|-------------|
| Response threshold | 3000ms | Max time for "return" |
| Missed threshold | 5000ms | Silence for "missed opportunity" |
| VAD threshold | 0.02 | Energy threshold for speech |
| Min speech | 100ms | Minimum speech duration |
| Min silence | 300ms | Minimum silence to end segment |

## Configuration

Edit defines in `platformio.ini` or source files:

```ini
build_flags =
    -DI2S_SAMPLE_RATE=16000
    -DBLE_DEVICE_NAME="ECC-"
```

## Debugging

### Serial Monitor
```bash
pio device monitor -b 115200
```

Output:
```
Audio level: 0.023 | VAD threshold: 0.015 | Silence: 1234 ms
Speech started
Speech ended
Speech segment: 850 ms, energy: 0.045, speaker: child
Event: SERVE (child spoke)
Event: RETURN (response time: 1200 ms)
```

### LED Indicators

| Color | Meaning |
|-------|---------|
| Green pulse | Successful turn |
| Blue flash | BLE connected |
| Red flash | BLE disconnected / error |
| Yellow flash | Low battery |
| Off | Normal operation (session active) |

### Haptic Patterns

| Pattern | Meaning |
|---------|---------|
| Short buzz | Session start |
| Double buzz | Session end |
| Gentle pulse | Missed opportunity |

## Known Limitations

1. **Speaker classification**: Currently uses energy heuristics. Real implementation needs pitch estimation (F0 analysis).

2. **No pitch estimation**: `pitch_hz` is always 0 in events. Would need FFT or autocorrelation.

3. **Battery reading**: Placeholder - needs ADC connection to battery voltage divider.

4. **No OTA updates**: Would need to add ESP32 OTA library.

## Future Improvements

- [ ] Add pitch estimation for adult/child classification
- [ ] Implement battery voltage reading via ADC
- [ ] Add OTA firmware update support
- [ ] Deep sleep for battery saving when idle
- [ ] Store events locally when BLE disconnected
- [ ] Calibration mode for VAD threshold

## License

MIT
