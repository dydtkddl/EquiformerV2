import useSWR from 'swr';
import { api } from '@/lib/api';
import { POLLING_INTERVAL } from '@/lib/constants';
import { useSettingsStore } from '@/stores';

export function useHealth() {
  const pollingEnabled = useSettingsStore((s) => s.pollingEnabled);
  
  return useSWR(
    'health',
    () => api.getHealth(),
    {
      refreshInterval: pollingEnabled ? POLLING_INTERVAL : 0,
      revalidateOnFocus: false,
      errorRetryCount: 3
    }
  );
}

export function useReadiness() {
  return useSWR(
    'readiness',
    () => api.getReadiness(),
    {
      revalidateOnFocus: false
    }
  );
}
