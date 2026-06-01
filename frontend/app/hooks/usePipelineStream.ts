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
   * Consumes the SSE stream and returns the final answer string directly.
   * This avoids stale-closure issues where React state hasn't updated yet
   * when the caller reads pipeline.streamingAnswer after await.
   */
  const consumeStream = useCallback(async (response: Response): Promise<string> => {
    reset();

    let finalAnswer = '';

    for await (const event of parseSSEStream(response)) {
      const data = event.data as Record<string, unknown>;

      if (event.event === 'stage_update') {
        const stageNum = data.stage_number as number;
        setState(prev => {
          const nextState = {
            ...prev,
            currentStageNumber: stageNum,
            stages: prev.stages.map(s =>
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
            ),
          };

          if (stageNum === 5 && data.status === 'complete' && data.detail) {
            const detail = data.detail as Record<string, unknown>;
            if (Array.isArray(detail.sources)) {
              nextState.sources = detail.sources as SourceRef[];
            }
          }

          return nextState;
        });
      } else if (event.event === 'token') {
        // Streaming token — update UI progressively
        const text = (data as { text: string }).text || '';
        finalAnswer = text; // capture last token as current answer
        setState(prev => ({ ...prev, streamingAnswer: text }));
      } else if (event.event === 'done') {
        // Final event — resolve all state
        const doneAnswer = (data.final_answer as string) || finalAnswer;
        finalAnswer = doneAnswer;

        setState(prev => ({
          ...prev,
          isComplete: true,
          runId: (data.run_id as string) || null,
          sources: (data.sources as SourceRef[]) || [],
          claims: (data.claims as Claim[]) || [],
          verificationResults: (data.verification_results as VerificationResult[]) || [],
          provenance: (data.provenance as ProvenanceRecord) || null,
          streamingAnswer: doneAnswer,
          stages: prev.stages.map(s =>
            s.status === 'pending' || s.status === 'running'
              ? { ...s, status: 'complete' as StageStatus }
              : s
          ),
        }));

        // Break out of the loop — we're done
        break;
      }
    }

    return finalAnswer;
  }, [reset]);

  return { ...state, consumeStream, reset };
}
