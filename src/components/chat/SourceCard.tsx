import React from 'react';
import { ExternalLink, ShieldCheck } from 'lucide-react';
import { WebSource } from '../../types';

export interface SourceCardProps {
  sources: WebSource[];
}

export const SourceCard: React.FC<SourceCardProps> = ({ sources }) => {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="my-3 space-y-2">
      <div className="text-[11px] font-mono text-muted font-medium flex items-center gap-1.5 uppercase tracking-wide">
        <ShieldCheck className="w-3.5 h-3.5 text-success" />
        Sources ({sources.length})
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
        {sources.map((src) => (
          <a
            key={src.id}
            href={src.url}
            target="_blank"
            rel="noreferrer"
            className="block p-3 bg-surface border border-border rounded-lg hover:border-border-strong transition-colors space-y-1 group focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            <div className="flex items-center justify-between text-[11px] font-mono gap-2">
              <span className="text-accent truncate">{src.domain}</span>
              <span className="text-[10px] text-muted shrink-0">{src.trustScore}%</span>
            </div>
            <span className="flex items-center gap-1 font-medium text-xs text-primary group-hover:text-accent line-clamp-1">
              {src.title}
              <ExternalLink className="w-3 h-3 text-muted opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
            </span>
            <p className="text-[11px] text-secondary line-clamp-2 font-sans">{src.snippet}</p>
          </a>
        ))}
      </div>
    </div>
  );
};
