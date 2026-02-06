"""Research paper summarizer for parent-friendly content.

Generates plain-language summaries of academic research
on early childhood development.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


class ResearchSummarizer:
    """
    Summarizes research papers for parents.

    Uses Claude API to generate plain-language summaries
    and pre-caches them for offline access.
    """

    def __init__(self, summaries_path: Optional[Path] = None):
        """
        Initialize summarizer.

        Args:
            summaries_path: Path to summaries JSON file
        """
        if summaries_path is None:
            summaries_path = Path(__file__).parent.parent.parent / "content" / "research" / "summaries.json"

        self.summaries_path = summaries_path
        self._summaries: Optional[Dict] = None
        self._claude_client = None

    def _get_claude_client(self):
        """Lazy-load Claude client."""
        if self._claude_client is None:
            try:
                import anthropic
                self._claude_client = anthropic.Anthropic()
            except ImportError:
                return None
        return self._claude_client

    @property
    def summaries(self) -> Dict:
        """Lazy-load summaries from file."""
        if self._summaries is None:
            self._summaries = self._load_summaries()
        return self._summaries

    def _load_summaries(self) -> Dict:
        """Load summaries from JSON file."""
        if not self.summaries_path.exists():
            return {"papers": [], "last_updated": None}

        try:
            with open(self.summaries_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"papers": [], "last_updated": None}

    def _save_summaries(self):
        """Save summaries to JSON file."""
        self.summaries_path.parent.mkdir(parents=True, exist_ok=True)

        self._summaries["last_updated"] = datetime.now().isoformat()

        with open(self.summaries_path, "w", encoding="utf-8") as f:
            json.dump(self._summaries, f, indent=2, ensure_ascii=False)

    def list_papers(
        self,
        tags: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        List available research papers.

        Args:
            tags: Optional filter by tags
            limit: Maximum papers to return

        Returns:
            List of paper summaries
        """
        papers = self.summaries.get("papers", [])

        if tags:
            papers = [
                p for p in papers
                if any(t in p.get("tags", []) for t in tags)
            ]

        return papers[:limit]

    def get_paper(self, paper_id: str) -> Optional[Dict]:
        """
        Get a specific paper by ID.

        Args:
            paper_id: Paper ID

        Returns:
            Paper dictionary or None
        """
        for paper in self.summaries.get("papers", []):
            if paper.get("id") == paper_id:
                return paper
        return None

    def get_featured_papers(self, count: int = 3) -> List[Dict]:
        """
        Get featured/recommended papers.

        Args:
            count: Number of papers

        Returns:
            List of featured papers
        """
        papers = self.summaries.get("papers", [])

        # Prioritize papers with 'featured' tag or highest relevance
        featured = [p for p in papers if "featured" in p.get("tags", [])]

        if len(featured) >= count:
            return featured[:count]

        # Fill with other papers
        remaining = [p for p in papers if p not in featured]
        return (featured + remaining)[:count]

    def get_available_tags(self) -> List[str]:
        """Get all available tags."""
        tags = set()
        for paper in self.summaries.get("papers", []):
            tags.update(paper.get("tags", []))
        return sorted(list(tags))

    def generate_summary(
        self,
        title: str,
        abstract: str,
        full_text: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict:
        """
        Generate a plain-language summary for a paper.

        Args:
            title: Paper title
            abstract: Paper abstract
            full_text: Optional full text
            use_cache: Whether to cache the result

        Returns:
            Summary dictionary
        """
        # Check cache first
        if use_cache:
            for paper in self.summaries.get("papers", []):
                if paper.get("title") == title:
                    return paper

        client = self._get_claude_client()
        if client is None:
            return {
                "error": "Claude API not available",
                "title": title,
            }

        prompt = f"""Voce e um especialista em desenvolvimento infantil explicando pesquisa para pais.

Resuma este artigo academico em linguagem simples:

TITULO: {title}

RESUMO: {abstract}

{f"TEXTO COMPLETO: {full_text[:3000]}..." if full_text else ""}

Forneca:
1. Um resumo em 2-3 frases para pais (plain_summary)
2. 2-3 descobertas principais (key_findings)
3. Como isso se conecta com conversas pai-filho (relevance_to_maestro)
4. 2-3 tags relevantes (tags)
5. Tempo estimado de leitura em minutos (reading_time_min)

Responda em JSON valido em portugues."""

        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse response
            text = response.content[0].text

            # Try to extract JSON
            import re
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = {"plain_summary": text}

            summary = {
                "id": self._generate_id(title),
                "title": title,
                "plain_summary": data.get("plain_summary", ""),
                "key_findings": data.get("key_findings", []),
                "relevance_to_maestro": data.get("relevance_to_maestro", ""),
                "tags": data.get("tags", []),
                "reading_time_min": data.get("reading_time_min", 3),
                "generated_at": datetime.now().isoformat(),
            }

            # Cache if enabled
            if use_cache:
                self._summaries["papers"].append(summary)
                self._save_summaries()

            return summary

        except Exception as e:
            return {
                "error": str(e),
                "title": title,
            }

    def _generate_id(self, title: str) -> str:
        """Generate ID from title."""
        import hashlib
        return hashlib.md5(title.encode()).hexdigest()[:12]
