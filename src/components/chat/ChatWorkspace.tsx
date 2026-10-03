import React, { useCallback, useEffect, useRef, useState } from 'react';
import { AlertCircle, Loader2, RefreshCw, ShieldAlert } from 'lucide-react';
import {
  ActivityStep,
  AgentApprovalRequest,
  AgentPermissionMode,
  AgentWorkspace,
  ChatMode,
  Message,
  WebSource,
} from '../../types';
import { ChatMessages } from './ChatMessages';
import { ChatComposer } from './ChatComposer';
import { ConversationList } from './ConversationList';
import { ModelSelector } from '../ui/ModelSelector';
import { Button } from '../ui/Button';
import { Modal } from '../ui/Modal';
import { Input } from '../ui/Input';
import { chatService, ConversationSummary } from '../../lib/services/chatService';
import { agentService } from '../../lib/services/agentService';
import { useIntllm } from '../../hooks/use-intllm';
import { cn } from '../../lib/utils';

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
    case 'agent.step':
      return {
        ...base,
        type: 'thinking',
        label: `Agent step ${data?.step ?? ''}/${data?.max ?? ''}`.trim(),
        status: 'running',
      };
    case 'agent.tool.started':
      return {
        ...base,
        type: 'tool',
        label: data?.summary ?? data?.tool ?? 'Tool',
        status: 'running',
        detail: data?.target ?? undefined,
      };
    case 'agent.tool.completed': {
      return {
        ...base,
        type: 'tool',
        label: data?.summary ?? data?.tool ?? 'Tool',
        status: data?.status === 'completed' ? 'completed' : 'failed',
        latencyMs: typeof data?.durationMs === 'number' ? Math.round(data.durationMs) : undefined,
        detail: data?.detail ?? data?.target ?? undefined,
      };
    }
    case 'agent.permission.resolved':
      return data?.allowed
        ? { ...base, type: 'tool', label: 'Permission granted', status: 'running' }
        : { ...base, type: 'tool', label: 'Permission denied', status: 'failed' };
    default:
      return null;
  }
}

export interface ChatWorkspaceProps {
  currentModelId: string;
  onModelSelect: (modelId: string) => void;
  isConnected?: boolean;
}

