import { create } from 'zustand';

export interface Tab {
  id: string;
  title: string;
  isActive: boolean;
  queryState?: any;
}

interface TabState {
  tabs: Tab[];
  fetchTabs: () => Promise<void>;
  addTab: (tab: Omit<Tab, 'isActive'>) => Promise<void>;
  removeTab: (id: string) => Promise<void>;
  setActiveTab: (id: string) => void;
  updateTabState: (id: string, title: string, queryState: any) => Promise<void>;
}

export const useTabStore = create<TabState>((set) => ({
  tabs: [],

  fetchTabs: async () => {
    try {
      const response = await fetch('/api/users/me/tabs', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (response.ok) {
        const tabs = await response.json();
        // Backend uses query_state, frontend uses queryState
        const formattedTabs = tabs.map((t: any) => ({
          id: t.id,
          title: t.title,
          isActive: t.is_active,
          queryState: t.query_state ? JSON.parse(t.query_state) : {}
        }));
        set({ tabs: formattedTabs });
      }
    } catch (error) {
      console.error('Failed to fetch tabs:', error);
    }
  },

  addTab: async (tab) => {
    try {
      const response = await fetch('/api/queries', {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const { query_id } = await response.json();
        set((state) => {
          const deactivatedTabs = state.tabs.map((t) => ({ ...t, isActive: false }));
          return {
            tabs: [...deactivatedTabs, { id: query_id, title: tab.title, isActive: true, queryState: {} }],
          };
        });
      }
    } catch (error) {
      console.error('Failed to create tab:', error);
    }
  },

  removeTab: async (id) => {
    try {
      await fetch(`/api/queries/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });

      set((state) => {
        const tabToRemove = state.tabs.find((t) => t.id === id);
        if (!tabToRemove) return state;

        const remainingTabs = state.tabs.filter((t) => t.id !== id);
        
        if (tabToRemove.isActive && remainingTabs.length > 0) {
          return {
            tabs: remainingTabs.map((t, index) => ({
              ...t,
              isActive: index === 0,
            })),
          };
        }

        return {
          tabs: remainingTabs,
        };
      });
    } catch (error) {
      console.error('Failed to remove tab:', error);
    }
  },

  setActiveTab: (id) => {
    set((state) => ({
      tabs: state.tabs.map((t) => ({
        ...t,
        isActive: t.id === id,
      })),
    }));
  },

  updateTabState: async (id, title, queryState) => {
    try {
      await fetch(`/api/queries/${id}`, {
        method: 'PUT',
        headers: { 
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ title, query_state: queryState })
      });

      set((state) => ({
        tabs: state.tabs.map((t) => 
          t.id === id ? { ...t, title, queryState } : t
        ),
      }));
    } catch (error) {
      console.error('Failed to update tab state:', error);
    }
  }
}));
