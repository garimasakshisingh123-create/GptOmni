// app/types/pipeline.ts

export type StageStatus = 'pending' | 'running' | 'complete' | 'failed' | 'skipped';

export interface StageLog {
  stage_number: number;
  stage_name: string;
  status: StageStatus;
  summary?: string;
  detail?: Record<string, unknown>;
  duration_ms?: number | null;
  error?: string | null;
}

export interface PipelineState {
  run_id: string;
  stage_logs: StageLog[];
  is_complete: boolean;
  current_stage_number: number;
}
