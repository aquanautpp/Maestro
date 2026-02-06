"""Knowledge base module with RAG for evidence-based coaching.

Provides semantic search over early childhood development research
and generates evidence-cited coaching tips.
"""

from .vector_store import VectorStore
from .document_loader import DocumentLoader, Document, Chunk
from .rag_engine import RAGEngine

__all__ = [
    "VectorStore",
    "DocumentLoader",
    "Document",
    "Chunk",
    "RAGEngine",
]
