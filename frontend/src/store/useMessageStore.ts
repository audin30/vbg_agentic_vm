import { create } from 'zustand';

export interface Message {
  id: string;
  query_id: string;
  role: 'user' | 'assistant';
  content: string;
  isThought: boolean;
  timestamp: number;
}

interface MessageState {
  messages: Record<string, Message[]>;
  addMessage: (tabId: string, message: Message) => void;
  updateLastMessage: (tabId: string, query_id: string, contentChunk: string, isThought: boolean) => void;
  clearMessages: (tabId: string) => void;
}

export const useMessageStore = create<MessageState>((set) => ({
  messages: {},

  addMessage: (tabId, message) => {
    set((state) => ({
      messages: {
        ...state.messages,
        [tabId]: [...(state.messages[tabId] || []), message],
      },
    }));
  },

  updateLastMessage: (tabId, query_id, contentChunk, isThought) => {
    set((state) => {
      const tabMessages = state.messages[tabId] || [];
      // Look for the last message with the same query_id and isThought status
      const lastMsgIndex = [...tabMessages].reverse().findIndex(
        (m) => m.query_id === query_id && m.isThought === isThought && m.role === 'assistant'
      );

      if (lastMsgIndex === -1) {
        // Create new assistant message if none exists for this query_id/type
        const newMessage: Message = {
          id: Math.random().toString(36).substring(7),
          query_id,
          role: 'assistant',
          content: contentChunk,
          isThought,
          timestamp: Date.now(),
        };
        return {
          messages: {
            ...state.messages,
            [tabId]: [...tabMessages, newMessage],
          },
        };
      }

      // Update existing message
      const actualIndex = tabMessages.length - 1 - lastMsgIndex;
      const updatedMessages = [...tabMessages];
      updatedMessages[actualIndex] = {
        ...updatedMessages[actualIndex],
        content: updatedMessages[actualIndex].content + contentChunk,
      };

      return {
        messages: {
          ...state.messages,
          [tabId]: updatedMessages,
        },
      };
    });
  },

  clearMessages: (tabId) => {
    set((state) => {
      const newMessages = { ...state.messages };
      delete newMessages[tabId];
      return { messages: newMessages };
    });
  },
}));
