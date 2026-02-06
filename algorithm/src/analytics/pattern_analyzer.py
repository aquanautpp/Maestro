"""Pattern analysis over time to identify strengths and growth areas.

Analyzes session history to understand what serve-and-return behaviors
the parent does well and where they might want to grow.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict

from .serve_return_mapper import ServeReturnMapper


@dataclass
class PatternInsight:
    """An insight about the user's interaction patterns."""
    category: str  # 'strength', 'growth_area', 'observation'
    title: str
    description: str
    metric: Optional[str] = None
    value: Optional[float] = None
    trend: Optional[str] = None  # 'improving', 'stable', 'declining'

    def to_dict(self) -> dict:
        return asdict(self)


class PatternAnalyzer:
    """
    Analyzes patterns in parent-child interactions over time.

    Identifies:
    - What the parent does well (strengths)
    - Areas for growth (positive framing)
    - Time-of-day patterns
    - Response time patterns
    - Serve-and-return step proficiency
    """

    def __init__(self, sessions_dir: Optional[Path] = None):
        """
        Initialize pattern analyzer.

        Args:
            sessions_dir: Directory containing session JSON files
        """
        if sessions_dir is None:
            sessions_dir = Path(__file__).parent.parent.parent / "data" / "sessions"

        self.sessions_dir = sessions_dir
        self.serve_return_mapper = ServeReturnMapper()

    def load_sessions(
        self,
        days: int = 30,
        child_id: Optional[str] = None
    ) -> List[dict]:
        """
        Load sessions from the specified time period.

        Args:
            days: Number of days to look back
            child_id: Optional filter by child ID

        Returns:
            List of session dictionaries
        """
        if not self.sessions_dir.exists():
            return []

        cutoff = datetime.now() - timedelta(days=days)
        sessions = []

        for filepath in self.sessions_dir.glob("*.json"):
            try:
                # Parse date from filename (YYYY-MM-DD_HH-MM.json)
                date_str = filepath.stem[:10]
                file_date = datetime.strptime(date_str, "%Y-%m-%d")

                if file_date >= cutoff:
                    with open(filepath, "r", encoding="utf-8") as f:
                        session = json.load(f)

                    # Filter by child if specified
                    if child_id and session.get("child_id") != child_id:
                        continue

                    session["_filename"] = filepath.name
                    session["_date"] = file_date
                    sessions.append(session)

            except Exception:
                continue

        # Sort by date
        sessions.sort(key=lambda x: x.get("_date", datetime.min))
        return sessions

    def analyze_response_patterns(
        self,
        sessions: List[dict]
    ) -> Dict[str, Any]:
        """
        Analyze response time patterns.

        Args:
            sessions: List of session dictionaries

        Returns:
            Dictionary with response time analysis
        """
        all_response_times = []
        for session in sessions:
            times = session.get("response_times", [])
            all_response_times.extend(times)

        if not all_response_times:
            return {
                "average": None,
                "median": None,
                "fastest": None,
                "consistency": None,
                "total_responses": 0,
            }

        import numpy as np
        times = np.array(all_response_times)

        return {
            "average": round(float(np.mean(times)), 2),
            "median": round(float(np.median(times)), 2),
            "fastest": round(float(np.min(times)), 2),
            "slowest": round(float(np.max(times)), 2),
            "std_dev": round(float(np.std(times)), 2),
            "consistency": round(1.0 - min(float(np.std(times)) / 5.0, 1.0), 2),  # 0-1 score
            "total_responses": len(all_response_times),
        }

    def analyze_time_of_day(self, sessions: List[dict]) -> Dict[str, Any]:
        """
        Analyze when interactions tend to happen.

        Args:
            sessions: List of session dictionaries

        Returns:
            Dictionary with time-of-day patterns
        """
        hour_counts = {h: 0 for h in range(24)}
        hour_moments = {h: 0 for h in range(24)}

        for session in sessions:
            started_at = session.get("started_at", "")
            moments = session.get("moments", 0)

            try:
                if started_at:
                    dt = datetime.fromisoformat(started_at.replace("Z", ""))
                    hour = dt.hour
                    hour_counts[hour] += 1
                    hour_moments[hour] += moments
            except Exception:
                continue

        # Find peak hours
        peak_hour = max(hour_counts, key=hour_counts.get) if any(hour_counts.values()) else None
        best_hour = max(hour_moments, key=hour_moments.get) if any(hour_moments.values()) else None

        # Categorize into time periods
        morning = sum(hour_counts[h] for h in range(6, 12))
        afternoon = sum(hour_counts[h] for h in range(12, 18))
        evening = sum(hour_counts[h] for h in range(18, 22))
        night = sum(hour_counts[h] for h in list(range(22, 24)) + list(range(0, 6)))

        periods = {
            "morning": morning,
            "afternoon": afternoon,
            "evening": evening,
            "night": night,
        }
        preferred_period = max(periods, key=periods.get) if any(periods.values()) else None

        return {
            "peak_hour": peak_hour,
            "best_hour_for_moments": best_hour,
            "preferred_period": preferred_period,
            "periods": periods,
            "hour_distribution": hour_counts,
        }

    def analyze_serve_return_steps(
        self,
        sessions: List[dict]
    ) -> Dict[str, Any]:
        """
        Analyze proficiency in each serve-and-return step.

        Based on detectable patterns:
        - Step 3 (Name): Response with descriptive language
        - Step 4 (Wait): Response timing patterns

        Args:
            sessions: List of session dictionaries

        Returns:
            Dictionary with step-by-step analysis
        """
        return self.serve_return_mapper.analyze_sessions(sessions)

    def identify_strengths(
        self,
        sessions: List[dict]
    ) -> List[PatternInsight]:
        """
        Identify what the parent does well.

        Args:
            sessions: List of session dictionaries

        Returns:
            List of strength insights
        """
        strengths = []

        if not sessions:
            return strengths

        # Analyze patterns
        response_patterns = self.analyze_response_patterns(sessions)
        time_patterns = self.analyze_time_of_day(sessions)
        step_patterns = self.analyze_serve_return_steps(sessions)

        # Check consistency
        total_sessions = len(sessions)
        if total_sessions >= 5:
            strengths.append(PatternInsight(
                category="strength",
                title="Consistencia",
                description=f"Voce fez {total_sessions} sessoes! Consistencia e fundamental.",
                metric="sessions",
                value=total_sessions,
            ))

        # Check response speed
        avg_response = response_patterns.get("average")
        if avg_response and avg_response < 3.0:
            strengths.append(PatternInsight(
                category="strength",
                title="Respostas rapidas",
                description="Voce responde rapidamente quando seu filho fala. Isso mostra atencao!",
                metric="avg_response_time",
                value=avg_response,
            ))

        # Check response consistency
        consistency = response_patterns.get("consistency", 0)
        if consistency > 0.7:
            strengths.append(PatternInsight(
                category="strength",
                title="Timing consistente",
                description="Suas respostas tem um ritmo previsivel. Isso ajuda a crianca a antecipar.",
                metric="consistency",
                value=consistency,
            ))

        # Check for regular time
        if time_patterns.get("preferred_period"):
            period_names = {
                "morning": "manha",
                "afternoon": "tarde",
                "evening": "noite",
            }
            period = time_patterns["preferred_period"]
            if period in period_names:
                strengths.append(PatternInsight(
                    category="strength",
                    title="Rotina estabelecida",
                    description=f"Voces interagem mais de {period_names.get(period, period)}. Rotinas ajudam!",
                    metric="preferred_period",
                ))

        # Check serve-return steps
        step_scores = step_patterns.get("step_scores", {})
        for step_key, score in step_scores.items():
            if score >= 0.7:
                step_info = step_patterns.get("step_details", {}).get(step_key, {})
                strengths.append(PatternInsight(
                    category="strength",
                    title=step_info.get("name", step_key),
                    description=step_info.get("strength_message", "Voce faz isso muito bem!"),
                    metric=f"step_{step_key}",
                    value=score,
                ))

        return strengths

    def identify_growth_areas(
        self,
        sessions: List[dict]
    ) -> List[PatternInsight]:
        """
        Identify areas for growth (positive framing, never negative).

        Args:
            sessions: List of session dictionaries

        Returns:
            List of growth opportunity insights
        """
        growth_areas = []

        if not sessions:
            return growth_areas

        step_patterns = self.analyze_serve_return_steps(sessions)
        step_scores = step_patterns.get("step_scores", {})

        # Find lowest scoring step (opportunity for growth)
        if step_scores:
            lowest_step = min(step_scores, key=step_scores.get)
            lowest_score = step_scores[lowest_step]

            if lowest_score < 0.5:
                step_info = step_patterns.get("step_details", {}).get(lowest_step, {})
                growth_areas.append(PatternInsight(
                    category="growth_area",
                    title=f"Proxima aventura: {step_info.get('name', lowest_step)}",
                    description=step_info.get("growth_message", "Uma oportunidade para explorar!"),
                    metric=f"step_{lowest_step}",
                    value=lowest_score,
                ))

        return growth_areas

    def get_full_analysis(
        self,
        days: int = 30,
        child_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get complete pattern analysis.

        Args:
            days: Days to analyze
            child_id: Optional child filter

        Returns:
            Complete analysis dictionary
        """
        sessions = self.load_sessions(days=days, child_id=child_id)

        if not sessions:
            return {
                "status": "no_data",
                "message": "Ainda nao ha sessoes para analisar. Continue interagindo!",
                "sessions_analyzed": 0,
            }

        return {
            "status": "success",
            "sessions_analyzed": len(sessions),
            "period_days": days,
            "response_patterns": self.analyze_response_patterns(sessions),
            "time_patterns": self.analyze_time_of_day(sessions),
            "serve_return_steps": self.analyze_serve_return_steps(sessions),
            "strengths": [s.to_dict() for s in self.identify_strengths(sessions)],
            "growth_areas": [g.to_dict() for g in self.identify_growth_areas(sessions)],
        }
