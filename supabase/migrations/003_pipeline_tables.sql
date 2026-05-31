-- ============================================================
-- 003_pipeline_tables.sql
-- Pipeline runs and stage-by-stage logs — powers Intelligence Engine
-- ============================================================

-- One row per pipeline execution
CREATE TABLE pipeline_runs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id     UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id             UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    message_id          UUID REFERENCES messages(id) ON DELETE SET NULL,
    original_query      TEXT NOT NULL,
    query_hash          TEXT NOT NULL,          -- SHA-256 of original_query
    status              TEXT NOT NULL DEFAULT 'running'
                            CHECK (status IN ('running', 'complete', 'failed', 'partial')),
    intent_result       JSONB,                  -- Stage 1 output
    search_queries      JSONB,                  -- Stage 2 output
    models_used         JSONB,                  -- Array of model strings used
    prompt_versions     JSONB,                  -- Which prompt versions were active
    total_duration_ms   INT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ
);

-- One row per stage per run
CREATE TABLE stage_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    stage_number    INT NOT NULL CHECK (stage_number BETWEEN 1 AND 9),
    stage_name      TEXT NOT NULL,
    status          TEXT NOT NULL CHECK (status IN ('running', 'complete', 'failed', 'skipped')),
    summary         TEXT,                   -- Human-readable one-liner
    detail          JSONB,                  -- Full detail for expanded IE view
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    duration_ms     INT,
    error           TEXT
);

CREATE INDEX idx_stage_logs_run_id ON stage_logs(run_id);
CREATE INDEX idx_pipeline_runs_conversation ON pipeline_runs(conversation_id);

-- RLS
ALTER TABLE pipeline_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE stage_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users see own pipeline runs"
    ON pipeline_runs FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "Users see stage logs for own runs"
    ON stage_logs FOR SELECT
    USING (
        run_id IN (
            SELECT id FROM pipeline_runs WHERE user_id = auth.uid()
        )
    );

-- Allow service role to insert pipeline data
CREATE POLICY "Service role can insert pipeline runs"
    ON pipeline_runs FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Service role can update pipeline runs"
    ON pipeline_runs FOR UPDATE
    USING (true);

CREATE POLICY "Service role can insert stage logs"
    ON stage_logs FOR INSERT
    WITH CHECK (true);
