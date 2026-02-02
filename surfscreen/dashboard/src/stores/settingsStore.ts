import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SettingsState {
  // Theme
  theme: 'dark' | 'light' | 'system';
  
  // API Settings
  apiUrl: string;
  apiKey: string;
  
  // Defaults
  defaultEngine: string;
  defaultDevice: string;
  
  // Polling
  pollingEnabled: boolean;
  pollingInterval: number;
  
  // Actions
  setTheme: (theme: 'dark' | 'light' | 'system') => void;
  setApiUrl: (url: string) => void;
  setApiKey: (key: string) => void;
  setDefaultEngine: (engine: string) => void;
  setDefaultDevice: (device: string) => void;
  setPollingEnabled: (enabled: boolean) => void;
  setPollingInterval: (interval: number) => void;
  reset: () => void;
}

const defaultState = {
  theme: 'dark' as const,
  apiUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  apiKey: process.env.NEXT_PUBLIC_API_KEY || '',
  defaultEngine: 'mace',
  defaultDevice: 'cuda',
  pollingEnabled: true,
  pollingInterval: 5000
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      ...defaultState,
      
      setTheme: (theme) => set({ theme }),
      setApiUrl: (apiUrl) => set({ apiUrl }),
      setApiKey: (apiKey) => set({ apiKey }),
      setDefaultEngine: (defaultEngine) => set({ defaultEngine }),
      setDefaultDevice: (defaultDevice) => set({ defaultDevice }),
      setPollingEnabled: (pollingEnabled) => set({ pollingEnabled }),
      setPollingInterval: (pollingInterval) => set({ pollingInterval }),
      reset: () => set(defaultState)
    }),
    {
      name: 'surfscreen-settings',
      version: 1,
    }
  )
);
