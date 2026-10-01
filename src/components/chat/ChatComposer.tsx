import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowUp, Brain, Globe, Loader2, Square } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Button } from '../ui/Button';

export interface ChatComposerProps {
  isConnected?: boolean;
  isStreaming?: boolean;
  onSend: (text: string, options: { useWeb: boolean; useBrain: boolean }) => void;
  onStop: () => void;
}

const MIN_HEIGHT_PX = 44;
const MAX_HEIGHT_PX = 180;

export const ChatComposer: React.FC<ChatComposerProps> = ({
  isConnected = false,
  isStreaming = false,
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
    // Return focus to the composer after sending.
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
      <div className="max-w-3xl mx-auto w-full px-4 md:px-6 py-3">
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
              isConnected
                ? 'Message INTLLM…  (Enter to send, Shift+Enter for a new line)'
                : 'Runtime offline — start the INTLLM backend to send messages'
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
                    <Loader2 className="w-3.5 h-3.5" aria-hidden />
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
