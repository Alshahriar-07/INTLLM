import React, { useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  Brain,
  Globe,
  CheckCircle2,
  Clock,
  Wrench,
  ShieldCheck,
  Zap,
  Sparkles,
  Loader2
} from 'lucide-react';
import { ActivityStep, ActivityStepType } from '../../types';
import { cn } from '../../lib/utils';

export interface ActivityRowProps {
  activities: ActivityStep[];
  memoryCount?: number;
  sourceCount?: number;
}

export const ActivityRow: React.FC<ActivityRowProps> = ({
  activities,
  memoryCount = 0,
  sourceCount = 0
}) => {
  const [expanded, setExpanded] = useState(false);

  if (!activities || activities.length === 0) return null;

  const getStepIcon = (type: ActivityStepType, status: string) => {
    if (status === 'running') return <Loader2 className="w-3.5 h-3.5 text-accent animate-spin" />;
    switch (type) {
      case 'thinking':
        return <Sparkles className="w-3.5 h-3.5 text-accent" />;
      case 'flash_brain':
        return <Brain className="w-3.5 h-3.5 text-accent" />;
      case 'hot_cache':
        return <Zap className="w-3.5 h-3.5 text-warning" />;
      case 'secondary_brain':
        return <Brain className="w-3.5 h-3.5 text-accent" />;
      case 'web_search':
        return <Globe className="w-3.5 h-3.5 text-success" />;
      case 'tool':
        return <Wrench className="w-3.5 h-3.5 text-warning" />;
      case 'verification':
        return <ShieldCheck className="w-3.5 h-3.5 text-success" />;
      default:
        return <Clock className="w-3.5 h-3.5 text-muted" />;
    }
  };

  const anyRunning = activities.some((a) => a.status === 'running');
  const totalTime = activities.reduce((acc, a) => acc + (a.latencyMs || 0), 0);

  return (
    <div className="my-2 border border-border bg-panel rounded-md overflow-hidden text-xs font-mono">
      {/* Summary Row */}
      <button
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-panel-hover transition-colors text-secondary focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
      >
        <div className="flex items-center gap-2 flex-wrap min-w-0">
          {anyRunning ? (
            <span className="flex items-center gap-1.5 text-accent font-medium">
              <Loader2 className="w-3.5 h-3.5 animate-spin" /> Working…
            </span>
          ) : (
            <span className="flex items-center gap-1 text-success font-medium">
              <CheckCircle2 className="w-3.5 h-3.5" /> Reasoning &amp; retrieval complete
            </span>
          )}
          {totalTime > 0 && (
            <>
              <span className="text-muted">·</span>
              <span className="text-muted">{totalTime}ms</span>
            </>
          )}
          {memoryCount > 0 && (
            <span className="text-accent px-1.5 py-0.5 rounded bg-accent/10 border border-accent/25 text-[10px]">
              {memoryCount} memories
            </span>
          )}
          {sourceCount > 0 && (
            <span className="text-success px-1.5 py-0.5 rounded bg-success/10 border border-success/25 text-[10px]">
              {sourceCount} web sources
            </span>
          )}
        </div>
        <div className="flex items-center gap-1 text-muted hover:text-primary">
          <span className="text-[11px]">{expanded ? 'Hide' : 'Details'}</span>
          {expanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        </div>
      </button>

      {/* Expanded Stack Details */}
      {expanded && (
        <div className="p-2.5 space-y-1.5 border-t border-border bg-panel">
          {activities.map((step) => (
            <div
              key={step.id}
              className="flex items-start gap-2.5 px-2 py-1.5 rounded hover:bg-panel-hover transition-colors"
            >
              <span className="mt-0.5 shrink-0">{getStepIcon(step.type, step.status)}</span>
              <div className="flex-1 space-y-0.5 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium text-primary">{step.label}</span>
                  {step.latencyMs && <span className="text-[10px] text-muted shrink-0">{step.latencyMs}ms</span>}
                </div>
                {step.detail && <p className="text-[11px] text-secondary font-sans break-words">{step.detail}</p>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
