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
  Settings,
  ChevronLeft,
  ChevronRight,
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
  const navItems: { id: NavigationTab; label: string; icon: React.ReactNode }[] = [
    { id: 'overview', label: 'Overview', icon: <LayoutDashboard className="w-4 h-4" /> },
    { id: 'chat', label: 'Chat', icon: <MessageSquare className="w-4 h-4" /> },
    { id: 'models', label: 'Models', icon: <Cpu className="w-4 h-4" /> },
    { id: 'brain', label: 'Brain', icon: <Brain className="w-4 h-4" /> },
    { id: 'web', label: 'Web', icon: <Globe className="w-4 h-4" /> },
    { id: 'browser', label: 'Browser', icon: <Compass className="w-4 h-4" /> },
    { id: 'tools', label: 'Tools', icon: <Wrench className="w-4 h-4" /> },
    { id: 'api', label: 'API', icon: <Key className="w-4 h-4" /> },
    { id: 'system', label: 'System', icon: <Activity className="w-4 h-4" /> },
    { id: 'settings', label: 'Settings', icon: <Settings className="w-4 h-4" /> }
  ];

  const statusOf = (key: string): boolean => services?.[key]?.status === 'connected';

  return (
    <aside
      className={cn(
        'flex flex-col h-screen bg-slate-100 dark:bg-[#0A0D12] border-r border-slate-200 dark:border-[#1C2128] transition-all duration-200 z-30 select-none shrink-0',
        collapsed ? 'w-16' : 'w-56'
      )}
    >
      {/* Brand Header */}
      <div className="h-14 flex items-center px-4 border-b border-slate-200 dark:border-[#1C2128] justify-between">
        <div className="flex items-center gap-2.5 overflow-hidden">
          <BrandLogo variant={collapsed ? 'icon' : 'logo'} className="h-6" />
        </div>
        <button
          onClick={onToggleCollapse}
          className="p-1 rounded transition-colors text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-800/60"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-expanded={!collapsed}
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Navigation List */}
      <nav className="flex-1 py-3 px-2 space-y-1 overflow-y-auto" aria-label="Primary">
        {navItems.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              aria-current={isActive ? 'page' : undefined}
              className={cn(
                'w-full flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-all group relative',
                'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-cyan-500',
                isActive
                  ? 'bg-cyan-100 dark:bg-cyan-950/60 text-cyan-700 dark:text-cyan-400 border border-cyan-300 dark:border-cyan-700/40 shadow-sm font-semibold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-[#161B22]'
              )}
              title={collapsed ? item.label : undefined}
            >
              <span
                className={cn(
                  'shrink-0 transition-colors',
                  isActive
                    ? 'text-cyan-600 dark:text-cyan-400'
                    : 'text-slate-500 dark:text-slate-400 group-hover:text-slate-900 dark:group-hover:text-slate-200'
                )}
              >
                {item.icon}
              </span>
              {!collapsed && <span>{item.label}</span>}
              {isActive && (
                <span className="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-cyan-600 dark:bg-cyan-400 rounded-l" />
              )}
            </button>
          );
        })}
      </nav>

      {/* Footer Status & Version */}
      <div className="p-3 border-t border-slate-200 dark:border-[#1C2128] bg-slate-50 dark:bg-[#07090C]">
        {!collapsed ? (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-[11px] text-slate-600 dark:text-slate-400 font-mono">
              <span>Status</span>
              <span
                className={cn(
                  'inline-flex items-center gap-1 font-sans',
                  connected ? 'text-emerald-500' : 'text-amber-500'
                )}
              >
                <span
                  className={cn(
                    'w-1.5 h-1.5 rounded-full',
                    connected ? 'bg-emerald-400' : 'bg-amber-400'
                  )}
                />
                {connected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-1 text-[9px] font-mono text-slate-500 pt-1 border-t border-slate-200 dark:border-[#161B22]">
              {SERVICE_DOTS.map((svc) => {
                const up = statusOf(svc.key);
                return (
                  <span key={svc.key} title={`${svc.label}: ${up ? 'connected' : 'offline'}`}>
                    {svc.short} {up ? '●' : '○'}
                  </span>
                );
              })}
            </div>
            <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1">
              <span className="font-mono">v{version ?? '0.4.2'}</span>
              <span className="flex items-center gap-1 text-slate-600 dark:text-slate-400">
                <ShieldCheck className="w-3 h-3 text-cyan-500" /> Local
              </span>
            </div>
          </div>
        ) : (
          <div
            className="flex flex-col items-center gap-2"
            title={`INTLLM v${version ?? '0.4.2'} — ${connected ? 'Connected' : 'Disconnected'}`}
          >
            <span
              className={cn('w-2 h-2 rounded-full', connected ? 'bg-emerald-400' : 'bg-amber-400')}
            />
            <span className="text-[9px] font-mono text-slate-500">v0.4</span>
          </div>
        )}
      </div>
    </aside>
  );
};
