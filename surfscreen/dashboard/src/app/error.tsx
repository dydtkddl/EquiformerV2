'use client';

import { useEffect } from 'react';
import { Button } from '@/components/ui';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';
import Link from 'next/link';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Application error:', error);
  }, [error]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 dark:bg-gray-950 p-4">
      <div className="max-w-md w-full text-center">
        <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-red-500/20 flex items-center justify-center">
          <AlertTriangle className="w-8 h-8 text-red-500" />
        </div>
        
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Something went wrong!
        </h1>
        
        <p className="text-gray-500 dark:text-gray-400 mb-6">
          예기치 않은 오류가 발생했습니다. 다시 시도하거나 홈으로 돌아가세요.
        </p>

        {error.message && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-left">
            <p className="text-sm font-mono text-red-400">{error.message}</p>
          </div>
        )}
        
        <div className="flex justify-center gap-3">
          <Button variant="outline" onClick={reset} icon={<RefreshCw className="w-4 h-4" />}>
            Try Again
          </Button>
          <Link href="/">
            <Button icon={<Home className="w-4 h-4" />}>
              Go Home
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
