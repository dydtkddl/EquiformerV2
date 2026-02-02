import Link from 'next/link';
import { Button } from '@/components/ui';
import { Home, SearchX } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 dark:bg-gray-950 p-4">
      <div className="max-w-md w-full text-center">
        <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-gray-500/20 flex items-center justify-center">
          <SearchX className="w-8 h-8 text-gray-500" />
        </div>
        
        <h1 className="text-6xl font-bold text-gray-900 dark:text-white mb-2">
          404
        </h1>
        
        <h2 className="text-xl font-semibold text-gray-700 dark:text-gray-300 mb-4">
          Page Not Found
        </h2>
        
        <p className="text-gray-500 dark:text-gray-400 mb-6">
          요청하신 페이지를 찾을 수 없습니다.
        </p>
        
        <Link href="/">
          <Button icon={<Home className="w-4 h-4" />}>
            Go Home
          </Button>
        </Link>
      </div>
    </div>
  );
}
