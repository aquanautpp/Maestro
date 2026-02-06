"""RAG (Retrieval-Augmented Generation) engine for evidence-based coaching.

Combines semantic search with LLM generation to provide
personalized, evidence-cited coaching tips.
"""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any

from .vector_store import VectorStore
from .document_loader import DocumentLoader, Document, Chunk


class RAGEngine:
    """
    RAG engine for generating evidence-based coaching responses.

    Uses semantic search to find relevant content, then optionally
    uses Claude API to generate personalized, cited responses.
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        content_dir: Optional[Path] = None,
    ):
        """
        Initialize RAG engine.

        Args:
            vector_store: VectorStore instance. If None, creates new one.
            content_dir: Directory containing content files.
        """
        self.vector_store = vector_store or VectorStore()
        self.content_dir = content_dir or Path(__file__).parent.parent.parent / "content"
        self.loader = DocumentLoader()

        # LLM client (lazy-loaded) - supports OpenAI and Claude
        self._llm_client = None

    def _get_llm_client(self):
        """Lazy-load LLM client (OpenAI or Claude)."""
        if self._llm_client is None:
            try:
                from ..coaching.claude_client import LLMClient
                self._llm_client = LLMClient()
                if self._llm_client.available:
                    print(f"RAG using LLM provider: {self._llm_client.provider}")
                else:
                    print("No LLM API key found (OPENAI_API_KEY or ANTHROPIC_API_KEY)")
                    return None
            except ImportError as e:
                print(f"LLM client not available: {e}")
                return None
            except Exception as e:
                print(f"Error initializing LLM client: {e}")
                return None
        return self._llm_client

    def index_content(self, force_reindex: bool = False) -> dict:
        """
        Index all content files for semantic search.

        Args:
            force_reindex: If True, clear existing index first

        Returns:
            Indexing statistics
        """
        if force_reindex:
            self.vector_store.clear()

        stats = {
            "documents_indexed": 0,
            "chunks_created": 0,
            "errors": [],
        }

        # Load harvard_cdc.json
        harvard_cdc_path = self.content_dir / "harvard_cdc.json"
        if harvard_cdc_path.exists():
            try:
                documents = self.loader.load_json_content(harvard_cdc_path)
                for doc in documents:
                    self.vector_store.add_document(doc)
                    stats["documents_indexed"] += 1

                    # Chunk and embed
                    chunks = self.loader.chunk_document(doc)
                    for chunk in chunks:
                        if self.vector_store.embed_and_store_chunk(chunk):
                            stats["chunks_created"] += 1

            except Exception as e:
                stats["errors"].append(f"harvard_cdc.json: {e}")

        # Load any PDFs in research directory
        research_dir = self.content_dir / "research"
        if research_dir.exists():
            for pdf_path in research_dir.glob("*.pdf"):
                try:
                    doc = self.loader.load_pdf(pdf_path)
                    if doc:
                        self.vector_store.add_document(doc)
                        stats["documents_indexed"] += 1

                        chunks = self.loader.chunk_document(doc)
                        for chunk in chunks:
                            if self.vector_store.embed_and_store_chunk(chunk):
                                stats["chunks_created"] += 1

                except Exception as e:
                    stats["errors"].append(f"{pdf_path.name}: {e}")

        return stats

    def search(
        self,
        query: str,
        k: int = 5,
        include_sources: bool = True
    ) -> List[dict]:
        """
        Search for relevant content.

        Args:
            query: Search query
            k: Number of results
            include_sources: Whether to include source info

        Returns:
            List of search results with content and metadata
        """
        results = self.vector_store.search(query, k=k)

        formatted = []
        for chunk, similarity in results:
            result = {
                "content": chunk.content,
                "similarity": round(similarity, 3),
            }
            if include_sources:
                result["source"] = chunk.metadata.get("source", "unknown")
                result["document_title"] = chunk.metadata.get("document_title", "")
            formatted.append(result)

        return formatted

    def get_context_for_query(self, query: str, k: int = 3) -> str:
        """
        Get relevant context for a query as a formatted string.

        Args:
            query: The query
            k: Number of chunks to include

        Returns:
            Formatted context string
        """
        results = self.search(query, k=k)

        if not results:
            return ""

        context_parts = []
        for i, result in enumerate(results, 1):
            source = result.get("document_title", result.get("source", ""))
            context_parts.append(
                f"[{i}] {source}:\n{result['content']}"
            )

        return "\n\n".join(context_parts)

    def generate_response(
        self,
        query: str,
        user_context: Optional[Dict[str, Any]] = None,
        use_llm: bool = True,
        max_tokens: int = 500,
    ) -> dict:
        """
        Generate an evidence-based response to a query.

        Args:
            query: User's question or topic
            user_context: Optional context about the user (child age, patterns, etc.)
            use_llm: Whether to use Claude for generation
            max_tokens: Maximum response tokens

        Returns:
            Response with answer and sources
        """
        # Get relevant context
        search_results = self.search(query, k=4)
        context = self.get_context_for_query(query, k=4)

        if not context:
            return {
                "answer": "Nao encontrei informacoes relevantes na base de conhecimento.",
                "sources": [],
                "used_llm": False,
            }

        # If not using LLM, return raw context
        if not use_llm:
            return {
                "answer": context,
                "sources": [r.get("document_title", r.get("source")) for r in search_results],
                "used_llm": False,
            }

        # Generate with LLM (OpenAI or Claude)
        client = self._get_llm_client()
        if client is None:
            # Fallback to context-only response
            return {
                "answer": context,
                "sources": [r.get("document_title", r.get("source")) for r in search_results],
                "used_llm": False,
                "note": "No LLM API key configured",
            }

        # Build prompt
        system_prompt = self._build_system_prompt(user_context)
        user_prompt = self._build_user_prompt(query, context)

        try:
            result = client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
            )

            return {
                "answer": result.get("text", context),
                "sources": [r.get("document_title", r.get("source")) for r in search_results],
                "used_llm": not result.get("fallback", False),
                "provider": result.get("provider"),
            }

        except Exception as e:
            return {
                "answer": context,
                "sources": [r.get("document_title", r.get("source")) for r in search_results],
                "used_llm": False,
                "error": str(e),
            }

    def _build_system_prompt(self, user_context: Optional[Dict[str, Any]] = None) -> str:
        """Build system prompt for Claude."""
        prompt = """Voce e o Maestro, um coach gentil de desenvolvimento infantil.

