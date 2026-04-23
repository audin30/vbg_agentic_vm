import { fetchEventSource } from '@microsoft/fetch-event-source';
import { useMessageStore } from '../store/useMessageStore';
import { useEvidenceStore } from '../store/useEvidenceStore';
import { parseIndicators } from '../utils/evidenceParser';
import { useRef, useEffect } from 'react';

export const useStreamingResponse = (tabId: string) => {
  const updateLastMessage = useMessageStore((state) => state.updateLastMessage);
  const addEvidence = useEvidenceStore((state) => state.addEvidence);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const stream = async (query: string, options: { indicator?: string, indicator_type?: string } = {}) => {
    // Abort existing connection if any
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    abortControllerRef.current = new AbortController();
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
        signal: abortControllerRef.current.signal,
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

          // Parse and add evidence
          const indicators = parseIndicators(ev.data);
          indicators.forEach((indicator) => {
            addEvidence(tabId, indicator);
          });
        },
        onerror(err) {
          if (err instanceof Error && err.name === 'AbortError') {
            console.log('Stream aborted');
            return;
          }
          console.error('SSE Error:', err);
          // fetch-event-source will automatically retry by default unless we throw
          throw err; 
        }
      });
    } catch (err: any) {
      if (err.name === 'AbortError') return;
      console.error('Failed to start stream:', err);
    }
  };

  return { stream };
};
