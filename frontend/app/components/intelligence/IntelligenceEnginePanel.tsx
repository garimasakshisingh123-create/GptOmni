'use client';
// app/components/intelligence/IntelligenceEnginePanel.tsx
import { useState } from 'react';
import { Zap, X } from 'lucide-react';
import { StageLog } from '../../types/pipeline';
import { Claim, VerificationResult, SourceRef, ProvenanceRecord } from '../../types/verification';
import { PipelineStageCard } from './PipelineStageCard';
import { SourceCard } from './SourceCard';
import { ClaimVerifierCard } from './ClaimVerifierCard';

interface Props {
  stages: StageLog[];
  sources: SourceRef[];
  claims: Claim[];
  verificationResults: VerificationResult[];
  provenance: ProvenanceRecord | null;
  isComplete: boolean;
  currentStageNumber: number;
  runId: string | null;
}

type Tab = 'pipeline' | 'sources' | 'verification' | 'provenance';

export function IntelligenceEnginePanel({
  stages, sources, claims, verificationResults, provenance, isComplete, currentStageNumber, runId
}: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>('pipeline');

  const isRunning = !isComplete && currentStageNumber > 0;
  const verifiedCount = verificationResults.filter(r => r.verdict === 'VERIFIED').length;
  const contradictedCount = verificationResults.filter(r => r.verdict === 'CONTRADICTED').length;

  const buttonLabel = isRunning
    ? `Running... Stage ${currentStageNumber}/9`
    : 'Intelligence Engine';

  const tabs: { id: Tab; label: string; count?: number }[] = [
    { id: 'pipeline', label: 'Pipeline', count: stages.filter(s => s.status === 'complete').length },
    { id: 'sources', label: 'Sources', count: sources.length },
    { id: 'verification', label: 'Verification', count: verificationResults.length },
    { id: 'provenance', label: 'Provenance' },
  ];

  return (
    <div className="mt-2">
      {/* Toggle Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-all ${
          isRunning
            ? 'text-[#10a37f] bg-[#10a37f]/10 border border-[#10a37f]/30 animate-pulse'
            : 'text-zinc-400 hover:text-zinc-200 bg-zinc-800/50 hover:bg-zinc-800 border border-zinc-700'
        }`}
      >
        <Zap className="w-3.5 h-3.5" />
        <span>{buttonLabel}</span>
        {isComplete && <span className="text-xs">{isOpen ? '▲' : '▼'}</span>}
      </button>

      {/* Collapsible Panel */}
      {isOpen && (
        <div className="mt-2 rounded-xl border border-zinc-700 bg-zinc-900/80 backdrop-blur-sm overflow-hidden">
          {/* Panel Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-[#10a37f]" />
              <span className="text-sm font-semibold text-zinc-200">Intelligence Engine</span>
              {verificationResults.length > 0 && (
                <span className="text-xs text-zinc-500">
                  · {verifiedCount} verified{contradictedCount > 0 ? `, ${contradictedCount} contradicted` : ''}
                </span>
              )}
            </div>
            <button onClick={() => setIsOpen(false)} className="text-zinc-500 hover:text-zinc-300">
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-zinc-800">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 text-xs font-medium transition-colors relative ${
                  activeTab === tab.id
                    ? 'text-[#10a37f]'
                    : 'text-zinc-500 hover:text-zinc-300'
                }`}
              >
                {tab.label}
                {tab.count !== undefined && tab.count > 0 && (
                  <span className="ml-1 text-zinc-600">({tab.count})</span>
                )}
                {activeTab === tab.id && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#10a37f]" />
                )}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="max-h-96 overflow-y-auto">
            {/* Pipeline Tab */}
            {activeTab === 'pipeline' && (
              <div className="p-2 space-y-0.5">
                {stages.map(stage => (
                  <PipelineStageCard key={stage.stage_number} stage={stage} />
                ))}
              </div>
            )}

            {/* Sources Tab */}
            {activeTab === 'sources' && (
              <div className="p-3 space-y-3">
                {sources.length === 0 ? (
                  <p className="text-sm text-zinc-500 text-center py-4">No sources retrieved</p>
                ) : (
                  sources.map((source, i) => (
                    <SourceCard
                      key={source.source_id}
                      source={source}
                      verificationResults={verificationResults}
                      index={i}
                    />
                  ))
                )}
              </div>
            )}

            {/* Verification Tab */}
            {activeTab === 'verification' && (
              <div className="p-3 space-y-3">
                {verificationResults.length === 0 ? (
                  <p className="text-sm text-zinc-500 text-center py-4">No claims verified</p>
                ) : (
                  verificationResults.map(result => (
                    <ClaimVerifierCard key={result.claim_id} result={result} />
                  ))
                )}
              </div>
            )}

            {/* Provenance Tab */}
            {activeTab === 'provenance' && (
              <div className="p-4 space-y-3 text-sm">
                {!provenance ? (
                  <p className="text-zinc-500 text-center py-4">Provenance data not available</p>
                ) : (
                  <>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="bg-zinc-800/50 rounded-lg p-3">
                        <div className="text-xs text-zinc-500 mb-1">Run ID</div>
                        <div className="text-xs text-zinc-300 font-mono truncate">{runId || provenance.run_id}</div>
                      </div>
                      <div className="bg-zinc-800/50 rounded-lg p-3">
                        <div className="text-xs text-zinc-500 mb-1">Pipeline Version</div>
                        <div className="text-xs text-zinc-300">{provenance.pipeline_version}</div>
                      </div>
                      <div className="bg-zinc-800/50 rounded-lg p-3">
                        <div className="text-xs text-zinc-500 mb-1">Query Hash</div>
                        <div className="text-xs text-zinc-300 font-mono truncate">{provenance.query_hash}</div>
                      </div>
                      <div className="bg-zinc-800/50 rounded-lg p-3">
                        <div className="text-xs text-zinc-500 mb-1">Timestamp</div>
                        <div className="text-xs text-zinc-300">{new Date(provenance.created_at).toLocaleString()}</div>
                      </div>
                    </div>

                    <div className="bg-zinc-800/50 rounded-lg p-3">
                      <div className="text-xs text-zinc-500 mb-2">Verification Summary</div>
                      <div className="flex gap-3">
                        {Object.entries(provenance.verification_summary).map(([verdict, count]) => (
                          <span key={verdict} className="text-xs text-zinc-300">
                            {verdict}: <strong>{count as number}</strong>
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="bg-zinc-800/50 rounded-lg p-3">
                      <div className="text-xs text-zinc-500 mb-2">Models Used</div>
                      <div className="space-y-1">
                        {provenance.models_used.map(m => (
                          <div key={m} className="text-xs text-zinc-300 font-mono">{m}</div>
                        ))}
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
