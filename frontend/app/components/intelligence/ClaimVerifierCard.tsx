'use client';
// app/components/intelligence/ClaimVerifierCard.tsx
import { useState } from 'react';
import { VerificationResult } from '../../types/verification';
import { VerificationBadge } from './VerificationBadge';

interface Props {
  result: VerificationResult;
}

const CONFIDENCE_COLOR: Record<string, string> = {
  VERIFIED: 'bg-emerald-500',
  UNCERTAIN: 'bg-amber-500',
  CONTRADICTED: 'bg-red-500',
};

export function ClaimVerifierCard({ result }: Props) {
  const [expanded, setExpanded] = useState(false);

  const barWidth = `${Math.round(result.confidence * 100)}%`;

  return (
    <div className="rounded-lg border border-zinc-700 bg-zinc-900/40 p-3">
      {/* Claim text + badge */}
      <div className="flex items-start justify-between gap-3 mb-2">
        <p className="text-sm text-zinc-200 leading-relaxed flex-1">
          &ldquo;{result.claim_text}&rdquo;
        </p>
        <div className="flex-shrink-0">
          <VerificationBadge verdict={result.verdict} confidence={result.confidence} />
        </div>
      </div>

      {/* Confidence bar */}
      <div className="h-1 bg-zinc-800 rounded-full mb-2 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${CONFIDENCE_COLOR[result.verdict] || 'bg-zinc-500'}`}
          style={{ width: barWidth }}
        />
      </div>

      {/* Expand button */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
      >
        {expanded ? '▲ Hide details' : '▼ Show reasoning'}
      </button>

      {/* Expanded details */}
      {expanded && (
        <div className="mt-3 space-y-2 text-xs">
          {result.reasoning && (
            <div>
              <span className="text-zinc-500 block mb-1">Reasoning:</span>
              <p className="text-zinc-300">{result.reasoning}</p>
            </div>
          )}
          {result.supporting_text && (
            <div>
              <span className="text-zinc-500 block mb-1">Supporting text:</span>
              <p className="text-emerald-400 bg-emerald-500/10 rounded p-2 border border-emerald-500/20">
                &ldquo;{result.supporting_text}&rdquo;
              </p>
            </div>
          )}
          {result.contradicting_text && (
            <div>
              <span className="text-zinc-500 block mb-1">Contradicting text:</span>
              <p className="text-red-400 bg-red-500/10 rounded p-2 border border-red-500/20">
                &ldquo;{result.contradicting_text}&rdquo;
              </p>
            </div>
          )}
          {result.supporting_source_ids?.length > 0 && (
            <div className="flex gap-1 flex-wrap">
              <span className="text-zinc-500">Sources:</span>
              {result.supporting_source_ids.map(id => (
                <span key={id} className="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700">
                  {id}
                </span>
              ))}
            </div>
          )}
          <div className="text-zinc-600">Verifier: {result.verifier_model}</div>
        </div>
      )}
    </div>
  );
}
