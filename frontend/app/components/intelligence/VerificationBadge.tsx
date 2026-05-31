'use client';
// app/components/intelligence/VerificationBadge.tsx
import { Verdict } from '../../types/verification';

interface Props {
  verdict: Verdict;
  confidence: number;
  size?: 'sm' | 'md';
}

const CONFIG = {
  VERIFIED: {
    icon: '✓',
    label: 'VERIFIED',
    className: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
  },
  UNCERTAIN: {
    icon: '⚠',
    label: 'UNCERTAIN',
    className: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
  },
  CONTRADICTED: {
    icon: '✗',
    label: 'CONTRADICTED',
    className: 'bg-red-500/20 text-red-400 border border-red-500/30',
  },
};

export function VerificationBadge({ verdict, confidence, size = 'sm' }: Props) {
  const cfg = CONFIG[verdict];
  const px = size === 'md' ? 'px-3 py-1 text-sm' : 'px-2 py-0.5 text-xs';

  return (
    <span className={`inline-flex items-center gap-1 rounded-full font-medium ${px} ${cfg.className}`}>
      <span>{cfg.icon}</span>
      <span>{cfg.label}</span>
      <span className="opacity-70">· {Math.round(confidence * 100)}%</span>
    </span>
  );
}
