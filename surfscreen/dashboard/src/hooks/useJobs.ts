import useSWR from 'swr';
import { api } from '@/lib/api';
import { POLLING_INTERVAL } from '@/lib/constants';
import { useSettingsStore } from '@/stores';
import type { JobStatus, JobType } from '@/types';

interface UseJobsOptions {
  status?: JobStatus;
  jobType?: JobType;
  limit?: number;
}

export function useJobs(options: UseJobsOptions = {}) {
  const pollingEnabled = useSettingsStore((s) => s.pollingEnabled);
  
  const key = ['jobs', options.status, options.jobType, options.limit].join('-');
  
  return useSWR(
    key,
    () => api.listJobs({
      status_filter: options.status,
      job_type: options.jobType,
      limit: options.limit || 100
    }),
    {
      refreshInterval: pollingEnabled ? POLLING_INTERVAL : 0,
      revalidateOnFocus: false
    }
  );
}
