"""Vector store for semantic search using SQLite.

Provides offline-first vector storage and similarity search
without requiring external vector databases.
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Optional, Tuple
import numpy as np

from .document_loader import Document, Chunk


class VectorStore:
    """
    SQLite-based vector store for offline semantic search.

    Uses numpy for vector operations. For production, consider
    using sqlite-vss extension for better performance.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize vector store.

        Args:
            db_path: Path to SQLite database. If None, uses default location.
        """
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / "data" / "knowledge.db"

        self.db_path = db_path
        self._embedding_dim: Optional[int] = None
        self._embedder = None

        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                authors TEXT,
                year INTEGER,
                filepath TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Chunks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                content TEXT NOT NULL,
                chunk_index INTEGER,
                metadata TEXT,
                FOREIGN KEY (document_id) REFERENCES documents(id)
            )
        """)

        # Embeddings table (vectors stored as JSON arrays)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                chunk_id TEXT PRIMARY KEY,
                embedding TEXT NOT NULL,
                model TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chunk_id) REFERENCES chunks(id)
            )
        """)

        # Index for faster document lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunks_document
            ON chunks(document_id)
        """)

        conn.commit()
        conn.close()

    def _get_embedder(self):
        """Lazy-load sentence transformer model."""
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer
                # Use a small, fast model that works well for Portuguese
                self._embedder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                self._embedding_dim = 384
            except ImportError:
                print("sentence-transformers not installed. Run: pip install sentence-transformers")
                return None
        return self._embedder

    def add_document(self, document: Document) -> bool:
        """
        Add a document to the store.

        Args:
            document: Document to add

        Returns:
            True if added successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO documents
                (id, title, source, authors, year, filepath, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                document.id,
                document.title,
                document.source,
                document.authors,
                document.year,
                document.filepath,
                json.dumps(document.metadata),
            ))
            conn.commit()
            return True

        except Exception as e:
            print(f"Error adding document: {e}")
            return False

        finally:
            conn.close()

    def add_chunk(self, chunk: Chunk) -> bool:
        """
        Add a chunk to the store.

        Args:
            chunk: Chunk to add

        Returns:
            True if added successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO chunks
                (id, document_id, content, chunk_index, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (
                chunk.id,
                chunk.document_id,
                chunk.content,
                chunk.chunk_index,
                json.dumps(chunk.metadata),
            ))
            conn.commit()
            return True

        except Exception as e:
            print(f"Error adding chunk: {e}")
            return False

        finally:
            conn.close()

    def add_embedding(
        self,
        chunk_id: str,
        embedding: np.ndarray,
        model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    ) -> bool:
        """
        Add an embedding for a chunk.

        Args:
            chunk_id: ID of the chunk
            embedding: Embedding vector
            model: Name of the model used

        Returns:
            True if added successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Store as JSON array
            embedding_json = json.dumps(embedding.tolist())

            cursor.execute("""
                INSERT OR REPLACE INTO embeddings
                (chunk_id, embedding, model)
                VALUES (?, ?, ?)
            """, (chunk_id, embedding_json, model))
            conn.commit()
            return True

        except Exception as e:
            print(f"Error adding embedding: {e}")
            return False

        finally:
            conn.close()

    def embed_and_store_chunk(self, chunk: Chunk) -> bool:
        """
        Generate embedding for a chunk and store both.

        Args:
            chunk: Chunk to embed and store

        Returns:
            True if successful
        """
        embedder = self._get_embedder()
        if embedder is None:
            return False

        # Store chunk
        if not self.add_chunk(chunk):
            return False

        # Generate and store embedding
        embedding = embedder.encode(chunk.content)
        return self.add_embedding(chunk.id, embedding)

    def embed_query(self, query: str) -> Optional[np.ndarray]:
        """
        Generate embedding for a query string.

        Args:
            query: Query text

        Returns:
            Embedding vector or None if failed
        """
        embedder = self._get_embedder()
        if embedder is None:
            return None

        return embedder.encode(query)

    def search(
        self,
        query: str,
        k: int = 5,
        min_similarity: float = 0.3
    ) -> List[Tuple[Chunk, float]]:
        """
        Search for similar chunks using cosine similarity.

        Args:
            query: Search query
            k: Number of results to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of (Chunk, similarity_score) tuples
        """
        query_embedding = self.embed_query(query)
        if query_embedding is None:
            return []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get all embeddings (for small datasets, this is fine)
            cursor.execute("""
                SELECT c.id, c.document_id, c.content, c.chunk_index, c.metadata,
                       e.embedding
                FROM chunks c
                JOIN embeddings e ON c.id = e.chunk_id
            """)

            results = []
            for row in cursor.fetchall():
                chunk_id, doc_id, content, chunk_idx, metadata_json, embedding_json = row

                # Calculate cosine similarity
                embedding = np.array(json.loads(embedding_json))
                similarity = self._cosine_similarity(query_embedding, embedding)

                if similarity >= min_similarity:
                    chunk = Chunk(
                        id=chunk_id,
                        document_id=doc_id,
                        content=content,
                        chunk_index=chunk_idx,
                        metadata=json.loads(metadata_json) if metadata_json else {},
                    )
                    results.append((chunk, similarity))

            # Sort by similarity and return top k
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:k]

        except Exception as e:
            print(f"Error searching: {e}")
            return []

        finally:
            conn.close()

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def get_document(self, doc_id: str) -> Optional[Document]:
        """
        Get a document by ID.

        Args:
            doc_id: Document ID

        Returns:
            Document or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, title, source, authors, year, filepath, metadata
                FROM documents WHERE id = ?
            """, (doc_id,))

            row = cursor.fetchone()
            if not row:
                return None

            return Document(
                id=row[0],
                title=row[1],
                content="",  # Content not stored in documents table
                source=row[2],
                authors=row[3],
                year=row[4],
                filepath=row[5],
                metadata=json.loads(row[6]) if row[6] else {},
            )

        finally:
            conn.close()

    def list_documents(self) -> List[dict]:
        """List all documents in the store."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT d.id, d.title, d.source, d.authors, d.year,
                       COUNT(c.id) as chunk_count
                FROM documents d
                LEFT JOIN chunks c ON d.id = c.document_id
                GROUP BY d.id
            """)

            return [
                {
                    "id": row[0],
                    "title": row[1],
                    "source": row[2],
                    "authors": row[3],
                    "year": row[4],
                    "chunk_count": row[5],
                }
                for row in cursor.fetchall()
            ]

        finally:
            conn.close()

    def get_stats(self) -> dict:
        """Get statistics about the vector store."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT COUNT(*) FROM documents")
            doc_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM chunks")
            chunk_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM embeddings")
            embedding_count = cursor.fetchone()[0]

            return {
                "documents": doc_count,
                "chunks": chunk_count,
                "embeddings": embedding_count,
                "db_path": str(self.db_path),
            }

        finally:
            conn.close()

    def clear(self):
        """Clear all data from the store."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM embeddings")
            cursor.execute("DELETE FROM chunks")
            cursor.execute("DELETE FROM documents")
            conn.commit()

        finally:
            conn.close()
