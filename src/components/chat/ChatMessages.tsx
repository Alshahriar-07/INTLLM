import React, { useEffect, useRef } from 'react';
import { BrainCircuit, Loader2, User } from 'lucide-react';
import { Message } from '../../types';
import { ActivityRow } from './ActivityRow';
import { SourceCard } from './SourceCard';
import { Markdown } from './Markdown';
import { cn } from '../../lib/utils';

export interface ChatMessagesProps {
  messages: Message[];
  isConnected?: boolean;
  isStreaming?: boolean;
  /** Bumped when a new conversation is opened so scroll resets. */
  conversationKey?: string;
}

export const ChatMessages: React.FC<ChatMessagesProps> = ({
  messages,
  isConnected = false,
  isStreaming = false,
  conversationKey
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const pinnedRef = useRef(true);

  // Track whether the user is scrolled near the bottom (auto-follow behavior).
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const onScroll = () => {
      pinnedRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    };
    el.addEventListener('scroll', onScroll, { passive: true });
    return () => el.removeEventListener('scroll', onScroll);
  }, []);

  // Reset follow state when switching conversations, then jump to the bottom.
  useEffect(() => {
    pinnedRef.current = true;
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [conversationKey]);

  // Auto-scroll while streaming, only when the user hasn't scrolled up.
  useEffect(() => {
    if (pinnedRef.current) {
      bottomRef.current?.scrollIntoView({ block: 'end' });
    }
  }, [messages, isStreaming]);

  if (!messages || messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
        <div className="max-w-md space-y-3">
          <div className="mx-auto w-11 h-11 rounded-lg border border-border bg-surface flex items-center justify-center">
            <BrainCircuit className="w-5 h-5 text-accent" aria-hidden />
          </div>
          <h2 className="text-lg font-semibold text-primary">Local intelligence, ready</h2>
          <p className="text-sm text-secondary leading-relaxed">
            {isConnected
              ? 'Ask anything. Layered memory and live retrieval are applied automatically when useful.'
              : 'The INTLLM runtime is offline. Start the backend service to begin chatting.'}
          </p>
          <div
            className={cn(
              'inline-flex items-center gap-2 px-2.5 py-1 rounded-md border text-[11px] font-mono',
              isConnected
                ? 'bg-success/10 border-success/25 text-success'
                : 'bg-warning/10 border-warning/25 text-warning'
            )}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-current" aria-hidden />
            {isConnected ? 'Runtime ready' : 'Runtime standby'}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto">
      <div className="max-w-3xl mx-auto w-full px-4 md:px-6 py-6 space-y-5">
        {messages.map((msg) => {
          const isUser = msg.role === 'user';
          return (
            <article key={msg.id} className="group">
              {/* Message header: role + meta */}
              <div className="flex items-center gap-2 mb-1">
                <span
                  className={cn(
                    'w-5 h-5 rounded flex items-center justify-center shrink-0',
                    isUser ? 'bg-panel-hover text-secondary' : 'bg-accent/10 text-accent'
                  )}
                  aria-hidden
                >
                  {isUser ? <User className="w-3 h-3" /> : <BrainCircuit className="w-3 h-3" />}
                </span>
                <span className="text-xs font-medium text-primary">{isUser ? 'You' : 'INTLLM'}</span>
                {msg.model && <span className="text-[11px] font-mono text-muted truncate">{msg.model}</span>}
                {msg.tokensPerSec && (
                  <span className="text-[11px] font-mono text-muted">{msg.tokensPerSec} tok/s</span>
                )}
              </div>

              {/* Body */}
              <div
                className={cn(
                  'rounded-lg border px-3.5 py-2.5 text-sm leading-relaxed',
                  isUser
                    ? 'bg-panel border-border text-primary'
                    : 'bg-transparent border-transparent text-primary'
                )}
              >
                {isUser ? (
                  <p className="whitespace-pre-wrap break-words">{msg.content}</p>
                ) : msg.content ? (
                  <Markdown content={msg.content} />
                ) : (
                  <span className="inline-flex items-center gap-2 text-muted">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden />
                    {msg.isStreaming ? 'Thinking…' : ''}
                  </span>
                )}
                {msg.isStreaming && msg.content && (
                  <span className="stream-cursor" aria-hidden />
                )}
              </div>

              {/* Activity + sources (assistant only) */}
              {!isUser && msg.activities && msg.activities.length > 0 && (
                <ActivityRow
                  activities={msg.activities}
                  memoryCount={msg.memoryUsed ?? 0}
                  sourceCount={msg.sources?.length ?? 0}
                />
              )}
              {!isUser && msg.sources && msg.sources.length > 0 && <SourceCard sources={msg.sources} />}
            </article>
          );
        })}
        <div ref={bottomRef} aria-hidden />
      </div>
    </div>
  );
};
