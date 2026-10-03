import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from './Button';

interface ErrorFallbackProps {
  error: Error | null;
  onReset: () => void;
}

export const ErrorFallback: React.FC<ErrorFallbackProps> = ({ error, onReset }) => {
  return (
    <div className="flex items-center justify-center min-h-screen bg-canvas p-4">
      <div className="max-w-md w-full text-center space-y-4">
        <div className="flex justify-center">
          <div className="p-4 rounded-full bg-error/10">
            <AlertTriangle className="w-8 h-8 text-error" />
          </div>
        </div>
        
        <div className="space-y-2">
          <h2 className="text-lg font-semibold text-primary">Something went wrong</h2>
          <p className="text-sm text-secondary">
            The application encountered an unexpected error. This is not a normal state.
          </p>
          {error && (
            <div className="text-left p-3 bg-surface rounded border border-border text-xs font-mono text-error bg-error/5">
              <div className="font-semibold mb-1">Error details:</div>
              <div>{error.message}</div>
            </div>
          )}
        </div>

        <div className="flex gap-3 justify-center pt-2">
          <Button variant="primary" onClick={() => { onReset(); window.location.reload(); }}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Reload Application
          </Button>
        </div>

        <p className="text-xs text-muted">
          If this problem persists, check that the INTLLM backend is running and PostgreSQL is available.
        </p>
      </div>
    </div>
  );
};
