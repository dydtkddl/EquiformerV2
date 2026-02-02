import useSWR from 'swr';
import { api } from '@/lib/api';
import { POLLING_INTERVAL } from '@/lib/constants';
import type { Job } from '@/types';

export function useJob(jobId: string | null) {
  const { data, error, isLoading, mutate } = useSWR(
    jobId ? `job-${jobId}` : null,
    () => api.getJob(jobId!),
    {
      refreshInterval: (data: Job | undefined) => {
        // 실행 중이거나 대기 중일 때만 폴링
        if (data?.status === 'running' || data?.status === 'pending') {
          return POLLING_INTERVAL;
        }
        return 0;
      },
      revalidateOnFocus: false
    }
  );

  return { job: data, error, isLoading, mutate };
}

export function useJobLogs(jobId: string | null, enabled = true) {
  return useSWR(
    jobId && enabled ? `job-logs-${jobId}` : null,
    () => api.getJobLogs(jobId!, 200),
    {
      refreshInterval: POLLING_INTERVAL,
      revalidateOnFocus: false
    }
  );
}

export function useJobResult(jobId: string | null, enabled = true) {
  return useSWR(
    jobId && enabled ? `job-result-${jobId}` : null,
    () => api.getJobResult(jobId!),
    {
      revalidateOnFocus: false
    }
  );
}
