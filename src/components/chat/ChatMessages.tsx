import React from 'react';
import { MessageSquareOff, WifiOff, User, Sparkles } from 'lucide-react';
import { Message } from '../../types';
import { ActivityRow } from './ActivityRow';
import { SourceCard } from './SourceCard';

export interface ChatMessagesProps {
  messages: Message[];
  isConnected?: boolean;
}

export const ChatMessages: React.FC<ChatMessagesProps> = ({ messages, isConnected = false }) => {
  if (!messages || messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center max-w-md mx-auto">
        <div className="p-4 rounded-full bg-slate-200 dark:bg-slate-800/50 text-slate-400 mb-3">
          <MessageSquareOff className="w-8 h-8 text-slate-500" />
        </div>
        <h2 className="text-base font-bold font-mono text-slate-800 dark:text-slate-200">
          No conversation yet
        </h2>
        <p className="text-xs text-slate-600 dark:text-slate-400 mt-1 font-sans">
          {isConnected
            ? 'Ask INTLLM a question to start. Memory and live retrieval are applied automatically.'
            : 'Connect INTLLM runtime service to start chatting with local language models.'}
        </p>
        <div
          className={`mt-4 flex items-center gap-2 px-3 py-1.5 rounded border text-[11px] font-mono ${
            isConnected
              ? 'bg-emerald-950/20 border-emerald-800/40 text-emerald-500 dark:text-emerald-400'
              : 'bg-amber-950/30 border-amber-800/40 text-amber-500 dark:text-amber-400'
          }`}
        >
          {isConnected ? <Sparkles className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
          <span>{isConnected ? 'Local AI Runtime Ready' : 'Local AI Runtime Standby'}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
      <div className="max-w-4xl mx-auto w-full space-y-6">
        {messages.map((msg) => (
          <div key={msg.id} className="space-y-1">
            <div className="flex items-center gap-2 text-[11px] font-mono text-slate-500">
              {msg.role === 'user' ? (
                <User className="w-3.5 h-3.5" />
              ) : (
                <Sparkles className="w-3.5 h-3.5 text-cyan-500" />
              )}
              <span className="uppercase font-semibold tracking-wide">{msg.role}</span>
              {msg.model && <span className="text-slate-400">· {msg.model}</span>}
              {msg.tokensPerSec ? <span className="text-slate-400">· {msg.tokensPerSec} tok/s</span> : null}
            </div>

            <div
              className={`rounded-lg border px-4 py-3 text-sm font-sans whitespace-pre-wrap leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-slate-100 dark:bg-[#161B22] border-slate-200 dark:border-[#21262D] text-slate-800 dark:text-slate-200'
                  : 'bg-white dark:bg-[#0D1117] border-slate-200 dark:border-[#21262D] text-slate-800 dark:text-slate-100'
              }`}
            >
              {msg.content || (
                <span className="inline-flex items-center gap-2 text-slate-500">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                  {msg.isStreaming ? 'Generating…' : ''}
                </span>
              )}
            </div>

            {msg.activities && msg.activities.length > 0 && (
              <ActivityRow
                activities={msg.activities}
                memoryCount={msg.memoryUsed ?? 0}
                sourceCount={msg.sources?.length ?? 0}
              />
            )}
            {msg.sources && msg.sources.length > 0 && <SourceCard sources={msg.sources} />}
          </div>
        ))}
      </div>
    </div>
  );
};
