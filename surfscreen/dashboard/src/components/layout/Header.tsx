'use client';

import { useTheme } from '@/hooks';
import { cn } from '@/lib/utils';
import { Menu, Sun, Moon, RefreshCw, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui';

interface HeaderProps {
  onMenuClick: () => void;
  title?: string;
}

export function Header({ onMenuClick, title }: HeaderProps) {
  const { theme, toggleTheme, isDark } = useTheme();

  const handleRefresh = () => {
    window.location.reload();
  };

  return (
    <header className="sticky top-0 z-30 h-16 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
      <div className="flex items-center justify-between h-full px-4 lg:px-6">
        {/* 왼쪽 */}
        <div className="flex items-center gap-4">
          <button
            onClick={onMenuClick}
            className="lg:hidden p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-white"
          >
            <Menu className="w-5 h-5" />
          </button>
          {title && (
            <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
              {title}
            </h1>
          )}
        </div>

        {/* 오른쪽 */}
        <div className="flex items-center gap-2">
          {/* 새로고침 */}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRefresh}
            title="새로고침"
          >
            <RefreshCw className="w-4 h-4" />
          </Button>

          {/* 테마 토글 */}
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleTheme}
            title={isDark ? '라이트 모드' : '다크 모드'}
          >
            {isDark ? (
              <Sun className="w-4 h-4" />
            ) : (
              <Moon className="w-4 h-4" />
            )}
          </Button>

          {/* 문서 링크 */}
          <a
            href="/docs"
            target="_blank"
            rel="noopener noreferrer"
            className={cn(
              'hidden sm:flex items-center gap-1 px-3 py-1.5 text-sm',
              'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-white',
              'transition-colors'
            )}
          >
            Docs
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
    </header>
  );
}
