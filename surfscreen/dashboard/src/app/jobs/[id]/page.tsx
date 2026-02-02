'use client';

import { useParams, useRouter } from 'next/navigation';
import { useJob, useJobLogs } from '@/hooks';
import { MainLayout } from '@/components/layout';
import { Card, CardContent, CardHeader, StatusBadge, ProgressBar, Button, Spinner } from '@/components/ui';
import { formatDate, formatDuration, getJobTypeLabel, downloadFile } from '@/lib/utils';
import { api } from '@/lib/api';
import { ArrowLeft, Download, XCircle, FileText, RefreshCw } from 'lucide-react';
import { useState, useEffect, useRef } from 'react';
import toast from 'react-hot-toast';

export default function JobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.id as string;
  
  const { job, isLoading, mutate } = useJob(jobId);
  const { data: logsData } = useJobLogs(jobId, job?.status === 'running');
  
  const [cancelling, setCancelling] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const logsRef = useRef<HTMLTextAreaElement>(null);

  // 로그 자동 스크롤
  useEffect(() => {
    if (logsRef.current) {
      logsRef.current.scrollTop = logsRef.current.scrollHeight;
    }
  }, [logsData?.logs]);

  const handleCancel = async () => {
    if (!confirm('정말로 이 작업을 취소하시겠습니까?')) return;
    
    setCancelling(true);
    try {
      await api.cancelJob(jobId);
      toast.success('작업이 취소되었습니다.');
      mutate();
    } catch (error) {
      toast.error('작업 취소에 실패했습니다.');
    } finally {
      setCancelling(false);
    }
  };

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const blob = await api.downloadJobResults(jobId);
      downloadFile(blob, `${jobId}_results.zip`);
      toast.success('다운로드를 시작합니다.');
    } catch (error) {
      toast.error('다운로드에 실패했습니다.');
    } finally {
      setDownloading(false);
    }
  };

  if (isLoading) {
    return (
      <MainLayout title="Job Detail">
        <div className="flex items-center justify-center h-64">
          <Spinner size="lg" />
        </div>
      </MainLayout>
    );
  }

  if (!job) {
    return (
      <MainLayout title="Job Not Found">
        <div className="text-center py-12">
          <p className="text-gray-500">작업을 찾을 수 없습니다.</p>
          <Button variant="outline" className="mt-4" onClick={() => router.push('/jobs')}>
            목록으로 돌아가기
          </Button>
        </div>
      </MainLayout>
    );
  }

  const canCancel = job.status === 'pending' || job.status === 'running';
  const canDownload = job.status === 'completed';

  return (
    <MainLayout title={`Job: ${jobId}`}>
      <div className="space-y-6">
        {/* 헤더 */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-4">
            <Button variant="ghost" onClick={() => router.push('/jobs')} icon={<ArrowLeft className="w-4 h-4" />}>
              Back
            </Button>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-xl font-bold font-mono text-gray-900 dark:text-white">
                  {jobId}
                </h1>
                <StatusBadge status={job.status} />
              </div>
              <p className="text-sm text-gray-500">{getJobTypeLabel(job.job_type)}</p>
            </div>
          </div>
          <div className="flex gap-2">
            {canCancel && (
              <Button
                variant="danger"
                onClick={handleCancel}
                loading={cancelling}
                icon={<XCircle className="w-4 h-4" />}
              >
                Cancel
              </Button>
            )}
            {canDownload && (
              <Button
                variant="primary"
                onClick={handleDownload}
                loading={downloading}
                icon={<Download className="w-4 h-4" />}
              >
                Download
              </Button>
            )}
          </div>
        </div>

        {/* 정보 카드 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <h3 className="font-semibold">Job Information</h3>
            </CardHeader>
            <CardContent>
              <dl className="space-y-3">
                <div className="flex justify-between">
                  <dt className="text-sm text-gray-500">ID</dt>
                  <dd className="text-sm font-mono text-gray-900 dark:text-white">{job.job_id}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-sm text-gray-500">Type</dt>
                  <dd className="text-sm text-gray-900 dark:text-white">{getJobTypeLabel(job.job_type)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-sm text-gray-500">Created</dt>
                  <dd className="text-sm text-gray-900 dark:text-white">{formatDate(job.created_at)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-sm text-gray-500">Started</dt>
                  <dd className="text-sm text-gray-900 dark:text-white">{formatDate(job.started_at)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-sm text-gray-500">Completed</dt>
                  <dd className="text-sm text-gray-900 dark:text-white">{formatDate(job.completed_at)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-sm text-gray-500">Duration</dt>
                  <dd className="text-sm text-gray-900 dark:text-white">{formatDuration(job.started_at, job.completed_at)}</dd>
                </div>
              </dl>
            </CardContent>
          </Card>

          {/* 진행률 */}
          <Card>
            <CardHeader>
              <h3 className="font-semibold">Progress</h3>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-sm text-gray-500">Progress</span>
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {job.progress.toFixed(1)}%
                    </span>
                  </div>
                  <ProgressBar
                    value={job.progress}
                    size="lg"
                    color={job.status === 'running' ? 'gradient' : 'blue'}
                    animated={job.status === 'running'}
                  />
                </div>
                
                {job.error_message && (
                  <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
                    <h4 className="text-sm font-medium text-red-500 mb-1">Error</h4>
                    <pre className="text-xs text-red-400 whitespace-pre-wrap overflow-auto max-h-32">
                      {job.error_message}
                    </pre>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 로그 */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <h3 className="font-semibold flex items-center gap-2">
                <FileText className="w-4 h-4" />
                Logs
              </h3>
              <span className="text-xs text-gray-500">
                {logsData?.lines || 0} lines
              </span>
            </div>
          </CardHeader>
          <CardContent>
            <textarea
              ref={logsRef}
              readOnly
              value={logsData?.logs || 'No logs available.'}
              className="w-full h-64 p-4 font-mono text-xs bg-gray-900 text-gray-300 rounded-lg resize-none"
            />
          </CardContent>
        </Card>
      </div>
    </MainLayout>
  );
}
