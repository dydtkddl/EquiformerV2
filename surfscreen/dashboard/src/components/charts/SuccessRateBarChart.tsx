'use client';

import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { Card } from '@/components/ui';
import { Skeleton } from '@/components/ui';

interface SuccessRateDataPoint {
  name: string;
  successRate: number;
  total: number;
}

interface SuccessRateBarChartProps {
  data?: SuccessRateDataPoint[];
  isLoading?: boolean;
  className?: string;
}

const getBarColor = (rate: number): string => {
  if (rate >= 90) return '#22c55e'; // green
  if (rate >= 70) return '#84cc16'; // lime
  if (rate >= 50) return '#f59e0b'; // amber
  return '#ef4444'; // red
};

export function SuccessRateBarChart({
  data,
  isLoading = false,
  className = '',
}: SuccessRateBarChartProps) {
  if (isLoading) {
    return (
      <Card className={className}>
        <div className="p-4">
          <Skeleton className="h-6 w-40 mb-4" />
          <Skeleton className="h-64 w-full" />
        </div>
      </Card>
    );
  }

  // Generate sample data if not provided
  const chartData: SuccessRateDataPoint[] = data ?? generateSampleData();

  if (chartData.length === 0) {
    return (
      <Card className={className}>
        <div className="p-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Success Rate by Day
          </h3>
          <div className="h-64 flex items-center justify-center text-gray-500 dark:text-gray-400">
            No success rate data available
          </div>
        </div>
      </Card>
    );
  }

  const avgRate =
    chartData.reduce((sum, d) => sum + d.successRate, 0) / chartData.length;

  return (
    <Card className={className}>
      <div className="p-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Success Rate by Day
          </h3>
          <span
            className={`text-sm font-medium ${avgRate >= 80 ? 'text-green-600' : avgRate >= 60 ? 'text-amber-600' : 'text-red-600'}`}
          >
            Avg: {avgRate.toFixed(1)}%
          </span>
        </div>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              margin={{ top: 5, right: 30, left: 0, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 12 }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fontSize: 12 }}
                tickLine={false}
                axisLine={false}
                width={40}
                tickFormatter={(value) => `${value}%`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(0, 0, 0, 0.8)',
                  border: 'none',
                  borderRadius: '8px',
                  color: '#fff',
                }}
              />
              <Bar dataKey="successRate" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={getBarColor(entry.successRate)}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </Card>
  );
}

function generateSampleData(): SuccessRateDataPoint[] {
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  return days.map((name) => ({
    name,
    successRate: Math.floor(Math.random() * 30) + 70, // 70-100%
    total: Math.floor(Math.random() * 50) + 20,
  }));
}

export default SuccessRateBarChart;
