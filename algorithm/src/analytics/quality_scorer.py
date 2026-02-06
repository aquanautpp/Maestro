"""Quality scoring for conversation sessions.

Goes beyond simple counting to assess engagement quality:
- Turn length (longer = more engaged)
- Response latency distribution
- Engagement depth (sustained exchanges)
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import numpy as np


@dataclass
class EngagementMetrics:
    """Detailed engagement metrics for a session."""
    longest_exchange: int  # Most consecutive turns
    total_exchanges: int  # Number of back-and-forth sequences
    avg_turn_duration_ms: float
    response_time_consistency: float  # Lower variance = more attentive
    child_initiation_ratio: float  # Child starting conversations
    engagement_depth_score: float  # 0-1 score for sustained interaction

    def to_dict(self) -> dict:
        return asdict(self)


class QualityScorer:
    """
    Calculates quality metrics for conversation sessions.

    Quality Dimensions:
    1. Turn Length - Longer exchanges indicate deeper engagement
    2. Response Latency - Optimal timing shows attentiveness
    3. Engagement Depth - Sustained back-and-forth is valuable
    4. Consistency - Predictable timing helps child development
    """

    def __init__(self):
        """Initialize quality scorer."""
        # Optimal response time range (seconds)
        self.optimal_response_min = 1.0
        self.optimal_response_max = 3.0

    def calculate_turn_length_score(self, events: List[dict]) -> float:
        """
        Calculate score based on turn lengths.

        Longer speech segments suggest more engaged conversation.

        Args:
            events: List of event dictionaries

        Returns:
            Score from 0-1
        """
        turn_durations = []

        for event in events:
            if event.get("type") in ["child", "adult"]:
                # Estimate duration from frame count if available
                duration_ms = event.get("duration_ms", 500)  # Default 500ms
                turn_durations.append(duration_ms)

        if not turn_durations:
            return 0.5  # Neutral score

        avg_duration = np.mean(turn_durations)

        # Score: 500ms = 0.5, 1000ms = 0.75, 2000ms+ = 1.0
        if avg_duration >= 2000:
            return 1.0
        elif avg_duration >= 1000:
            return 0.75 + ((avg_duration - 1000) / 4000)
        else:
            return 0.3 + (avg_duration / 2000) * 0.45

    def calculate_latency_score(self, response_times: List[float]) -> float:
        """
        Calculate score based on response latency.

        Optimal: 1-3 seconds (gives child time but stays engaged)

        Args:
            response_times: List of response times in seconds

        Returns:
            Score from 0-1
        """
        if not response_times:
            return 0.5

        times = np.array(response_times)
        avg_time = np.mean(times)

        # Score based on proximity to optimal range
        if self.optimal_response_min <= avg_time <= self.optimal_response_max:
            return 1.0
        elif avg_time < self.optimal_response_min:
            # Fast but not too fast is still good
            return max(0.6, 1.0 - (self.optimal_response_min - avg_time) * 0.4)
        else:
            # Slower responses - gradual decrease
            excess = avg_time - self.optimal_response_max
            return max(0.3, 1.0 - (excess * 0.1))

    def calculate_engagement_depth(self, events: List[dict]) -> EngagementMetrics:
        """
        Calculate engagement depth metrics.

        Looks for sustained back-and-forth exchanges.

        Args:
            events: List of event dictionaries

        Returns:
            EngagementMetrics with detailed analysis
        """
        if not events:
            return EngagementMetrics(
                longest_exchange=0,
                total_exchanges=0,
                avg_turn_duration_ms=0,
                response_time_consistency=0,
                child_initiation_ratio=0,
                engagement_depth_score=0,
            )

        # Count consecutive speaker alternations
        exchanges = []
        current_exchange = 0
        last_speaker = None

        child_starts = 0
        adult_starts = 0
        turn_durations = []

        for event in events:
            event_type = event.get("type")

            if event_type in ["child", "adult"]:
                speaker = event_type
                duration = event.get("duration_ms", 500)
                turn_durations.append(duration)

                if last_speaker is None:
                    # First speaker
                    if speaker == "child":
                        child_starts += 1
                    else:
                        adult_starts += 1
                    current_exchange = 1
                elif speaker != last_speaker:
                    # Speaker changed - exchange continues
                    current_exchange += 1
                else:
                    # Same speaker - exchange ended
                    if current_exchange > 1:
                        exchanges.append(current_exchange)
                    current_exchange = 1

                last_speaker = speaker

            elif event_type == "moment":
                # Conversation turn detected
                if current_exchange > 1:
                    exchanges.append(current_exchange)
                current_exchange = 0
                last_speaker = None

        # Save final exchange
        if current_exchange > 1:
            exchanges.append(current_exchange)

        # Calculate metrics
        longest_exchange = max(exchanges) if exchanges else 0
        total_exchanges = len(exchanges)
        avg_turn_duration = np.mean(turn_durations) if turn_durations else 0

        total_starts = child_starts + adult_starts
        child_initiation_ratio = child_starts / total_starts if total_starts > 0 else 0

        # Engagement depth score
        # Based on: longest exchange, number of exchanges, and child initiation
        depth_score = 0.0
        if longest_exchange >= 4:
            depth_score += 0.4
        elif longest_exchange >= 2:
            depth_score += 0.2

        if total_exchanges >= 5:
            depth_score += 0.3
        elif total_exchanges >= 2:
            depth_score += 0.15

        if 0.3 <= child_initiation_ratio <= 0.7:
            depth_score += 0.3  # Balanced initiation is ideal
        elif child_initiation_ratio > 0:
            depth_score += 0.15

        return EngagementMetrics(
            longest_exchange=longest_exchange,
            total_exchanges=total_exchanges,
            avg_turn_duration_ms=round(avg_turn_duration, 1),
            response_time_consistency=0,  # Calculated separately
            child_initiation_ratio=round(child_initiation_ratio, 2),
            engagement_depth_score=min(1.0, depth_score),
        )

    def calculate_consistency_score(self, response_times: List[float]) -> float:
        """
        Calculate response time consistency score.

        Lower variance = more consistent = better for child development.

        Args:
            response_times: List of response times

        Returns:
            Score from 0-1 (higher = more consistent)
        """
        if len(response_times) < 2:
            return 0.5

        times = np.array(response_times)
        std_dev = np.std(times)

        # Lower std dev = higher score
        # std_dev of 0 = perfect consistency = score 1.0
        # std_dev of 3+ = low consistency = score ~0.3
        return max(0.3, 1.0 - (std_dev / 5.0))

    def calculate_session_quality(self, session: dict) -> Dict[str, Any]:
        """
        Calculate overall quality score for a session.

        Args:
            session: Session dictionary

        Returns:
            Quality analysis with component scores
        """
        events = session.get("events", [])
        response_times = session.get("response_times", [])

        # Calculate component scores
        turn_length_score = self.calculate_turn_length_score(events)
        latency_score = self.calculate_latency_score(response_times)
        consistency_score = self.calculate_consistency_score(response_times)
        engagement_metrics = self.calculate_engagement_depth(events)

        # Update consistency in engagement metrics
        engagement_metrics.response_time_consistency = consistency_score

        # Calculate composite score (weighted average)
        weights = {
            "turn_length": 0.2,
            "latency": 0.25,
            "engagement": 0.35,
            "consistency": 0.2,
        }

        composite = (
            turn_length_score * weights["turn_length"] +
            latency_score * weights["latency"] +
            engagement_metrics.engagement_depth_score * weights["engagement"] +
            consistency_score * weights["consistency"]
        )

        # Convert to 0-100 scale
        quality_score = round(composite * 100)

        return {
            "quality_score": quality_score,
            "components": {
                "turn_length_score": round(turn_length_score, 2),
                "latency_score": round(latency_score, 2),
                "engagement_score": round(engagement_metrics.engagement_depth_score, 2),
                "consistency_score": round(consistency_score, 2),
            },
            "engagement_metrics": engagement_metrics.to_dict(),
            "interpretation": self._interpret_score(quality_score),
        }

    def _interpret_score(self, score: int) -> str:
        """Get positive interpretation of quality score."""
        if score >= 80:
            return "Interacoes profundas e engajadas!"
        elif score >= 60:
            return "Boas conversas com espaco para crescer!"
        elif score >= 40:
            return "Voces estao construindo conexao!"
        else:
            return "Cada momento de conversa conta!"
