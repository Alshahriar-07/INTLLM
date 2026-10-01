import React, { useMemo, useState } from 'react';
import { Check, Loader2, MessageSquare, MoreHorizontal, Pencil, Plus, Search, Trash2, X } from 'lucide-react';
import { ConversationSummary } from '../../lib/services/chatService';
import { cn } from '../../lib/utils';

export interface ConversationListProps {
  conversations: ConversationSummary[];
  activeId: string | null;
  loading: boolean;
  query: string;
  onQueryChange: (q: string) => void;
  onSelect: (id: string) => void;
  onNew: () => void;
  onRename: (id: string, title: string) => void;
  onDelete: (id: string) => void;
}

/** Group a conversation's update time into a human bucket label. */
function timeBucket(iso: string): string {
  const then = new Date(iso);
  if (Number.isNaN(then.getTime())) return 'Older';
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const t = then.getTime();
  if (t >= startOfToday) return 'Today';
  if (t >= startOfToday - 86_400_000) return 'Yesterday';
  if (t >= startOfToday - 7 * 86_400_000) return 'Previous 7 days';
  return 'Older';
}

const BUCKET_ORDER = ['Today', 'Yesterday', 'Previous 7 days', 'Older'];

export const ConversationList: React.FC<ConversationListProps> = ({
  conversations,
  activeId,
  loading,
  query,
  onQueryChange,
  onSelect,
  onNew,
  onRename,
  onDelete
}) => {
  const [menuId, setMenuId] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = q
      ? conversations.filter((c) => c.title.toLowerCase().includes(q))
      : conversations;
    const groups = new Map<string, ConversationSummary[]>();
    for (const c of list) {
      const bucket = timeBucket(c.updatedAt || c.createdAt);
      if (!groups.has(bucket)) groups.set(bucket, []);
      groups.get(bucket)!.push(c);
    }
    return BUCKET_ORDER.map((bucket) => ({ bucket, items: groups.get(bucket) ?? [] })).filter(
      (g) => g.items.length > 0
    );
  }, [conversations, query]);

  const startRename = (c: ConversationSummary) => {
    setRenamingId(c.id);
    setRenameValue(c.title);
    setMenuId(null);
  };

  const commitRename = () => {
    if (renamingId && renameValue.trim()) {
      onRename(renamingId, renameValue.trim());
    }
    setRenamingId(null);
  };

  const confirmDelete = (id: string) => {
    onDelete(id);
    setConfirmDeleteId(null);
    setMenuId(null);
  };

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* New chat + search */}
      <div className="p-2.5 space-y-2 shrink-0">
        <button
          type="button"
          onClick={onNew}
          className="w-full flex items-center gap-2 h-8 px-2.5 rounded-md bg-accent text-accent-foreground text-sm font-medium hover:bg-accent-hover transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/60"
        >
          <Plus className="w-4 h-4" aria-hidden />
          New chat
        </button>
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-muted absolute left-2.5 top-1/2 -translate-y-1/2" aria-hidden />
          <input
            type="search"
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            placeholder="Search chats…"
            aria-label="Search conversations"
            className="w-full h-8 pl-8 pr-2 rounded-md border border-border bg-canvas text-xs text-primary placeholder:text-muted/80 focus:outline-none focus:ring-1 focus:ring-ring/50 focus:border-accent/50"
          />
        </div>
      </div>

      {/* History list */}
      <div className="flex-1 overflow-y-auto min-h-0 px-2.5 pb-2" role="list" aria-label="Conversation history">
        {loading && conversations.length === 0 && (
          <div className="flex items-center justify-center gap-2 py-8 text-xs text-muted font-mono">
            <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden />
            Loading conversations…
          </div>
        )}

        {!loading && conversations.length === 0 && (
          <div className="py-8 px-2 text-center space-y-1.5">
            <MessageSquare className="w-5 h-5 text-muted mx-auto" aria-hidden />
            <p className="text-xs text-secondary font-medium">No conversations yet</p>
            <p className="text-[11px] text-muted leading-relaxed">
              {query ? 'No chats match your search.' : 'Start a new chat — history is saved automatically.'}
            </p>
          </div>
        )}

        {filtered.map(({ bucket, items }) => (
          <div key={bucket} className="mb-2">
            <div className="px-1.5 pt-2 pb-1 text-[10px] font-medium uppercase tracking-wider text-muted select-none">
              {bucket}
            </div>
            <div className="space-y-0.5">
              {items.map((c) => {
                const isActive = c.id === activeId;
                if (renamingId === c.id) {
                  return (
                    <div key={c.id} className="flex items-center gap-1 px-1 py-0.5">
                      <input
                        autoFocus
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') commitRename();
                          if (e.key === 'Escape') setRenamingId(null);
                        }}
                        aria-label="Conversation title"
                        className="flex-1 min-w-0 h-7 px-1.5 rounded border border-accent/50 bg-canvas text-xs text-primary focus:outline-none focus:ring-1 focus:ring-ring/50"
                      />
                      <button
                        type="button"
                        onClick={commitRename}
                        aria-label="Confirm rename"
                        className="p-1 rounded text-success hover:bg-panel-hover focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                      >
                        <Check className="w-3.5 h-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => setRenamingId(null)}
                        aria-label="Cancel rename"
                        className="p-1 rounded text-muted hover:bg-panel-hover focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  );
                }

                if (confirmDeleteId === c.id) {
                  return (
                    <div
                      key={c.id}
                      className="px-2 py-1.5 rounded-md border border-error/30 bg-error/5 space-y-1.5"
                    >
                      <p className="text-[11px] text-secondary leading-snug">Delete “{c.title}”?</p>
                      <div className="flex items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => confirmDelete(c.id)}
                          className="px-2 h-6 rounded text-[11px] font-medium bg-error/15 text-error hover:bg-error/25 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                        >
                          Delete
                        </button>
                        <button
                          type="button"
                          onClick={() => setConfirmDeleteId(null)}
                          className="px-2 h-6 rounded text-[11px] text-secondary hover:bg-panel-hover focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  );
                }

                return (
                  <div key={c.id} className="relative group">
                    <button
                      type="button"
                      role="listitem"
                      onClick={() => onSelect(c.id)}
                      aria-current={isActive ? 'true' : undefined}
                      title={c.title}
                      className={cn(
                        'w-full flex items-center gap-2 h-8 px-2 rounded-md text-left text-xs transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
                        isActive
                          ? 'bg-panel-hover text-primary font-medium'
                          : 'text-secondary hover:bg-panel-hover hover:text-primary'
                      )}
                    >
                      <MessageSquare
                        className={cn('w-3.5 h-3.5 shrink-0', isActive ? 'text-accent' : 'text-muted')}
                        aria-hidden
                      />
                      <span className="flex-1 min-w-0 truncate">{c.title}</span>
                    </button>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setMenuId(menuId === c.id ? null : c.id);
                      }}
                      aria-label={`Options for ${c.title}`}
                      aria-expanded={menuId === c.id}
                      className={cn(
                        'absolute right-1 top-1/2 -translate-y-1/2 p-1 rounded text-muted hover:text-primary hover:bg-panel-hover focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
                        menuId === c.id ? 'opacity-100' : 'opacity-0 group-hover:opacity-100 focus-visible:opacity-100'
                      )}
                    >
                      <MoreHorizontal className="w-3.5 h-3.5" />
                    </button>

                    {menuId === c.id && (
                      <div
                        role="menu"
                        className="absolute right-1 top-8 z-20 w-36 bg-elevated border border-border rounded-md shadow-lg py-1 animate-scale-in"
                      >
                        <button
                          role="menuitem"
                          onClick={() => startRename(c)}
                          className="w-full flex items-center gap-2 px-2.5 py-1.5 text-xs text-secondary hover:bg-panel-hover hover:text-primary focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                        >
                          <Pencil className="w-3.5 h-3.5" /> Rename
                        </button>
                        <button
                          role="menuitem"
                          onClick={() => {
                            setConfirmDeleteId(c.id);
                            setMenuId(null);
                          }}
                          className="w-full flex items-center gap-2 px-2.5 py-1.5 text-xs text-error hover:bg-error/10 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                        >
                          <Trash2 className="w-3.5 h-3.5" /> Delete
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
