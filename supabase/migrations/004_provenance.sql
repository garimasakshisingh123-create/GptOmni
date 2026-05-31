-- ============================================================
-- 004_provenance.sql
-- Claims, verification results, and provenance records
-- ============================================================

-- Claims extracted from generation
CREATE TABLE claims (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    claim_id        TEXT NOT NULL,          -- "C1", "C2" etc. from pipeline
    claim_text      TEXT NOT NULL,
    claim_type      TEXT NOT NULL,
    confidence      FLOAT,
    source_ids      JSONB,                  -- Array of SOURCE_N strings
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Verification result per claim
CREATE TABLE verification_results (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id                  UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    claim_id                TEXT NOT NULL,
    verdict                 TEXT NOT NULL CHECK (verdict IN ('VERIFIED', 'UNCERTAIN', 'CONTRADICTED')),
    confidence              FLOAT NOT NULL,
    reasoning               TEXT,
    supporting_text         TEXT,
    contradicting_text      TEXT,
    supporting_source_ids   JSONB,
    verifier_model          TEXT NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Full provenance record per run
CREATE TABLE provenance_records (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id                  UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    sources                 JSONB NOT NULL,         -- Array of SourceRef objects
    verification_summary    JSONB NOT NULL,         -- {"VERIFIED": N, "UNCERTAIN": N, "CONTRADICTED": N}
    models_used             JSONB NOT NULL,
    pipeline_version        TEXT NOT NULL DEFAULT 'v1.0.0',
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_claims_run_id ON claims(run_id);
CREATE INDEX idx_verification_run_id ON verification_results(run_id);

-- RLS
ALTER TABLE claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE verification_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE provenance_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users see own claims"
    ON claims FOR SELECT
    USING (run_id IN (SELECT id FROM pipeline_runs WHERE user_id = auth.uid()));

CREATE POLICY "Users see own verification results"
    ON verification_results FOR SELECT
    USING (run_id IN (SELECT id FROM pipeline_runs WHERE user_id = auth.uid()));

CREATE POLICY "Users see own provenance"
    ON provenance_records FOR SELECT
    USING (run_id IN (SELECT id FROM pipeline_runs WHERE user_id = auth.uid()));

-- Service role inserts
CREATE POLICY "Service role can insert claims"
    ON claims FOR INSERT WITH CHECK (true);

CREATE POLICY "Service role can insert verification results"
    ON verification_results FOR INSERT WITH CHECK (true);

CREATE POLICY "Service role can insert provenance records"
    ON provenance_records FOR INSERT WITH CHECK (true);
