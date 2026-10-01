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
import { DocsDashboard } from '../docs/DocsDashboard';
import { SystemDashboard } from '../system/SystemDashboard';
import { BackgroundLearningWidget } from '../learning/BackgroundLearningWidget';
import { SettingsWorkspace } from '../settings/SettingsWorkspace';

export const AppShell: React.FC = () => {
  const [booting, setBooting] = useState(true);
  const [activeTab, setActiveTab] = useState<NavigationTab>('chat');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [showLearningWidget, setShowLearningWidget] = useState(false);
  const intllm = useIntllm();

  if (booting) {
    return <BootScreen onComplete={() => setBooting(false)} />;
  }

  const navigate = (tab: NavigationTab) => {
    setShowLearningWidget(false);
    setActiveTab(tab);
  };

  const renderCurrentPage = () => {
    if (showLearningWidget) {
      return <BackgroundLearningWidget />;
    }

    switch (activeTab) {
      case 'overview':
        return <OverviewDashboard onNavigate={navigate} />;
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
      case 'docs':
        return <DocsDashboard />;
      case 'settings':
        return <SettingsWorkspace />;
      default:
        return <OverviewDashboard onNavigate={navigate} />;
    }
  };

  return (
    <div className="flex h-screen bg-canvas text-primary overflow-hidden font-sans antialiased transition-colors duration-150">
      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={showLearningWidget ? 'overview' : activeTab}
        onTabChange={navigate}
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
          onOpenSettings={() => navigate('settings')}
          onOpenBackgroundLearning={() => setShowLearningWidget(!showLearningWidget)}
          isConnected={intllm.connected}
          models={intllm.models}
          status={intllm.status}
          ollamaStatus={intllm.ollama?.status}
          onOpenSystem={() => navigate('system')}
        />

        {/* Dynamic Page View */}
        <main className="flex-1 overflow-hidden bg-canvas flex flex-col min-h-0">
          {/* Backend Offline banner — shown on every page until connected */}
          {!intllm.loading && !intllm.connected && (
            <div
              role="alert"
              className="flex items-center justify-between gap-3 px-4 py-2 bg-error/10 border-b border-error/20 text-error text-xs font-mono"
            >
              <span className="flex items-center gap-2 min-w-0">
                <WifiOff className="w-3.5 h-3.5 shrink-0" aria-hidden />
                <span className="truncate">
                  INTLLM backend offline —{' '}
                  {intllm.endpointConfigured
                    ? 'cannot reach the configured endpoint'
                    : 'no valid endpoint configured (check VITE_INTLLM_BASE_URL)'}
                </span>
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => intllm.refresh()}
                disabled={intllm.loading}
                className="shrink-0"
              >
                <Loader2 className={`w-3.5 h-3.5 ${intllm.loading ? 'animate-spin' : ''}`} aria-hidden />
                Retry
              </Button>
            </div>
          )}
          {renderCurrentPage()}
        </main>
      </div>
    </div>
  );
};
