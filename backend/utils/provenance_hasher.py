"""
backend/utils/provenance_hasher.py
SHA-256 hashing for content provenance tracking.
"""

import hashlib


def hash_content(text: str) -> str:
    """
    Compute SHA-256 hex digest of a string.
    Used to create tamper-evident hashes of source snippets and queries.
    
    Args:
        text: Text to hash
        
    Returns:
        64-character hex string (SHA-256)
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
