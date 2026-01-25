"""
Tests for the conversation analyzer using synthetic audio.

Creates synthetic audio that simulates:
- Child voice: Higher pitch (~300Hz fundamental)
- Adult voice: Lower pitch (~150Hz fundamental)
- Various turn patterns with pauses
"""

import numpy as np
import pytest
import tempfile
import soundfile as sf
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.audio.loader import load_audio
from src.vad.detector import VADDetector
from src.turn_detection.pitch import PitchEstimator, classify_segment_speaker
from src.turn_detection.analyzer import ConversationAnalyzer


SAMPLE_RATE = 16000


def generate_tone(frequency: float, duration: float, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Generate a sine wave tone."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    # Add harmonics to make it more speech-like
    signal = (
        0.5 * np.sin(2 * np.pi * frequency * t) +
        0.3 * np.sin(2 * np.pi * frequency * 2 * t) +
        0.2 * np.sin(2 * np.pi * frequency * 3 * t)
    )
    # Add amplitude envelope (attack/decay)
    envelope = np.ones_like(signal)
    attack = int(0.05 * sample_rate)
    decay = int(0.1 * sample_rate)
    envelope[:attack] = np.linspace(0, 1, attack)
    envelope[-decay:] = np.linspace(1, 0, decay)
    return (signal * envelope * 0.8).astype(np.float32)


def generate_silence(duration: float, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Generate silence."""
    return np.zeros(int(sample_rate * duration), dtype=np.float32)


def generate_child_voice(duration: float) -> np.ndarray:
    """Generate synthetic child voice (~300Hz)."""
    return generate_tone(300, duration)


def generate_adult_voice(duration: float) -> np.ndarray:
    """Generate synthetic adult voice (~150Hz)."""
    return generate_tone(150, duration)


def create_test_audio_successful_turn() -> np.ndarray:
    """
    Create audio with successful conversational turn:
    - Child speaks (1s)
    - Short pause (0.5s)
    - Adult responds (1.5s)
    """
    return np.concatenate([
        generate_silence(0.5),      # 0.0 - 0.5: silence
        generate_child_voice(1.0),   # 0.5 - 1.5: child speaks
        generate_silence(0.5),       # 1.5 - 2.0: short pause
        generate_adult_voice(1.5),   # 2.0 - 3.5: adult responds
        generate_silence(0.5),       # 3.5 - 4.0: end silence
    ])


def create_test_audio_missed_opportunity() -> np.ndarray:
    """
    Create audio with missed opportunity:
    - Child speaks (1s)
    - Long silence (6s) - missed opportunity
    - Adult speaks (but too late)
    """
    return np.concatenate([
        generate_silence(0.5),       # 0.0 - 0.5: silence
        generate_child_voice(1.0),   # 0.5 - 1.5: child speaks
        generate_silence(6.0),       # 1.5 - 7.5: long silence (missed)
        generate_adult_voice(1.0),   # 7.5 - 8.5: adult (too late)
        generate_silence(0.5),       # 8.5 - 9.0: end
    ])


def create_test_audio_multiple_turns() -> np.ndarray:
    """
    Create audio with multiple turn patterns:
    1. Child → Adult (successful, 0.5s latency)
    2. Child → silence (missed, 5.5s)
    3. Child → Adult (successful, 1.0s latency)
    """
    return np.concatenate([
        # Turn 1: Successful
        generate_silence(0.3),
        generate_child_voice(0.8),   # Serve 1
        generate_silence(0.5),       # Short pause
        generate_adult_voice(1.0),   # Return 1
        generate_silence(1.0),

        # Turn 2: Missed
        generate_child_voice(1.0),   # Serve 2
        generate_silence(5.5),       # Long silence - missed

        # Turn 3: Successful
        generate_child_voice(0.7),   # Serve 3
        generate_silence(1.0),       # Pause
        generate_adult_voice(1.2),   # Return 3
        generate_silence(0.5),
    ])


class TestPitchEstimator:
    """Test pitch estimation and speaker classification."""

    def test_adult_pitch_detection(self):
        """Adult voice should be classified as adult."""
        samples = generate_adult_voice(1.0)
        speaker, pitch = classify_segment_speaker(samples, SAMPLE_RATE)

        assert speaker == "adult"
        assert pitch is not None
        assert 100 < pitch < 250  # Adult range

    def test_child_pitch_detection(self):
        """Child voice should be classified as child."""
        samples = generate_child_voice(1.0)
        speaker, pitch = classify_segment_speaker(samples, SAMPLE_RATE)

        assert speaker == "child"
        assert pitch is not None
        assert pitch >= 250  # Child threshold

    def test_silence_classification(self):
        """Silence should return unknown."""
        samples = generate_silence(1.0)
        speaker, pitch = classify_segment_speaker(samples, SAMPLE_RATE)

        assert speaker == "unknown"
        assert pitch is None


class TestVADDetector:
    """Test voice activity detection."""

    def test_detects_speech(self):
        """VAD should detect speech segments."""
        audio = create_test_audio_successful_turn()
        vad = VADDetector(sample_rate=SAMPLE_RATE)

        segments = vad.detect(audio)

        assert len(segments) >= 2  # At least child and adult

    def test_silence_no_segments(self):
        """Pure silence should have no segments."""
        silence = generate_silence(2.0)
        vad = VADDetector(sample_rate=SAMPLE_RATE)

        segments = vad.detect(silence)

        assert len(segments) == 0


class TestConversationAnalyzer:
    """Test the full conversation analyzer."""

    def test_successful_turn(self):
        """Test detection of successful serve-return."""
        audio = create_test_audio_successful_turn()
        analyzer = ConversationAnalyzer(sample_rate=SAMPLE_RATE)

        result = analyzer.analyze(audio)

        # Should have at least one serve and one return
        serves = [e for e in result.events if e.type == "serve"]
        returns = [e for e in result.events if e.type == "return"]

        assert len(serves) >= 1
        assert len(returns) >= 1
        assert result.summary.successful_return_rate > 0

    def test_missed_opportunity(self):
        """Test detection of missed opportunity."""
        audio = create_test_audio_missed_opportunity()
        analyzer = ConversationAnalyzer(
            sample_rate=SAMPLE_RATE,
            missed_threshold_sec=5.0,
        )

        result = analyzer.analyze(audio)

        missed = [e for e in result.events if e.type == "missed_opportunity"]
        assert len(missed) >= 1
        assert missed[0].silence_duration >= 5.0

    def test_multiple_turns(self):
        """Test audio with multiple turn patterns."""
        audio = create_test_audio_multiple_turns()
        analyzer = ConversationAnalyzer(
            sample_rate=SAMPLE_RATE,
            response_threshold_sec=3.0,
            missed_threshold_sec=5.0,
        )

        result = analyzer.analyze(audio)

        serves = [e for e in result.events if e.type == "serve"]
        returns = [e for e in result.events if e.type == "return"]
        missed = [e for e in result.events if e.type == "missed_opportunity"]

        # Should detect multiple serves
        assert len(serves) >= 2

        # Should have some returns and at least one missed
        assert result.summary.total_returns >= 1
        assert result.summary.missed_opportunities >= 1

    def test_json_output(self):
        """Test JSON serialization."""
        audio = create_test_audio_successful_turn()
        analyzer = ConversationAnalyzer(sample_rate=SAMPLE_RATE)

        result = analyzer.analyze(audio)
        json_str = result.to_json()

        # Should be valid JSON
        import json
        parsed = json.loads(json_str)

        assert "events" in parsed
        assert "summary" in parsed
        assert isinstance(parsed["events"], list)

    def test_empty_audio(self):
        """Test with silent audio."""
        silence = generate_silence(5.0)
        analyzer = ConversationAnalyzer(sample_rate=SAMPLE_RATE)

        result = analyzer.analyze(silence)

        assert len(result.events) == 0
        assert result.summary.total_serves == 0


class TestAudioLoader:
    """Test audio loading functionality."""

    def test_load_wav(self):
        """Test loading a WAV file."""
        # Create temporary WAV file
        audio = create_test_audio_successful_turn()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            sf.write(f.name, audio, SAMPLE_RATE)
            temp_path = f.name

        try:
            samples, sr = load_audio(temp_path)
            assert sr == SAMPLE_RATE
            assert len(samples) > 0
        finally:
            Path(temp_path).unlink()


class TestIntegration:
    """Integration tests with file I/O."""

    def test_full_pipeline_with_file(self):
        """Test complete pipeline: file → analysis → JSON."""
        # Create test audio
        audio = create_test_audio_multiple_turns()

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            sf.write(f.name, audio, SAMPLE_RATE)
            temp_path = f.name

        try:
            # Load and analyze
            samples, sr = load_audio(temp_path)
            analyzer = ConversationAnalyzer(sample_rate=sr)
            result = analyzer.analyze(samples)

            # Verify output
            assert result.summary.total_serves >= 1
            json_output = result.to_json()
            assert len(json_output) > 0

        finally:
            Path(temp_path).unlink()


def create_sample_test_file():
    """
    Utility function to create a sample test audio file.
    Run this to generate a test file for manual testing.
    """
    audio = create_test_audio_multiple_turns()
    output_path = Path(__file__).parent / "sample_conversation.wav"
    sf.write(str(output_path), audio, SAMPLE_RATE)
    print(f"Created test file: {output_path}")
    return output_path


if __name__ == "__main__":
    # Generate sample file for manual testing
    create_sample_test_file()

    # Run a quick test
    print("\nRunning quick analysis test...")
    audio = create_test_audio_multiple_turns()
    analyzer = ConversationAnalyzer(sample_rate=SAMPLE_RATE)
    result = analyzer.analyze(audio)

    print("\nAnalysis Result:")
    print(result.to_json())
