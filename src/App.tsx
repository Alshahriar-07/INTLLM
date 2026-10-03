import React, { ErrorInfo } from 'react';
import { ThemeProvider } from './hooks/use-theme';
import { IntllmProvider } from './hooks/use-intllm';
import { AppShell } from './components/layout/AppShell';
import { ErrorFallback } from './components/ui/ErrorFallback';

export const App: React.FC = () => {
  return (
    <ThemeProvider defaultTheme="dark" storageKey="intllm-theme">
      <IntllmProvider>
        <ErrorBoundary>
          <AppShell />
        </ErrorBoundary>
      </IntllmProvider>
    </ThemeProvider>
  );
};

interface ErrorBoundaryProps {
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('INTLLM caught an error:', error, errorInfo);
  }

  render(): React.ReactNode {
    if (this.state.hasError) {
      return (
        <ErrorFallback
          error={this.state.error}
          onReset={() => this.setState({ hasError: false, error: null })}
        />
      );
    }
    return this.props.children;
  }
}

export default App;
