import React, { createContext, useContext, useEffect, useState } from 'react';

export type Theme = 'dark' | 'light' | 'system';
export type ResolvedTheme = 'dark' | 'light';

interface ThemeProviderProps {
  children: React.ReactNode;
  defaultTheme?: Theme;
  storageKey?: string;
}

interface ThemeProviderState {
  theme: Theme;
  resolvedTheme: ResolvedTheme;
  setTheme: (theme: Theme) => void;
}

const initialState: ThemeProviderState = {
  theme: 'system',
  resolvedTheme: 'dark',
  setTheme: () => undefined,
};

const ThemeProviderContext = createContext<ThemeProviderState>(initialState);

const systemPrefersDark = () => window.matchMedia('(prefers-color-scheme: dark)').matches;

export function ThemeProvider({
  children,
  defaultTheme = 'system',
  storageKey = 'intllm-theme',
}: ThemeProviderProps) {
  const [theme, setThemeState] = useState<Theme>(() => {
    try {
      const stored = localStorage.getItem(storageKey) as Theme | null;
      if (stored === 'dark' || stored === 'light' || stored === 'system') return stored;
    } catch {
      /* storage unavailable */
    }
    return defaultTheme;
  });
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>(() =>
    theme === 'system' ? (systemPrefersDark() ? 'dark' : 'light') : theme
  );

  useEffect(() => {
    const root = window.document.documentElement;
    const apply = (next: ResolvedTheme) => {
      root.classList.remove('light', 'dark');
      root.classList.add(next);
      root.style.colorScheme = next;
      setResolvedTheme(next);
    };

    if (theme === 'system') {
      const media = window.matchMedia('(prefers-color-scheme: dark)');
      apply(media.matches ? 'dark' : 'light');
      const onChange = (e: MediaQueryListEvent) => apply(e.matches ? 'dark' : 'light');
      media.addEventListener('change', onChange);
      return () => media.removeEventListener('change', onChange);
    }
    apply(theme);
  }, [theme]);

  const setTheme = (next: Theme) => {
    try {
      localStorage.setItem(storageKey, next);
    } catch {
      /* storage unavailable */
    }
    setThemeState(next);
  };

  return <ThemeProviderContext.Provider value={{ theme, resolvedTheme, setTheme }}>{children}</ThemeProviderContext.Provider>;
}

export const useTheme = () => {
  const context = useContext(ThemeProviderContext);
  if (context === undefined) throw new Error('useTheme must be used within a ThemeProvider');
  return context;
};
