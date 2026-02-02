'use client';

import Link from 'next/link';
import { MainLayout } from '@/components/layout';
import { useJobs } from '@/hooks';
import { Card, CardContent, StatusBadge, ProgressBar, Button, Skeleton } from '@/components/ui';
import { formatRelativeTime, formatDuration } from '@/lib/utils';
import { Plus, Zap } from 'lucide-react';

export default function ScreeningPage() {
  const { data, isLoading } = useJobs({ jobType: 'screening', limit: 20 });

  return (
    <MainLayout title="Screening">
      <div className="space-y-6">
        {/* 헤더 */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <Zap className="w-6 h-6 text-yellow-500" />
              Screening Jobs
            </h1>
            <p className="mt-1 text-sm text-gray-500">
              표면-분자 흡착 스크리닝 작업을 관리합니다.
            </p>
          </div>
          <Link href="/screening/new">
            <Button icon={<Plus className="w-4 h-4" />}>
              New Screening
            </Button>
          </Link>
        </div>

        {/* Job 목록 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {isLoading ? (
            Array.from({ length: 6 }).map((_, i) => (
              <Card key={i}>
                <CardContent>
                  <Skeleton className="h-4 w-24 mb-2" />
                  <Skeleton className="h-6 w-16 mb-4" />
                  <Skeleton className="h-2 w-full mb-2" />
                  <Skeleton className="h-3 w-20" />
                </CardContent>
              </Card>
            ))
          ) : data?.jobs.length === 0 ? (
            <Card className="col-span-full">
              <CardContent className="text-center py-12">
                <Zap className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                <p className="text-gray-500">아직 스크리닝 작업이 없습니다.</p>
                <Link href="/screening/new" className="inline-block mt-4">
                  <Button variant="outline">첫 번째 스크리닝 시작</Button>
                </Link>
              </CardContent>
            </Card>
          ) : (
            data?.jobs.map((job) => (
              <Link key={job.job_id} href={`/jobs/${job.job_id}`}>
                <Card hover className="h-full">
                  <CardContent>
                    <div className="flex items-center justify-between mb-3">
                      <span className="font-mono text-sm text-blue-500">{job.job_id}</span>
                      <StatusBadge status={job.status} />
                    </div>
                    <ProgressBar value={job.progress} size="sm" className="mb-3" />
                    <div className="flex justify-between text-xs text-gray-500">
                      <span>{formatRelativeTime(job.created_at)}</span>
                      <span>{formatDuration(job.started_at, job.completed_at)}</span>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))
          )}
        </div>
      </div>
    </MainLayout>
  );
}
