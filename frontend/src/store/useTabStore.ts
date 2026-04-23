import { create } from 'zustand';

export interface Tab {
  id: string;
  title: string;
  isActive: boolean;
}

interface TabState {
  tabs: Tab[];
  addTab: (tab: Omit<Tab, 'isActive'>) => void;
  removeTab: (id: string) => void;
  setActiveTab: (id: string) => void;
}

export const useTabStore = create<TabState>((set) => ({
  tabs: [],

  addTab: (tab) => {
    set((state) => {
      // Deactivate all existing tabs
      const deactivatedTabs = state.tabs.map((t) => ({ ...t, isActive: false }));
      // Check if tab already exists to avoid duplicates
      const exists = state.tabs.some((t) => t.id === tab.id);
      
      if (exists) {
        // If it exists, just make it active
        return {
          tabs: state.tabs.map((t) => ({
            ...t,
            isActive: t.id === tab.id,
          })),
        };
      }

      return {
        tabs: [...deactivatedTabs, { ...tab, isActive: true }],
      };
    });
  },

  removeTab: (id) => {
    set((state) => {
      const tabToRemove = state.tabs.find((t) => t.id === id);
      if (!tabToRemove) return state;

      const remainingTabs = state.tabs.filter((t) => t.id !== id);
      
      // If we removed the active tab, we must set a new active tab if available
      if (tabToRemove.isActive && remainingTabs.length > 0) {
        return {
          tabs: remainingTabs.map((t, index) => ({
            ...t,
            isActive: index === 0, // Fallback to first available
          })),
        };
      }

      return {
        tabs: remainingTabs,
      };
    });
  },

  setActiveTab: (id) => {
    set((state) => ({
      tabs: state.tabs.map((t) => ({
        ...t,
        isActive: t.id === id,
      })),
    }));
  },
}));
