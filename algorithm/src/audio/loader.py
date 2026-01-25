"""Audio file loading utilities."""

import io
import numpy as np
import soundfile as sf
from pathlib import Path
from typing import Tuple


def load_audio(file_path: str, target_sr: int = 16000) -> Tuple[np.ndarray, int]:
    """
    Load audio file and convert to mono at target sample rate.

    Supports: .wav, .mp3, .flac, .ogg

    Args:
        file_path: Path to audio file
        target_sr: Target sample rate (default 16000 for VAD)

    Returns:
        Tuple of (audio_samples, sample_rate)
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    suffix = path.suffix.lower()

    if suffix == ".mp3":
        # Use pydub for MP3 (requires ffmpeg)
        try:
            from pydub import AudioSegment
            audio_segment = AudioSegment.from_mp3(file_path)
            audio_segment = audio_segment.set_frame_rate(target_sr).set_channels(1)
            samples = np.array(audio_segment.get_array_of_samples(), dtype=np.float32)
            samples = samples / 32768.0  # Normalize int16 to float
            return samples, target_sr
        except ImportError:
            raise ImportError("pydub required for MP3 support: pip install pydub")
        except Exception as e:
            raise RuntimeError(f"Failed to load MP3 (is ffmpeg installed?): {e}")
    else:
        # Use soundfile for wav, flac, ogg
        samples, sr = sf.read(file_path, dtype='float32')

        # Convert to mono if stereo
        if len(samples.shape) > 1:
            samples = np.mean(samples, axis=1)

        # Resample if needed
        if sr != target_sr:
            samples = _resample(samples, sr, target_sr)

        return samples, target_sr


def _resample(samples: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """Simple resampling using scipy."""
    from scipy import signal

    duration = len(samples) / orig_sr
    target_length = int(duration * target_sr)

    return signal.resample(samples, target_length)


def samples_to_int16(samples: np.ndarray) -> bytes:
    """Convert float32 samples to int16 bytes for webrtcvad."""
    int16_samples = (samples * 32767).astype(np.int16)
    return int16_samples.tobytes()
