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
          // Handle different event types
          // event: 'thought' -> ev.data is a chunk of the thought process
          // event: 'message' -> ev.data is a chunk of the final response
          if (ev.event === 'thought') {
            updateLastMessage(tabId, query_id, ev.data, true);
          } else if (ev.event === 'message' || !ev.event) {
            // Default to main message if event is 'message' or missing
            updateLastMessage(tabId, query_id, ev.data, false);
          }
        },
        onerror(err) {
          console.error('SSE Error:', err);
          // fetch-event-source will automatically retry by default unless we throw
          throw err; 
        }
      });
    } catch (err) {
      console.error('Failed to start stream:', err);
    }
  };

  return { stream };
};
