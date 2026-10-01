import { Message } from '../../types';
import { apiRequest, openEventStream } from '../api/client';

export interface ChatServiceResponse {
  connected: boolean;
  messages: Message[];
  error?: string;
}

export interface ChatStreamPayload {
  messages: { role: 'system' | 'user' | 'assistant'; content: string }[];
  model?: string;
  conversation_id?: string | null;
  use_brain?: boolean;
  use_web?: boolean;
}

export interface ChatStreamCallbacks {
  onStarted?: (data: any) => void;
  onActivity?: (type: string, data: any) => void;
  onDelta: (content: string) => void;
  onCompleted: (data: any) => void;
  onError: (message: string) => void;
  onClose?: () => void;
}

/** Conversation summary as returned by GET /api/conversations. */
export interface ConversationSummary {
  id: string;
  title: string;
  model?: string | null;
  createdAt: string;
  updatedAt: string;
}

interface ConversationDto {
  id: string;
  title: string;
  model?: string | null;
  createdAt: string;
  updatedAt: string;
}

export const chatService = {
  /** List persisted conversations (summaries only, newest first). */
  async listConversations(limit = 100): Promise<ConversationSummary[]> {
    const result = await apiRequest<ConversationDto[]>(`/conversations?limit=${limit}`);
    if (!result.ok || !result.data) return [];
    return result.data;
  },

  /** Load the full message history of one conversation. */
  async getConversationMessages(conversationId: string): Promise<Message[]> {
    const result = await apiRequest<{ messages: Message[] }>(
      `/conversations/${conversationId}`
    );
    return result.data?.messages ?? [];
  },

  /** Explicitly create an empty conversation (used by "New Chat"). */
  async createConversation(title?: string, model?: string): Promise<ConversationSummary | null> {
    const result = await apiRequest<ConversationDto>('/conversations', {
      method: 'POST',
      body: JSON.stringify({ title: title || null, model: model || null })
    });
    return result.ok ? (result.data ?? null) : null;
  },

  /** Rename a conversation via PATCH /conversations/{id}. */
  async renameConversation(conversationId: string, title: string): Promise<boolean> {
    const result = await apiRequest<ConversationDto>(`/conversations/${conversationId}`, {
      method: 'PATCH',
      body: JSON.stringify({ title })
    });
    return result.ok;
  },

  /** Delete a conversation (cascades to its messages server-side). */
  async deleteConversation(conversationId: string): Promise<boolean> {
    const result = await apiRequest(`/conversations/${conversationId}`, { method: 'DELETE' });
    return result.ok;
  },

  /**
   * Stream a chat completion. Returns an abort function for stop-generation.
   * Activity events (brain.lookup, memory.retrieved, web.*) are forwarded only
   * when the backend actually emits them.
   */
  stream(payload: ChatStreamPayload, callbacks: ChatStreamCallbacks): () => void {
    return openEventStream('/chat/stream', payload, {
      onEvent: (type, data) => {
        switch (type) {
          case 'chat.started':
            callbacks.onStarted?.(data);
            break;
          case 'assistant.delta':
            callbacks.onDelta(data?.content ?? '');
            break;
          case 'chat.completed':
            callbacks.onCompleted(data);
            break;
          case 'chat.error':
            callbacks.onError(data?.message ?? 'Chat failed');
            break;
          default:
            callbacks.onActivity?.(type, data);
        }
      },
      onError: callbacks.onError,
      onClose: callbacks.onClose
    });
  }
};
