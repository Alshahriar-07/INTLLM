import React, { Suspense, useEffect, useState } from 'react';
import { NavigationTab } from '../../types';
import { useIntllm } from '../../hooks/use-intllm';
import { WifiOff, Loader2 } from 'lucide-react';
import { Button } from '../ui/Button';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { BootScreen } from './BootScreen';
import { DegradedModeBanner } from '../ui/DegradedModeBanner';
import { ChatWorkspace } from '../chat/ChatWorkspace';

// Heavy views are lazy-loaded so the startup bundle stays small (chat is the
// default landing view and is loaded eagerly).
const OverviewDashboard = React.lazy(() =>
  import('../overview/OverviewDashboard').then((m) => ({ default: m.OverviewDashboard }))
);
const ModelManager = React.lazy(() =>
  import('../models/ModelManager').then((m) => ({ default: m.ModelManager }))
);
const BrainDashboard = React.lazy(() =>
  import('../brain/BrainDashboard').then((m) => ({ default: m.BrainDashboard }))
);
const WebDashboard = React.lazy(() =>
  import('../web/WebDashboard').then((m) => ({ default: m.WebDashboard }))
);
const BrowserControlPanel = React.lazy(() =>
  import('../browser/BrowserControlPanel').then((m) => ({ default: m.BrowserControlPanel }))
);
const ToolGateway = React.lazy(() =>
  import('../tools/ToolGateway').then((m) => ({ default: m.ToolGateway }))
);
const ApiDashboard = React.lazy(() =>
  import('../api/ApiDashboard').then((m) => ({ default: m.ApiDashboard }))
);
const DocsDashboard = React.lazy(() =>
  import('../docs/DocsDashboard').then((m) => ({ default: m.DocsDashboard }))
);
const SystemDashboard = React.lazy(() =>
  import('../system/SystemDashboard').then((m) => ({ default: m.SystemDashboard }))
);
const BackgroundLearningWidget = React.lazy(() =>
  import('../learning/BackgroundLearningWidget').then((m) => ({
    default: m.BackgroundLearningWidget,
  }))
);
const SettingsWorkspace = React.lazy(() =>
  import('../settings/SettingsWorkspace').then((m) => ({ default: m.SettingsWorkspace }))
);

const ViewFallback: React.FC = () => (
  <div className="flex-1 flex items-center justify-center text-muted" aria-busy="true">
    <Loader2 className="w-5 h-5 animate-spin" aria-hidden />
  </div>
);

export const AppShell: React.FC = () => {
  const [booting, setBooting] = useState(true);
  const [activeTab, setActiveTab] = useState<NavigationTab>('chat');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [showLearningWidget, setShowLearningWidget] = useState(false);
  const intllm = useIntllm();

  // Wait for initial connection check before showing the UI
  useEffect(() => {
    if (!intllm.loading) {
      setBooting(false);
    }
  }, [intllm.loading]);

  // Failsafe: the boot screen must never become a permanent black screen. If
  // initialization has not completed within 30s, surface the real UI (which
  // shows the offline/degraded banners with Retry) instead.
  useEffect(() => {
    const failsafe = window.setTimeout(() => {
      setBooting(false);
      console.error('INTLLM boot exceeded 30s; showing the application with connection state.');
    }, 30000);
    return () => window.clearTimeout(failsafe);
  }, []);

  // Show boot screen while still loading initial state
  if (booting || intllm.loading) {
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
        <main className="flex-1 overflow-hidden bg-canvas flex flex-col min-h-0">      {/* Degraded mode banner — shows when backend is reachable but services are down */}
          {!intllm.loading && intllm.connected && intllm.status === 'degraded' && (
            <DegradedModeBanner services={intllm.services} onRefresh={() => intllm.refresh()} />
          )}

          {/* Backend Offline banner — shown when backend is unreachable */}
          {!intllm.loading && !intllm.connected && (
            <div
              role="alert"
              className="flex items-center justify-between gap-3 px-4 py-2 bg-error/10 border-b border-error/20 text-error text-xs font-mono"
            >
              <span className="flex items-center gap-2 min-w-0">
                <WifiOff className="w-3.5 h-3.5 shrink-0" aria-hidden />
                <span className="truncate">
                  INTLLM backend offline — {' '}
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

          <Suspense fallback={<ViewFallback />}>{renderCurrentPage()}</Suspense>
        </main>
      </div>
    </div>
  );
};
