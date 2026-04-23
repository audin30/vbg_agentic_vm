# Automated Evidence Logic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a background observer that parses streaming text for indicators (IPs, domains, hashes) and populates a per-tab "Evidence Locker".

**Architecture:** Use a Zustand store to manage evidence items per tab. A regex-based parser will process incoming text chunks from the streaming response. The Evidence Panel will subscribe to the store and display items for the active tab.

**Tech Stack:** React, TypeScript, Zustand, Regex.

---

### Task 1: Evidence Store

**Files:**
- Create: `frontend/src/store/useEvidenceStore.ts`

- [ ] **Step 1: Define the evidence store**

```typescript
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/store/useEvidenceStore.ts
git commit -m "feat: add useEvidenceStore for managing indicators"
```

---

### Task 2: Indicator Parser

**Files:**
- Create: `frontend/src/utils/evidenceParser.ts`
- Create: `frontend/src/utils/evidenceParser.test.ts`

- [ ] **Step 1: Write failing tests for the parser**

```typescript
// frontend/src/utils/evidenceParser.test.ts
import { parseIndicators } from './evidenceParser';

describe('parseIndicators', () => {
  it('should parse IPv4 addresses', () => {
    const text = 'Check 192.168.1.1 and 10.0.0.1';
    const result = parseIndicators(text);
    expect(result).toContainEqual({ type: 'ip', value: '192.168.1.1' });
    expect(result).toContainEqual({ type: 'ip', value: '10.0.0.1' });
  });

  it('should parse domains', () => {
    const text = 'Visit google.com or malicious-site.net';
    const result = parseIndicators(text);
    expect(result).toContainEqual({ type: 'domain', value: 'google.com' });
    expect(result).toContainEqual({ type: 'domain', value: 'malicious-site.net' });
  });

  it('should parse SHA256 hashes', () => {
    const text = 'Hash: 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824';
    const result = parseIndicators(text);
    expect(result).toContainEqual({ type: 'hash', value: '2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824' });
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test frontend/src/utils/evidenceParser.test.ts` (assuming vitest/jest is setup)

- [ ] **Step 3: Implement the parser**

```typescript
// frontend/src/utils/evidenceParser.ts
export interface DiscoveredIndicator {
  type: 'ip' | 'domain' | 'hash';
  value: string;
}

const IP_REGEX = /\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b/g;
const DOMAIN_REGEX = /\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}\b/gi;
const HASH_REGEX = /\b[A-Fa-f0-9]{64}\b/g;

export const parseIndicators = (text: string): DiscoveredIndicator[] => {
  const indicators: DiscoveredIndicator[] = [];

  const ips = text.match(IP_REGEX);
  if (ips) {
    ips.forEach((ip) => indicators.push({ type: 'ip', value: ip }));
  }

  const domains = text.match(DOMAIN_REGEX);
  if (domains) {
    domains.forEach((domain) => {
        // Simple filter to avoid some false positives
        if (!domain.includes('..') && domain.split('.').every(part => part.length > 0)) {
            indicators.push({ type: 'domain', value: domain.toLowerCase() });
        }
    });
  }

  const hashes = text.match(HASH_REGEX);
  if (hashes) {
    hashes.forEach((hash) => indicators.push({ type: 'hash', value: hash.toLowerCase() }));
  }

  return indicators;
};
```

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/evidenceParser.ts frontend/src/utils/evidenceParser.test.ts
git commit -m "feat: implement indicator parser with regex"
```

---

### Task 3: Integration

**Files:**
- Modify: `frontend/src/hooks/useStreamingResponse.ts`

- [ ] **Step 1: Integrate parser and store into the streaming hook**

```typescript
// frontend/src/hooks/useStreamingResponse.ts
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { useMessageStore } from '../store/useMessageStore';
import { useEvidenceStore } from '../store/useEvidenceStore'; // Add this
import { parseIndicators } from '../utils/evidenceParser'; // Add this
import { useRef, useEffect } from 'react';

export const useStreamingResponse = (tabId: string) => {
  const updateLastMessage = useMessageStore((state) => state.updateLastMessage);
  const addEvidence = useEvidenceStore((state) => state.addEvidence); // Add this
  const abortControllerRef = useRef<AbortController | null>(null);

  // ... (rest of the code)

        onmessage(ev) {
          if (ev.event === 'thought') {
            updateLastMessage(tabId, query_id, ev.data, true);
          } else if (ev.event === 'message' || !ev.event) {
            updateLastMessage(tabId, query_id, ev.data, false);
          }
          
          // Parse and add evidence
          const indicators = parseIndicators(ev.data);
          indicators.forEach((indicator) => {
            addEvidence(tabId, indicator);
          });
        },
  // ...
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/useStreamingResponse.ts
git commit -m "feat: integrate evidence extraction into streaming response"
```

---

### Task 4: UI Component

**Files:**
- Create: `frontend/src/components/EvidenceList.tsx`
- Modify: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: Create EvidenceList component**

```typescript
import React from 'react';
import { useEvidenceStore, EvidenceItem } from '../store/useEvidenceStore';
import { useTabStore } from '../store/useTabStore';

const EvidenceList: React.FC = () => {
  const activeTabId = useTabStore((state) => state.tabs.find((t) => t.isActive)?.id);
  const evidence = useEvidenceStore((state) => 
    activeTabId ? state.evidence[activeTabId] || [] : []
  );

  if (evidence.length === 0) {
    return <div style={{ color: '#8b949e', fontSize: '0.9rem' }}>No evidence collected yet.</div>;
  }

  return (
    <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
      {evidence.map((item) => (
        <li key={item.id} style={{ 
          padding: '0.5rem', 
          borderBottom: '1px solid var(--border)',
          fontSize: '0.85rem'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
            <span style={{ 
              textTransform: 'uppercase', 
              fontSize: '0.7rem', 
              color: '#58a6ff',
              fontWeight: 'bold'
            }}>
              {item.type}
            </span>
            <span style={{ fontSize: '0.7rem', color: '#8b949e' }}>
              {new Date(item.timestamp).toLocaleTimeString()}
            </span>
          </div>
          <div style={{ wordBreak: 'break-all', fontFamily: 'monospace' }}>
            {item.value}
          </div>
        </li>
      ))}
    </ul>
  );
};

export default EvidenceList;
```

- [ ] **Step 2: Integrate into Layout**

```typescript
// frontend/src/components/Layout.tsx
import React, { useState } from 'react';
import TabBar from './TabBar';
import EvidenceList from './EvidenceList'; // Add this

// ...
        <div style={{ padding: '1rem', width: '300px' }}>
          <h3 style={{ margin: 0 }}>Evidence Panel</h3>
          <div style={{ marginTop: '1rem' }}>
             <EvidenceList /> {/* Replace the placeholder text */}
          </div>
        </div>
// ...
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/EvidenceList.tsx frontend/src/components/Layout.tsx
git commit -m "feat: add EvidenceList component to EvidencePanel"
```

- [ ] **Step 4: Final verification and merge**

```bash
git commit -m "feat: add automated evidence extraction logic"
```
