# Streaming Chat Component Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a real-time streaming chat interface with Server-Sent Events (SSE) support for final responses and internal thought traces.

**Architecture:** A Zustand-based message store maps tab IDs to message histories. A custom hook uses `@microsoft/fetch-event-source` to handle SSE streams, updating the store in real-time. A `ChatView` component renders the messages with auto-scroll and visual differentiation for "thoughts".

**Tech Stack:** React, TypeScript, Zustand, @microsoft/fetch-event-source, Lucide-React.

---

### Task 1: Message Store

**Files:**
- Create: `frontend/src/store/useMessageStore.ts`

- [ ] **Step 1: Create the store with basic types and actions**

```typescript
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/store/useMessageStore.ts
git commit -m "feat: add useMessageStore for per-tab message history"
```

---

### Task 2: Streaming Hook

**Files:**
- Create: `frontend/src/hooks/useStreamingResponse.ts`

- [ ] **Step 1: Implement the hook using fetch-event-source**

```typescript
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { useMessageStore } from '../store/useMessageStore';

export const useStreamingResponse = (tabId: string) => {
  const updateLastMessage = useMessageStore((state) => state.updateLastMessage);

  const stream = async (query: string, options: { indicator?: string, indicator_type?: string } = {}) => {
    const query_id = Math.random().toString(36).substring(7);
    const token = localStorage.getItem('access_token');

    try {
      await fetchEventSource('http://localhost:8000/api/orchestrate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          question: query,
          ...options
        }),
        onmessage(ev) {
          if (ev.event === 'thought') {
            updateLastMessage(tabId, query_id, ev.data, true);
          } else if (ev.event === 'message' || !ev.event) {
            updateLastMessage(tabId, query_id, ev.data, false);
          }
        },
        onerror(err) {
          console.error('SSE Error:', err);
          throw err;
        }
      });
    } catch (err) {
      console.error('Failed to start stream:', err);
    }
  };

  return { stream };
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/useStreamingResponse.ts
git commit -m "feat: implement useStreamingResponse hook with SSE support"
```

---

### Task 3: Chat Component

**Files:**
- Create: `frontend/src/components/ChatView.tsx`

- [ ] **Step 1: Create the ChatView component with auto-scroll and message rendering**

```tsx
import React, { useState, useRef, useEffect } from 'react';
import { useMessageStore } from '../store/useMessageStore';
import { useStreamingResponse } from '../hooks/useStreamingResponse';
import { Send, BrainCircuit, Shield } from 'lucide-react';

interface ChatViewProps {
  tabId: string;
}

export const ChatView: React.FC<ChatViewProps> = ({ tabId }) => {
  const [input, setInput] = useState('');
  const messages = useMessageStore((state) => state.messages[tabId] || []);
  const addMessage = useMessageStore((state) => state.addMessage);
  const { stream } = useStreamingResponse(tabId);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = {
      id: Math.random().toString(36).substring(7),
      query_id: Math.random().toString(36).substring(7),
      role: 'user' as const,
      content: input,
      isThought: false,
      timestamp: Date.now(),
    };

    addMessage(tabId, userMessage);
    const query = input;
    setInput('');
    await stream(query);
  };

  return (
    <div className="flex flex-col h-full bg-slate-900 text-slate-100">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg p-3 ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : msg.isThought
                  ? 'bg-slate-800 border border-slate-700 text-slate-400 italic'
                  : 'bg-slate-800 text-slate-100'
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                {msg.role === 'assistant' && (
                  msg.isThought ? <BrainCircuit size={14} className="text-purple-400" /> : <Shield size={14} className="text-emerald-400" />
                )}
                <span className="text-xs font-bold uppercase tracking-wider opacity-50">
                  {msg.role === 'user' ? 'You' : msg.isThought ? 'Thought Trace' : 'Orchestrator'}
                </span>
              </div>
              <div className="whitespace-pre-wrap">{msg.content}</div>
            </div>
          </div>
        ))}
        <div ref={scrollRef} />
      </div>

      <form onSubmit={handleSend} className="p-4 border-t border-slate-800 bg-slate-900/50">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask anything..."
            className="flex-1 bg-slate-800 border border-slate-700 rounded-md px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            className="bg-blue-600 hover:bg-blue-700 text-white p-2 rounded-md transition-colors"
          >
            <Send size={20} />
          </button>
        </div>
      </form>
    </div>
  );
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ChatView.tsx
git commit -m "feat: add streaming chat view with thought trace support"
```
