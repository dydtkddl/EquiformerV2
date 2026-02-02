'use client';

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { Card } from '@/components/ui';
import { Skeleton } from '@/components/ui';

interface ThroughputDataPoint {
  time: string;
  submitted: number;
  completed: number;
  failed: number;
}

interface ThroughputLineChartProps {
  data?: ThroughputDataPoint[];
  isLoading?: boolean;
  className?: string;
  timeRange?: '1h' | '24h' | '7d' | '30d';
}

export function ThroughputLineChart({
  data,
  isLoading = false,
  className = '',
  timeRange = '24h',
}: ThroughputLineChartProps) {
  if (isLoading) {
    return (
      <Card className={className}>
        <div className="p-4">
          <Skeleton className="h-6 w-48 mb-4" />
          <Skeleton className="h-64 w-full" />
        </div>
      </Card>
    );
  }

  // Generate sample data if not provided
  const chartData: ThroughputDataPoint[] = data ?? generateSampleData(timeRange);

  if (chartData.length === 0) {
    return (
      <Card className={className}>
        <div className="p-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Throughput Over Time
          </h3>
          <div className="h-64 flex items-center justify-center text-gray-500 dark:text-gray-400">
            No throughput data available
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <div className="p-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Throughput Over Time
          </h3>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            Last {timeRange}
          </span>
        </div>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={{ top: 5, right: 30, left: 0, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
              <XAxis
                dataKey="time"
                tick={{ fontSize: 12 }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                tick={{ fontSize: 12 }}
                tickLine={false}
                axisLine={false}
                width={40}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(0, 0, 0, 0.8)',
                  border: 'none',
                  borderRadius: '8px',
                  color: '#fff',
                }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="submitted"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={false}
                name="Submitted"
              />
              <Line
                type="monotone"
                dataKey="completed"
                stroke="#22c55e"
                strokeWidth={2}
                dot={false}
                name="Completed"
              />
              <Line
                type="monotone"
                dataKey="failed"
                stroke="#ef4444"
                strokeWidth={2}
                dot={false}
                name="Failed"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </Card>
  );
}

function generateSampleData(timeRange: string): ThroughputDataPoint[] {
  const points: ThroughputDataPoint[] = [];
  const now = new Date();
  
  let count = 24;
  let interval = 60; // minutes
  
  switch (timeRange) {
    case '1h':
      count = 12;
      interval = 5;
      break;
    case '24h':
      count = 24;
      interval = 60;
      break;
    case '7d':
      count = 7;
      interval = 24 * 60;
      break;
    case '30d':
      count = 30;
      interval = 24 * 60;
      break;
  }

  for (let i = count - 1; i >= 0; i--) {
    const time = new Date(now.getTime() - i * interval * 60 * 1000);
    const label =
      timeRange === '1h' || timeRange === '24h'
        ? time.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
        : time.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });

    points.push({
      time: label,
      submitted: Math.floor(Math.random() * 20) + 5,
      completed: Math.floor(Math.random() * 18) + 3,
      failed: Math.floor(Math.random() * 3),
    });
  }

  return points;
}

export default ThroughputLineChart;
