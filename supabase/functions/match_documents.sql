-- ============================================================
-- match_documents.sql
-- Cosine similarity search function for RAG (Stage 3)
-- ============================================================

CREATE OR REPLACE FUNCTION match_documents(
    query_embedding VECTOR(384),
    match_threshold FLOAT DEFAULT 0.3,
    match_count     INT DEFAULT 5
)
RETURNS TABLE (
    id              UUID,
    url             TEXT,
    title           TEXT,
    domain          TEXT,
    chunk_text      TEXT,
    published_date  TEXT,
    similarity      FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.url,
        d.title,
        d.domain,
        d.chunk_text,
        d.published_date,
        1 - (d.embedding <=> query_embedding) AS similarity
    FROM documents d
    WHERE 1 - (d.embedding <=> query_embedding) > match_threshold
    ORDER BY d.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
