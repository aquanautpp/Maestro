"""Prompt templates for personalized coaching.

Contains system prompts and templates for generating
personalized, evidence-based coaching tips.
"""

from typing import Optional, Dict, Any


class PromptTemplates:
    """Templates for Claude prompts."""

    @staticmethod
    def get_system_prompt(
        child_age_months: Optional[int] = None,
        patterns: Optional[Dict] = None,
        strengths: Optional[list] = None,
    ) -> str:
        """
        Build system prompt for coaching.

        Args:
            child_age_months: Child's age
            patterns: User's interaction patterns
            strengths: Identified strengths

        Returns:
            System prompt string
        """
        prompt = """Voce e o Maestro, um coach gentil de desenvolvimento infantil.

FILOSOFIA (CRITICO - NUNCA VIOLE):
- NUNCA use palavras negativas como "errou", "falhou", "perdeu", "missed"
- NUNCA diga o que o pai/mae NAO esta fazendo
- SEMPRE celebre o que ja esta sendo feito antes de sugerir algo novo
- Sugestoes devem ser praticas, especificas e incrementais
- Tom SEMPRE esperancoso e encorajador
- Cite a ciencia quando relevante, de forma acessivel

FORMATO:
- Maximo 4 frases curtas
- Linguagem simples e direta
- Uma sugestao pratica por vez
- Se mencionar pesquisa, explique em uma frase
"""

        if child_age_months is not None:
            age_years = child_age_months / 12
            prompt += f"\n\nCRIANCA:\n- Idade: {child_age_months} meses ({age_years:.1f} anos)"

            # Add age-specific guidance
            if child_age_months < 12:
                prompt += "\n- Fase: Bebe - foco em responder a balbucios, contato visual, sorrisos"
            elif child_age_months < 24:
                prompt += "\n- Fase: Toddler - explosao de vocabulario, nomear tudo"
            elif child_age_months < 36:
                prompt += "\n- Fase: 2 anos - frases curtas, perguntas 'por que?', faz-de-conta"
            elif child_age_months < 48:
                prompt += "\n- Fase: 3 anos - historias, imaginacao, amizades"
            else:
                prompt += "\n- Fase: Pre-escolar - pensamento logico, interesse em letras/numeros"

        if patterns:
            prompt += "\n\nPADROES OBSERVADOS:"
            if patterns.get("avg_response_time"):
                prompt += f"\n- Tempo medio de resposta: {patterns['avg_response_time']:.1f}s"
            if patterns.get("total_moments"):
                prompt += f"\n- Momentos de conversa: {patterns['total_moments']}"
            if patterns.get("preferred_time"):
                prompt += f"\n- Horario preferido: {patterns['preferred_time']}"

        if strengths:
            prompt += "\n\nPONTOS FORTES (celebre estes!):"
            for s in strengths[:3]:
                if isinstance(s, dict):
                    prompt += f"\n- {s.get('title', s.get('description', str(s)))}"
                else:
                    prompt += f"\n- {s}"

        return prompt

    @staticmethod
    def get_coaching_prompt(
        topic: str,
        context: Optional[Dict] = None,
        rag_context: Optional[str] = None,
    ) -> str:
        """
        Build user prompt for coaching request.

        Args:
            topic: Topic or question
            context: Additional context
            rag_context: Retrieved knowledge base context

        Returns:
            User prompt string
        """
        prompt = ""

        if rag_context:
            prompt += f"BASE CIENTIFICA RELEVANTE:\n{rag_context}\n\n"

        if context:
            if context.get("current_session"):
                session = context["current_session"]
                prompt += f"SESSAO ATUAL:\n- Momentos: {session.get('moments', 0)}\n"
                prompt += f"- Duracao: {session.get('duration_minutes', 0):.1f} min\n\n"

        prompt += f"PEDIDO: {topic}\n\n"
        prompt += "Responda de forma pratica, positiva e encorajadora."

        return prompt

    @staticmethod
    def get_explanation_prompt(tip: str) -> str:
        """
        Build prompt to explain why a tip was given.

        Args:
            tip: The tip that was given

        Returns:
            Prompt for explanation
        """
        return f"""Esta dica foi dada: "{tip}"

Explique em 2-3 frases simples:
1. Por que essa pratica e importante para o desenvolvimento
2. O que a ciencia diz sobre isso

Use linguagem acessivel, sem jargao academico."""

    @staticmethod
    def get_encouragement_prompt(
        session_data: Dict,
        is_end_of_session: bool = False
    ) -> str:
        """
        Build prompt for session encouragement.

        Args:
            session_data: Current session metrics
            is_end_of_session: Whether session is ending

        Returns:
            Prompt for encouragement
        """
        moments = session_data.get("moments", 0)
        duration = session_data.get("duration_minutes", 0)

        if is_end_of_session:
            prompt = f"""A sessao terminou com {moments} momentos de conversa em {duration:.1f} minutos.

Gere uma frase de encorajamento CURTA (1-2 frases) que:
- Celebre o esforco
- Seja especifica para os numeros (sem repetir os numeros literalmente)
- Encoraje a continuar
- NUNCA mencione o que 'faltou' ou 'poderia ter sido melhor'"""
        else:
            prompt = f"""A sessao tem {moments} momentos ate agora ({duration:.1f} min).

Gere uma frase de encorajamento CURTA durante a sessao que:
- Celebre o progresso
- Motive a continuar
- Seja leve e positiva"""

        return prompt
