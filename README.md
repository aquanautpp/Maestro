# Early Childhood Coach

Wearable device system for coaching parents through real-time conversational feedback.

## The Problem

Children from low-income families hear 30 million fewer words by age 3. Research shows that **conversational turns** (back-and-forth exchanges) are more important than word volume for brain development. Parents don't need lectures—they need gentle, real-time nudges during daily interactions.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        WEARABLE DEVICE                          │
│  ┌─────────┐    ┌──────────────┐    ┌─────────┐                │
│  │  Mic    │───▶│  ESP32-S3    │───▶│ Haptic  │                │
│  │(INMP441)│    │  (VAD + Turn │    │  Motor  │                │
│  └─────────┘    │   Detection) │    └─────────┘                │
│                 └──────┬───────┘                                │
│                        │ BLE                                    │
└────────────────────────┼────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MOBILE APP (React Native)                  │
│  • Session logging & trends                                     │
│  • Settings & calibration                                       │
│  • Family dashboard                                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND (Supabase)                         │
│  • Session data storage                                         │
│  • User authentication                                          │
│  • Analytics aggregation                                        │
└─────────────────────────────────────────────────────────────────┘
```

## Modules

| Module | Language | Purpose |
|--------|----------|---------|
| `/algorithm` | Python | Audio processing, VAD, conversational turn detection |
| `/backend` | TypeScript | Supabase schema and edge functions |
| `/app` | React Native | Mobile app with BLE connectivity |

## Quick Start

```bash
# Algorithm (Python)
cd algorithm
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Backend (Supabase)
cd backend
npm install
npx supabase start

# App (React Native)
cd app
npm install
npx expo start
```

## Design Principles

1. **Simplicity first** — Start with voice activity detection + timing, not ML
2. **Privacy by design** — Audio processed on-device, never uploaded
3. **Validate before optimizing** — Get devices in parents' hands fast
4. **Delete aggressively** — If a feature isn't essential for V1, cut it

## Hardware BOM (Prototype)

| Component | Part | Est. Cost |
|-----------|------|-----------|
| MCU | ESP32-S3-DevKitC-1 | $10 |
| Microphone | INMP441 (I2S MEMS) | $3-5 |
| Haptic | ERM vibration motor | $0.50 |
| Battery | 800mAh LiPo + TP4056 | $5 |
| Enclosure | 3D printed | $5-10 |
| **Total** | | **~$25** |

## License

MIT
