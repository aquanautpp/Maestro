"""Conversational turn analyzer for parent-child interactions."""

import json
from dataclasses import dataclass, asdict
from typing import List, Optional, Literal, Union

from ..vad.detector import VADDetector, SpeechSegment
from .pitch import PitchEstimator, Speaker


EventType = Literal["serve", "return", "missed_opportunity"]


@dataclass
class ServeEvent:
    """Child initiates conversation."""
    type: str  # "serve"
    start_time: float
    end_time: float
    speaker: str  # "child"
    pitch_hz: Optional[float] = None


@dataclass
class ReturnEvent:
    """Adult responds to child."""
    type: str  # "return"
    start_time: float
    end_time: float
    speaker: str  # "adult"
    response_latency: float
    pitch_hz: Optional[float] = None


@dataclass
class MissedOpportunityEvent:
    """Adult failed to respond to child within threshold."""
    type: str  # "missed_opportunity"
    start_time: float
    silence_duration: float


@dataclass
class AnalysisSummary:
    """Summary statistics for the analysis."""
    total_serves: int
    total_returns: int
    missed_opportunities: int
    successful_return_rate: float
    average_response_latency: Optional[float]


@dataclass
class AnalysisResult:
    """Complete analysis result."""
    events: List[Union[ServeEvent, ReturnEvent, MissedOpportunityEvent]]
    summary: AnalysisSummary

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "events": [asdict(e) for e in self.events],
            "summary": asdict(self.summary)
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class ConversationAnalyzer:
    """
    Analyzes parent-child audio for conversational turns.

    Detects:
    - SERVE: Child speaks (initiates)
    - RETURN: Adult responds within response_threshold seconds
    - MISSED_OPPORTUNITY: Silence > missed_threshold seconds after child
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        response_threshold_sec: float = 3.0,
        missed_threshold_sec: float = 5.0,
        child_pitch_threshold: float = 250.0,
        vad_aggressiveness: int = 2,
    ):
        """
        Initialize analyzer.

        Args:
            sample_rate: Audio sample rate
            response_threshold_sec: Max seconds for adult response to count as return
            missed_threshold_sec: Seconds of silence to count as missed opportunity
            child_pitch_threshold: F0 threshold for child classification (Hz)
            vad_aggressiveness: WebRTC VAD aggressiveness (0-3)
        """
        self.sample_rate = sample_rate
        self.response_threshold = response_threshold_sec
        self.missed_threshold = missed_threshold_sec

        self.vad = VADDetector(
            sample_rate=sample_rate,
            aggressiveness=vad_aggressiveness,
        )
        self.pitch_estimator = PitchEstimator(
            sample_rate=sample_rate,
            child_threshold=child_pitch_threshold,
        )

    def analyze(self, samples) -> AnalysisResult:
        """
        Analyze audio for conversational turns.

        Args:
            samples: Audio samples as numpy array

        Returns:
            AnalysisResult with events and summary
        """
        # Step 1: Detect speech segments
        segments = self.vad.detect(samples)

        if not segments:
            return AnalysisResult(
                events=[],
                summary=AnalysisSummary(
                    total_serves=0,
                    total_returns=0,
                    missed_opportunities=0,
                    successful_return_rate=0.0,
                    average_response_latency=None,
                )
            )

        # Step 2: Classify each segment by speaker
        classified_segments = []
        for segment in segments:
            speaker, pitch = self.pitch_estimator.classify_speaker(segment.samples)
            classified_segments.append((segment, speaker, pitch))

        # Step 3: Detect turn patterns
        events = self._detect_turns(classified_segments)

        # Step 4: Generate summary
        summary = self._generate_summary(events)

        return AnalysisResult(events=events, summary=summary)

    def _detect_turns(
        self,
        classified_segments: List[tuple[SpeechSegment, Speaker, Optional[float]]]
    ) -> List[Union[ServeEvent, ReturnEvent, MissedOpportunityEvent]]:
        """Detect serve, return, and missed opportunity patterns."""
        events = []
        waiting_for_response = False
        last_child_segment = None
        last_child_end = 0.0

        for segment, speaker, pitch in classified_segments:
            if speaker == "child":
                # Check if previous child serve was missed
                if waiting_for_response:
                    gap = segment.start_time - last_child_end
                    if gap >= self.missed_threshold:
                        events.append(MissedOpportunityEvent(
                            type="missed_opportunity",
                            start_time=last_child_end,
                            silence_duration=round(gap, 2),
                        ))

                # Record new serve
                events.append(ServeEvent(
                    type="serve",
                    start_time=round(segment.start_time, 2),
                    end_time=round(segment.end_time, 2),
                    speaker="child",
                    pitch_hz=round(pitch, 1) if pitch else None,
                ))

                waiting_for_response = True
                last_child_segment = segment
                last_child_end = segment.end_time

            elif speaker == "adult" and waiting_for_response:
                # Adult responding to child
                response_latency = segment.start_time - last_child_end

                if response_latency <= self.response_threshold:
                    # Successful return
                    events.append(ReturnEvent(
                        type="return",
                        start_time=round(segment.start_time, 2),
                        end_time=round(segment.end_time, 2),
                        speaker="adult",
                        response_latency=round(response_latency, 2),
                        pitch_hz=round(pitch, 1) if pitch else None,
                    ))
                    waiting_for_response = False
                elif response_latency >= self.missed_threshold:
                    # Too late - missed opportunity
                    events.append(MissedOpportunityEvent(
                        type="missed_opportunity",
                        start_time=last_child_end,
                        silence_duration=round(response_latency, 2),
                    ))
                    waiting_for_response = False

            elif speaker == "adult":
                # Adult speaking without prior child serve - just note it
                pass

        # Check for trailing missed opportunity
        if waiting_for_response and last_child_segment:
            # Assume end of audio, calculate gap
            # We'll mark as missed if there's significant silence
            pass

        return events

    def _generate_summary(
        self,
        events: List[Union[ServeEvent, ReturnEvent, MissedOpportunityEvent]]
    ) -> AnalysisSummary:
        """Generate summary statistics."""
        serves = [e for e in events if isinstance(e, ServeEvent)]
        returns = [e for e in events if isinstance(e, ReturnEvent)]
        missed = [e for e in events if isinstance(e, MissedOpportunityEvent)]

        total_serves = len(serves)
        total_returns = len(returns)
        missed_opportunities = len(missed)

        if total_serves > 0:
            successful_rate = total_returns / total_serves
        else:
            successful_rate = 0.0

        if returns:
            avg_latency = sum(r.response_latency for r in returns) / len(returns)
        else:
            avg_latency = None

        return AnalysisSummary(
            total_serves=total_serves,
            total_returns=total_returns,
            missed_opportunities=missed_opportunities,
            successful_return_rate=round(successful_rate, 2),
            average_response_latency=round(avg_latency, 2) if avg_latency else None,
        )
