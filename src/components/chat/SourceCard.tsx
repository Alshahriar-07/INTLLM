import React from 'react';
import { ExternalLink, ShieldCheck } from 'lucide-react';
import { WebSource } from '../../types';
import { Card } from '../ui/Card';

export interface SourceCardProps {
  sources: WebSource[];
}

export const SourceCard: React.FC<SourceCardProps> = ({ sources }) => {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="my-3 space-y-2">
      <div className="text-xs font-mono text-slate-400 font-semibold flex items-center gap-1.5">
        <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
        VERIFIED SOURCES ({sources.length})
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
        {sources.map((src) => (
          <Card key={src.id} className="p-3 bg-[#0D1117] border-[#21262D] hover:border-emerald-500/40 transition-all space-y-1.5 group">
            <div className="flex items-center justify-between text-[11px] font-mono">
              <span className="text-emerald-400 truncate max-w-[140px]">{src.domain}</span>
              <span className="text-[10px] text-slate-500">{src.trustScore}% Trust</span>
            </div>
            <a
              href={src.url}
              target="_blank"
              rel="noreferrer"
              className="font-medium text-xs text-slate-200 group-hover:text-emerald-300 line-clamp-1 flex items-center gap-1"
            >
              {src.title}
              <ExternalLink className="w-3 h-3 text-slate-500 opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
            </a>
            <p className="text-[11px] text-slate-400 line-clamp-2 font-sans">{src.snippet}</p>
          </Card>
        ))}
      </div>
    </div>
  );
};
