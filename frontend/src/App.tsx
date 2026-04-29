import { useEffect, useState } from 'react'
import './App.css'
import Layout from './components/Layout'
import { useTabStore } from './store/useTabStore'

function App() {
  const { tabs, addTab, fetchTabs } = useTabStore();
  const [isInitializing, setIsInitializing] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const init = async () => {
      try {
        console.log("Initializing Security Hub...");
        await fetchTabs();
        
        const currentTabs = useTabStore.getState().tabs;
        if (currentTabs.length === 0) {
          console.log("No tabs found, creating dashboard...");
          await addTab({ id: 'dashboard', title: 'Main Dashboard' });
        }
      } catch (err: any) {
        console.error("Initialization error:", err);
        setError(err.message || "Failed to connect to backend");
      } finally {
        setIsInitializing(false);
      }
    };

    init();
  }, [fetchTabs, addTab]);

  if (error) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#f85149' }}>
        <h1>Connection Error</h1>
        <p>{error}</p>
        <button onClick={() => window.location.reload()} style={{ padding: '10px 20px', cursor: 'pointer' }}>
          Retry Connection
        </button>
      </div>
    );
  }

  if (isInitializing) {
    return (
      <div style={{ 
        display: 'flex', 
        height: '100vh', 
        width: '100vw', 
        justifyContent: 'center', 
        alignItems: 'center',
        backgroundColor: '#0d1117',
        color: '#c9d1d9',
        flexDirection: 'column'
      }}>
        <h2>Loading Security Hub...</h2>
        <p style={{ opacity: 0.5 }}>Connecting to services at {window.location.hostname}</p>
      </div>
    );
  }

  return (
    <Layout>
      <div className="content">
        <h1>Centralized Security Hub</h1>
        <p>Phase 3: Sub-Agent & HITL Persistence Active</p>
        <div style={{ marginTop: '2rem', padding: '1rem', border: '1px solid var(--border)', borderRadius: '8px' }}>
          <h3>Welcome to the Investigation Portal</h3>
          <p>Status: Authenticated and Connected to {window.location.hostname}</p>
        </div>
      </div>
    </Layout>
  )
}

export default App
