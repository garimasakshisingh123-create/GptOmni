'use client';
// app/components/intelligence/PipelineStageCard.tsx
import { useState } from 'react';
import { StageLog, StageStatus } from '../../types/pipeline';

interface Props {
  stage: StageLog;
}

function StatusIcon({ status }: { status: StageStatus }) {
  if (status === 'complete') return <span className="text-[#10a37f] text-sm font-bold">✓</span>;
  if (status === 'failed') return <span className="text-red-400 text-sm font-bold">✗</span>;
  if (status === 'skipped') return <span className="text-zinc-500 text-sm">─</span>;
  if (status === 'running') return (
    <span className="inline-block w-3 h-3 rounded-full border-2 border-[#10a37f] border-t-transparent animate-spin" />
  );
  return <span className="inline-block w-3 h-3 rounded-full border border-zinc-600" />;
}

export function PipelineStageCard({ stage }: Props) {
  const [expanded, setExpanded] = useState(false);

  const durationText = stage.duration_ms != null
    ? stage.duration_ms < 1000
      ? `${stage.duration_ms}ms`
      : `${(stage.duration_ms / 1000).toFixed(1)}s`
    : null;

  const isRunning = stage.status === 'running';

  return (
    <div className={`flex gap-3 py-2 px-3 rounded-lg transition-colors ${isRunning ? 'bg-[#10a37f]/5' : ''}`}>
      <div className="flex-shrink-0 w-5 h-5 flex items-center justify-center mt-0.5">
        <StatusIcon status={stage.status} />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <span className={`text-sm font-medium ${
            stage.status === 'complete' ? 'text-zinc-200' :
            stage.status === 'running' ? 'text-[#10a37f]' :
            stage.status === 'failed' ? 'text-red-400' :
            'text-zinc-500'
          }`}>
            {stage.stage_number}. {stage.stage_name}
          </span>
          <div className="flex items-center gap-2 flex-shrink-0">
            {durationText && (
              <span className="text-xs text-zinc-500">{durationText}</span>
            )}
            {stage.detail && Object.keys(stage.detail).length > 0 && stage.status === 'complete' && (
              <button
                onClick={() => setExpanded(!expanded)}
                className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
              >
                {expanded ? '▲' : '▼'}
              </button>
            )}
          </div>
        </div>

        {stage.summary && (
          <p className="text-xs text-zinc-400 mt-0.5 leading-relaxed">{stage.summary}</p>
        )}

        {stage.error && (
          <p className="text-xs text-red-400 mt-0.5">{stage.error}</p>
        )}

        {expanded && stage.detail && (
          <div className="mt-2 p-2 bg-zinc-900/60 rounded text-xs text-zinc-400 space-y-1 border border-zinc-800">
            {Object.entries(stage.detail).map(([key, val]) => (
              <div key={key} className="flex gap-2">
                <span className="text-zinc-500 flex-shrink-0">{key}:</span>
                <span className="text-zinc-300 break-all">
                  {Array.isArray(val) ? val.join(', ') : String(val)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
