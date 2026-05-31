-- ============================================================
-- 002_vector_store.sql
-- Vector store for RAG: document chunks with embeddings
-- ============================================================

-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Document chunks table (the vector store)
CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES auth.users(id) ON DELETE SET NULL,  -- null = shared/public docs
    url             TEXT NOT NULL,
    title           TEXT,
    domain          TEXT,
    chunk_text      TEXT NOT NULL,
    chunk_index     INT NOT NULL DEFAULT 0,         -- Position within source document
    embedding       VECTOR(384) NOT NULL,           -- all-MiniLM-L6-v2 outputs 384 dims
    published_date  TEXT,
    source_type     TEXT DEFAULT 'web',             -- 'web' | 'upload' | 'kb'
    content_hash    TEXT NOT NULL,                  -- SHA-256 of chunk_text
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Cosine similarity index (IVFFlat — fast for 384 dims)
CREATE INDEX idx_documents_embedding
    ON documents
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX idx_documents_domain ON documents(domain);
CREATE INDEX idx_documents_content_hash ON documents(content_hash);

-- RLS: documents are readable by all authenticated users
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users can read documents"
    ON documents FOR SELECT
    USING (auth.role() = 'authenticated');

CREATE POLICY "Service role can insert documents"
    ON documents FOR INSERT
    WITH CHECK (true);   -- Backend service role handles inserts
