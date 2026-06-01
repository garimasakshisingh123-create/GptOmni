'use client';
// app/hooks/usePipelineStream.ts
import { useState, useCallback } from 'react';
import { StageLog, StageStatus } from '../types/pipeline';
import { Claim, VerificationResult, SourceRef, ProvenanceRecord } from '../types/verification';
import { parseSSEStream } from '../lib/sse';

function makeInitialStages(): StageLog[] {
  const names = [
    'Intent Analysis', 'Query Optimizer', 'Constant RAG',
    'Retrieval Reranking', 'Context Construction', 'Output Generation',
    'Verification', 'Post-Processing', 'Delivery',
  ];
  return names.map((name, i) => ({
    stage_number: i + 1,
    stage_name: name,
    status: 'pending' as StageStatus,
  }));
}

export interface PipelineStreamState {
  stages: StageLog[];
  sources: SourceRef[];
  claims: Claim[];
  verificationResults: VerificationResult[];
  provenance: ProvenanceRecord | null;
  isComplete: boolean;
  currentStageNumber: number;
  runId: string | null;
  streamingAnswer: string;
}

export interface ConsumeStreamResult {
  finalAnswer: string;
  /** A plain-JS snapshot of the completed pipeline state, captured inside the
   *  stream loop BEFORE React has had a chance to flush the final setState.
   *  Use this when saving the message so you always get the full IE data. */
  finalState: PipelineStreamState;
}

export function usePipelineStream() {
  const [state, setState] = useState<PipelineStreamState>({
    stages: makeInitialStages(),
    sources: [],
    claims: [],
    verificationResults: [],
    provenance: null,
    isComplete: false,
    currentStageNumber: 0,
    runId: null,
    streamingAnswer: '',
  });

  const reset = useCallback(() => {
    setState({
      stages: makeInitialStages(),
      sources: [],
      claims: [],
      verificationResults: [],
      provenance: null,
      isComplete: false,
      currentStageNumber: 0,
      runId: null,
      streamingAnswer: '',
    });
  }, []);

  /**
   * Consumes the SSE stream.
   * Returns { finalAnswer, finalState } where finalState is the complete
   * pipeline state built synchronously during streaming — it is NOT stale
   * React state, so the caller can safely use it to attach IE data to a message.
   */
  const consumeStream = useCallback(async (response: Response): Promise<ConsumeStreamResult> => {
    reset();

    // --- Mutable local mirror of state ---
    // We maintain this in parallel with React state so that when the stream
    // finishes we can hand back the complete snapshot to the caller without
    // waiting for React's async setState to flush.
    let localState: PipelineStreamState = {
      stages: makeInitialStages(),
      sources: [],
      claims: [],
      verificationResults: [],
      provenance: null,
      isComplete: false,
      currentStageNumber: 0,
      runId: null,
      streamingAnswer: '',
    };

    for await (const event of parseSSEStream(response)) {
      const data = event.data as Record<string, unknown>;

      if (event.event === 'stage_update') {
        const stageNum = data.stage_number as number;
        const updatedStages = localState.stages.map(s =>
          s.stage_number === stageNum
            ? {
                ...s,
                status: (data.status as StageStatus) || s.status,
                summary: (data.summary as string) || s.summary,
                detail: (data.detail as Record<string, unknown>) || s.detail,
                duration_ms: (data.duration_ms as number) || s.duration_ms,
                error: (data.error as string) || s.error,
              }
            : s
        );

        let updatedSources = localState.sources;
        if (stageNum === 5 && data.status === 'complete' && data.detail) {
          const detail = data.detail as Record<string, unknown>;
          if (Array.isArray(detail.sources)) {
            updatedSources = detail.sources as SourceRef[];
          }
        }

        localState = {
          ...localState,
          currentStageNumber: stageNum,
          stages: updatedStages,
          sources: updatedSources,
        };

        // Mirror into React state for live UI updates
        setState(prev => ({
          ...prev,
          currentStageNumber: stageNum,
          stages: updatedStages,
          sources: updatedSources,
        }));

      } else if (event.event === 'token') {
        // Single streaming token — update live display
        const text = (data as { text: string }).text || '';
        localState = { ...localState, streamingAnswer: text };
        setState(prev => ({ ...prev, streamingAnswer: text }));

      } else if (event.event === 'done') {
        // Final event — build the authoritative complete state
        const doneAnswer = (data.final_answer as string) || localState.streamingAnswer;

        const completedStages = localState.stages.map(s =>
          s.status === 'pending' || s.status === 'running'
            ? { ...s, status: 'complete' as StageStatus }
            : s
        );

        // Also merge in the full stage_logs from the done payload if provided
        // (the done event contains the authoritative stage summaries from backend)
        const stageLogs = data.stage_logs as Array<Record<string, unknown>> | undefined;
        const mergedStages = stageLogs && stageLogs.length > 0
          ? completedStages.map(s => {
              const log = stageLogs.find(l => (l.stage_number as number) === s.stage_number);
              if (log) {
                return {
                  ...s,
                  status: (log.status as StageStatus) || s.status,
                  summary: (log.summary as string) || s.summary,
                  detail: (log.detail as Record<string, unknown>) || s.detail,
                  duration_ms: (log.duration_ms as number) || s.duration_ms,
                  error: (log.error as string) || s.error,
                };
              }
              return s;
            })
          : completedStages;

        localState = {
          stages: mergedStages,
          sources: (data.sources as SourceRef[]) || localState.sources,
          claims: (data.claims as Claim[]) || [],
          verificationResults: (data.verification_results as VerificationResult[]) || [],
          provenance: (data.provenance as ProvenanceRecord) || null,
          isComplete: true,
          currentStageNumber: 9,
          runId: (data.run_id as string) || null,
          streamingAnswer: doneAnswer,
        };

        setState(localState);

        // Break out — we're done
        break;
      }
    }

    return { finalAnswer: localState.streamingAnswer, finalState: { ...localState } };
  }, [reset]);

  return { ...state, consumeStream, reset };
}
