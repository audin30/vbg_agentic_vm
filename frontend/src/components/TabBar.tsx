import React from 'react';
import { useTabStore } from '../store/useTabStore';

const TabBar: React.FC = () => {
  const { tabs, setActiveTab, removeTab } = useTabStore();

  return (
    <div style={{ 
      display: 'flex', 
      backgroundColor: 'var(--sidebar-bg)', 
      borderBottom: '1px solid var(--border)',
      padding: '0 10px',
      gap: '5px',
      overflowX: 'auto',
      minHeight: '40px'
    }}>
      {tabs.map((tab) => (
        <div 
          key={tab.id}
          onClick={() => setActiveTab(tab.id)}
          style={{
            padding: '8px 15px',
            cursor: 'pointer',
            backgroundColor: tab.isActive ? 'var(--bg-dark)' : 'transparent',
            borderBottom: tab.isActive ? '2px solid var(--accent)' : 'none',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            whiteSpace: 'nowrap',
            borderRight: '1px solid var(--border)',
            borderLeft: '1px solid var(--border)'
          }}
        >
          <span style={{ fontSize: '0.9rem' }}>{tab.title}</span>
          <button 
            onClick={(e) => {
              e.stopPropagation();
              removeTab(tab.id);
            }}
            style={{
              background: 'none',
              border: 'none',
              color: '#8b949e',
              cursor: 'pointer',
              fontSize: '1rem',
              padding: '0 4px'
            }}
          >
            ×
          </button>
        </div>
      ))}
      {tabs.length === 0 && (
        <div style={{ display: 'flex', alignItems: 'center', padding: '0 10px', color: '#8b949e', fontSize: '0.8rem' }}>
          No active investigations
        </div>
      )}
    </div>
  );
};

export default TabBar;
