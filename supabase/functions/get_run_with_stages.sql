-- ============================================================
-- get_run_with_stages.sql
-- Fetch full pipeline run with all stage logs (for Intelligence Engine on reload)
-- ============================================================

CREATE OR REPLACE FUNCTION get_run_with_stages(p_run_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'run',        row_to_json(r),
        'stage_logs', (
            SELECT jsonb_agg(row_to_json(sl) ORDER BY sl.stage_number)
            FROM stage_logs sl
            WHERE sl.run_id = p_run_id
        ),
        'claims', (
            SELECT jsonb_agg(row_to_json(c))
            FROM claims c
            WHERE c.run_id = p_run_id
        ),
        'verification_results', (
            SELECT jsonb_agg(row_to_json(vr))
            FROM verification_results vr
            WHERE vr.run_id = p_run_id
        ),
        'provenance', (
            SELECT row_to_json(pr)
            FROM provenance_records pr
            WHERE pr.run_id = p_run_id
            LIMIT 1
        )
    ) INTO result
    FROM pipeline_runs r
    WHERE r.id = p_run_id;

    RETURN result;
END;
$$;
