# Algorithm Module

Audio processing and conversational turn detection for the Early Childhood Coach.

## Purpose

Analyzes parent-child audio interactions to detect **conversational turns** — the back-and-forth exchanges that build children's brains.

### What it detects:

| Event Type | Description |
|------------|-------------|
| **SERVE** | Child initiates (speaks) |
| **RETURN** | Adult responds within 3 seconds |
| **MISSED_OPPORTUNITY** | Silence >5 seconds after child without adult response |

## Quick Start

```bash
# Install dependencies
cd algorithm
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Analyze an audio file
python analyze.py recording.wav

# With options
python analyze.py recording.mp3 --output results.json --verbose
```

## How It Works

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Audio Input    │────▶│  VAD Detection  │────▶│ Pitch Analysis  │
│  (.wav/.mp3)    │     │  (WebRTC VAD)   │     │  (Autocorrel.)  │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                          │
                         ┌─────────────────┐              │
                         │  Turn Pattern   │◀─────────────┘
                         │    Analysis     │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │  JSON Output    │
                         │  (events +      │
                         │   summary)      │
                         └─────────────────┘
```

### 1. Voice Activity Detection
Uses WebRTC VAD to detect speech segments. Configurable aggressiveness (0-3).

### 2. Speaker Classification
Estimates fundamental frequency (F0) via autocorrelation:
- **Adult**: F0 < 250 Hz (typically 100-200 Hz)
- **Child**: F0 ≥ 250 Hz (typically 250-400 Hz)

### 3. Turn Pattern Detection
Analyzes timing between segments:
- Child speaks → **SERVE**
- Adult responds within threshold → **RETURN**
- Long silence after child → **MISSED_OPPORTUNITY**

## Output Format

```json
{
  "events": [
    {
      "type": "serve",
      "start_time": 0.5,
      "end_time": 1.5,
      "speaker": "child",
      "pitch_hz": 312.5
    },
    {
      "type": "return",
      "start_time": 2.0,
      "end_time": 3.5,
      "speaker": "adult",
      "response_latency": 0.5,
      "pitch_hz": 148.2
    },
    {
      "type": "missed_opportunity",
      "start_time": 10.5,
      "silence_duration": 6.2
    }
  ],
  "summary": {
    "total_serves": 5,
    "total_returns": 3,
    "missed_opportunities": 2,
    "successful_return_rate": 0.6,
    "average_response_latency": 1.2
  }
}
```

## CLI Options

```
python analyze.py <audio_file> [options]

Options:
  --output, -o          Output file (default: stdout)
  --child-threshold     F0 threshold for child classification (default: 250 Hz)
  --response-threshold  Max seconds for successful return (default: 3.0)
  --missed-threshold    Silence seconds for missed opportunity (default: 5.0)
  --vad-aggressiveness  VAD aggressiveness 0-3 (default: 2)
  --verbose, -v         Print progress info
```

## Project Structure

```
algorithm/
├── analyze.py              # CLI entry point
├── requirements.txt
├── src/
│   ├── audio/
│   │   └── loader.py       # Audio file loading (wav/mp3)
│   ├── vad/
│   │   └── detector.py     # WebRTC VAD wrapper
│   └── turn_detection/
│       ├── pitch.py        # F0 estimation, speaker classification
│       └── analyzer.py     # Main turn detection logic
├── tests/
│   └── test_analyzer.py    # Tests with synthetic audio
└── config/
    └── config.example.yaml
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing

# Generate sample test audio and run quick analysis
python tests/test_analyzer.py
```

## Limitations & Future Work

### Current Limitations
- Pitch-based classification is approximate (works best with clear speech)
- No handling of overlapping speech
- Single threshold for all children (age affects pitch)

### Potential Improvements
- ML-based speaker diarization (more accurate but heavier)
- Age-adaptive thresholds
- Prosody analysis (not just pitch)
- Noise robustness improvements

## Dependencies

| Package | Purpose |
|---------|---------|
| numpy | Array operations |
| scipy | Signal processing, resampling |
| soundfile | WAV/FLAC loading |
| pydub | MP3 loading (requires ffmpeg) |
| webrtcvad | Voice activity detection |

### MP3 Support
MP3 loading requires ffmpeg. Install:
- **macOS**: `brew install ffmpeg`
- **Ubuntu**: `sudo apt install ffmpeg`
- **Windows**: Download from https://ffmpeg.org/

## Integration

### Python API

```python
from src.audio.loader import load_audio
from src.turn_detection.analyzer import ConversationAnalyzer

# Load audio
samples, sr = load_audio("recording.wav")

# Analyze
analyzer = ConversationAnalyzer(sample_rate=sr)
result = analyzer.analyze(samples)

# Get results
print(result.to_json())
print(f"Success rate: {result.summary.successful_return_rate:.0%}")
```

### With Custom Thresholds

```python
analyzer = ConversationAnalyzer(
    sample_rate=16000,
    response_threshold_sec=2.5,      # Stricter response time
    missed_threshold_sec=4.0,        # Earlier missed detection
    child_pitch_threshold=280.0,     # Higher threshold for younger kids
    vad_aggressiveness=3,            # More aggressive VAD
)
```
