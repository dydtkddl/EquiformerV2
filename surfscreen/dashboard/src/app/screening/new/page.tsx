'use client';

import { MainLayout } from '@/components/layout';
import { ScreeningForm } from '@/components/forms';
import { Zap } from 'lucide-react';

export default function NewScreeningPage() {
  return (
    <MainLayout title="New Screening">
      <div className="max-w-4xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Zap className="w-6 h-6 text-yellow-500" />
            New Screening Job
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            표면 구조와 분자 파일을 업로드하고 스크리닝 설정을 구성하세요.
          </p>
        </div>

        <ScreeningForm />
      </div>
    </MainLayout>
  );
}