export const ChatWorkspace: React.FC<ChatWorkspaceProps> = ({
  currentModelId,
  onModelSelect,
  isConnected = false
}) => {
  const intllm = useIntllm();

  // --- conversation state -------------------------------------------------
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [conversationsLoading, setConversationsLoading] = useState(true);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [query, setQuery] = useState('');
  const [listOpen, setListOpen] = useState(true);

  // --- Agent mode / workspace --------------------------------------------
  const [mode, setMode] = useState<ChatMode>('chat');
  const [permissionMode, setPermissionMode] = useState<AgentPermissionMode>('ask');
  const [pendingApproval, setPendingApproval] = useState<AgentApprovalRequest | null>(null);
  const [workspace, setWorkspace] = useState<AgentWorkspace | null>(null);
  const [workspaceBusy, setWorkspaceBusy] = useState(false);
  const [showWorkspaceModal, setShowWorkspaceModal] = useState(false);
  const [workspaceInput, setWorkspaceInput] = useState('');
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);

  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<(() => void) | null>(null);
  const assistantIdRef = useRef<string | null>(null);

  const refreshConversations = useCallback(async () => {
    setConversationsLoading(true);
    const list = await chatService.listConversations();
    setConversations(list);
    setConversationsLoading(false);
  }, []);

  // Load persisted history on mount and whenever the backend reconnects.
  useEffect(() => {
    if (intllm.loading) return;
    if (intllm.connected) {
      refreshConversations();
    } else {
      setConversationsLoading(false);
    }
  }, [intllm.connected, intllm.loading, refreshConversations]);

  // Load the Agent workspace and permission mode from the backend (never
  // frontend-only).
  useEffect(() => {
    if (intllm.connected) {
      agentService.getStatus().then((status) => {
        setWorkspace(status);
        if (status?.permissionMode) setPermissionMode(status.permissionMode);
      });
    }
  }, [intllm.connected]);

  const changePermissionMode = useCallback(async (next: AgentPermissionMode) => {
    setPermissionMode(next);
    const applied = await agentService.setPermissionMode(next);
    if (applied) setPermissionMode(applied);
  }, []);

  const decideApproval = useCallback(
    async (decision: 'allow' | 'deny') => {
      const request = pendingApproval;
      setPendingApproval(null);
      if (request) await agentService.decidePermission(request.request_id, decision);
    },
    [pendingApproval]
  );

  const openWorkspaceSelector = useCallback(async () => {
    setWorkspaceError(null);
    setWorkspaceBusy(true);
    try {
      const picked = await agentService.pickWorkspace();
      if (picked?.configured) {
        setWorkspace(picked);
        return;
      }
    } finally {
      setWorkspaceBusy(false);
    }
    setWorkspaceInput(workspace?.path ?? '');
    setShowWorkspaceModal(true);
  }, [workspace?.path]);

  const applyWorkspacePath = useCallback(async () => {
    const path = workspaceInput.trim();
    if (!path) return;
    setWorkspaceBusy(true);
    setWorkspaceError(null);
    const updated = await agentService.setWorkspace(path);
    setWorkspaceBusy(false);
    if (updated?.configured) {
      setWorkspace(updated);
      setShowWorkspaceModal(false);
    } else {
      setWorkspaceError(
        'Could not use that folder. Check the path exists and the backend can read it.'
      );
    }
  }, [workspaceInput]);

  const clearWorkspace = useCallback(async () => {
    setWorkspaceBusy(true);
    const updated = await agentService.clearWorkspace();
    setWorkspace(updated);
    setWorkspaceBusy(false);
  }, []);

  const openConversation = useCallback(async (id: string) => {
    abortRef.current?.();
    abortRef.current = null;
    setIsStreaming(false);
    setError(null);
    setActiveId(id);
    setLoadingMessages(true);
    const history = await chatService.getConversationMessages(id);
    setMessages(
      history.map((m) => ({
        ...m,
        isStreaming: false
      }))
    );
    setLoadingMessages(false);
  }, []);

  const startNewChat = useCallback(() => {
    abortRef.current?.();
    abortRef.current = null;
    setIsStreaming(false);
    setError(null);
    setActiveId(null);
    setMessages([]);
  }, []);

  const handleRename = useCallback(async (id: string, title: string) => {
    const ok = await chatService.renameConversation(id, title);
    if (ok) {
      setConversations((prev) => prev.map((c) => (c.id === id ? { ...c, title } : c)));
    }
  }, []);

  const handleDelete = useCallback(
    async (id: string) => {
      const ok = await chatService.deleteConversation(id);
      if (ok) {
        setConversations((prev) => prev.filter((c) => c.id !== id));
        if (activeId === id) {
          setActiveId(null);
          setMessages([]);
        }
      }
    },
    [activeId]
  );

  // --- streaming ----------------------------------------------------------
  const updateAssistant = useCallback((updater: (msg: Message) => Message) => {
    setMessages((prev) => prev.map((m) => (m.id === assistantIdRef.current ? updater(m) : m)));
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
          conversation_id: activeId,
          use_brain: options.useBrain,
          use_web: options.useWeb,
          mode,
          workspace: mode === 'agent' ? workspace?.path ?? null : null
        },
        {
          onDelta: (content) => updateAssistant((m) => ({ ...m, content: m.content + content })),
          onActivity: (type, data) => {
            if (type === 'agent.permission.required') {
              setPendingApproval({
                request_id: data?.request_id,
                tool: data?.tool,
                target: data?.target ?? null,
                summary: data?.summary ?? 'Agent requests permission',
                command: data?.command ?? null,
                cwd: data?.cwd ?? null,
                risk: data?.risk ?? 'Low'
              });
              return;
            }
            const step = activityFromEvent(type, data);
            if (!step) return;
            updateAssistant((m) => {
              const activities = [...(m.activities ?? [])];
              const idx = activities.findIndex((a) => a.type === step.type && a.status === 'running');
              if (idx >= 0 && step.status !== 'running') activities[idx] = step;
              else activities.push(step);
              return { ...m, activities };
            });
          },
          onCompleted: (data) => {
            setPendingApproval(null);
            const sources: WebSource[] = data?.sources ?? [];
            updateAssistant((m) => ({
              ...m,
              content: m.content,
              isStreaming: false,
              sources,
              memoryUsed: data?.memory_used ?? 0
            }));
            const completedId: string | null = data?.conversation_id ?? null;
            if (completedId && !activeId) {
              // First exchange in a new chat: adopt the server-created id and
              // refresh the list so the new conversation appears immediately.
              setActiveId(completedId);
              refreshConversations();
            } else if (completedId) {
              // Keep the sidebar ordering fresh after each exchange.
              refreshConversations();
            }
            setIsStreaming(false);
            abortRef.current = null;
          },
          onError: (message) => {
            setPendingApproval(null);
            setError(message);
            updateAssistant((m) => ({ ...m, isStreaming: false }));
            setIsStreaming(false);
            abortRef.current = null;
          }
        }
      );
    },
    [activeId, currentModelId, isConnected, messages, mode, refreshConversations, updateAssistant, workspace?.path]
  );

  const handleStop = useCallback(() => {
    abortRef.current?.();
    abortRef.current = null;
    setPendingApproval(null);
    setIsStreaming(false);
    updateAssistant((m) => ({ ...m, isStreaming: false }));
  }, [updateAssistant]);

  // Cleanup in-flight streams when the workspace unmounts.
  useEffect(() => {
    return () => {
      abortRef.current?.();
    };
  }, []);

  const activeConversation = conversations.find((c) => c.id === activeId);

  return (
    <div className="flex flex-1 min-h-0">
      {/* Conversation History Sidebar */}
      <div
        className={cn(
          'h-full shrink-0 border-r border-border bg-panel flex flex-col transition-[width] duration-150 overflow-hidden',
          listOpen ? 'w-64' : 'w-0 border-r-0'
        )}
        aria-hidden={!listOpen}
      >
        {listOpen && (
          <ConversationList
            conversations={conversations}
            activeId={activeId}
            loading={conversationsLoading}
            query={query}
            onQueryChange={setQuery}
            onSelect={openConversation}
            onNew={startNewChat}
            onRename={handleRename}
            onDelete={handleDelete}
          />
        )}
      </div>

      {/* Chat column */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Chat header */}
        <div className="h-11 shrink-0 border-b border-border bg-canvas px-3 flex items-center justify-between gap-2 select-none">
          <div className="flex items-center gap-1.5 min-w-0">
            <button
              type="button"
              onClick={() => setListOpen((v) => !v)}
              aria-label={listOpen ? 'Hide conversation history' : 'Show conversation history'}
              aria-expanded={listOpen}
              title={listOpen ? 'Hide history' : 'Show history'}
              className="p-1.5 rounded-md text-muted hover:text-primary hover:bg-panel-hover transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              <svg viewBox="0 0 16 16" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden>
                {listOpen ? (
                  <>
                    <path d="M6 3v10" strokeLinecap="round" />
                    <path d="M3 5.5 5.5 8 3 10.5" strokeLinecap="round" strokeLinejoin="round" />
                    <rect x="9" y="3" width="4" height="10" rx="1" />
                  </>
                ) : (
                  <>
                    <path d="M6 3v10" strokeLinecap="round" />
                    <path d="M5.5 5.5 3 8l2.5 2.5" strokeLinecap="round" strokeLinejoin="round" />
                    <rect x="9" y="3" width="4" height="10" rx="1" />
                  </>
                )}
              </svg>
            </button>
            <h2 className="text-sm font-medium text-primary truncate max-w-[220px] sm:max-w-xs">
              {activeConversation ? activeConversation.title : 'New chat'}
            </h2>
            {loadingMessages && <Loader2 className="w-3.5 h-3.5 text-muted animate-spin" aria-hidden />}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {error ? (
              <span className="hidden md:flex items-center gap-1.5 text-xs text-error max-w-[280px] truncate" title={error}>
                <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                {error}
              </span>
            ) : isStreaming ? (
              <span className="hidden md:flex items-center gap-1.5 text-xs text-accent">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Streaming…
              </span>
            ) : null}

            <ModelSelector
              currentModelId={currentModelId}
              onModelSelect={onModelSelect}
              models={intllm.models}
              connected={isConnected}
            />
            <Button
              variant="ghost"
              size="icon"
              onClick={refreshConversations}
              title="Refresh conversation list"
              aria-label="Refresh conversation list"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>

        {/* Messages */}
        {loadingMessages ? (
          <div className="flex-1 flex items-center justify-center gap-2 text-xs text-muted font-mono">
            <Loader2 className="w-4 h-4 animate-spin" aria-hidden />
            Loading conversation…
          </div>
        ) : (
          <ChatMessages
            messages={messages}
            isConnected={isConnected}
            isStreaming={isStreaming}
            conversationKey={activeId ?? 'new'}
          />
        )}

        {/* Agent approval prompt (ASK ME mode) */}
        {mode === 'agent' && pendingApproval && (
          <div className="shrink-0 border-t border-warning/30 bg-warning/[0.06]">
            <div className="max-w-3xl mx-auto w-full px-4 md:px-6 py-3 space-y-2">
              <div className="flex items-center gap-2 text-xs font-mono text-warning">
                <ShieldAlert className="w-4 h-4" aria-hidden />
                Agent wants to {pendingApproval.summary}
              </div>
              {pendingApproval.command && (
                <div className="text-[11px] font-mono text-primary bg-canvas border border-border rounded p-2 space-y-1">
                  <div className="text-muted">
                    Working directory: {pendingApproval.cwd || workspace?.path || '(workspace)'}
                  </div>
                  <code className="block break-all">{pendingApproval.command}</code>
                </div>
              )}
              <div className="flex items-center gap-2">
                <Button variant="primary" size="sm" onClick={() => decideApproval('allow')}>
                  Allow
                </Button>
                <Button variant="danger" size="sm" onClick={() => decideApproval('deny')}>
                  Deny
                </Button>
                <span className="text-[10px] font-mono text-muted">risk {pendingApproval.risk}</span>
              </div>
            </div>
          </div>
        )}

        {/* Composer */}
        <ChatComposer
          isConnected={isConnected}
          isStreaming={isStreaming}
          mode={mode}
          onModeChange={setMode}
          workspace={workspace}
          onSelectWorkspace={openWorkspaceSelector}
          onClearWorkspace={clearWorkspace}
          workspaceBusy={workspaceBusy}
          permissionMode={permissionMode}
          onPermissionModeChange={changePermissionMode}
          onSend={handleSend}
          onStop={handleStop}
        />
      </div>

      {/* Workspace selection fallback (when the native folder chooser is unavailable) */}
      <Modal
        isOpen={showWorkspaceModal}
        onClose={() => setShowWorkspaceModal(false)}
        title="Select Agent Workspace"
        description="Enter the absolute path of the folder the Agent may work in."
        footer={
          <>
            <Button variant="ghost" onClick={() => setShowWorkspaceModal(false)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={applyWorkspacePath} disabled={!workspaceInput.trim()}>
              Use Folder
            </Button>
          </>
        }
      >
        <div className="space-y-2">
          <Input
            value={workspaceInput}
            onChange={(e) => setWorkspaceInput(e.target.value)}
            placeholder="e.g. C:\\Projects\\my-app"
            className="font-mono text-sm"
          />
          {workspaceError && (
            <p className="text-[11px] font-mono text-error">{workspaceError}</p>
          )}
          <p className="text-[11px] text-muted font-sans">
            The Agent is sandboxed to this folder. It cannot read or modify paths outside it,
            and destructive operations require your approval.
          </p>
        </div>
      </Modal>
    </div>
  );
};
