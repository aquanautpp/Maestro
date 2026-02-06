"""Test the full indexing pipeline."""
import sys
sys.path.insert(0, '.')

from pathlib import Path
from src.knowledge.document_loader import DocumentLoader
from src.knowledge.vector_store import VectorStore

# Test loading a PDF
loader = DocumentLoader()
research_dir = Path("content/research")
pdfs = list(research_dir.glob("*.pdf"))

print(f"Found {len(pdfs)} PDFs")
print(f"\nTesting first PDF...")

doc = loader.load_pdf(pdfs[0])
if doc:
    print(f"Document loaded: {doc.title}")
    print(f"Content length: {len(doc.content)} chars")

    # Test chunking
    chunks = loader.chunk_document(doc)
    print(f"Chunks created: {len(chunks)}")

    if chunks:
        print(f"First chunk: {chunks[0].content[:200]}...")

        # Test embedding
        print(f"\nTesting vector store...")
        store = VectorStore()

        # Try to embed one chunk
        success = store.embed_and_store_chunk(chunks[0])
        print(f"Embed success: {success}")

        if success:
            # Test search
            results = store.search("child development", k=1)
            print(f"Search results: {len(results)}")

        print(f"\nStore stats: {store.get_stats()}")
else:
    print("Failed to load document!")
