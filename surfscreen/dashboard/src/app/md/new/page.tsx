'use client';

import { MainLayout } from '@/components/layout';
import { MDForm } from '@/components/forms';
import { Activity } from 'lucide-react';

export default function NewMDPage() {
  return (
    <MainLayout title="New MD Simulation">
      <div className="max-w-4xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Activity className="w-6 h-6 text-blue-500" />
            New MD Simulation
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            흡착 구조 파일을 업로드하고 MD 시뮬레이션 설정을 구성하세요.
          </p>
        </div>

        <MDForm />
      </div>
    </MainLayout>
  );
}