FILOSOFIA (CRITICO):
- NUNCA use palavras negativas como "errou", "falhou", "perdeu"
- Sempre celebre o que o pai/mae JA faz bem
- Sugestoes devem ser praticas e incrementais
- Cite a ciencia quando relevante
- Tom esperancoso e encorajador

FORMATO:
- Respostas curtas (2-4 frases)
- Uma sugestao pratica por vez
- Linguagem simples e acessivel
"""

        if user_context:
            prompt += "\n\nCONTEXTO DO USUARIO:\n"
            if user_context.get("child_age_months"):
                prompt += f"- Crianca: {user_context['child_age_months']} meses\n"
            if user_context.get("patterns"):
                prompt += f"- Padroes observados: {user_context['patterns']}\n"
            if user_context.get("strengths"):
                prompt += f"- Pontos fortes: {user_context['strengths']}\n"

        return prompt

    def _build_user_prompt(self, query: str, context: str) -> str:
        """Build user prompt with query and context."""
        return f"""BASE CIENTIFICA RELEVANTE:
{context}

PERGUNTA: {query}

Responda de forma pratica e encorajadora, citando a ciencia quando apropriado."""

    def ask(
        self,
        question: str,
        child_age_months: Optional[int] = None,
        use_llm: bool = True,
    ) -> dict:
        """
        Simplified interface for asking questions.

        Args:
            question: User's question
            child_age_months: Optional child's age
            use_llm: Whether to use Claude

        Returns:
            Response dictionary
        """
        user_context = None
        if child_age_months:
            user_context = {"child_age_months": child_age_months}

        return self.generate_response(
            query=question,
            user_context=user_context,
            use_llm=use_llm,
        )

    def get_coaching_tip(
        self,
        topic: str,
        child_age_months: Optional[int] = None,
        patterns: Optional[dict] = None,
    ) -> dict:
        """
        Get a coaching tip on a specific topic.

        Args:
            topic: Topic area (e.g., "nomear", "esperar", "transicoes")
            child_age_months: Optional child's age
            patterns: Optional user's interaction patterns

        Returns:
            Coaching tip with evidence
        """
        query = f"dica pratica sobre {topic} para pais de criancas pequenas"

        user_context = {}
        if child_age_months:
            user_context["child_age_months"] = child_age_months
        if patterns:
            user_context["patterns"] = patterns

        return self.generate_response(
            query=query,
            user_context=user_context if user_context else None,
            use_llm=True,
        )

    def explain_science(self, topic: str) -> dict:
        """
        Explain the science behind a topic.

        Args:
            topic: Topic to explain (e.g., "serve-and-return", "arquitetura cerebral")

        Returns:
            Explanation with sources
        """
        query = f"explicacao cientifica sobre {topic} no desenvolvimento infantil"

        return self.generate_response(
            query=query,
            use_llm=True,
            max_tokens=800,
        )
