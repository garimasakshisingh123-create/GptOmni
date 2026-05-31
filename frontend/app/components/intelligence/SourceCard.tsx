'use client';
// app/components/intelligence/SourceCard.tsx
import { useState } from 'react';
import { SourceRef, VerificationResult } from '../../types/verification';

interface Props {
  source: SourceRef;
  verificationResults: VerificationResult[];
  index: number;
}

export function SourceCard({ source, verificationResults, index }: Props) {
  const [expanded, setExpanded] = useState(false);

  const isHighAuthority = source.authority_tag === 'high';
  const claimIds = source.claim_ids || [];
  const snippet = source.snippet || '';
  const truncated = snippet.length > 150 ? snippet.slice(0, 150) + '…' : snippet;

  return (
    <div className={`rounded-lg border bg-zinc-900/40 overflow-hidden ${
      isHighAuthority ? 'border-l-4 border-l-blue-500 border-zinc-700' : 'border-l-4 border-l-zinc-600 border-zinc-700'
    }`}>
      <div className="p-3">
        {/* Header: favicon + domain */}
        <div className="flex items-center justify-between gap-2 mb-2">
          <div className="flex items-center gap-2 min-w-0">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={`https://www.google.com/s2/favicons?domain=${source.domain}&sz=16`}
              alt=""
              className="w-4 h-4 flex-shrink-0"
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
            <span className="text-xs text-zinc-400 truncate">{source.domain}</span>
            {isHighAuthority && (
              <span className="text-xs px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30 flex-shrink-0">
                HIGH AUTH
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            {source.published_date && (
              <span className="text-xs text-zinc-500">{source.published_date}</span>
            )}
            <span className="text-xs text-zinc-600 font-mono">SOURCE_{index + 1}</span>
          </div>
        </div>

        {/* Title */}
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-zinc-200 hover:text-[#10a37f] transition-colors font-medium line-clamp-2 block mb-2"
        >
          {source.title} ↗
        </a>

        {/* Snippet */}
        <p className="text-xs text-zinc-400 leading-relaxed">
          {expanded ? snippet : truncated}
          {snippet.length > 150 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="ml-1 text-[#10a37f] hover:underline"
            >
              {expanded ? 'Show less' : 'Show more'}
            </button>
          )}
        </p>

        {/* Claim IDs */}
        {claimIds.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {claimIds.map(id => (
              <span key={id} className="text-xs px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700">
                {id}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
