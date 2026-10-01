import React, { useEffect, useState } from 'react';
import { Activity, Gauge, WifiOff, Pause, Play, CheckCircle2 } from 'lucide-react';
import { BackgroundTask } from '../../types';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Progress } from '../ui/Progress';
import { Button } from '../ui/Button';
import { backgroundService } from '../../lib/services/backgroundService';

export const BackgroundLearningWidget: React.FC = () => {
  const [tasks, setTasks] = useState<BackgroundTask[]>([]);
  const [connected, setConnected] = useState(false);
  const [paused, setPaused] = useState(false);
  const [state, setState] = useState('NORMAL');
  const [error, setError] = useState<string | undefined>();

  const load = async () => {
    const result = await backgroundService.getTaskQueue();
    setTasks(result.tasks);
    setConnected(result.connected);
    setPaused(result.paused);
    setState(result.state);
    setError(result.error);
  };

  useEffect(() => {
    load();
    const timer = setInterval(load, 5000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="flex-1 overflow-y-auto"
      >
      <div className="max-w-7xl mx-auto px-4 md:px-6 py-6 space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold font-mono tracking-tight text-primary">
              BACKGROUND LEARNING ENGINE
            </h1>
            <Badge variant="outline">P2 LOW-PRIORITY WORKER</Badge>
          </div>
          <p className="text-xs text-secondary mt-1">
            Memory maintenance, expiry verification and index upkeep that yields to interactive work.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={connected ? (paused ? 'amber' : 'emerald') : 'outline'} size="md">
            {connected ? state : 'Offline'}
          </Badge>
          <Button
            variant="outline"
            size="sm"
            disabled={!connected}
            onClick={async () => {
              if (paused) await backgroundService.resume();
              else await backgroundService.pause();
              await load();
            }}
          >
            {paused ? <Play className="w-3.5 h-3.5 mr-1" /> : <Pause className="w-3.5 h-3.5 mr-1" />}
            {paused ? 'Resume' : 'Pause'}
          </Button>
        </div>
      </div>

      {/* Governor policy diagram */}
      <Card className="p-5 space-y-4 border-border bg-surface">
        <div className="text-xs font-mono font-semibold text-primary flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Gauge className="w-4 h-4 text-accent" /> RESOURCE ALLOCATION GOVERNOR POLICY
          </span>
          <span className="text-muted text-[11px]">P0 &gt; P1 &gt; P2 &gt; P3</span>
        </div>
        <div className="space-y-3 font-mono text-xs">
          <div>
            <div className="flex justify-between text-primary mb-1">
              <span>Interactive User Request (P0)</span>
              <span className="text-accent font-bold">Preempts background work</span>
            </div>
            <Progress value={100} color="cyan" showPercent={false} />
          </div>
          <div>
            <div className="flex justify-between text-primary mb-1">
              <span>Background Maintenance (P2)</span>
              <span className="text-warning font-bold">
                {connected && state !== 'NORMAL' ? 'Throttled / paused' : 'Runs when idle'}
              </span>
            </div>
            <Progress value={connected && state !== 'NORMAL' ? 15 : 60} color="amber" showPercent={false} />
          </div>
        </div>
      </Card>

      {/* Tasks */}
      {tasks.length > 0 ? (
        <div className="space-y-2">
          {tasks.map((task) => (
            <Card key={task.id} className="p-3 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-accent" />
                  <span className="text-sm font-semibold font-mono text-primary">
                    {task.name}
                  </span>
                  <Badge variant="outline" size="sm">{task.priority}</Badge>
                </div>
                <Badge
                  variant={task.status === 'completed' ? 'emerald' : task.status === 'failed' ? 'rose' : 'amber'}
                  size="sm"
                >
                  {task.status}
                </Badge>
              </div>
              <p className="text-[11px] font-mono text-muted">{task.currentAction}</p>
              <Progress value={Math.round(task.progress)} color="cyan" />
            </Card>
          ))}
        </div>
      ) : (
        <Card className="p-12 text-center space-y-3 border-border">
          <div className="p-3 rounded-full bg-panel-hover w-fit mx-auto text-muted">
            <Activity className="w-8 h-8 text-muted" />
          </div>
          <div className="space-y-1">
            <h2 className="text-base font-bold font-mono text-primary">
              {connected ? 'No background tasks yet' : 'Background learning is unavailable'}
            </h2>
            <p className="text-xs text-secondary font-sans max-w-sm mx-auto">
              {error ?? 'Maintenance tasks appear here when the worker has real work to run.'}
            </p>
            {!connected && (
              <Badge variant="outline" size="sm">
                <WifiOff className="w-3 h-3 mr-1" /> Worker Engine Offline
              </Badge>
            )}
          </div>
        </Card>
      )}
    </div>
    </div>
  );
};
