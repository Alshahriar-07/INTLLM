import React, { useState } from 'react';
import { NavigationTab } from '../../types';
import { useIntllm } from '../../hooks/use-intllm';
import { WifiOff, Loader2 } from 'lucide-react';
import { Button } from '../ui/Button';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { BootScreen } from './BootScreen';
import { OverviewDashboard } from '../overview/OverviewDashboard';
import { ChatWorkspace } from '../chat/ChatWorkspace';
import { ModelManager } from '../models/ModelManager';
import { BrainDashboard } from '../brain/BrainDashboard';
import { WebDashboard } from '../web/WebDashboard';
import { BrowserControlPanel } from '../browser/BrowserControlPanel';
import { ToolGateway } from '../tools/ToolGateway';
import { ApiDashboard } from '../api/ApiDashboard';
import { SystemDashboard } from '../system/SystemDashboard';
import { BackgroundLearningWidget } from '../learning/BackgroundLearningWidget';
import { SettingsWorkspace } from '../settings/SettingsWorkspace';

export const AppShell: React.FC = () => {
  const [booting, setBooting] = useState(true);
  const [activeTab, setActiveTab] = useState<NavigationTab>('overview');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [showLearningWidget, setShowLearningWidget] = useState(false);
  const intllm = useIntllm();

  if (booting) {
    return <BootScreen onComplete={() => setBooting(false)} />;
  }

  const renderCurrentPage = () => {
    if (showLearningWidget) {
      return <BackgroundLearningWidget />;
    }

    switch (activeTab) {
      case 'overview':
        return (
          <OverviewDashboard
            onNavigate={(tab) => {
              setShowLearningWidget(false);
              setActiveTab(tab);
            }}
          />
        );
      case 'chat':
        return (
          <ChatWorkspace
            currentModelId={intllm.currentModelId}
            onModelSelect={intllm.setCurrentModel}
            isConnected={intllm.connected && intllm.models.length > 0}
          />
        );
      case 'system':
        return <SystemDashboard />;
      case 'models':
        return <ModelManager />;
      case 'brain':
        return <BrainDashboard />;
      case 'web':
        return <WebDashboard />;
      case 'browser':
        return <BrowserControlPanel />;
      case 'tools':
        return <ToolGateway />;
      case 'api':
        return <ApiDashboard />;
      case 'settings':
        return <SettingsWorkspace />;
      default:
        return <OverviewDashboard onNavigate={setActiveTab} />;
    }
  };

  return (
    <div className="flex h-screen bg-slate-50 dark:bg-[#090D11] text-slate-900 dark:text-slate-100 overflow-hidden font-sans antialiased transition-colors">
      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={showLearningWidget ? ('overview' as any) : activeTab}
        onTabChange={(tab) => {
          setShowLearningWidget(false);
          setActiveTab(tab);
        }}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        connected={intllm.connected}
        services={intllm.services}
        version={intllm.version}
      />

      {/* Main Workspace Frame */}
      <div className="flex-1 flex flex-col h-screen min-w-0 overflow-hidden">
        {/* Header Bar */}
        <Header
          currentModelId={intllm.currentModelId}
          onModelSelect={intllm.setCurrentModel}
          onOpenSettings={() => {
            setShowLearningWidget(false);
            setActiveTab('settings');
          }}
          onOpenBackgroundLearning={() => setShowLearningWidget(!showLearningWidget)}
          isConnected={intllm.connected}
          models={intllm.models}
          services={intllm.services}
          status={intllm.status}
          ollamaStatus={intllm.ollama?.status}
          onOpenSystem={() => {
            setShowLearningWidget(false);
            setActiveTab('system');
          }}
        />

        {/* Dynamic Page View */}
        <main className="flex-1 overflow-hidden bg-slate-50 dark:bg-[#090D11] flex flex-col">
          {/* Backend Offline banner — shown on every page until connected */}
          {!intllm.loading && !intllm.connected && (
            <div className="flex items-center justify-between gap-3 px-4 py-2 bg-rose-950/40 border-b border-rose-800/40 text-rose-300 dark:text-rose-400 text-xs font-mono">
              <span className="flex items-center gap-2">
                <WifiOff className="w-3.5 h-3.5" />
                INTLLM Backend Offline — cannot reach {intllm.endpointConfigured ? 'the configured INTLLM endpoint' : 'a valid endpoint (check VITE_INTLLM_BASE_URL)'}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => intllm.refresh()}
                disabled={intllm.loading}
              >
                <Loader2 className={`w-3.5 h-3.5 ${intllm.loading ? 'animate-spin' : ''}`} />
                Retry Connection
              </Button>
            </div>
          )}
          {renderCurrentPage()}
        </main>
      </div>
    </div>
  );
};
