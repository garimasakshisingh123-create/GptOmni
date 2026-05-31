// app/types/verification.ts

export type Verdict = 'VERIFIED' | 'UNCERTAIN' | 'CONTRADICTED';

export interface Claim {
  claim_id: string;
  claim_text: string;
  claim_type: string;
  confidence: number;
  supporting_source_ids: string[];
}

export interface VerificationResult {
  claim_id: string;
  claim_text: string;
  verdict: Verdict;
  confidence: number;
  reasoning: string;
  supporting_text: string | null;
  contradicting_text: string | null;
  supporting_source_ids: string[];
  verifier_model: string;
}

export interface SourceRef {
  source_id: string;
  url: string;
  title: string;
  domain: string;
  snippet: string;
  published_date: string | null;
  content_hash: string;
  claim_ids: string[];
  authority_tag: string;
}

export interface ProvenanceRecord {
  run_id: string;
  query_hash: string;
  verification_summary: Record<string, number>;
  models_used: string[];
  pipeline_version: string;
  created_at: string;
}
