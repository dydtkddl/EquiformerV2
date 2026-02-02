'use client';

import { useCallback, useEffect, useState } from 'react';
import { MainLayout } from '@/components/layout';
import { StatsCard, ServerStatus, QuickActions, RecentJobs } from '@/components/dashboard';
import { JobStatusPieChart, ThroughputLineChart, SuccessRateBarChart } from '@/components/charts';
import { useJobs, useHealth, useWebSocket } from '@/hooks';
import { Activity, CheckCircle, Clock, Zap, AlertCircle, Wifi, WifiOff } from 'lucide-react';
import { Card } from '@/components/ui';
import toast from 'react-hot-toast';

export default function DashboardPage() {
  const { data: jobs, isLoading: jobsLoading, mutate: refreshJobs } = useJobs({ limit: 100 });
  const { data: health, isLoading: healthLoading } = useHealth();
  
  // WebSocket for real-time updates
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const wsUrl = apiUrl.replace('http', 'ws') + '/ws/jobs';
  
  const [isWsEnabled, setIsWsEnabled] = useState(false);
  
  const handleJobUpdate = useCallback((message: { type: string; data: unknown }) => {
    if (message.type === 'job.completed' || message.type === 'job.failed') {
      const jobData = message.data as { job_id?: string; status?: string };
      const status = message.type === 'job.completed' ? 'completed' : 'failed';
      
      toast(
        `Job ${jobData.job_id?.slice(0, 8)}... ${status}`,
        {
          icon: status === 'completed' ? '✅' : '❌',
          duration: 4000,
        }
      );
      
      // Refresh jobs list
      refreshJobs();
    }
  }, [refreshJobs]);
  
  const { status: wsStatus, isConnected } = useWebSocket({
    url: wsUrl,
    autoConnect: isWsEnabled,
    autoReconnect: true,
    onMessage: handleJobUpdate,
    onOpen: () => {
      toast.success('Real-time updates connected', { duration: 2000 });
    },
    onClose: () => {
      if (isWsEnabled) {
        toast.error('Real-time updates disconnected', { duration: 2000 });
      }
    },
  });

  // 통계 계산
  const stats = {
    active: jobs?.jobs.filter((j) => j.status === 'running').length || 0,
    pending: jobs?.jobs.filter((j) => j.status === 'pending').length || 0,
    completed: jobs?.jobs.filter((j) => j.status === 'completed').length || 0,
    failed: jobs?.jobs.filter((j) => j.status === 'failed').length || 0,
    total: jobs?.total || 0
  };

  // Chart data
  const statusData = {
    pending: stats.pending,
    running: stats.active,
    completed: stats.completed,
    failed: stats.failed,
  };

  return (
    <MainLayout title="Dashboard">
      <div className="space-y-6">
        {/* 페이지 헤더 */}
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Dashboard
            </h1>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              SurfScreen 작업 현황 및 서버 상태를 확인하세요.
            </p>
          </div>
          
          {/* Real-time toggle */}
          <button
            onClick={() => setIsWsEnabled(!isWsEnabled)}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              isConnected
                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                : isWsEnabled
                ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
            }`}
          >
            {isConnected ? (
              <>
                <Wifi className="w-4 h-4" />
                Live
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4" />
                {isWsEnabled ? 'Connecting...' : 'Offline'}
              </>
            )}
          </button>
        </div>

        {/* 통계 카드 */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatsCard
            icon={<Activity className="w-5 h-5" />}
            label="Active Jobs"
            value={stats.active}
            color="blue"
          />
          <StatsCard
            icon={<Clock className="w-5 h-5" />}
            label="Pending"
            value={stats.pending}
            color="yellow"
          />
          <StatsCard
            icon={<CheckCircle className="w-5 h-5" />}
            label="Completed"
            value={stats.completed}
            color="green"
          />
          <StatsCard
            icon={<AlertCircle className="w-5 h-5" />}
            label="Failed"
            value={stats.failed}
            color="red"
          />
        </div>

        {/* 차트 그리드 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <JobStatusPieChart
            data={statusData}
            isLoading={jobsLoading}
          />
          <ThroughputLineChart
            isLoading={jobsLoading}
            timeRange="24h"
          />
          <SuccessRateBarChart
            isLoading={jobsLoading}
          />
          <Card className="p-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              System Overview
            </h3>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">Total Jobs Today</span>
                <span className="font-semibold text-gray-900 dark:text-white">{stats.total}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">Success Rate</span>
                <span className="font-semibold text-green-600">
                  {stats.total > 0
                    ? `${((stats.completed / stats.total) * 100).toFixed(1)}%`
                    : 'N/A'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">Queue Size</span>
                <span className="font-semibold text-gray-900 dark:text-white">
                  {stats.pending + stats.active}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">API Status</span>
                <span className={`font-semibold ${health?.status === 'ok' ? 'text-green-600' : 'text-red-600'}`}>
                  {health?.status || 'Unknown'}
                </span>
              </div>
            </div>
          </Card>
        </div>

        {/* 메인 컨텐츠 */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 최근 Jobs */}
          <div className="lg:col-span-2">
            <RecentJobs />
          </div>

          {/* 사이드 패널 */}
          <div className="space-y-6">
            <ServerStatus health={health} isLoading={healthLoading} />
            <QuickActions />
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
