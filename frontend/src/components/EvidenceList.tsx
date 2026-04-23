import React from 'react';
import { useEvidenceStore } from '../store/useEvidenceStore';
import { useTabStore } from '../store/useTabStore';

const EvidenceList: React.FC = () => {
  const activeTabId = useTabStore((state) => state.tabs.find((t) => t.isActive)?.id);
  const evidence = useEvidenceStore((state) => 
    activeTabId ? state.evidence[activeTabId] || [] : []
  );

  if (evidence.length === 0) {
    return <div style={{ color: '#8b949e', fontSize: '0.9rem' }}>No evidence collected yet.</div>;
  }

  // Sort evidence by timestamp (newest first)
  const sortedEvidence = [...evidence].sort((a, b) => b.timestamp - a.timestamp);

  return (
    <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
      {sortedEvidence.map((item) => (
        <li key={item.id} style={{ 
          padding: '0.75rem 0', 
          borderBottom: '1px solid var(--border)',
          fontSize: '0.85rem'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.3rem' }}>
            <span style={{ 
              textTransform: 'uppercase', 
              fontSize: '0.65rem', 
              color: '#58a6ff',
              fontWeight: 'bold',
              backgroundColor: 'rgba(56, 139, 253, 0.1)',
              padding: '1px 4px',
              borderRadius: '3px'
            }}>
              {item.type}
            </span>
            <span style={{ fontSize: '0.7rem', color: '#8b949e' }}>
              {new Date(item.timestamp).toLocaleTimeString()}
            </span>
          </div>
          <div style={{ 
            wordBreak: 'break-all', 
            fontFamily: 'var(--font-mono)', 
            color: 'var(--text-main)',
            lineHeight: '1.4'
          }}>
            {item.value}
          </div>
        </li>
      ))}
    </ul>
  );
};

export default EvidenceList;
