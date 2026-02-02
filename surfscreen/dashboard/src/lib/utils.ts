import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { formatDistanceToNow, format } from 'date-fns';
import { ko } from 'date-fns/locale';
import type { JobStatus } from '@/types';

// Tailwind 클래스 병합 유틸리티
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// 날짜 포맷팅
export function formatDate(date: string | null): string {
  if (!date) return '-';
  return format(new Date(date), 'yyyy-MM-dd HH:mm:ss');
}

export function formatRelativeTime(date: string | null): string {
  if (!date) return '-';
  return formatDistanceToNow(new Date(date), { addSuffix: true, locale: ko });
}

export function formatDuration(start: string | null, end: string | null): string {
  if (!start) return '-';
  const endTime = end ? new Date(end) : new Date();
  const ms = endTime.getTime() - new Date(start).getTime();
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  
  if (hours > 0) return `${hours}h ${minutes % 60}m`;
  if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
  return `${seconds}s`;
}

// 숫자 포맷팅
export function formatEnergy(value: number, decimals = 4): string {
  return value.toFixed(decimals);
}

export function formatPercent(value: number, decimals = 1): string {
  return `${value.toFixed(decimals)}%`;
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat().format(value);
}

// 상태 색상
export function getStatusColor(status: JobStatus): string {
  const colors: Record<JobStatus, string> = {
    pending: 'bg-yellow-500',
    running: 'bg-blue-500',
    completed: 'bg-green-500',
    failed: 'bg-red-500',
    cancelled: 'bg-gray-500'
  };
  return colors[status] || 'bg-gray-400';
}

export function getStatusTextColor(status: JobStatus): string {
  const colors: Record<JobStatus, string> = {
    pending: 'text-yellow-500',
    running: 'text-blue-500',
    completed: 'text-green-500',
    failed: 'text-red-500',
    cancelled: 'text-gray-500'
  };
  return colors[status] || 'text-gray-400';
}

export function getStatusBgColor(status: JobStatus): string {
  const colors: Record<JobStatus, string> = {
    pending: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    running: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    completed: 'bg-green-500/20 text-green-400 border-green-500/30',
    failed: 'bg-red-500/20 text-red-400 border-red-500/30',
    cancelled: 'bg-gray-500/20 text-gray-400 border-gray-500/30'
  };
  return colors[status] || 'bg-gray-500/20 text-gray-400';
}

// 파일 다운로드
export function downloadFile(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

// 파일 크기 포맷팅
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Job 타입 라벨
export function getJobTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    screening: '스크리닝',
    md: 'MD 시뮬레이션',
    analysis: '분석'
  };
  return labels[type] || type;
}

// 상태 라벨
export function getStatusLabel(status: JobStatus): string {
  const labels: Record<JobStatus, string> = {
    pending: '대기 중',
    running: '실행 중',
    completed: '완료',
    failed: '실패',
    cancelled: '취소됨'
  };
  return labels[status] || status;
}
