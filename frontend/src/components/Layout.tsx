import React, { useState } from 'react';
import TabBar from './TabBar';

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isEvidencePanelOpen, setIsEvidencePanelOpen] = useState(true);

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden' }}>
      {/* Sidebar */}
      <aside style={{ width: '260px', backgroundColor: 'var(--sidebar-bg)', borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '1rem', borderBottom: '1px solid var(--border)' }}>
          <h2 style={{ fontSize: '1.2rem', margin: 0 }}>Security Hub</h2>
        </div>
        <nav style={{ flex: 1, padding: '1rem' }}>
          {/* History/Navigation will go here */}
          <div style={{ color: '#8b949e', fontSize: '0.9rem' }}>Investigation History</div>
        </nav>
      </aside>

      {/* Main Area */}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-dark)' }}>
        <TabBar />
        <section style={{ flex: 1, overflowY: 'auto', padding: '1rem' }}>
          {children}
        </section>
      </main>

      {/* Evidence Panel */}
      <aside style={{ 
        width: isEvidencePanelOpen ? '300px' : '0px', 
        backgroundColor: 'var(--sidebar-bg)', 
        borderLeft: isEvidencePanelOpen ? '1px solid var(--border)' : 'none',
        transition: 'width 0.3s ease',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        overflow: 'hidden'
      }}>
        <button 
          onClick={() => setIsEvidencePanelOpen(!isEvidencePanelOpen)}
          style={{
            position: 'absolute',
            left: isEvidencePanelOpen ? '0px' : '-25px',
            top: '50%',
            transform: 'translateY(-50%)',
            backgroundColor: 'var(--border)',
            border: 'none',
            color: 'white',
            cursor: 'pointer',
            padding: '10px 5px',
            borderRadius: '5px 0 0 5px',
            zIndex: 10
          }}
        >
          {isEvidencePanelOpen ? '>' : '<'}
        </button>
        <div style={{ padding: '1rem', width: '300px' }}>
          <h3 style={{ margin: 0 }}>Evidence Panel</h3>
          <div style={{ marginTop: '1rem', color: '#8b949e', fontSize: '0.9rem' }}>Collected artifacts will appear here.</div>
        </div>
      </aside>
    </div>
  );
};

export default Layout;
