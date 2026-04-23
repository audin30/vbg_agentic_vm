import { useEffect } from 'react'
import './App.css'
import Layout from './components/Layout'
import { useTabStore } from './store/useTabStore'

function App() {
  const addTab = useTabStore((state) => state.addTab);

  useEffect(() => {
    // Add a default tab on load if none exist
    addTab({ id: 'dashboard', title: 'Main Dashboard' });
  }, [addTab]);

  return (
    <Layout>
      <div className="content">
        <h1>Centralized Security Hub</h1>
        <p>Phase 2: Web Portal Initialized</p>
        <div style={{ marginTop: '2rem', padding: '1rem', border: '1px solid var(--border)', borderRadius: '8px' }}>
          <h3>Welcome to the Investigation Portal</h3>
          <p>Use the sidebar to navigate or start a new investigation from the search bar (coming soon).</p>
        </div>
      </div>
    </Layout>
  )
}

export default App
