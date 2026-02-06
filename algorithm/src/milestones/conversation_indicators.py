"""Maps conversation metrics to developmental milestone indicators.

Links measurable conversation patterns to developmental milestones,
providing parents with insight into their child's progress.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class MilestoneIndicator:
    """An indicator for a developmental milestone."""
    milestone_id: str
    milestone_name: str
    indicator_name: str
    metric: str  # The metric to check (e.g., "child_speech_count")
    threshold: float
    period: str  # "session", "day", "week"
    achieved: bool = False
    current_value: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)


# Milestone indicators mapped to conversation metrics
MILESTONE_INDICATORS = {
    "language_12mo": {
        "name": "Primeiras palavras",
        "age_range": (10, 14),  # months
        "indicators": [
            {
                "name": "Vocalizacoes frequentes",
                "metric": "child_speech_count",
                "threshold": 5,
                "period": "session",
            },
        ],
    },
    "language_18mo": {
        "name": "Vocabulario em expansao",
        "age_range": (16, 20),
        "indicators": [
            {
                "name": "Inicia conversas",
                "metric": "child_initiation_ratio",
                "threshold": 0.3,
                "period": "session",
            },
        ],
    },
    "language_24mo": {
        "name": "Combinando palavras",
        "age_range": (22, 26),
        "indicators": [
            {
                "name": "Turnos de conversa",
                "metric": "moments_per_hour",
                "threshold": 20,
                "period": "session",
            },
        ],
    },
    "communication_36mo": {
        "name": "Frases mais longas",
        "age_range": (34, 38),
        "indicators": [
            {
                "name": "Conversas sustentadas",
                "metric": "longest_exchange",
                "threshold": 4,
                "period": "session",
            },
        ],
    },
    "social_12mo": {
        "name": "Respondendo a interacoes",
        "age_range": (10, 14),
        "indicators": [
            {
                "name": "Responde ao adulto",
                "metric": "response_rate",
                "threshold": 0.5,
                "period": "session",
            },
        ],
    },
    "social_24mo": {
        "name": "Interesse em outros",
        "age_range": (22, 26),
        "indicators": [
            {
                "name": "Engajamento em conversa",
                "metric": "engagement_score",
                "threshold": 0.5,
                "period": "session",
            },
        ],
    },
}


class ConversationIndicators:
    """
    Maps conversation metrics to developmental milestone indicators.

    Uses session data to identify patterns that correlate with
    healthy developmental progress.
    """

    def __init__(self):
        """Initialize conversation indicators."""
        self.indicators = MILESTONE_INDICATORS

    def get_indicators_for_age(self, age_months: int) -> List[Dict]:
        """
        Get relevant indicators for a child's age.

        Args:
            age_months: Child's age in months

        Returns:
            List of relevant milestone indicators
        """
        relevant = []

        for milestone_id, milestone_data in self.indicators.items():
            min_age, max_age = milestone_data["age_range"]

            # Include if within range or slightly before (to show upcoming)
            if min_age - 2 <= age_months <= max_age + 2:
                relevant.append({
                    "id": milestone_id,
                    "name": milestone_data["name"],
                    "age_range": f"{min_age}-{max_age} meses",
                    "indicators": milestone_data["indicators"],
                    "status": "upcoming" if age_months < min_age else "current",
                })

        return relevant

    def evaluate_session(
        self,
        session: Dict,
        age_months: int
    ) -> List[MilestoneIndicator]:
        """
        Evaluate a session against milestone indicators.

        Args:
            session: Session data dictionary
            age_months: Child's age

        Returns:
            List of evaluated indicators
        """
        results = []
        relevant_milestones = self.get_indicators_for_age(age_months)

        for milestone in relevant_milestones:
            for indicator in milestone["indicators"]:
                metric = indicator["metric"]
                threshold = indicator["threshold"]

                # Get metric value from session
                value = self._get_metric_value(session, metric)

                achieved = value is not None and value >= threshold

                results.append(MilestoneIndicator(
                    milestone_id=milestone["id"],
                    milestone_name=milestone["name"],
                    indicator_name=indicator["name"],
                    metric=metric,
                    threshold=threshold,
                    period=indicator["period"],
                    achieved=achieved,
                    current_value=value,
                ))

        return results

    def _get_metric_value(self, session: Dict, metric: str) -> Optional[float]:
        """
        Extract metric value from session data.

        Args:
            session: Session dictionary
            metric: Metric name

        Returns:
            Metric value or None
        """
        # Direct metrics
        if metric in session:
            return session[metric]

        # Computed metrics
        if metric == "response_rate":
            moments = session.get("moments", 0)
            child_speech = session.get("child_speech", 0)
            if child_speech > 0:
                return moments / child_speech
            return None

        if metric == "child_initiation_ratio":
            child = session.get("child_speech", 0)
            adult = session.get("adult_speech", 0)
            total = child + adult
            if total > 0:
                return child / total
            return None

        if metric == "engagement_score":
            # Use quality score if available
            quality = session.get("quality", {})
            return quality.get("engagement_score")

        if metric == "longest_exchange":
            # Need to compute from events
            events = session.get("events", [])
            return self._compute_longest_exchange(events)

        return None

    def _compute_longest_exchange(self, events: List[Dict]) -> int:
        """Compute longest back-and-forth exchange from events."""
        longest = 0
        current = 0
        last_speaker = None

        for event in events:
            event_type = event.get("type")
            if event_type in ["child", "adult"]:
                if last_speaker is None or event_type != last_speaker:
                    current += 1
                    longest = max(longest, current)
                else:
                    current = 1
                last_speaker = event_type

        return longest

    def get_celebration_message(
        self,
        indicator: MilestoneIndicator
    ) -> Optional[str]:
        """
        Get celebration message for achieved indicator.

        Args:
            indicator: Achieved milestone indicator

        Returns:
            Celebration message or None
        """
        if not indicator.achieved:
            return None

        messages = {
            "Vocalizacoes frequentes": "Seu filho esta se comunicando cada vez mais!",
            "Inicia conversas": "Que lindo ver seu filho iniciando conversas!",
            "Turnos de conversa": "Voces estao tendo conversas de ida-e-volta incriveis!",
            "Conversas sustentadas": "As conversas estao ficando mais longas e ricas!",
            "Responde ao adulto": "Seu filho responde quando voce fala - conexao em acao!",
            "Engajamento em conversa": "O engajamento nas conversas esta crescendo!",
        }

        return messages.get(
            indicator.indicator_name,
            f"Parabens pelo progresso em {indicator.indicator_name}!"
        )
