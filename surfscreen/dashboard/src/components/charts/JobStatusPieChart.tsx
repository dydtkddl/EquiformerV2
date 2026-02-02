'use client';

import React from 'react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from 'recharts';
import { Card } from '@/components/ui';
import { Skeleton } from '@/components/ui';

interface JobStatusData {
  name: string;
  value: number;
  color: string;
}

interface JobStatusPieChartProps {
  data?: {
    pending: number;
    running: number;
    completed: number;
    failed: number;
  };
  isLoading?: boolean;
  className?: string;
}

const STATUS_COLORS = {
  pending: '#f59e0b',   // amber-500
  running: '#3b82f6',   // blue-500
  completed: '#22c55e', // green-500
  failed: '#ef4444',    // red-500
};

const STATUS_LABELS = {
  pending: 'Pending',
  running: 'Running',
  completed: 'Completed',
  failed: 'Failed',
};

export function JobStatusPieChart({
  data,
  isLoading = false,
  className = '',
}: JobStatusPieChartProps) {
  if (isLoading) {
    return (
      <Card className={className}>
        <div className="p-4">
          <Skeleton className="h-6 w-40 mb-4" />
          <Skeleton className="h-64 w-full rounded-full" />
        </div>
      </Card>
    );
  }

  const chartData: JobStatusData[] = data
    ? Object.entries(data)
        .filter(([_, value]) => value > 0)
        .map(([key, value]) => ({
          name: STATUS_LABELS[key as keyof typeof STATUS_LABELS],
          value,
          color: STATUS_COLORS[key as keyof typeof STATUS_COLORS],
        }))
    : [];

  const total = chartData.reduce((sum, item) => sum + item.value, 0);

  if (chartData.length === 0 || total === 0) {
    return (
      <Card className={className}>
        <div className="p-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Job Status Distribution
          </h3>
          <div className="h-64 flex items-center justify-center text-gray-500 dark:text-gray-400">
            No jobs data available
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <div className="p-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Job Status Distribution
        </h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={90}
                paddingAngle={2}
                dataKey="value"
                label={({ name, percent }) =>
                  `${name} ${((percent ?? 0) * 100).toFixed(0)}%`
                }
                labelLine={false}
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(0, 0, 0, 0.8)',
                  border: 'none',
                  borderRadius: '8px',
                  color: '#fff',
                }}
              />
              <Legend
                verticalAlign="bottom"
                height={36}
                formatter={(value) => (
                  <span className="text-sm text-gray-600 dark:text-gray-300">
                    {value}
                  </span>
                )}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-2 text-center text-sm text-gray-500 dark:text-gray-400">
          Total: {total} jobs
        </div>
      </div>
    </Card>
  );
}

export default JobStatusPieChart;
