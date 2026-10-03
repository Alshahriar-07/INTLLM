import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowUp, Brain, Globe, Loader2, Square, FolderOpen, X, MessageSquare, Terminal } from 'lucide-react';
import { cn } from '../../lib/utils';
import { AgentPermissionMode, AgentWorkspace, ChatMode } from '../../types';
import { Button } from '../ui/Button';

export interface ChatComposerProps {
  isConnected?: boolean;
  isStreaming?: boolean;
  mode?: ChatMode;
  onModeChange?: (mode: ChatMode) => void;
  workspace?: AgentWorkspace | null;
  onSelectWorkspace?: () => void;
  onClearWorkspace?: () => void;
  workspaceBusy?: boolean;
  permissionMode?: AgentPermissionMode;
  onPermissionModeChange?: (mode: AgentPermissionMode) => void;
  onSend: (text: string, options: { useWeb: boolean; useBrain: boolean }) => void;
  onStop: () => void;
}

const MIN_HEIGHT_PX = 44;
const MAX_HEIGHT_PX = 180;

export const ChatComposer: React.FC<ChatComposerProps> = ({
  isConnected = false,
  isStreaming = false,
  mode = 'chat',
  onModeChange,
  workspace = null,
  onSelectWorkspace,
  onClearWorkspace,
  workspaceBusy = false,
  permissionMode = 'ask',
  onPermissionModeChange,
  onSend,
  onStop
}) => {
  const [input, setInput] = useState('');
  const [useWeb, setUseWeb] = useState(false);
  const [useBrain, setUseBrain] = useState(true);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-grow the textarea with content (up to MAX_HEIGHT_PX, then scroll).
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(MAX_HEIGHT_PX, Math.max(MIN_HEIGHT_PX, el.scrollHeight))}px`;
  }, [input]);

  const submit = useCallback(() => {
    const text = input.trim();
    if (!text || !isConnected || isStreaming) return;
    onSend(text, { useWeb, useBrain });
    setInput('');
    requestAnimationFrame(() => textareaRef.current?.focus());
  }, [input, isConnected, isStreaming, onSend, useBrain, useWeb]);

  const onKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit();
    }
  };

  const disabled = !isConnected || isStreaming;

  return (
    <div className="shrink-0 bg-canvas border-t border-border">
      <div className="max-w-3xl mx-auto w-full px-4 md:px-6 py-3 space-y-2">
        {/* Mode control */}
        <div className="flex items-center justify-between gap-2">
          <div
            role="tablist"
            aria-label="Chat mode"
            className="inline-flex items-center rounded-md border border-border bg-surface p-0.5"
          >
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'chat'}
              onClick={() => onModeChange?.('chat')}
              className={cn(
                'flex items-center gap-1.5 h-6 px-2.5 rounded text-xs font-mono transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
                mode === 'chat' ? 'bg-panel-hover text-primary' : 'text-muted hover:text-primary'
              )}
            >
              <MessageSquare className="w-3.5 h-3.5" aria-hidden />
              Chat
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'agent'}
              onClick={() => onModeChange?.('agent')}
              className={cn(
                'flex items-center gap-1.5 h-6 px-2.5 rounded text-xs font-mono transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
                mode === 'agent' ? 'bg-accent/15 text-accent' : 'text-muted hover:text-primary'
              )}
            >
              <Terminal className="w-3.5 h-3.5" aria-hidden />
              Agent
            </button>
          </div>

          {mode === 'agent' && (
            <span className="text-[10px] font-mono text-muted hidden sm:inline">
              Coding mode · workspace-scoped, approval-gated
            </span>
          )}
        </div>

        {/* Agent workspace control */}
        {mode === 'agent' && (
          <div className="flex flex-wrap items-center gap-2 rounded-md border border-border bg-surface px-2.5 py-1.5">
            <span className="text-[11px] font-mono text-muted flex items-center gap-1.5">
              <FolderOpen className="w-3.5 h-3.5" aria-hidden />
              Workspace
            </span>
            {workspace?.configured && workspace.path ? (
              <>
                <code
                  className="flex-1 min-w-0 truncate text-[11px] font-mono text-primary"
                  title={workspace.path}
                >
                  {workspace.path}
                </code>
                <span
                  className={cn(
                    'text-[10px] font-mono px-1.5 py-0.5 rounded border',
                    workspace.exists && workspace.writable
                      ? 'text-success bg-success/10 border-success/25'
                      : workspace.exists
                        ? 'text-warning bg-warning/10 border-warning/25'
                        : 'text-error bg-error/10 border-error/25'
                  )}
                  title={
                    workspace.exists
                      ? workspace.writable
                        ? 'Workspace ready'
                        : 'Workspace is not writable'
                      : 'Workspace folder no longer exists'
                  }
                >
                  {workspace.exists ? (workspace.writable ? 'ready' : 'read-only') : 'missing'}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onSelectWorkspace}
                  disabled={workspaceBusy}
                >
                  {workspaceBusy ? <Loader2 className="w-3 h-3 animate-spin" /> : null}
                  Change
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onClearWorkspace}
                  disabled={workspaceBusy}
                  aria-label="Clear Agent workspace"
                >
                  <X className="w-3 h-3" />
                  Clear
                </Button>
              </>
            ) : (
              <>
                <span className="flex-1 text-[11px] font-mono text-muted">
                  No folder selected — the Agent cannot touch files until a workspace is set.
                </span>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={onSelectWorkspace}
                  disabled={workspaceBusy}
                >
                  {workspaceBusy ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <FolderOpen className="w-3 h-3" />
                  )}
                  Select Folder
                </Button>
              </>
            )}
          </div>
        )}

        {/* Agent permission mode (Allow / Ask Me) */}
        {mode === 'agent' && (
          <div className="flex flex-wrap items-center gap-2 rounded-md border border-border bg-surface px-2.5 py-1.5">
            <span className="text-[11px] font-mono text-muted">Permission</span>
            <div
              role="tablist"
              aria-label="Agent permission mode"
              className="inline-flex items-center rounded-md border border-border bg-canvas p-0.5"
            >
              {(['allow', 'ask'] as const).map((value) => (
                <button
                  key={value}
                  type="button"
                  role="tab"
                  aria-selected={permissionMode === value}
                  onClick={() => onPermissionModeChange?.(value)}
                  className={cn(
                    'h-6 px-2.5 rounded text-[11px] font-mono transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
                    permissionMode === value
                      ? value === 'allow'
                        ? 'bg-warning/15 text-warning'
                        : 'bg-accent/15 text-accent'
                      : 'text-muted hover:text-primary'
                  )}
                  title={
                    value === 'allow'
                      ? 'Allow: the Agent performs workspace actions automatically'
                      : 'Ask Me: the Agent asks before changing files or running commands'
                  }
                >
                  {value === 'allow' ? 'Allow' : 'Ask Me'}
                </button>
              ))}
            </div>
            <span className="text-[10px] font-mono text-muted hidden sm:inline">
              {permissionMode === 'allow'
                ? 'Workspace actions run automatically'
                : 'Approval required for file/terminal changes'}
            </span>
          </div>
        )}

        {/* Input */}
        <div
          className={cn(
            'bg-surface border border-border rounded-lg transition-colors focus-within:border-accent/50 focus-within:ring-2 focus-within:ring-ring/30',
            disabled && 'opacity-70'
          )}
        >
          <label className="sr-only" htmlFor="chat-input">
            Message INTLLM
          </label>
          <textarea
            id="chat-input"
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={
              !isConnected
                ? 'Runtime offline — start the INTLLM backend to send messages'
                : mode === 'agent'
                  ? 'Describe a coding task for the Agent…'
                  : 'Message INTLLM…  (Enter to send, Shift+Enter for a new line)'
            }
            rows={1}
            style={{ height: MIN_HEIGHT_PX }}
            className="block w-full bg-transparent text-primary placeholder:text-muted/80 text-sm focus:outline-none resize-none font-sans px-3.5 pt-2.5 pb-1 leading-relaxed"
            disabled={disabled}
          />

          <div className="flex flex-wrap items-center justify-between gap-2 px-2.5 pb-2.5 pt-1">
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                disabled={!isConnected || isStreaming}
                onClick={() => setUseWeb(!useWeb)}
                aria-pressed={useWeb}
                title="Retrieve live web sources for this message"
                className={cn(
                  'flex items-center gap-1.5 h-7 px-2 rounded-md text-xs font-mono transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:opacity-50',
                  useWeb
                    ? 'bg-success/10 text-success border border-success/25'
                    : 'text-muted border border-transparent hover:bg-panel-hover hover:text-primary'
                )}
              >
                <Globe className="w-3.5 h-3.5" aria-hidden />
                <span>Web {useWeb ? 'on' : 'off'}</span>
              </button>

              <button
                type="button"
                disabled={!isConnected || isStreaming}
                onClick={() => setUseBrain(!useBrain)}
                aria-pressed={useBrain}
                title="Use layered memory (L0/L1/L2) for this message"
                className={cn(
                  'flex items-center gap-1.5 h-7 px-2 rounded-md text-xs font-mono transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:opacity-50',
                  useBrain
                    ? 'bg-accent/10 text-accent border border-accent/30'
                    : 'text-muted border border-transparent hover:bg-panel-hover hover:text-primary'
                )}
              >
                <Brain className="w-3.5 h-3.5" aria-hidden />
                <span>Brain {useBrain ? 'on' : 'off'}</span>
              </button>
            </div>

            <div className="flex items-center gap-2">
              {isStreaming ? (
                <Button variant="danger" size="sm" onClick={onStop} aria-label="Stop generating">
                  <Square className="w-3.5 h-3.5" aria-hidden />
                  Stop
                </Button>
              ) : (
                <Button
                  variant="primary"
                  size="sm"
                  onClick={submit}
                  disabled={disabled || !input.trim()}
                  aria-label="Send message"
                  title={isConnected ? 'Send (Enter)' : 'Runtime offline'}
                >
                  {isConnected ? (
                    <ArrowUp className="w-3.5 h-3.5" aria-hidden />
                  ) : (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden />
                  )}
                  Send
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
