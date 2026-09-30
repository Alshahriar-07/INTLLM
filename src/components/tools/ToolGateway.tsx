import React, { useEffect, useState } from 'react';
import {
  Wrench,
  ShieldCheck,
  ShieldAlert,
  Lock,
  Globe,
  Compass,
  Folder,
  Terminal,
  Activity,
  WifiOff,
  CheckCircle2
} from 'lucide-react';
import { staticToolSchemas } from '../../lib/services/toolService';
import { toolService } from '../../lib/services/toolService';
import { SecurityLevel, Tool } from '../../types';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';

export const ToolGateway: React.FC = () => {
  const [tools, setTools] = useState<Tool[]>(staticToolSchemas);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    let active = true;
    toolService.getTools().then((result) => {
      if (!active) return;
      setTools(result.tools);
      setConnected(result.connected);
    });
    return () => {
      active = false;
    };
  }, []);

  const getCategoryIcon = (cat: string) => {
    switch (cat) {
      case 'web': return <Globe className="w-4 h-4 text-emerald-400" />;
      case 'browser': return <Compass className="w-4 h-4 text-cyan-400" />;
      case 'filesystem': return <Folder className="w-4 h-4 text-amber-400" />;
      case 'terminal': return <Terminal className="w-4 h-4 text-rose-400" />;
      case 'system': return <Activity className="w-4 h-4 text-purple-400" />;
      default: return <Wrench className="w-4 h-4 text-slate-400" />;
    }
  };

  const getSecurityBadge = (level: SecurityLevel) => {
    switch (level) {
      case 'read-only':
        return <Badge variant="emerald" size="sm"><ShieldCheck className="w-3 h-3 mr-1" /> Read-Only</Badge>;
      case 'requires-approval':
        return <Badge variant="amber" size="sm"><ShieldAlert className="w-3 h-3 mr-1" /> Approval Required</Badge>;
      case 'restricted':
        return <Badge variant="rose" size="sm"><Lock className="w-3 h-3 mr-1" /> Restricted OS Action</Badge>;
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto overflow-y-auto max-h-[calc(100vh-3.5rem)]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-[#21262D] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold font-mono tracking-tight text-slate-900 dark:text-slate-100">
              TOOL GATEWAY
            </h1>
            <Badge variant="outline">SECURITY SCHEMAS</Badge>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
            Sandboxed capability schemas and security policies. Models never execute OS operations
            directly without gateway validation.
          </p>
        </div>
        <div
          className={`flex items-center gap-2 text-xs font-mono px-3 py-1.5 rounded border ${
            connected
              ? 'text-emerald-500 dark:text-emerald-400 bg-emerald-950/20 border-emerald-800/40'
              : 'text-amber-500 dark:text-amber-400 bg-amber-950/30 border-amber-800/40'
          }`}
        >
          {connected ? <CheckCircle2 className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
          {connected ? 'Tool Gateway Connected' : 'Gateway Offline (static schemas)'}
        </div>
      </div>

      {/* Tools Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {tools.map((tool) => (
          <Card key={tool.id} className="p-4 space-y-3 border-slate-200 dark:border-[#21262D]">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded bg-slate-100 dark:bg-[#161B22] border border-slate-200 dark:border-slate-800">
                  {getCategoryIcon(tool.category)}
                </div>
                <div>
                  <h3 className="font-bold text-sm text-slate-900 dark:text-slate-100 font-mono">{tool.name}</h3>
                  <span className="text-[11px] text-slate-500 font-mono">ID: {tool.id}</span>
                </div>
              </div>
              <div className="flex flex-col items-end gap-1">
                {getSecurityBadge(tool.permissionLevel)}
                <Badge variant={tool.enabled ? 'outline' : 'rose'} size="sm">
                  {tool.enabled ? 'Enabled' : 'Disabled'}
                </Badge>
              </div>
            </div>

            <p className="text-xs text-slate-700 dark:text-slate-300 font-sans leading-relaxed">
              {tool.description}
            </p>
          </Card>
        ))}
      </div>
    </div>
  );
};
