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

interface ConversationDto {
  id: string;
  title: string;
  model?: string | null;
  createdAt: string;
  updatedAt: string;
}

export const chatService = {
  async getConversationHistory(): Promise<ChatServiceResponse> {
    const result = await apiRequest<ConversationDto[]>('/conversations');
    if (!result.ok || !result.data) {
      return { connected: false, messages: [], error: result.error };
    }
    // The list endpoint returns conversation summaries; message history is
    // loaded per-conversation when selected. Return empty rather than faking.
    return { connected: true, messages: [] };
  },

  async getConversationMessages(conversationId: string): Promise<Message[]> {
    const result = await apiRequest<{ messages: Message[] }>(
      `/conversations/${conversationId}`
    );
    return result.data?.messages ?? [];
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
