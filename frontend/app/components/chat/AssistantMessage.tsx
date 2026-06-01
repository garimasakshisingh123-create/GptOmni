'use client';
// app/components/chat/AssistantMessage.tsx
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { IntelligenceEnginePanel } from '../intelligence/IntelligenceEnginePanel';
import { StageLog } from '../../types/pipeline';
import { Claim, VerificationResult, SourceRef, ProvenanceRecord } from '../../types/verification';

interface Props {
  content: string;
  stages?: StageLog[];
  sources?: SourceRef[];
  claims?: Claim[];
  verificationResults?: VerificationResult[];
  provenance?: ProvenanceRecord | null;
  isComplete?: boolean;
  currentStageNumber?: number;
  runId?: string | null;
  showIE?: boolean;
}

export function AssistantMessage({
  content,
  stages = [],
  sources = [],
  claims = [],
  verificationResults = [],
  provenance = null,
  isComplete = true,
  currentStageNumber = 0,
  runId = null,
  showIE = true,
}: Props) {
  return (
    <div className="py-4 px-4 max-w-3xl mx-auto">
      <div className="flex gap-3">
        {/* Avatar */}
        <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#10a37f] to-emerald-600 flex items-center justify-center flex-shrink-0 mt-0.5">
          <span className="text-white text-xs font-bold">G</span>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Markdown answer */}
          <div className="prose prose-invert prose-sm max-w-none
            prose-p:leading-relaxed prose-p:text-zinc-200
            prose-headings:text-zinc-100
            prose-strong:text-zinc-100
            prose-code:text-emerald-400 prose-code:bg-zinc-900 prose-code:rounded prose-code:px-1
            prose-pre:bg-zinc-900 prose-pre:border prose-pre:border-zinc-800
            prose-a:text-[#10a37f] prose-a:no-underline hover:prose-a:underline
            prose-li:text-zinc-200
            prose-blockquote:border-l-[#10a37f] prose-blockquote:text-zinc-400">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {(() => {
                let cleaned = content || '';
                // Remove the claims JSON block at the end
                const jsonMatch = cleaned.lastIndexOf('```json');
                if (jsonMatch !== -1) {
                  cleaned = cleaned.substring(0, jsonMatch);
                }
                
                // Remove trailing "```" if it's caught in the stream before "json"
                if (cleaned.endsWith('```')) {
                  cleaned = cleaned.slice(0, -3);
                }

                // Remove "Sources: [...]" lines
                cleaned = cleaned.replace(/^(?:\*\*?)?Sources:(?:\*\*?)?\s*.*$/gm, '');

                // Remove inline citations like [1], [²], [SOURCE_1], etc.
                cleaned = cleaned.replace(/\[(?:SOURCE_)?\d+\]/gi, '');
                cleaned = cleaned.replace(/\[[¹²³⁴⁵⁶⁷⁸⁹⁰]+\]/g, '');

                return cleaned.trim();
              })()}
            </ReactMarkdown>
          </div>

          {/* Intelligence Engine toggle */}
          {showIE && stages.length > 0 && (
            <IntelligenceEnginePanel
              stages={stages}
              sources={sources}
              claims={claims}
              verificationResults={verificationResults}
              provenance={provenance}
              isComplete={isComplete}
              currentStageNumber={currentStageNumber}
              runId={runId}
            />
          )}
        </div>
      </div>
    </div>
  );
}
