"""Pitch estimation for speaker classification (adult vs child)."""

import numpy as np
from scipy import signal
from typing import Optional, Literal


Speaker = Literal["adult", "child", "unknown"]


# Default pitch thresholds by age (in months)
# Younger children have higher pitched voices
AGE_PITCH_THRESHOLDS = {
    0: 320,    # 0-12 months: infants have very high pitch
    12: 300,   # 12-24 months
    24: 285,   # 24-36 months
    36: 270,   # 36-48 months
    48: 260,   # 48-60 months
    60: 250,   # 60-72 months (approaching typical child threshold)
}


def get_pitch_threshold_for_age(age_months: Optional[int] = None) -> float:
    """
    Get appropriate pitch threshold based on child's age.

    Args:
        age_months: Child's age in months. If None, uses default (250 Hz).

    Returns:
        Pitch threshold in Hz
    """
    if age_months is None:
        return 250.0

    # Find the appropriate threshold for the age
    threshold = 250.0
    for min_age, pitch in sorted(AGE_PITCH_THRESHOLDS.items()):
        if age_months >= min_age:
            threshold = pitch
    return float(threshold)


class PitchEstimator:
    """
    Estimate fundamental frequency (F0) to classify speakers.

    Uses autocorrelation method - simple and works offline.

    Typical F0 ranges:
    - Adult male: 85-180 Hz
    - Adult female: 165-255 Hz
    - Child (varies by age):
      - Infant (0-1): 300-500 Hz
      - Toddler (1-3): 275-400 Hz
      - Preschool (3-6): 250-350 Hz
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        min_f0: float = 75.0,
        max_f0: float = 500.0,
        child_threshold: Optional[float] = None,
        age_months: Optional[int] = None,
    ):
        """
        Initialize pitch estimator.

        Args:
            sample_rate: Audio sample rate
            min_f0: Minimum F0 to detect (Hz)
            max_f0: Maximum F0 to detect (Hz)
            child_threshold: F0 above this is classified as child (Hz).
                           If None, determined by age_months.
            age_months: Child's age in months. Used to set child_threshold
                       if child_threshold is not explicitly provided.
        """
        self.sample_rate = sample_rate
        self.min_f0 = min_f0
        self.max_f0 = max_f0
        self.age_months = age_months

        # Determine child threshold based on age if not explicitly set
        if child_threshold is not None:
            self.child_threshold = child_threshold
        else:
            self.child_threshold = get_pitch_threshold_for_age(age_months)

        # Convert to lag in samples
        self.min_lag = int(sample_rate / max_f0)
        self.max_lag = int(sample_rate / min_f0)

    def estimate_f0(self, samples: np.ndarray) -> Optional[float]:
        """
        Estimate fundamental frequency using autocorrelation.

        Args:
            samples: Audio samples

        Returns:
            Estimated F0 in Hz, or None if no pitch detected
        """
        if len(samples) < self.max_lag * 2:
            return None

        # Normalize
        samples = samples - np.mean(samples)
        if np.max(np.abs(samples)) < 1e-6:
            return None
        samples = samples / np.max(np.abs(samples))

        # Compute autocorrelation
        correlation = np.correlate(samples, samples, mode='full')
        correlation = correlation[len(correlation) // 2:]

        # Find peaks in valid range
        if self.max_lag >= len(correlation):
            return None

        search_region = correlation[self.min_lag:self.max_lag]
        if len(search_region) == 0:
            return None

        # Find the highest peak
        peak_idx = np.argmax(search_region) + self.min_lag

        # Check if peak is significant (voiced detection)
        if correlation[peak_idx] < 0.3 * correlation[0]:
            return None

        # Convert lag to frequency
        f0 = self.sample_rate / peak_idx

        return f0

    def classify_speaker(self, samples: np.ndarray) -> tuple[Speaker, Optional[float]]:
        """
        Classify speaker as adult or child based on pitch.

        Args:
            samples: Audio samples of speech segment

        Returns:
            Tuple of (speaker_type, estimated_f0)
        """
        # Estimate F0 over multiple windows and take median
        window_size = int(self.sample_rate * 0.05)  # 50ms windows
        hop_size = int(self.sample_rate * 0.025)    # 25ms hop

        f0_estimates = []

        for i in range(0, len(samples) - window_size, hop_size):
            window = samples[i:i + window_size]
            f0 = self.estimate_f0(window)
            if f0 is not None:
                f0_estimates.append(f0)

        if not f0_estimates:
            return "unknown", None

        # Use median to be robust to outliers
        median_f0 = np.median(f0_estimates)

        if median_f0 >= self.child_threshold:
            return "child", median_f0
        else:
            return "adult", median_f0


def classify_segment_speaker(
    samples: np.ndarray,
    sample_rate: int = 16000,
    child_threshold: Optional[float] = None,
    age_months: Optional[int] = None,
) -> tuple[Speaker, Optional[float]]:
    """
    Convenience function to classify a speech segment.

    Args:
        samples: Audio samples
        sample_rate: Sample rate
        child_threshold: F0 threshold for child classification.
                        If None, determined by age_months.
        age_months: Child's age in months. Used to set threshold
                   if child_threshold is not provided.

    Returns:
        Tuple of (speaker_type, estimated_f0)
    """
    estimator = PitchEstimator(
        sample_rate=sample_rate,
        child_threshold=child_threshold,
        age_months=age_months,
    )
    return estimator.classify_speaker(samples)
