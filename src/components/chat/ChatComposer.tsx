import React, { useState } from 'react';
import { Send, Globe, Brain, WifiOff, Square } from 'lucide-react';
import { Button } from '../ui/Button';

export interface ChatComposerProps {
  isConnected?: boolean;
  isStreaming?: boolean;
  onSend: (text: string, options: { useWeb: boolean; useBrain: boolean }) => void;
  onStop: () => void;
}

export const ChatComposer: React.FC<ChatComposerProps> = ({
  isConnected = false,
  isStreaming = false,
  onSend,
  onStop
}) => {
  const [input, setInput] = useState('');
  const [useWeb, setUseWeb] = useState(false);
  const [useBrain, setUseBrain] = useState(true);

  const submit = () => {
    const text = input.trim();
    if (!text || !isConnected || isStreaming) return;
    onSend(text, { useWeb, useBrain });
    setInput('');
  };

  const onKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <div className="p-4 bg-slate-100 dark:bg-[#0A0D12] border-t border-slate-200 dark:border-[#21262D]">
      <div className="max-w-4xl mx-auto space-y-2">
        <div className="relative bg-white dark:bg-[#0D1117] border border-slate-300 dark:border-[#30363D] rounded-xl p-3 shadow-xl">
          <label className="sr-only" htmlFor="chat-input">
            Message INTLLM
          </label>
          <textarea
            id="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={
              isConnected
                ? 'Ask INTLLM anything… (Shift+Enter for new line)'
                : 'Runtime disconnected. Connect INTLLM service to send messages…'
            }
            rows={2}
            className="w-full bg-transparent text-slate-900 dark:text-slate-100 placeholder:text-slate-500 text-sm focus:outline-none resize-none font-sans"
            disabled={!isConnected || isStreaming}
          />

          <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-200 dark:border-[#1C2128]">
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={!isConnected || isStreaming}
                onClick={() => setUseWeb(!useWeb)}
                aria-pressed={useWeb}
                title="Retrieve live web sources for this message"
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono transition-all disabled:opacity-50 ${
                  useWeb
                    ? 'bg-emerald-950/60 text-emerald-500 dark:text-emerald-400 border border-emerald-800/40'
                    : 'text-slate-500 hover:bg-slate-200 dark:hover:bg-[#161B22]'
                }`}
              >
                <Globe className="w-3.5 h-3.5" />
                <span>Web {useWeb ? 'ON' : 'OFF'}</span>
              </button>

              <button
                type="button"
                disabled={!isConnected || isStreaming}
                onClick={() => setUseBrain(!useBrain)}
                aria-pressed={useBrain}
                title="Use layered memory (L0/L1/L2) for this message"
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono transition-all disabled:opacity-50 ${
                  useBrain
                    ? 'bg-purple-950/60 text-purple-400 border border-purple-800/40'
                    : 'text-slate-500 hover:bg-slate-200 dark:hover:bg-[#161B22]'
                }`}
              >
                <Brain className="w-3.5 h-3.5" />
                <span>Brain {useBrain ? 'ON' : 'OFF'}</span>
              </button>
            </div>

            <div className="flex items-center gap-2">
              {isStreaming ? (
                <Button variant="danger" size="sm" onClick={onStop} className="gap-1.5 font-mono">
                  <Square className="w-3.5 h-3.5" />
                  Stop
                </Button>
              ) : (
                <Button
                  variant="primary"
                  size="sm"
                  onClick={submit}
                  disabled={!isConnected || !input.trim()}
                  className="gap-1.5 font-mono"
                >
                  {isConnected ? <Send className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
                  {isConnected ? 'Send' : 'Runtime Offline'}
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
