"""Maps detected events to the 5 serve-and-return steps.

The 5 steps (from Harvard CDC):
1. Share the Focus - Follow child's interest
2. Support and Encourage - Respond with warmth
3. Name It - Build vocabulary
4. Take Turns - Wait for child to respond
5. Practice Endings - Help with transitions

Audio detection can primarily measure steps 3 and 4.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class StepScore:
    """Score for a serve-and-return step."""
    step: int
    name: str
    score: float  # 0-1
    detectable: bool  # Can we measure this from audio?
    indicators: List[str]
    strength_message: str
    growth_message: str

    def to_dict(self) -> dict:
        return asdict(self)


# Step definitions with indicators
SERVE_RETURN_STEPS = {
    1: StepScore(
        step=1,
        name="Compartilhe o Foco",
        score=0.0,
        detectable=False,
        indicators=["Seguir interesse da crianca", "Olhar para onde ela olha"],
        strength_message="Voce segue o interesse do seu filho naturalmente!",
        growth_message="Experimente observar mais para onde seu filho olha ou aponta.",
    ),
    2: StepScore(
        step=2,
        name="Apoie e Encoraje",
        score=0.0,
        detectable=False,  # Partially - tone could be analyzed
        indicators=["Sorrisos", "Expressoes positivas", "Tom de voz caloroso"],
        strength_message="Seu apoio emocional transparece nas interacoes!",
        growth_message="Tente adicionar mais sorrisos e tons animados.",
    ),
    3: StepScore(
        step=3,
        name="Nomeie",
        score=0.0,
        detectable=True,  # Can measure adult speech presence
        indicators=["Fala do adulto apos crianca", "Duracao da fala"],
        strength_message="Voce e otimo(a) em nomear e descrever!",
        growth_message="Quando seu filho apontar algo, diga o nome do objeto.",
    ),
    4: StepScore(
        step=4,
        name="Espere a Vez",
        score=0.0,
        detectable=True,  # Can measure response timing
        indicators=["Tempo de resposta", "Pausas entre falas"],
        strength_message="Voce da espaco para seu filho responder!",
        growth_message="Tente contar ate 5 antes de falar de novo.",
    ),
    5: StepScore(
        step=5,
        name="Pratique Transicoes",
        score=0.0,
        detectable=False,
        indicators=["Avisos de mudanca", "Descricao do que vem depois"],
        strength_message="Voce ajuda nas transicoes de forma suave!",
        growth_message="Avise 'mais um pouquinho e depois...' antes de mudar de atividade.",
    ),
}


class ServeReturnMapper:
    """
    Maps interaction patterns to serve-and-return steps.

    Uses detectable metrics to estimate proficiency in steps 3 and 4.
    Steps 1, 2, and 5 are harder to detect from audio alone.
    """

    def __init__(self):
        """Initialize the mapper."""
        self.steps = SERVE_RETURN_STEPS.copy()

    def analyze_sessions(self, sessions: List[dict]) -> Dict[str, Any]:
        """
        Analyze sessions and score each serve-and-return step.

        Args:
            sessions: List of session dictionaries

        Returns:
            Dictionary with step scores and analysis
        """
        if not sessions:
            return {
                "step_scores": {},
                "step_details": {},
                "total_sessions": 0,
            }

        # Aggregate metrics from sessions
        total_moments = 0
        total_child_speech = 0
        total_adult_speech = 0
        all_response_times = []

        for session in sessions:
            total_moments += session.get("moments", 0)
            total_child_speech += session.get("child_speech", 0)
            total_adult_speech += session.get("adult_speech", 0)
            all_response_times.extend(session.get("response_times", []))

        # Calculate step scores
        scores = {}
        details = {}

        # Step 3: Name It
        # Score based on adult speech following child speech (moments = successful returns)
        if total_child_speech > 0:
            step3_score = min(1.0, total_moments / total_child_speech)
        else:
            step3_score = 0.5  # Neutral if no data

        step3 = self.steps[3]
        step3.score = round(step3_score, 2)
        scores[3] = step3.score
        details[3] = step3.to_dict()

        # Step 4: Take Turns
        # Score based on response timing - faster isn't always better
        # Optimal is around 1-3 seconds
        if all_response_times:
            import numpy as np
            times = np.array(all_response_times)
            avg_time = np.mean(times)

            # Optimal timing: 1-3 seconds
            # Score decreases for very fast (<0.5s) or slow (>5s) responses
            if 1.0 <= avg_time <= 3.0:
                step4_score = 1.0
            elif avg_time < 1.0:
                # Too fast - might not be giving child space
                step4_score = 0.6 + (avg_time * 0.4)
            else:
                # Slower responses - still good, just score slightly lower
                step4_score = max(0.4, 1.0 - ((avg_time - 3.0) / 10.0))
        else:
            step4_score = 0.5

        step4 = self.steps[4]
        step4.score = round(step4_score, 2)
        scores[4] = step4.score
        details[4] = step4.to_dict()

        # Non-detectable steps get neutral scores
        for step_num in [1, 2, 5]:
            step = self.steps[step_num]
            step.score = 0.5  # Neutral - we can't measure these
            scores[step_num] = step.score
            details[step_num] = step.to_dict()

        return {
            "step_scores": scores,
            "step_details": details,
            "total_sessions": len(sessions),
            "total_moments": total_moments,
            "detectable_steps": [3, 4],
            "note": "Passos 1, 2 e 5 envolvem gestos e olhares que o audio nao captura.",
        }

    def get_step_tip(self, step: int, score: float) -> str:
        """
        Get a tip for a specific step based on score.

        Args:
            step: Step number (1-5)
            score: Current score for that step

        Returns:
            Appropriate tip string
        """
        step_data = self.steps.get(step)
        if not step_data:
            return ""

        if score >= 0.7:
            return step_data.strength_message
        else:
            return step_data.growth_message

    def get_weekly_focus(self, step_scores: Dict[int, float]) -> Dict[str, Any]:
        """
        Suggest which step to focus on this week.

        Args:
            step_scores: Current scores for each step

        Returns:
            Focus suggestion with tips
        """
        # Only consider detectable steps for data-driven suggestions
        detectable_scores = {k: v for k, v in step_scores.items() if k in [3, 4]}

        if not detectable_scores:
            # Default to step 3 (naming)
            focus_step = 3
        else:
            # Focus on lowest scoring detectable step
            focus_step = min(detectable_scores, key=detectable_scores.get)

        step_data = self.steps[focus_step]

        return {
            "focus_step": focus_step,
            "step_name": step_data.name,
            "current_score": step_scores.get(focus_step, 0.5),
            "tip": step_data.growth_message if step_scores.get(focus_step, 0) < 0.7 else step_data.strength_message,
            "indicators": step_data.indicators,
        }
