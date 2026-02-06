"""Test PDF extraction - full document."""
from PyPDF2 import PdfReader
from pathlib import Path

research_dir = Path(__file__).parent / "content" / "research"
pdfs = list(research_dir.glob("*.pdf"))

print(f"Found {len(pdfs)} PDFs\n")

# Test first PDF thoroughly
pdf = pdfs[0]
print(f"Testing: {pdf.name}")
reader = PdfReader(pdf)
print(f"Pages: {len(reader.pages)}")

total_text = ""
for i, page in enumerate(reader.pages):
    text = page.extract_text() or ""
    total_text += text
    print(f"  Page {i+1}: {len(text)} chars")

print(f"\nTotal extracted: {len(total_text)} chars")
print(f"\nFull content preview:\n{total_text[:1000]}")
