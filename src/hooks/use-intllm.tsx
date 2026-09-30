import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { Model } from '../types';
import {
  HealthSnapshot,
  isEndpointConfigured,
  probeHealth,
  POLLING_INTERVAL_MS
} from '../lib/api/client';
import { modelService } from '../lib/services/modelService';
import { ollamaService, OllamaStatus } from '../lib/services/ollamaService';

export interface IntllmState {
  endpointConfigured: boolean;
  connected: boolean;
  status: 'ok' | 'degraded' | 'offline';
  services: HealthSnapshot['services'];
  version?: string;
  models: Model[];
  modelsConnected: boolean;
  modelsError?: string;
  currentModelId: string;
  setCurrentModel: (modelId: string) => void;
  loading: boolean;
  refresh: () => Promise<void>;
  /** Real Ollama daemon snapshot from GET /api/ollama/status. */
  ollama: OllamaStatus | null;
  /** True while a start/stop/restart call is in flight. */
  ollamaTransitioning: boolean;
  startOllama: () => Promise<void>;
  stopOllama: () => Promise<void>;
  restartOllama: () => Promise<void>;
  refreshOllama: () => Promise<void>;
  /** Last Ollama control error (real backend reason). */
  ollamaError?: string;
}

const initialState: IntllmState = {
  endpointConfigured: false,
  connected: false,
  status: 'offline',
  services: {},
  models: [],
  modelsConnected: false,
  currentModelId: '',
  setCurrentModel: () => undefined,
  loading: true,
  refresh: async () => undefined,
  ollama: null,
  ollamaTransitioning: false,
  startOllama: async () => undefined,
  stopOllama: async () => undefined,
  restartOllama: async () => undefined,
  refreshOllama: async () => undefined
};

const IntllmContext = createContext<IntllmState>(initialState);

export const IntllmProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = useState<IntllmState>(initialState);
  const currentModelRef = useRef('');
  const pollingRef = useRef<number | null>(null);
  const inFlightRef = useRef(false);
  const transitioningRef = useRef(false);

  const refreshHealth = useCallback(async () => {
    if (inFlightRef.current) return;
    inFlightRef.current = true;
    try {
      const health = await probeHealth();

      let models: Model[] = [];
      let modelsConnected = false;
      let modelsError: string | undefined;

      if (health.connected) {
        const modelsResult = await modelService.getInstalledModels();
        models = modelsResult.models;
        modelsConnected = modelsResult.connected;
        modelsError = modelsResult.error;
      }

      // Pick a default model only from real installed models.
      let currentModelId = currentModelRef.current;
      if (!currentModelId || !models.some((m) => m.name === currentModelId)) {
        currentModelId =
          models.find((m) => m.isDefault)?.name ?? models.find((m) => m.installed)?.name ?? '';
      }

      setState((prev) => ({
        ...prev,
        endpointConfigured: isEndpointConfigured(),
        connected: health.connected,
        status: health.status,
        services: health.services,
        version: health.version,
        models,
        modelsConnected,
        modelsError,
        currentModelId,
        loading: false
      }));
    } finally {
      inFlightRef.current = false;
    }
  }, []);

  const refreshOllama = useCallback(async () => {
    const { status: ollama, error } = await ollamaService.getStatusOrError();
    setState((prev) => ({
      ...prev,
      ollama,
      ollamaError: error ?? (ollama?.status === 'error' || ollama?.status === 'unavailable' ? ollama?.reason ?? undefined : undefined)
    }));
  }, []);

  const runOllamaAction = useCallback(
    async (operation: 'start' | 'stop' | 'restart') => {
      if (transitioningRef.current) return;
      transitioningRef.current = true;
      setState((prev) => ({ ...prev, ollamaTransitioning: true, ollamaError: undefined }));
      try {
        // Optimistic transition state, then the real result from the backend.
        setState((prev) => ({
          ...prev,
          ollama: prev.ollama
            ? { ...prev.ollama, status: operation === 'stop' ? 'stopping' : 'starting' }
            : prev.ollama
        }));
        const result = await ollamaService[operation]();
        const { status: ollama } = await ollamaService.getStatusOrError();
        setState((prev) => ({
          ...prev,
          ollama,
          ollamaError: result?.error ?? undefined
        }));
      } catch {
        await refreshOllama();
      } finally {
        transitioningRef.current = false;
        setState((prev) => ({ ...prev, ollamaTransitioning: false }));
      }
    },
    [refreshOllama]
  );

  const startOllama = useCallback(() => runOllamaAction('start'), [runOllamaAction]);
  const stopOllama = useCallback(() => runOllamaAction('stop'), [runOllamaAction]);
  const restartOllama = useCallback(() => runOllamaAction('restart'), [runOllamaAction]);

  const setCurrentModel = useCallback((modelId: string) => {
    currentModelRef.current = modelId;
    setState((prev) => ({ ...prev, currentModelId: modelId }));
  }, []);

  useEffect(() => {
    refreshHealth();
    refreshOllama();

    const tick = () => {
      if (document.visibilityState === 'visible') {
        refreshHealth();
        refreshOllama();
      }
    };
    pollingRef.current = window.setInterval(tick, POLLING_INTERVAL_MS);

    const onVisibility = () => {
      if (document.visibilityState === 'visible') {
        // Refresh immediately when the tab becomes active again.
        refreshHealth();
        refreshOllama();
      }
    };
    document.addEventListener('visibilitychange', onVisibility);

    return () => {
      if (pollingRef.current !== null) window.clearInterval(pollingRef.current);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [refreshHealth, refreshOllama]);

  return (
    <IntllmContext.Provider
      value={{
        ...state,
        refresh: refreshHealth,
        setCurrentModel,
        startOllama,
        stopOllama,
        restartOllama,
        refreshOllama
      }}
    >
      {children}
    </IntllmContext.Provider>
  );
};

export const useIntllm = (): IntllmState => useContext(IntllmContext);
