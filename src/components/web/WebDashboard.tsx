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
    <div className="flex-1 overflow-y-auto"
      >
      <div className="max-w-7xl mx-auto px-4 md:px-6 py-6 space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold font-mono tracking-tight text-primary">
              LIVE WEB INTELLIGENCE
            </h1>
            <Badge variant="outline">RETRIEVAL GATEWAY</Badge>
          </div>
          <p className="text-xs text-secondary mt-1">
            Real-time web lookup with domain trust evaluation and content extraction. Sources are
            only shown when actually retrieved.
          </p>
        </div>
        <div
          className={`flex items-center gap-2 text-xs font-mono px-3 py-1.5 rounded border ${
            connected
              ? 'text-success bg-success/10 border-success/25'
              : 'text-warning bg-warning/10 border-warning/25'
          }`}
        >
          <WifiOff className={`w-3.5 h-3.5 ${connected ? 'hidden' : ''}`} />
          {connected === null ? 'Gateway Idle' : connected ? 'Gateway Connected' : 'Gateway Unavailable'}
        </div>
      </div>

      {/* Search Bar */}
      <form onSubmit={runSearch} className="flex gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-muted absolute left-3 top-1/2 -translate-y-1/2" />
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
            <Card key={src.id} className="p-3 space-y-1.5 border-border">
              <div className="flex items-center justify-between text-[11px] font-mono">
                <span className="text-success truncate max-w-[200px]">
                  {src.domain}
                </span>
                <span className="text-[10px] text-muted flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3" /> {src.trustScore}% trust
                </span>
              </div>
              <a
                href={src.url}
                target="_blank"
                rel="noreferrer"
                className="font-medium text-xs text-primary hover:text-accent line-clamp-1 flex items-center gap-1"
              >
                {src.title}
                <ExternalLink className="w-3 h-3 text-muted shrink-0" />
              </a>
              <p className="text-[11px] text-secondary line-clamp-2 font-sans">
                {src.snippet}
              </p>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="p-12 text-center space-y-3 border-border">
          <div className="p-3 rounded-full bg-panel-hover w-fit mx-auto text-muted">
            <Globe className="w-8 h-8 text-muted" />
          </div>
          <div className="space-y-1">
            <h2 className="text-base font-bold font-mono text-primary">
              {hasSearched && !error ? (searching ? 'Retrieving sources…' : 'No results returned') : 'Live Web unavailable'}
            </h2>
            <p className="text-xs text-secondary font-sans max-w-sm mx-auto">
              {error ??
                'Enter a query to retrieve verified documentation and current information from the web.'}
            </p>
          </div>
        </Card>
      )}
    </div>
    </div>
  );
};
