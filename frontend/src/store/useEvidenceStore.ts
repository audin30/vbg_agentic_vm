import { create } from 'zustand';

export interface EvidenceItem {
  id: string;
  type: 'ip' | 'domain' | 'hash';
  value: string;
  timestamp: number;
}

interface EvidenceState {
  evidence: Record<string, EvidenceItem[]>; // tabId -> EvidenceItem[]
  addEvidence: (tabId: string, item: Omit<EvidenceItem, 'id' | 'timestamp'>) => void;
  clearEvidence: (tabId: string) => void;
}

export const useEvidenceStore = create<EvidenceState>((set) => ({
  evidence: {},

  addEvidence: (tabId, item) => {
    set((state) => {
      const tabEvidence = state.evidence[tabId] || [];
      // Avoid duplicates
      if (tabEvidence.some((e) => e.value === item.value && e.type === item.type)) {
        return state;
      }

      const newItem: EvidenceItem = {
        ...item,
        id: Math.random().toString(36).substring(7),
        timestamp: Date.now(),
      };

      return {
        evidence: {
          ...state.evidence,
          [tabId]: [...tabEvidence, newItem],
        },
      };
    });
  },

  clearEvidence: (tabId) => {
    set((state) => ({
      evidence: {
        ...state.evidence,
        [tabId]: [],
      },
    }));
  },
}));
