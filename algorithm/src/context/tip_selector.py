"""Context-aware tip selection.

Selects tips based on current context, time of day,
user patterns, and child's age.
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from .time_context import TimeContext, Context


class TipSelector:
    """
    Selects contextually appropriate tips.

    Considers:
    - Time of day
    - Day of week
    - User's interaction patterns
    - Child's age
    - Recent tips shown (to avoid repetition)
    """

    def __init__(self, tips_path: Optional[Path] = None):
        """
        Initialize tip selector.

        Args:
            tips_path: Path to contextual tips JSON
        """
        if tips_path is None:
            tips_path = Path(__file__).parent.parent.parent / "content" / "contextual_tips.json"

        self.tips_path = tips_path
        self.time_context = TimeContext()
        self._tips: Optional[Dict] = None
        self._shown_tips: List[str] = []  # Recent tip IDs

    @property
    def tips(self) -> Dict:
        """Lazy-load tips from file."""
        if self._tips is None:
            self._tips = self._load_tips()
        return self._tips

    def _load_tips(self) -> Dict:
        """Load tips from JSON file."""
        if not self.tips_path.exists():
            return self._get_default_tips()

        try:
            with open(self.tips_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return self._get_default_tips()

    def _get_default_tips(self) -> Dict:
        """Get default tips if file doesn't exist."""
        return {
            "contexts": {
                "morning_routine": {
                    "tips": [
                        {
                            "id": "morning_narrate",
                            "text": "Manhas sao otimas para narrar: 'Agora vamos escovar os dentes!'",
                            "serve_return_step": 3,
                        },
                        {
                            "id": "morning_choices",
                            "text": "Ofereca escolhas simples: 'Camiseta azul ou vermelha?'",
                            "serve_return_step": 4,
                        },
                    ]
                },
                "mealtime": {
                    "tips": [
                        {
                            "id": "meal_naming",
                            "text": "Nomeie os alimentos: 'Olha a cenoura laranja! E crocante!'",
                            "serve_return_step": 3,
                        },
                        {
                            "id": "meal_questions",
                            "text": "Pergunte sobre preferencias: 'Do que voce mais gosta?'",
                            "serve_return_step": 4,
                        },
                    ]
                },
                "playtime": {
                    "tips": [
                        {
                            "id": "play_follow",
                            "text": "Siga a lideranca do seu filho na brincadeira",
                            "serve_return_step": 1,
                        },
                        {
                            "id": "play_narrate",
                            "text": "Narre o que voces estao fazendo juntos",
                            "serve_return_step": 3,
                        },
                    ]
                },
                "bedtime_routine": {
                    "tips": [
                        {
                            "id": "bedtime_transition",
                            "text": "Avise com antecedencia: 'Mais 5 minutinhos e vamos dormir'",
                            "serve_return_step": 5,
                        },
                        {
                            "id": "bedtime_story",
                            "text": "Na historia, pause e deixe seu filho completar frases",
                            "serve_return_step": 4,
                        },
                    ]
                },
                "general": {
                    "tips": [
                        {
                            "id": "general_wait",
                            "text": "Conte ate 5 mentalmente antes de responder",
                            "serve_return_step": 4,
                        },
                        {
                            "id": "general_follow",
                            "text": "Observe para onde seu filho olha e comente",
                            "serve_return_step": 1,
                        },
                    ]
                },
            }
        }

    def get_contextual_tip(
        self,
        context: Optional[Context] = None,
        exclude_ids: Optional[List[str]] = None,
        serve_return_step: Optional[int] = None,
    ) -> Optional[Dict]:
        """
        Get a contextually appropriate tip.

        Args:
            context: Specific context. If None, auto-detects.
            exclude_ids: Tip IDs to exclude (recently shown)
            serve_return_step: Filter by serve-and-return step

        Returns:
            Tip dictionary or None
        """
        if context is None:
            context = self.time_context.get_primary_context()

        context_key = context.value
        context_tips = self.tips.get("contexts", {}).get(context_key, {}).get("tips", [])

        # Fall back to general if no tips for context
        if not context_tips:
            context_tips = self.tips.get("contexts", {}).get("general", {}).get("tips", [])

        if not context_tips:
            return None

        # Filter out excluded tips
        if exclude_ids:
            context_tips = [t for t in context_tips if t.get("id") not in exclude_ids]

        # Filter by serve-return step if specified
        if serve_return_step:
            context_tips = [
                t for t in context_tips
                if t.get("serve_return_step") == serve_return_step
            ]

        if not context_tips:
            return None

        # Return first available tip (could randomize)
        tip = context_tips[0]

        # Track shown tips
        self._shown_tips.append(tip.get("id"))
        if len(self._shown_tips) > 10:
            self._shown_tips.pop(0)

        return {
            "context": context_key,
            "tip": tip.get("text"),
            "tip_id": tip.get("id"),
            "serve_return_step": tip.get("serve_return_step"),
        }

    def get_scheduled_tips(self) -> List[Dict]:
        """
        Get suggested interaction times with tips.

        Returns:
            List of scheduled tip suggestions
        """
        schedule = []

        # Morning routine (7-9am)
        schedule.append({
            "time_range": "7:00 - 9:00",
            "context": "morning_routine",
            "suggestion": "Aproveite a rotina matinal para conversar",
        })

        # Midday/Lunch (11:30am-1pm)
        schedule.append({
            "time_range": "11:30 - 13:00",
            "context": "mealtime",
            "suggestion": "Refeicoes sao otimas para nomear alimentos",
        })

        # Afternoon play (3-5pm)
        schedule.append({
            "time_range": "15:00 - 17:00",
            "context": "playtime",
            "suggestion": "Brincar juntos fortalece conexao",
        })

        # Bedtime (7-8:30pm)
        schedule.append({
            "time_range": "19:00 - 20:30",
            "context": "bedtime_routine",
            "suggestion": "Rotina de dormir com historias e conversas",
        })

        return schedule

    def get_tip_with_context(self) -> Dict[str, Any]:
        """
        Get a tip with full context information.

        Returns:
            Dictionary with tip and context details
        """
        context_info = self.time_context.get_context_info()
        primary_context = Context(context_info["primary_context"])

        tip = self.get_contextual_tip(
            context=primary_context,
            exclude_ids=self._shown_tips[-5:],  # Exclude last 5 shown
        )

        return {
            "greeting": self.time_context.get_greeting(),
            "context": context_info,
            "tip": tip,
        }
