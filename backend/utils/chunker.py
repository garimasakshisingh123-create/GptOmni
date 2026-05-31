"""
backend/utils/chunker.py
Text chunking with overlap for vector store ingestion.
"""


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: Input text to chunk
        chunk_size: Max characters per chunk
        overlap: Number of characters to overlap between chunks
    
    Returns:
        List of text chunks
    """
    if not text or len(text) <= chunk_size:
        return [text] if text else []

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # Try to break at sentence boundary if possible
        if end < len(text):
            # Look for the last period/newline in the window
            break_point = text.rfind(".", start, end)
            if break_point == -1:
                break_point = text.rfind("\n", start, end)
            if break_point != -1 and break_point > start + (chunk_size // 2):
                end = break_point + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Next chunk starts with overlap
        start = end - overlap
        if start >= len(text):
            break

    return chunks
