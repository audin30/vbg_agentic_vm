import React, { useState } from 'react';
import { useEvidenceStore } from '../store/useEvidenceStore';
import { CheckCircle, XCircle, ShieldAlert, Zap, Globe, Fingerprint } from 'lucide-react';

const EvidenceList: React.FC = () => {
  const { evidence } = useEvidenceStore();
  const [processing, setProcessing] = useState<string | null>(null);

  const handleFeedback = async (id: string, target: string, type: string, decision: string) => {
    setProcessing(id);
    try {
      const response = await fetch('/api/feedback', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          action_type: type,
          target: target,
          decision: decision,
          feedback_notes: `Human ${decision} via Web Portal`
        })
      });

      if (response.ok) {
        // We could update local state here, but for now just showing success
        console.log(`Feedback submitted: ${decision} for ${target}`);
      }
    } catch (err) {
      console.error("Feedback failed:", err);
    } finally {
      setProcessing(null);
    }
  };

  if (evidence.length === 0) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', opacity: 0.5, fontSize: '0.9rem' }}>
        No indicators detected in this session yet.
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', padding: '1rem 0' }}>
      {evidence.map((item) => (
        <div 
          key={item.id} 
          style={{ 
            padding: '1rem', 
            backgroundColor: '#161b22', 
            border: '1px solid #30363d', 
            borderRadius: '8px',
            fontSize: '0.9rem'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '0.5rem' }}>
            {item.type === 'ip' && <Globe size={14} className="text-blue-400" />}
            {item.type === 'cve' && <ShieldAlert size={14} className="text-red-400" />}
            {item.type === 'hash' && <Fingerprint size={14} className="text-purple-400" />}
            <span style={{ fontWeight: 600, color: '#c9d1d9' }}>{item.value}</span>
          </div>
          
          <div style={{ color: '#8b949e', fontSize: '0.8rem', marginBottom: '1rem' }}>
            Source: {item.source}
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              disabled={processing === item.id}
              onClick={() => handleFeedback(item.id, item.value, item.type, 'approved')}
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '4px',
                padding: '6px',
                backgroundColor: 'rgba(35, 134, 54, 0.1)',
                border: '1px solid rgba(35, 134, 54, 0.4)',
                borderRadius: '4px',
                color: '#3fb950',
                cursor: 'pointer',
                fontSize: '0.75rem'
              }}
            >
              <CheckCircle size={12} /> Approve
            </button>
            <button
              disabled={processing === item.id}
              onClick={() => handleFeedback(item.id, item.value, item.type, 'denied')}
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '4px',
                padding: '6px',
                backgroundColor: 'rgba(248, 81, 73, 0.1)',
                border: '1px solid rgba(248, 81, 73, 0.4)',
                borderRadius: '4px',
                color: '#f85149',
                cursor: 'pointer',
                fontSize: '0.75rem'
              }}
            >
              <XCircle size={12} /> Deny
            </button>
          </div>
        </div>
      ))}
    </div>
  );
};

export default EvidenceList;
