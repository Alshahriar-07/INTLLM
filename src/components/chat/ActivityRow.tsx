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
  Sparkles
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

  const getStepIcon = (type: ActivityStepType) => {
    switch (type) {
      case 'thinking': return <Sparkles className="w-3.5 h-3.5 text-purple-400" />;
      case 'flash_brain': return <Brain className="w-3.5 h-3.5 text-cyan-400" />;
      case 'hot_cache': return <Zap className="w-3.5 h-3.5 text-amber-400" />;
      case 'secondary_brain': return <Brain className="w-3.5 h-3.5 text-cyan-400" />;
      case 'web_search': return <Globe className="w-3.5 h-3.5 text-emerald-400" />;
      case 'tool': return <Wrench className="w-3.5 h-3.5 text-amber-400" />;
      case 'verification': return <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />;
      default: return <Clock className="w-3.5 h-3.5 text-slate-400" />;
    }
  };

  const totalTime = activities.reduce((acc, a) => acc + (a.latencyMs || 0), 0);

  return (
    <div className="my-2 border border-[#21262D] bg-[#0A0D12] rounded-md overflow-hidden text-xs font-mono">
      {/* Summary Row */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-3 py-2 bg-[#161B22]/80 hover:bg-[#1C2128] transition-colors text-slate-300"
      >
        <div className="flex items-center gap-2 flex-wrap">
          <span className="flex items-center gap-1 text-emerald-400 font-semibold">
            <CheckCircle2 className="w-3.5 h-3.5" /> Reasoning & Retrieval Complete
          </span>
          <span className="text-slate-500">•</span>
          <span className="text-slate-400">{totalTime}ms</span>
          {memoryCount > 0 && (
            <span className="text-cyan-400 font-sans px-1.5 py-0.2 rounded bg-cyan-950/60 border border-cyan-800/40 text-[10px]">
              {memoryCount} memories
            </span>
          )}
          {sourceCount > 0 && (
            <span className="text-emerald-400 font-sans px-1.5 py-0.2 rounded bg-emerald-950/60 border border-emerald-800/40 text-[10px]">
              {sourceCount} web sources
            </span>
          )}
        </div>
        <div className="flex items-center gap-1 text-slate-400 hover:text-slate-200">
          <span className="text-[11px]">{expanded ? 'Hide details' : 'Show details'}</span>
          {expanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        </div>
      </button>

      {/* Expanded Stack Details */}
      {expanded && (
        <div className="p-2.5 space-y-2 border-t border-[#21262D] bg-[#0A0D12]">
          {activities.map((step) => (
            <div key={step.id} className="flex items-start gap-2.5 px-2 py-1.5 rounded hover:bg-[#161B22] transition-colors">
              <span className="mt-0.5">{getStepIcon(step.type)}</span>
              <div className="flex-1 space-y-0.5">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-200">{step.label}</span>
                  {step.latencyMs && <span className="text-[10px] text-slate-500">{step.latencyMs}ms</span>}
                </div>
                {step.detail && <p className="text-[11px] text-slate-400 font-sans">{step.detail}</p>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
