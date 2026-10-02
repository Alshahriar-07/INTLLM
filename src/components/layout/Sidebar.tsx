import React from 'react';
import {
  LayoutDashboard,
  MessageSquare,
  Cpu,
  Brain,
  Globe,
  Compass,
  Wrench,
  Key,
  Activity,
  BookText,
  Settings,
  PanelLeftClose,
  PanelLeftOpen,
  ShieldCheck
} from 'lucide-react';
import { NavigationTab } from '../../types';
import { cn } from '../../lib/utils';
import { BrandLogo } from '../ui/BrandLogo';
import { HealthSnapshot } from '../../lib/api/client';

export interface SidebarProps {
  activeTab: NavigationTab;
  onTabChange: (tab: NavigationTab) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  connected: boolean;
  services: HealthSnapshot['services'];
  version?: string;
}

const PRIMARY_NAV: { id: NavigationTab; label: string; icon: React.ReactNode }[] = [
  { id: 'chat', label: 'Chat', icon: <MessageSquare className="w-4 h-4" /> },
  { id: 'overview', label: 'Overview', icon: <LayoutDashboard className="w-4 h-4" /> },
  { id: 'models', label: 'Models', icon: <Cpu className="w-4 h-4" /> },
  { id: 'brain', label: 'Brain', icon: <Brain className="w-4 h-4" /> }
];

const SECONDARY_NAV: { id: NavigationTab; label: string; icon: React.ReactNode }[] = [
  { id: 'web', label: 'Web', icon: <Globe className="w-4 h-4" /> },
  { id: 'browser', label: 'Browser', icon: <Compass className="w-4 h-4" /> },
  { id: 'tools', label: 'Tools', icon: <Wrench className="w-4 h-4" /> },
  { id: 'api', label: 'API', icon: <Key className="w-4 h-4" /> },
  { id: 'system', label: 'System', icon: <Activity className="w-4 h-4" /> },
  { id: 'docs', label: 'Docs', icon: <BookText className="w-4 h-4" /> }
];

const SERVICE_DOTS: { key: string; label: string; short: string }[] = [
  { key: 'ollama', label: 'Ollama engine', short: 'OLL' },
  { key: 'postgres', label: 'Postgres database', short: 'PG' },
  { key: 'intllm', label: 'Local AI runtime', short: 'INT' }
];

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onTabChange,
  collapsed,
  onToggleCollapse,
  connected,
  services,
  version
}) => {
  const statusOf = (key: string): boolean => services?.[key]?.status === 'connected';

  const renderItem = (item: { id: NavigationTab; label: string; icon: React.ReactNode }) => {
    const isActive = activeTab === item.id;
    return (
      <button
        key={item.id}
        onClick={() => onTabChange(item.id)}
        aria-current={isActive ? 'page' : undefined}
        title={collapsed ? item.label : undefined}
        className={cn(
          'w-full flex items-center gap-2.5 h-8 px-2.5 rounded-md text-[13px] transition-colors group relative focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
          collapsed && 'justify-center px-0',
          isActive
            ? 'bg-panel-hover text-primary font-medium'
            : 'text-secondary hover:text-primary hover:bg-panel-hover'
        )}
      >
        <span
          className={cn(
            'shrink-0 transition-colors',
            isActive ? 'text-accent' : 'text-muted group-hover:text-primary'
          )}
        >
          {item.icon}
        </span>
        {!collapsed && <span className="truncate">{item.label}</span>}
        {isActive && (
          <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 bg-accent rounded-r" aria-hidden />
        )}
      </button>
    );
  };

  return (
    <aside
      className={cn(
        'flex flex-col h-screen bg-panel border-r border-border transition-[width] duration-150 z-30 select-none shrink-0',
        collapsed ? 'w-14' : 'w-56'
      )}
    >
      {/* Brand Header */}
      <div className="h-14 flex items-center px-3 border-b border-border justify-between shrink-0">
        <div className="flex items-center gap-2.5 overflow-hidden">
          <BrandLogo variant={collapsed ? 'icon' : 'logo'} className="h-6" />
        </div>
        <button
          onClick={onToggleCollapse}
          className="p-1.5 rounded-md transition-colors text-muted hover:text-primary hover:bg-panel-hover focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-expanded={!collapsed}
        >
          {collapsed ? <PanelLeftOpen className="w-4 h-4" /> : <PanelLeftClose className="w-4 h-4" />}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-3 px-2 space-y-1 overflow-y-auto min-h-0" aria-label="Primary">
        {!collapsed && (
          <div className="px-2.5 pb-1 text-[10px] font-medium uppercase tracking-wider text-muted">Workspace</div>
        )}
        {PRIMARY_NAV.map(renderItem)}
        {!collapsed && (
          <div className="px-2.5 pt-4 pb-1 text-[10px] font-medium uppercase tracking-wider text-muted">
            Capabilities
          </div>
        )}
        {collapsed && <div className="mx-2 my-2 border-t border-border" aria-hidden />}
        {SECONDARY_NAV.map(renderItem)}
      </nav>

      {/* Footer: settings + status */}
      <div className="p-2 border-t border-border space-y-1 shrink-0">
        {renderItem({ id: 'settings', label: 'Settings', icon: <Settings className="w-4 h-4" /> })}

        {!collapsed ? (
          <div className="px-1.5 pt-2 space-y-1.5">
            <div className="flex items-center justify-between text-[11px] font-mono">
              <span className="text-muted">Runtime</span>
              <span className={cn('flex items-center gap-1', connected ? 'text-success' : 'text-warning')}>
                <span className={cn('w-1.5 h-1.5 rounded-full', connected ? 'bg-success' : 'bg-warning')} aria-hidden />
                {connected ? 'Connected' : 'Offline'}
              </span>
            </div>
            <div className="flex items-center gap-2 text-[9px] font-mono text-muted pt-1.5 border-t border-border">
              {SERVICE_DOTS.map((svc) => {
                const up = statusOf(svc.key);
                return (
                  <span key={svc.key} title={`${svc.label}: ${up ? 'connected' : 'offline'}`}>
                    {svc.short} {up ? '●' : '○'}
                  </span>
                );
              })}
              <span className="ml-auto flex items-center gap-1">
                <ShieldCheck className="w-3 h-3 text-success" aria-hidden />
                v{version ?? '1.0.2'}
              </span>
            </div>
          </div>
        ) : (
          <div
            className="flex flex-col items-center gap-1.5 pt-2"
            title={`INTLLM v${version ?? '1.0.2'} — ${connected ? 'Connected' : 'Offline'}`}
          >
            <span className={cn('w-2 h-2 rounded-full', connected ? 'bg-success' : 'bg-warning')} aria-hidden />
            <span className="text-[9px] font-mono text-muted">v{(version ?? '1.0.2').split('.').slice(0, 2).join('.')}</span>
          </div>
        )}
      </div>
    </aside>
  );
};
