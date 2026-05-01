import { useEffect, useState } from 'react'
import './App.css'
import Layout from './components/Layout'
import Login from './components/Login'
import { useTabStore } from './store/useTabStore'
import { ChatView } from './components/ChatView'

function App() {
  const { tabs, addTab, fetchTabs } = useTabStore();
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('token'));
  const [isInitializing, setIsInitializing] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      setIsInitializing(false);
      return;
    }

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
  }, [fetchTabs, addTab, isAuthenticated]);

  const handleLoginSuccess = () => {
    setIsAuthenticated(true);
    setIsInitializing(true);
  };

  if (!isAuthenticated) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

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

  const activeTab = tabs.find(t => t.isActive);

  return (
    <Layout>
      {activeTab ? (
        <ChatView tabId={activeTab.id} />
      ) : (
        <div className="content">
          <h1>Centralized Security Hub</h1>
          <p>Please select an investigation tab to begin.</p>
        </div>
      )}
    </Layout>
  )
}

export default App
