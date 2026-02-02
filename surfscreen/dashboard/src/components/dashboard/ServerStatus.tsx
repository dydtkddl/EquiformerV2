'use client';

import { cn } from '@/lib/utils';
import { Card, CardContent, CardHeader } from '@/components/ui';
import { Server, Cpu, HardDrive, CircleDot } from 'lucide-react';
import type { HealthStatus } from '@/types';

interface ServerStatusProps {
  health: HealthStatus | undefined;
  isLoading?: boolean;
}

export function ServerStatus({ health, isLoading }: ServerStatusProps) {
  const isConnected = !!health;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Server className="w-5 h-5 text-gray-400" />
          <h3 className="font-semibold text-gray-900 dark:text-white">
            API Server
          </h3>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* 연결 상태 */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">Status</span>
            <div className="flex items-center gap-2">
              <CircleDot
                className={cn(
                  'w-3 h-3',
                  isConnected ? 'text-green-500' : 'text-red-500'
                )}
              />
              <span
                className={cn(
                  'text-sm font-medium',
                  isConnected ? 'text-green-500' : 'text-red-500'
                )}
              >
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>

          {/* 버전 */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">Version</span>
            <span className="text-sm font-medium text-gray-900 dark:text-white">
              {health?.version || '-'}
            </span>
          </div>

          {/* 사용 가능 엔진 */}
          <div>
            <span className="text-sm text-gray-500">Engines</span>
            <div className="flex flex-wrap gap-2 mt-2">
              {health?.engines?.map((engine) => (
                <span
                  key={engine}
                  className="px-2 py-1 text-xs font-medium bg-blue-500/10 text-blue-500 rounded"
                >
                  {engine.toUpperCase()}
                </span>
              )) || (
                <span className="text-sm text-gray-400">-</span>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
