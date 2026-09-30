import React, { useCallback, useRef, useState } from 'react';
import { ActivityStep, Message, WebSource } from '../../types';
import { ChatMessages } from './ChatMessages';
import { ChatComposer } from './ChatComposer';
import { AlertCircle, Cpu } from 'lucide-react';
import { chatService } from '../../lib/services/chatService';

export interface ChatWorkspaceProps {
  currentModelId: string;
  onModelSelect: (modelId: string) => void;
  isConnected?: boolean;
}

const uid = () => Math.random().toString(36).slice(2, 11);

function activityFromEvent(type: string, data: any): ActivityStep | null {
  const base = { id: uid(), latencyMs: undefined as number | undefined };
  switch (type) {
    case 'chat.thinking':
      return { ...base, type: 'thinking', label: 'Reasoning', status: 'running' };
    case 'brain.lookup':
      return {
        ...base,
        type: 'flash_brain',
        label: 'Brain lookup',
        status: 'running',
        detail: `Query: ${String(data?.query ?? '').slice(0, 80)}`
      };
    case 'memory.retrieved':
      return {
        ...base,
        type: 'flash_brain',
        label: `Memory retrieved (${data?.source ?? 'memory'})`,
        status: 'completed',
        detail: `${data?.count ?? 0} memories · confidence ${Math.round(data?.confidence ?? 0)}%`
      };
    case 'web.search.started':
      return { ...base, type: 'web_search', label: 'Live web retrieval', status: 'running' };
    case 'web.source.received':
      return {
        ...base,
        type: 'web_search',
        label: 'Web source received',
        status: 'completed',
        detail: data?.domain ?? data?.url
      };
    case 'web.search.failed':
      return {
        ...base,
        type: 'web_search',
        label: 'Web retrieval failed',
        status: 'failed',
        detail: data?.message
      };
    default:
      return null;
  }
}

export const ChatWorkspace: React.FC<ChatWorkspaceProps> = ({
  currentModelId,
  onModelSelect: _onModelSelect,
  isConnected = false
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<(() => void) | null>(null);
  const conversationIdRef = useRef<string | null>(null);
  const assistantIdRef = useRef<string | null>(null);

  const updateAssistant = useCallback((updater: (msg: Message) => Message) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === assistantIdRef.current ? updater(m) : m))
    );
  }, []);

  const handleSend = useCallback(
    (text: string, options: { useWeb: boolean; useBrain: boolean }) => {
      if (!isConnected) return;
      setError(null);

      const userMessage: Message = {
        id: uid(),
        role: 'user',
        content: text,
        timestamp: new Date().toISOString()
      };
      const assistantId = uid();
      assistantIdRef.current = assistantId;
      const assistantMessage: Message = {
        id: assistantId,
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
        model: currentModelId,
        activities: [],
        sources: [],
        memoryUsed: 0,
        isStreaming: true
      };

      const history = [...messages, userMessage].map((m) => ({ role: m.role, content: m.content }));
      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setIsStreaming(true);

      abortRef.current = chatService.stream(
        {
          messages: history,
          model: currentModelId || undefined,
          conversation_id: conversationIdRef.current,
          use_brain: options.useBrain,
          use_web: options.useWeb
        },
        {
          onDelta: (content) =>
            updateAssistant((m) => ({ ...m, content: m.content + content })),
          onActivity: (type, data) => {
            const step = activityFromEvent(type, data);
            if (!step) return;
            updateAssistant((m) => {
              const activities = [...(m.activities ?? [])];
              const idx = activities.findIndex(
                (a) => a.type === step.type && a.status === 'running'
              );
              if (idx >= 0 && step.status !== 'running') activities[idx] = step;
              else activities.push(step);
              return { ...m, activities };
            });
          },
          onCompleted: (data) => {
            const sources: WebSource[] = data?.sources ?? [];
            updateAssistant((m) => ({
              ...m,
              content: m.content,
              isStreaming: false,
              sources,
              memoryUsed: data?.memory_used ?? 0,
              activities: m.activities
            }));
            if (data?.conversation_id) conversationIdRef.current = data.conversation_id;
            setIsStreaming(false);
            abortRef.current = null;
          },
          onError: (message) => {
            setError(message);
            updateAssistant((m) => ({ ...m, isStreaming: false }));
            setIsStreaming(false);
            abortRef.current = null;
          }
        }
      );
    },
    [currentModelId, isConnected, messages, updateAssistant]
  );

  const handleStop = useCallback(() => {
    abortRef.current?.();
    abortRef.current = null;
    setIsStreaming(false);
    updateAssistant((m) => ({ ...m, isStreaming: false }));
  }, [updateAssistant]);

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)] bg-slate-50 dark:bg-[#090D11]">
      {/* Top Context Bar */}
      <div className="h-10 border-b border-slate-200 dark:border-[#21262D] px-4 flex items-center justify-between bg-white dark:bg-[#0D1117] text-xs font-mono text-slate-500 select-none">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5" />
            {isConnected ? currentModelId || 'No model selected' : 'No model loaded'}
          </span>
          {messages.length > 0 && <span>{messages.length} messages</span>}
        </div>

        <div className="flex items-center gap-2 text-[11px]">
          {error ? (
            <span className="flex items-center gap-1.5 text-rose-500">
              <AlertCircle className="w-3.5 h-3.5" />
              {error}
            </span>
          ) : (
            <span className={isStreaming ? 'text-cyan-500' : 'text-slate-500'}>
              {isStreaming
                ? 'Streaming…'
                : isConnected
                  ? 'Runtime connected'
                  : 'Connect INTLLM runtime to start chatting'}
            </span>
          )}
        </div>
      </div>

      {/* Messages Stream */}
      <ChatMessages messages={messages} isConnected={isConnected} />

      {/* Composer */}
      <ChatComposer isConnected={isConnected} isStreaming={isStreaming} onSend={handleSend} onStop={handleStop} />
    </div>
  );
};
