"""Voice Activity Detection using WebRTC VAD."""

import numpy as np
import webrtcvad
from dataclasses import dataclass
from typing import List

from ..audio.loader import samples_to_int16


@dataclass
class SpeechSegment:
    """A segment of detected speech."""
    start_time: float
    end_time: float
    samples: np.ndarray

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


class VADDetector:
    """
    Voice Activity Detector using WebRTC VAD.

    WebRTC VAD works with 10, 20, or 30ms frames at 8000, 16000, 32000, or 48000 Hz.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
        aggressiveness: int = 2,
        min_speech_duration_ms: int = 100,
        min_silence_duration_ms: int = 300,
    ):
        """
        Initialize VAD detector.

        Args:
            sample_rate: Audio sample rate (must be 8000, 16000, 32000, or 48000)
            frame_duration_ms: Frame size in ms (must be 10, 20, or 30)
            aggressiveness: VAD aggressiveness (0-3, higher = more aggressive filtering)
            min_speech_duration_ms: Minimum speech duration to keep
            min_silence_duration_ms: Minimum silence duration to split segments
        """
        if sample_rate not in (8000, 16000, 32000, 48000):
            raise ValueError(f"Sample rate must be 8000, 16000, 32000, or 48000, got {sample_rate}")
        if frame_duration_ms not in (10, 20, 30):
            raise ValueError(f"Frame duration must be 10, 20, or 30 ms, got {frame_duration_ms}")

        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.aggressiveness = aggressiveness
        self.min_speech_duration_ms = min_speech_duration_ms
        self.min_silence_duration_ms = min_silence_duration_ms

        self.vad = webrtcvad.Vad(aggressiveness)
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)

    def detect(self, samples: np.ndarray) -> List[SpeechSegment]:
        """
        Detect speech segments in audio.

        Args:
            samples: Audio samples as float32 numpy array

        Returns:
            List of SpeechSegment objects
        """
        frames = self._split_into_frames(samples)
        speech_flags = self._detect_speech_frames(frames)
        segments = self._merge_speech_segments(speech_flags, samples)

        return segments

    def _split_into_frames(self, samples: np.ndarray) -> List[np.ndarray]:
        """Split audio into frames."""
        frames = []
        for i in range(0, len(samples) - self.frame_size + 1, self.frame_size):
            frame = samples[i:i + self.frame_size]
            frames.append(frame)
        return frames

    def _detect_speech_frames(self, frames: List[np.ndarray]) -> List[bool]:
        """Run VAD on each frame."""
        speech_flags = []
        for frame in frames:
            frame_bytes = samples_to_int16(frame)
            is_speech = self.vad.is_speech(frame_bytes, self.sample_rate)
            speech_flags.append(is_speech)
        return speech_flags

    def _merge_speech_segments(
        self, speech_flags: List[bool], samples: np.ndarray
    ) -> List[SpeechSegment]:
        """Merge consecutive speech frames into segments."""
        segments = []
        in_speech = False
        speech_start = 0
        silence_frames = 0

        min_speech_frames = int(self.min_speech_duration_ms / self.frame_duration_ms)
        min_silence_frames = int(self.min_silence_duration_ms / self.frame_duration_ms)

        for i, is_speech in enumerate(speech_flags):
            frame_time = i * self.frame_duration_ms / 1000

            if is_speech:
                if not in_speech:
                    speech_start = frame_time
                    in_speech = True
                silence_frames = 0
            else:
                if in_speech:
                    silence_frames += 1
                    if silence_frames >= min_silence_frames:
                        # End of speech segment
                        end_time = frame_time - (silence_frames - 1) * self.frame_duration_ms / 1000
                        duration_ms = (end_time - speech_start) * 1000

                        if duration_ms >= self.min_speech_duration_ms:
                            start_sample = int(speech_start * self.sample_rate)
                            end_sample = int(end_time * self.sample_rate)
                            segment_samples = samples[start_sample:end_sample]

                            segments.append(SpeechSegment(
                                start_time=speech_start,
                                end_time=end_time,
                                samples=segment_samples
                            ))

                        in_speech = False
                        silence_frames = 0

        # Handle final segment
        if in_speech:
            end_time = len(speech_flags) * self.frame_duration_ms / 1000
            duration_ms = (end_time - speech_start) * 1000

            if duration_ms >= self.min_speech_duration_ms:
                start_sample = int(speech_start * self.sample_rate)
                segment_samples = samples[start_sample:]

                segments.append(SpeechSegment(
                    start_time=speech_start,
                    end_time=end_time,
                    samples=segment_samples
                ))

        return segments
