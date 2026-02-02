'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { useHealth } from '@/hooks';
import {
  Home,
  Zap,
  Activity,
  List,
  Settings,
  X,
  ChevronLeft,
  CircleDot
} from 'lucide-react';

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

const navItems = [
  { href: '/', label: 'Dashboard', icon: Home },
  { href: '/screening', label: 'Screening', icon: Zap },
  { href: '/md', label: 'MD Simulation', icon: Activity },
  { href: '/jobs', label: 'All Jobs', icon: List },
  { href: '/settings', label: 'Settings', icon: Settings },
];

export function Sidebar({ open, onClose }: SidebarProps) {
  const pathname = usePathname();
  const { data: health, error: healthError } = useHealth();

  const isConnected = health && !healthError;

  return (
    <>
      {/* 모바일 오버레이 */}
      {open && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* 사이드바 */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-64 bg-gray-900 border-r border-gray-800',
          'flex flex-col transition-transform duration-300',
          'lg:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* 헤더 */}
        <div className="flex items-center justify-between h-16 px-4 border-b border-gray-800">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <span className="text-lg font-bold text-white">SurfScreen</span>
          </Link>
          <button
            onClick={onClose}
            className="lg:hidden p-1 text-gray-400 hover:text-white"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 네비게이션 */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href || 
              (item.href !== '/' && pathname.startsWith(item.href));

            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => onClose()}
                className={cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium',
                  'transition-all duration-200',
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800'
                )}
              >
                <Icon className="w-5 h-5" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* 하단 - 연결 상태 */}
        <div className="p-4 border-t border-gray-800">
          <div className="flex items-center gap-2 text-sm">
            <CircleDot
              className={cn(
                'w-3 h-3',
                isConnected ? 'text-green-500' : 'text-red-500'
              )}
            />
            <span className="text-gray-400">
              {isConnected ? 'API Connected' : 'Disconnected'}
            </span>
          </div>
          {health && (
            <p className="mt-1 text-xs text-gray-500">
              v{health.version}
            </p>
          )}
        </div>
      </aside>
    </>
  );
}
