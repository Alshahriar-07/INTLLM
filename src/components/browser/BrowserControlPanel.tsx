import React, { useEffect, useState } from 'react';
import { Compass, WifiOff, Lock, Radar } from 'lucide-react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { browserService, BrowserServiceResponse } from '../../lib/services/browserService';

export const BrowserControlPanel: React.FC = () => {
  const [state, setState] = useState<BrowserServiceResponse | null>(null);
  const [url, setUrl] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | undefined>();

  const load = async () => {
    setState(await browserService.getBrowserState());
  };

  useEffect(() => {
    load();
    // Refresh status every 15s to reflect real agent state.
    const timer = setInterval(load, 15000);
    return () => clearInterval(timer);
  }, []);

  const openUrl = async () => {
    if (!url.trim() || busy) return;
    setBusy(true);
    setMessage(undefined);
    const result = await browserService.action('open', { url: url.trim() });
    if (result?.error) setMessage(String(result.error));
    await load();
    setBusy(false);
  };

  const connected = state?.connected ?? false;
  const currentUrl = state?.tabs?.[0]?.url;

  return (
    <div className="flex-1 overflow-y-auto"
      >
      <div className="max-w-7xl mx-auto px-4 md:px-6 py-6 space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold font-mono tracking-tight text-primary">
              BROWSER AGENT CONTROL PANEL
            </h1>
            <Badge variant="outline">PLAYWRIGHT HEADLESS</Badge>
          </div>
          <p className="text-xs text-secondary mt-1">
            Policy-controlled browser runtime for DOM inspection and user-approved actions.
          </p>
        </div>
        <div
          className={`flex items-center gap-2 text-xs font-mono px-3 py-1.5 rounded border ${
            connected
              ? 'text-success bg-success/10 border-success/25'
              : 'text-warning bg-warning/10 border-warning/25'
          }`}
        >
          {connected ? <Radar className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
          {connected ? (state?.active ? 'Session Active' : 'Agent Ready') : 'Browser Agent Offline'}
        </div>
      </div>

      {/* Browser Frame */}
      <Card className="p-0 overflow-hidden border-border bg-canvas">
        <div className="flex items-center gap-3 px-4 py-2.5 bg-surface border-b border-border">
          <Lock className="w-3.5 h-3.5 text-muted" />
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder={currentUrl ?? 'https://… (requires agent available)'}
            className="flex-1 bg-panel-hover rounded px-3 py-1 text-xs font-mono text-primary focus:outline-none focus:ring-1 focus:ring-ring"
          />
          <Button variant="outline" size="sm" onClick={openUrl} disabled={!connected || busy || !url.trim()}>
            Open
          </Button>
        </div>

        <div className="p-12 min-h-[300px] flex flex-col items-center justify-center text-center space-y-3">
          {state?.screenshot ? (
            <img
              src={`data:image/png;base64,${state.screenshot}`}
              alt="Browser screenshot"
              className="max-h-[420px] rounded border border-border"
            />
          ) : (
            <>
              <div className="p-4 rounded-full bg-panel-hover text-muted">
                <Compass className="w-8 h-8" />
              </div>
              <div className="space-y-1">
                <h2 className="text-base font-bold font-mono text-primary">
                  {connected ? 'No active page' : 'Browser agent offline'}
                </h2>
                <p className="text-xs text-secondary font-sans max-w-sm">
                  {connected
                    ? 'Open a URL above to start a managed browser session.'
                    : 'Playwright is not available. Install it (`pip install playwright && playwright install`) and enable the browser agent.'}
                </p>
                {message && <p className="text-xs text-error font-mono">{message}</p>}
              </div>
            </>
          )}
        </div>
      </Card>
    </div>
    </div>
  );
};
