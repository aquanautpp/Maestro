"""Document loading and chunking for the knowledge base.

Loads research papers (PDF, text) and educational content (JSON)
and chunks them for embedding and retrieval.
"""

import json
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Iterator
from datetime import datetime


@dataclass
class Document:
    """Represents a loaded document."""
    id: str
    title: str
    content: str
    source: str  # 'harvard_cdc', 'shonkoff', 'pdf', etc.
    authors: Optional[str] = None
    year: Optional[int] = None
    filepath: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "authors": self.authors,
            "year": self.year,
            "filepath": self.filepath,
            "metadata": self.metadata,
            "content_length": len(self.content),
        }


@dataclass
class Chunk:
    """Represents a chunk of a document for embedding."""
    id: str
    document_id: str
    content: str
    chunk_index: int
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "content": self.content,
            "chunk_index": self.chunk_index,
            "metadata": self.metadata,
        }


class DocumentLoader:
    """
    Loads and chunks documents for the knowledge base.

    Supports:
    - JSON files (harvard_cdc.json, etc.)
    - PDF files (research papers)
    - Plain text files
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ):
        """
        Initialize document loader.

        Args:
            chunk_size: Target size of each chunk in characters
            chunk_overlap: Overlap between chunks to maintain context
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def load_json_content(self, filepath: Path) -> List[Document]:
        """
        Load educational content from JSON file.

        Extracts structured content and creates one document per section.

        Args:
            filepath: Path to JSON file

        Returns:
            List of Document objects
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        documents = []
        source = filepath.stem  # e.g., "harvard_cdc"

        # Extract serve_and_return section
        if "serve_and_return" in data:
            sr = data["serve_and_return"]
            content_parts = [
                f"Serve-and-Return: {sr.get('definition', '')}",
                f"Por que importa: {sr.get('why', '')}",
            ]

            for step in sr.get("steps", []):
                step_text = f"\nPasso {step['step']}: {step['name']}\n{step['description']}"
                if step.get("examples"):
                    step_text += "\nExemplos: " + "; ".join(step["examples"])
                content_parts.append(step_text)

            doc = Document(
                id=self._generate_id(f"{source}_serve_and_return"),
                title="Serve-and-Return: Os 5 Passos",
                content="\n".join(content_parts),
                source=source,
                metadata={"section": "serve_and_return"},
            )
            documents.append(doc)

        # Extract brain_architecture section
        if "brain_architecture" in data:
            ba = data["brain_architecture"]
            content = "Arquitetura Cerebral\n\nFatos importantes:\n"
            content += "\n".join(f"- {fact}" for fact in ba.get("key_facts", []))
            content += "\n\nO que pais podem fazer:\n"
            content += "\n".join(f"- {tip}" for tip in ba.get("what_parents_can_do", []))

            doc = Document(
                id=self._generate_id(f"{source}_brain_architecture"),
                title="Arquitetura Cerebral nos Primeiros Anos",
                content=content,
                source=source,
                metadata={"section": "brain_architecture"},
            )
            documents.append(doc)

        # Extract activities by area
        if "activities_by_area" in data:
            for area, area_data in data["activities_by_area"].items():
                content_parts = [
                    f"Area: {area.capitalize()}",
                    area_data.get("description", ""),
                ]

                for activity in area_data.get("activities", []):
                    act_text = f"\n{activity['title']} (idades {activity.get('ages', '0-6')})"
                    act_text += f"\n{activity['description']}"
                    act_text += f"\nPor que funciona: {activity.get('why', '')}"
                    content_parts.append(act_text)

                doc = Document(
                    id=self._generate_id(f"{source}_activities_{area}"),
                    title=f"Atividades: {area.capitalize()}",
                    content="\n".join(content_parts),
                    source=source,
                    metadata={"section": "activities", "area": area},
                )
                documents.append(doc)

        # Extract developmental milestones
        if "developmental_milestones" in data:
            content_parts = ["Marcos do Desenvolvimento por Idade"]

            for age_range, milestone in data["developmental_milestones"].items():
                ms_text = f"\n{age_range}:"
                ms_text += f"\nO que esperar: {milestone.get('what_to_expect', '')}"
                ms_text += f"\nComo interagir: {milestone.get('how_to_interact', '')}"
                content_parts.append(ms_text)

            doc = Document(
                id=self._generate_id(f"{source}_milestones"),
                title="Marcos do Desenvolvimento",
                content="\n".join(content_parts),
                source=source,
                metadata={"section": "milestones"},
            )
            documents.append(doc)

        # Extract three principles
        if "three_principles" in data:
            tp = data["three_principles"]
            content_parts = [
                f"3 Principios para Melhorar Resultados",
                f"Fonte: {tp.get('source', 'Harvard CDC')}",
            ]

            for principle in tp.get("principles", []):
                p_text = f"\n{principle['name']}"
                p_text += f"\n{principle['description']}"
                p_text += f"\nPara o Maestro: {principle.get('for_maestro', '')}"
                content_parts.append(p_text)

            doc = Document(
                id=self._generate_id(f"{source}_three_principles"),
                title="3 Principios Harvard CDC",
                content="\n".join(content_parts),
                source=source,
                metadata={"section": "three_principles"},
            )
            documents.append(doc)

        return documents

    def load_pdf(self, filepath: Path) -> Optional[Document]:
        """
        Load a PDF research paper.

        Requires PyPDF2 to be installed.

        Args:
            filepath: Path to PDF file

        Returns:
            Document object or None if loading fails
        """
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            print("PyPDF2 not installed. Run: pip install PyPDF2")
            return None

        try:
            reader = PdfReader(filepath)
            content_parts = []

            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    content_parts.append(f"[Pagina {page_num + 1}]\n{text}")

            content = "\n\n".join(content_parts)

            # Try to extract title from first page
            title = filepath.stem.replace("_", " ").replace("-", " ").title()

            doc = Document(
                id=self._generate_id(f"pdf_{filepath.stem}"),
                title=title,
                content=content,
                source="pdf",
                filepath=str(filepath),
                metadata={
                    "num_pages": len(reader.pages),
                    "loaded_at": datetime.now().isoformat(),
                },
            )
            return doc

        except Exception as e:
            print(f"Error loading PDF {filepath}: {e}")
            return None

    def load_text(self, filepath: Path) -> Optional[Document]:
        """
        Load a plain text file.

        Args:
            filepath: Path to text file

        Returns:
            Document object or None if loading fails
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            doc = Document(
                id=self._generate_id(f"text_{filepath.stem}"),
                title=filepath.stem.replace("_", " ").replace("-", " ").title(),
                content=content,
                source="text",
                filepath=str(filepath),
            )
            return doc

        except Exception as e:
            print(f"Error loading text file {filepath}: {e}")
            return None

    def chunk_document(self, document: Document) -> List[Chunk]:
        """
        Split a document into chunks for embedding.

        Uses sentence-aware chunking to avoid breaking mid-sentence.

        Args:
            document: Document to chunk

        Returns:
            List of Chunk objects
        """
        content = document.content
        chunks = []

        # Simple sentence splitting
        sentences = self._split_sentences(content)

        current_chunk = []
        current_length = 0
        chunk_index = 0

        for sentence in sentences:
            sentence_length = len(sentence)

            # If adding this sentence exceeds chunk size, save current chunk
            if current_length + sentence_length > self.chunk_size and current_chunk:
                chunk_text = " ".join(current_chunk)
                chunk = Chunk(
                    id=self._generate_id(f"{document.id}_chunk_{chunk_index}"),
                    document_id=document.id,
                    content=chunk_text,
                    chunk_index=chunk_index,
                    metadata={
                        "document_title": document.title,
                        "source": document.source,
                    },
                )
                chunks.append(chunk)
                chunk_index += 1

                # Start new chunk with overlap
                overlap_sentences = current_chunk[-2:] if len(current_chunk) > 2 else []
                current_chunk = overlap_sentences
                current_length = sum(len(s) for s in current_chunk)

            current_chunk.append(sentence)
            current_length += sentence_length

        # Save final chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunk = Chunk(
                id=self._generate_id(f"{document.id}_chunk_{chunk_index}"),
                document_id=document.id,
                content=chunk_text,
                chunk_index=chunk_index,
                metadata={
                    "document_title": document.title,
                    "source": document.source,
                },
            )
            chunks.append(chunk)

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting on common delimiters
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _generate_id(self, seed: str) -> str:
        """Generate a short deterministic ID from a seed string."""
        return hashlib.md5(seed.encode()).hexdigest()[:12]

    def load_directory(self, directory: Path) -> List[Document]:
        """
        Load all supported documents from a directory.

        Args:
            directory: Path to directory

        Returns:
            List of loaded Document objects
        """
        documents = []

        if not directory.exists():
            return documents

        for filepath in directory.iterdir():
            if filepath.suffix == ".json":
                docs = self.load_json_content(filepath)
                documents.extend(docs)
            elif filepath.suffix == ".pdf":
                doc = self.load_pdf(filepath)
                if doc:
                    documents.append(doc)
            elif filepath.suffix in (".txt", ".md"):
                doc = self.load_text(filepath)
                if doc:
                    documents.append(doc)

        return documents
