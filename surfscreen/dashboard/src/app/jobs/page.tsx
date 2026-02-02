'use client';

import Link from 'next/link';
import { useJobs } from '@/hooks';
import { MainLayout } from '@/components/layout';
import { Card, CardContent, StatusBadge, ProgressBar, Button, Skeleton, Select } from '@/components/ui';
import { formatRelativeTime, formatDuration, getJobTypeLabel } from '@/lib/utils';
import { Plus, RefreshCw, Download, Eye, XCircle } from 'lucide-react';
import { useState } from 'react';
import type { JobStatus, JobType } from '@/types';

export default function JobsPage() {
  const [statusFilter, setStatusFilter] = useState<JobStatus | ''>('');
  const [typeFilter, setTypeFilter] = useState<JobType | ''>('');

  const { data, isLoading, mutate } = useJobs({
    status: statusFilter || undefined,
    jobType: typeFilter || undefined,
    limit: 50
  });

  const statusOptions = [
    { value: '', label: '모든 상태' },
    { value: 'pending', label: '대기 중' },
    { value: 'running', label: '실행 중' },
    { value: 'completed', label: '완료' },
    { value: 'failed', label: '실패' },
    { value: 'cancelled', label: '취소됨' }
  ];

  const typeOptions = [
    { value: '', label: '모든 유형' },
    { value: 'screening', label: '스크리닝' },
    { value: 'md', label: 'MD 시뮬레이션' }
  ];

  return (
    <MainLayout title="Jobs">
      <div className="space-y-6">
        {/* 헤더 */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              All Jobs
            </h1>
            <p className="mt-1 text-sm text-gray-500">
              {data?.total || 0}개의 작업
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => mutate()} icon={<RefreshCw className="w-4 h-4" />}>
              새로고침
            </Button>
          </div>
        </div>

        {/* 필터 */}
        <Card>
          <CardContent>
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="w-full sm:w-48">
                <Select
                  label="상태"
                  options={statusOptions}
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value as JobStatus | '')}
                />
              </div>
              <div className="w-full sm:w-48">
                <Select
                  label="유형"
                  options={typeOptions}
                  value={typeFilter}
                  onChange={(e) => setTypeFilter(e.target.value as JobType | '')}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 테이블 */}
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Progress</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Duration</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {isLoading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i}>
                      <td className="px-6 py-4"><Skeleton className="h-4 w-16" /></td>
                      <td className="px-6 py-4"><Skeleton className="h-4 w-20" /></td>
                      <td className="px-6 py-4"><Skeleton className="h-5 w-16" /></td>
                      <td className="px-6 py-4"><Skeleton className="h-2 w-24" /></td>
                      <td className="px-6 py-4"><Skeleton className="h-4 w-20" /></td>
                      <td className="px-6 py-4"><Skeleton className="h-4 w-16" /></td>
                      <td className="px-6 py-4"><Skeleton className="h-8 w-20 ml-auto" /></td>
                    </tr>
                  ))
                ) : data?.jobs.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                      조건에 맞는 작업이 없습니다.
                    </td>
                  </tr>
                ) : (
                  data?.jobs.map((job) => (
                    <tr key={job.job_id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                      <td className="px-6 py-4">
                        <Link
                          href={`/jobs/${job.job_id}`}
                          className="font-mono text-sm text-blue-500 hover:text-blue-600"
                        >
                          {job.job_id}
                        </Link>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900 dark:text-white">
                        {getJobTypeLabel(job.job_type)}
                      </td>
                      <td className="px-6 py-4">
                        <StatusBadge status={job.status} />
                      </td>
                      <td className="px-6 py-4 w-32">
                        <div className="flex items-center gap-2">
                          <ProgressBar value={job.progress} size="sm" />
                          <span className="text-xs text-gray-500 w-10">
                            {job.progress.toFixed(0)}%
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {formatRelativeTime(job.created_at)}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {formatDuration(job.started_at, job.completed_at)}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <Link href={`/jobs/${job.job_id}`}>
                          <Button variant="ghost" size="sm" icon={<Eye className="w-4 h-4" />}>
                            View
                          </Button>
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </MainLayout>
  );
}
