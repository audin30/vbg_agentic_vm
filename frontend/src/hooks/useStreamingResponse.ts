import { fetchEventSource } from '@microsoft/fetch-event-source';
import { useMessageStore } from '../store/useMessageStore';
import { useEvidenceStore } from '../store/useEvidenceStore';
import { useTabStore } from '../store/useTabStore';
import { parseIndicators } from '../utils/evidenceParser';
import { useRef, useEffect } from 'react';

export const useStreamingResponse = (tabId: string) => {
  const updateLastMessage = useMessageStore((state) => state.updateLastMessage);
  const addEvidence = useEvidenceStore((state) => state.addEvidence);
  const updateTabState = useTabStore((state) => state.updateTabState);
  const getTab = (id: string) => useTabStore.getState().tabs.find(t => t.id === id);
  
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
    let accumulatedContent = '';
    // Abort existing connection if any
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    abortControllerRef.current = new AbortController();
    const query_id = Math.random().toString(36).substring(7);
    const token = localStorage.getItem('token'); // Fixed key from access_token to token

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
          if (ev.event === 'thought') {
            updateLastMessage(tabId, query_id, ev.data, true);
          } else if (ev.event === 'message' || !ev.event) {
            updateLastMessage(tabId, query_id, ev.data, false);
          }

          accumulatedContent += ev.data || '';
          const indicators = parseIndicators(accumulatedContent);
          indicators.forEach((indicator) => {
            addEvidence(tabId, indicator);
          });
        },
        onclose() {
          console.log('Stream finished, saving state...');
          const tab = getTab(tabId);
          if (tab) {
            // Save state to backend
            const messages = useMessageStore.getState().messages[tabId] || [];
            const evidence = useEvidenceStore.getState().evidence[tabId] || [];
            updateTabState(tabId, tab.title, { messages, evidence });
          }
        },
        onerror(err) {
          if (err instanceof Error && err.name === 'AbortError') {
            console.log('Stream aborted');
            return;
          }
          console.error('SSE Error:', err);
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
