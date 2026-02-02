'use client';

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';

interface EnergyChartProps {
  data: Array<{ step: number; energy: number; temperature?: number }>;
  title?: string;
  height?: number;
  showTemperature?: boolean;
}

export function EnergyChart({
  data,
  title = 'Energy',
  height = 300,
  showTemperature = false
}: EnergyChartProps) {
  return (
    <div>
      {title && (
        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          {title}
        </h3>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis
            dataKey="step"
            stroke="#9CA3AF"
            fontSize={12}
            tickFormatter={(v) => `${v / 1000}k`}
          />
          <YAxis
            yAxisId="left"
            stroke="#9CA3AF"
            fontSize={12}
            tickFormatter={(v) => v.toFixed(2)}
          />
          {showTemperature && (
            <YAxis
              yAxisId="right"
              orientation="right"
              stroke="#9CA3AF"
              fontSize={12}
            />
          )}
          <Tooltip
            contentStyle={{
              backgroundColor: '#1F2937',
              border: '1px solid #374151',
              borderRadius: '8px',
              color: '#F9FAFB'
            }}
            labelFormatter={(label) => `Step: ${label}`}
          />
          <Legend />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="energy"
            stroke="#3B82F6"
            strokeWidth={2}
            dot={false}
            name="Energy (eV)"
          />
          {showTemperature && (
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="temperature"
              stroke="#F59E0B"
              strokeWidth={2}
              dot={false}
              name="Temperature (K)"
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
