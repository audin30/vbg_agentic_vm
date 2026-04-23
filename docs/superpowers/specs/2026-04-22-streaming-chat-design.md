# Design Spec: Streaming SSE Chat Component

## Overview
Implement a real-time, streaming chat interface for the Security Orchestrator portal using Server-Sent Events (SSE). This component will handle both final AI responses and "thought traces" (internal reasoning) to provide transparency to the user.

## Architecture
The system consists of three main parts:
1.  **State Management**: A Zustand store (`useMessageStore`) to manage message history per tab.
2.  **Streaming Hook**: A custom React hook (`useStreamingResponse`) that manages the SSE connection using `@microsoft/fetch-event-source`.
3.  **UI Component**: A React component (`ChatView`) that renders the messages and handles user input.

## Components

### 1. `useMessageStore` (Zustand)
- **State**:
    - `messages`: `Record<string, Message[]>` (Map of tabId to messages).
- **Message Object**:
    ```typescript
    interface Message {
      id: string;
      query_id: string;
      role: 'user' | 'assistant';
      content: string;
      isThought: boolean;
      timestamp: number;
    }
    ```
- **Actions**:
    - `addMessage(tabId: string, message: Message)`: Appends a message to the tab's history.
    - `updateLastMessage(tabId: string, query_id: string, contentChunk: string, isThought: boolean)`: Finds the last message for the given query_id and appends the chunk. If it doesn't exist, it creates one.
    - `clearMessages(tabId: string)`: Clears history for a tab.

### 2. `useStreamingResponse` (Hook)
- **Inputs**: `tabId: string`
- **Functionality**:
    - Uses `fetchEventSource` for robust SSE handling (handles POST requests and headers).
    - **Events**:
        - `thought`: Appends content to an `assistant` message with `isThought: true`.
        - `message`: Appends content to an `assistant` message with `isThought: false`.
    - **Error Handling**: Retries on connection failure (built-in to fetch-event-source).

### 3. `ChatView` (Component)
- **Layout**:
    - Message list at the top (flexible height).
    - Input area at the bottom (fixed).
- **Styling**:
    - **User messages**: Right-aligned, blue background.
    - **Assistant Thoughts**: Left-aligned, italicized, dimmed gray background, perhaps with a "Thought Trace" label.
    - **Assistant Responses**: Left-aligned, standard background.
- **Interactions**:
    - Auto-scroll to bottom whenever `messages` for the active tab changes.
    - Loading state while streaming.

## Data Flow
1. User enters text in `ChatView` and hits send.
2. `ChatView` calls `addMessage` (user role) and then triggers `useStreamingResponse.stream()`.
3. `useStreamingResponse` opens SSE connection to `/api/orchestrate/stream`.
4. As `thought` events arrive, `updateLastMessage` is called with `isThought: true`.
5. As `message` events arrive, `updateLastMessage` is called with `isThought: false`.
6. `ChatView` re-renders automatically as the store updates.

## Testing Strategy
- **Manual Verification**: Test with a mock SSE server or by observing logs.
- **Auto-scroll**: Verify the list scrolls when content exceeds viewport.
- **Multi-tab**: Verify switching tabs preserves and correctly displays separate message histories.
