"""Coaching module with Claude API for personalized guidance."""

from .coach import PersonalizedCoach
from .claude_client import ClaudeClient
from .prompt_templates import PromptTemplates

__all__ = [
    "PersonalizedCoach",
    "ClaudeClient",
    "PromptTemplates",
]
