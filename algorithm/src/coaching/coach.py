"""Personalized coaching using Claude API with RAG context.

Combines user patterns, knowledge base, and Claude to generate
personalized, evidence-based coaching tips.
"""

from typing import Optional, Dict, Any, List
from pathlib import Path

from .claude_client import ClaudeClient
from .prompt_templates import PromptTemplates


class PersonalizedCoach:
    """
    Personalized coaching powered by Claude API.

    Combines:
    - User's interaction patterns
    - Child's age and developmental stage
    - Knowledge base (RAG) for evidence
    - Claude API for generation
    """

    def __init__(self):
        """Initialize personalized coach."""
        self.client = ClaudeClient()
        self.templates = PromptTemplates()

        # Try to load RAG engine
        self._rag_engine = None
        try:
            from ..knowledge import RAGEngine
            self._rag_engine = RAGEngine()
        except ImportError:
            pass

        # Try to load pattern analyzer
        self._pattern_analyzer = None
        try:
            from ..analytics import PatternAnalyzer
            self._pattern_analyzer = PatternAnalyzer()
        except ImportError:
            pass

    def get_coaching_tip(
        self,
        topic: str,
        child_age_months: Optional[int] = None,
        include_evidence: bool = True,
        session_data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Get a personalized coaching tip.

        Args:
            topic: Topic or question
            child_age_months: Child's age
            include_evidence: Whether to include RAG context
            session_data: Current session data

        Returns:
            Coaching response with tip and metadata
        """
        # Gather context
        patterns = None
        strengths = None

        if self._pattern_analyzer:
            try:
                analysis = self._pattern_analyzer.get_full_analysis(days=30)
                if analysis.get("status") == "success":
                    patterns = analysis.get("response_patterns")
                    strengths = analysis.get("strengths", [])
            except Exception:
                pass

        # Get RAG context
        rag_context = None
        sources = []
        if include_evidence and self._rag_engine:
            try:
                rag_context = self._rag_engine.get_context_for_query(topic, k=2)
                search_results = self._rag_engine.search(topic, k=2)
                sources = [r.get("document_title", "") for r in search_results]
            except Exception:
                pass

        # Build prompts
        system_prompt = self.templates.get_system_prompt(
            child_age_months=child_age_months,
            patterns=patterns,
            strengths=strengths,
        )

        context = {}
        if session_data:
            context["current_session"] = session_data

        user_prompt = self.templates.get_coaching_prompt(
            topic=topic,
            context=context,
            rag_context=rag_context,
        )

        # Generate response
        response = self.client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            context={
                "topic": topic,
                "child_age": child_age_months,
            },
            max_tokens=400,
        )

        return {
            "tip": response.get("text", ""),
            "topic": topic,
            "child_age_months": child_age_months,
            "sources": sources if sources else None,
            "cached": response.get("cached", False),
            "fallback": response.get("fallback", False),
        }

    def explain_tip(self, tip: str) -> Dict[str, Any]:
        """
        Explain why a tip was given.

        Args:
            tip: The tip to explain

        Returns:
            Explanation with scientific backing
        """
        system_prompt = """Voce e um especialista em desenvolvimento infantil.
Explique a ciencia de forma simples e acessivel para pais.
Maximo 3 frases."""

        user_prompt = self.templates.get_explanation_prompt(tip)

        response = self.client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            context={"tip": tip},
            max_tokens=300,
        )

        return {
            "explanation": response.get("text", ""),
            "tip": tip,
            "cached": response.get("cached", False),
        }

    def get_encouragement(
        self,
        session_data: Dict,
        is_end_of_session: bool = False
    ) -> str:
        """
        Get encouragement for current or completed session.

        Args:
            session_data: Session metrics
            is_end_of_session: Whether session is ending

        Returns:
            Encouragement string
        """
        system_prompt = """Voce e o Maestro, um coach gentil.
Gere APENAS a frase de encorajamento, sem prefacio.
NUNCA use palavras negativas."""

        user_prompt = self.templates.get_encouragement_prompt(
            session_data=session_data,
            is_end_of_session=is_end_of_session,
        )

        response = self.client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            context={"session": session_data, "end": is_end_of_session},
            max_tokens=150,
        )

        return response.get("text", "Voces estao construindo conexao!")

    def get_weekly_insight(
        self,
        child_age_months: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get weekly insight based on patterns.

        Args:
            child_age_months: Child's age

        Returns:
            Weekly insight with tip and progress summary
        """
        # Get pattern analysis
        patterns = None
        strengths = []
        growth_areas = []

        if self._pattern_analyzer:
            try:
                analysis = self._pattern_analyzer.get_full_analysis(days=7)
                if analysis.get("status") == "success":
                    patterns = analysis
                    strengths = analysis.get("strengths", [])
                    growth_areas = analysis.get("growth_areas", [])
            except Exception:
                pass

        # Build insight
        system_prompt = self.templates.get_system_prompt(
            child_age_months=child_age_months,
            patterns=patterns.get("response_patterns") if patterns else None,
            strengths=strengths,
        )

        user_prompt = """Baseado nos padroes da semana, gere um insight personalizado:
1. Celebre um ponto forte especifico
2. Sugira UMA area para explorar na proxima semana (de forma positiva)

Seja especifico baseado nos dados, nao generico."""

        response = self.client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            context={"weekly": True, "child_age": child_age_months},
            max_tokens=400,
        )

        return {
            "insight": response.get("text", ""),
            "strengths": [s.get("title") if isinstance(s, dict) else s for s in strengths[:3]],
            "growth_area": growth_areas[0] if growth_areas else None,
            "sessions_this_week": patterns.get("sessions_analyzed", 0) if patterns else 0,
        }
