import React from 'react';
import { ThemeProvider } from './hooks/use-theme';
import { IntllmProvider } from './hooks/use-intllm';
import { AppShell } from './components/layout/AppShell';

export const App: React.FC = () => {
  return (
    <ThemeProvider defaultTheme="dark" storageKey="intllm-theme">
      <IntllmProvider>
        <AppShell />
      </IntllmProvider>
    </ThemeProvider>
  );
};

export default App;
