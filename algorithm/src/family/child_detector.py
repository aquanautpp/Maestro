"""Child detection and identification based on pitch profiles.

When a household has multiple children, this module helps identify
which child is speaking based on their pitch characteristics.
"""

from typing import Optional, List, Tuple
import numpy as np

from .household import Child, Household


class ChildDetector:
    """
    Identifies which child is speaking based on pitch analysis.

    Uses pitch profiles learned during calibration to distinguish
    between multiple children in the same household.
    """

    def __init__(self, household: Household):
        """
        Initialize child detector.

        Args:
            household: Household instance with children data
        """
        self.household = household

    def identify_child(
        self,
        pitch: float,
        confidence_threshold: float = 0.7
    ) -> Tuple[Optional[Child], float]:
        """
        Identify which child is speaking based on pitch.

        Args:
            pitch: Detected pitch in Hz
            confidence_threshold: Minimum confidence to return a match

        Returns:
            Tuple of (matched Child or None, confidence 0-1)
        """
        children = self.household.active_children

        # If only one child, return them with high confidence
        if len(children) == 1:
            return children[0], 0.95

        # If no children, return None
        if not children:
            return None, 0.0

        # Check children with pitch profiles first
        best_match: Optional[Child] = None
        best_confidence = 0.0

        for child in children:
            profile = child.pitch_profile
            if not profile or "mean_pitch" not in profile:
                continue

            confidence = self._calculate_match_confidence(pitch, profile)
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = child

        # If no profile matches well, try age-based matching
        if best_confidence < confidence_threshold:
            age_match, age_confidence = self._match_by_age(pitch, children)
            if age_confidence > best_confidence:
                best_match = age_match
                best_confidence = age_confidence

        # Return match if above threshold
        if best_confidence >= confidence_threshold:
            return best_match, best_confidence

        # Default to active child with low confidence
        return self.household.active_child, 0.5

    def _calculate_match_confidence(self, pitch: float, profile: dict) -> float:
        """
        Calculate confidence that a pitch matches a child's profile.

        Uses Gaussian likelihood based on mean and std from profile.

        Args:
            pitch: Detected pitch in Hz
            profile: Child's pitch profile

        Returns:
            Confidence score 0-1
        """
        mean = profile.get("mean_pitch", 300)
        std = profile.get("std_pitch", 30)

        # Ensure minimum std to avoid division issues
        std = max(std, 10)

        # Calculate z-score
        z = abs(pitch - mean) / std

        # Convert to confidence (higher z = lower confidence)
        # z=0 -> confidence=1, z=2 -> confidence~0.6, z=3 -> confidence~0.4
        confidence = np.exp(-0.5 * z * z)

        # Scale to reasonable range
        return float(max(0.3, min(1.0, confidence)))

    def _match_by_age(
        self,
        pitch: float,
        children: List[Child]
    ) -> Tuple[Optional[Child], float]:
        """
        Match pitch to child based on age-expected pitch ranges.

        Younger children typically have higher pitched voices.

        Args:
            pitch: Detected pitch in Hz
            children: List of children to match

        Returns:
            Tuple of (best matching Child, confidence)
        """
        best_match: Optional[Child] = None
        best_score = float('inf')

        for child in children:
            # Expected pitch based on age (rough estimates)
            age_months = child.age_months
            expected_pitch = self._expected_pitch_for_age(age_months)

            # Calculate distance from expected
            distance = abs(pitch - expected_pitch)

            if distance < best_score:
                best_score = distance
                best_match = child

        # Convert distance to confidence
        # Closer to expected = higher confidence
        max_reasonable_distance = 100  # Hz
        confidence = max(0.3, 1.0 - (best_score / max_reasonable_distance))

        return best_match, confidence

    def _expected_pitch_for_age(self, age_months: int) -> float:
        """
        Get expected pitch (Hz) for a child's age.

        Based on research on children's vocal development.

        Args:
            age_months: Child's age in months

        Returns:
            Expected pitch in Hz
        """
        # Pitch decreases as children age
        # These are rough midpoint estimates
        if age_months < 12:
            return 400  # Infants: very high
        elif age_months < 24:
            return 350  # Toddlers: high
        elif age_months < 36:
            return 320  # 2-3 years
        elif age_months < 48:
            return 300  # 3-4 years
        elif age_months < 60:
            return 285  # 4-5 years
        else:
            return 270  # 5-6 years

    def start_calibration(self, child_id: str) -> dict:
        """
        Start pitch calibration for a specific child.

        Returns instructions for the calibration process.

        Args:
            child_id: Child's ID

        Returns:
            Calibration instructions and session info
        """
        child = self.household.get_child(child_id)
        if not child:
            return {"error": "Child not found"}

        return {
            "child_id": child_id,
            "child_name": child.name,
            "status": "ready",
            "instructions": [
                f"Peca para {child.name} falar por alguns segundos",
                "Pode ser contando de 1 a 10 ou cantando uma musica",
                "O sistema vai detectar automaticamente a voz",
                "Repita 2-3 vezes para melhor precisao"
            ],
            "current_profile": child.pitch_profile or {},
        }

    def add_calibration_sample(
        self,
        child_id: str,
        pitches: List[float]
    ) -> dict:
        """
        Add calibration samples to a child's pitch profile.

        Args:
            child_id: Child's ID
            pitches: List of detected pitch values

        Returns:
            Updated profile info
        """
        if not pitches:
            return {"error": "No pitch data provided"}

        profile = self.household.update_child_pitch_profile(child_id, pitches)
        if not profile:
            return {"error": "Child not found or update failed"}

        child = self.household.get_child(child_id)
        return {
            "status": "updated",
            "child_name": child.name if child else "Unknown",
            "profile": profile,
            "message": f"Perfil atualizado com {len(pitches)} amostras!"
        }
