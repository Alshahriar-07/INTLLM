import React, { useState } from 'react';
import { Globe, Search, WifiOff, ExternalLink, ShieldCheck } from 'lucide-react';
import { WebSource } from '../../types';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Input } from '../ui/Input';
import { Button } from '../ui/Button';
import { webService } from '../../lib/services/webService';

export const WebDashboard: React.FC = () => {
  const [query, setQuery] = useState('');
  const [sources, setSources] = useState<WebSource[]>([]);
  const [connected, setConnected] = useState<boolean | null>(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | undefined>();
  const [hasSearched, setHasSearched] = useState(false);

  const runSearch = async (event?: React.FormEvent) => {
    event?.preventDefault();
    const q = query.trim();
    if (!q || searching) return;
    setSearching(true);
    setHasSearched(true);
    const result = await webService.searchWeb(q);
    setSources(result.sources);
    setConnected(result.connected);
    setError(result.error);
    setSearching(false);
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto overflow-y-auto max-h-[calc(100vh-3.5rem)]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-[#21262D] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold font-mono tracking-tight text-slate-900 dark:text-slate-100">
              LIVE WEB INTELLIGENCE
            </h1>
            <Badge variant="outline">RETRIEVAL GATEWAY</Badge>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
            Real-time web lookup with domain trust evaluation and content extraction. Sources are
            only shown when actually retrieved.
          </p>
        </div>
        <div
          className={`flex items-center gap-2 text-xs font-mono px-3 py-1.5 rounded border ${
            connected
              ? 'text-emerald-500 dark:text-emerald-400 bg-emerald-950/20 border-emerald-800/40'
              : 'text-amber-500 dark:text-amber-400 bg-amber-950/30 border-amber-800/40'
          }`}
        >
          <WifiOff className={`w-3.5 h-3.5 ${connected ? 'hidden' : ''}`} />
          {connected === null ? 'Gateway Idle' : connected ? 'Gateway Connected' : 'Gateway Unavailable'}
        </div>
      </div>

      {/* Search Bar */}
      <form onSubmit={runSearch} className="flex gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search live documentation and current information…"
            className="pl-9 font-mono text-xs h-10"
          />
        </div>
        <Button variant="primary" type="submit" disabled={!query.trim() || searching} className="h-10 px-5 font-mono">
          {searching ? 'Retrieving…' : 'Execute Live Search'}
        </Button>
      </form>

      {/* Results */}
      {sources.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {sources.map((src) => (
            <Card key={src.id} className="p-3 space-y-1.5 border-slate-200 dark:border-[#21262D]">
              <div className="flex items-center justify-between text-[11px] font-mono">
                <span className="text-emerald-500 dark:text-emerald-400 truncate max-w-[200px]">
                  {src.domain}
                </span>
                <span className="text-[10px] text-slate-500 flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3" /> {src.trustScore}% trust
                </span>
              </div>
              <a
                href={src.url}
                target="_blank"
                rel="noreferrer"
                className="font-medium text-xs text-slate-800 dark:text-slate-200 hover:text-emerald-500 line-clamp-1 flex items-center gap-1"
              >
                {src.title}
                <ExternalLink className="w-3 h-3 text-slate-500 shrink-0" />
              </a>
              <p className="text-[11px] text-slate-600 dark:text-slate-400 line-clamp-2 font-sans">
                {src.snippet}
              </p>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="p-12 text-center space-y-3 border-slate-200 dark:border-[#21262D]">
          <div className="p-3 rounded-full bg-slate-200 dark:bg-slate-800/50 w-fit mx-auto text-slate-400">
            <Globe className="w-8 h-8 text-slate-500" />
          </div>
          <div className="space-y-1">
            <h2 className="text-base font-bold font-mono text-slate-800 dark:text-slate-200">
              {hasSearched && !error ? (searching ? 'Retrieving sources…' : 'No results returned') : 'Live Web unavailable'}
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-400 font-sans max-w-sm mx-auto">
              {error ??
                'Enter a query to retrieve verified documentation and current information from the web.'}
            </p>
          </div>
        </Card>
      )}
    </div>
  );
};
