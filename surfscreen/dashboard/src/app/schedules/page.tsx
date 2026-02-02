'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

interface Schedule {
  schedule_id: string;
  name: string;
  schedule_type: string;
  status: string;
  job_type: string;
  next_run: string | null;
  last_run: string | null;
  run_count: number;
  cron_expression?: string;
  interval_seconds?: number;
}

export default function SchedulesPage() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSchedules();
  }, []);

  async function fetchSchedules() {
    try {
      const res = await fetch('/api/v1/schedules');
      if (res.ok) {
        const data = await res.json();
        setSchedules(data.schedules || []);
      }
    } catch (error) {
      console.error('Failed to fetch schedules:', error);
    } finally {
      setLoading(false);
    }
  }

  async function toggleSchedule(id: string, currentStatus: string) {
    const action = currentStatus === 'active' ? 'pause' : 'resume';
    try {
      const res = await fetch(`/api/v1/schedules/${id}/${action}`, { method: 'POST' });
      if (res.ok) {
        fetchSchedules();
      }
    } catch (error) {
      console.error('Failed to toggle schedule:', error);
    }
  }

  async function deleteSchedule(id: string) {
    if (!confirm('Are you sure you want to delete this schedule?')) return;
    try {
      const res = await fetch(`/api/v1/schedules/${id}`, { method: 'DELETE' });
      if (res.ok) {
        fetchSchedules();
      }
    } catch (error) {
      console.error('Failed to delete schedule:', error);
    }
  }

  const statusColors: Record<string, string> = {
    active: 'bg-green-100 text-green-800',
    paused: 'bg-yellow-100 text-yellow-800',
    completed: 'bg-gray-100 text-gray-600',
    failed: 'bg-red-100 text-red-800',
  };

  const typeIcons: Record<string, string> = {
    cron: '⏰',
    interval: '🔄',
    once: '📅',
    dependency: '🔗',
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Job Schedules
        </h1>
        <Link
          href="/schedules/new"
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition"
        >
          + New Schedule
        </Link>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-indigo-500 border-t-transparent"></div>
        </div>
      ) : schedules.length === 0 ? (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          <p className="text-4xl mb-4">📅</p>
          <p>No schedules configured</p>
          <Link href="/schedules/new" className="text-indigo-600 hover:underline mt-2 inline-block">
            Create your first schedule
          </Link>
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-700 dark:text-gray-300">Name</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-700 dark:text-gray-300">Type</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-700 dark:text-gray-300">Schedule</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-700 dark:text-gray-300">Status</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-700 dark:text-gray-300">Next Run</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-700 dark:text-gray-300">Runs</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-700 dark:text-gray-300">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {schedules.map(schedule => (
                <tr key={schedule.schedule_id} className="hover:bg-gray-50 dark:hover:bg-gray-750">
                  <td className="px-4 py-3">
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white">{schedule.name}</p>
                      <p className="text-sm text-gray-500">{schedule.job_type}</p>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-lg" title={schedule.schedule_type}>
                      {typeIcons[schedule.schedule_type] || '📋'}
                    </span>
                    <span className="ml-2 text-sm text-gray-600 dark:text-gray-400 capitalize">
                      {schedule.schedule_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
                    {schedule.cron_expression || 
                     (schedule.interval_seconds && `Every ${schedule.interval_seconds}s`) ||
                     'One-time'}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs ${statusColors[schedule.status]}`}>
                      {schedule.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
                    {schedule.next_run 
                      ? new Date(schedule.next_run).toLocaleString()
                      : '-'
                    }
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
                    {schedule.run_count}
                  </td>
                  <td className="px-4 py-3 text-right space-x-2">
                    <button
                      onClick={() => toggleSchedule(schedule.schedule_id, schedule.status)}
                      className={`text-sm ${
                        schedule.status === 'active' 
                          ? 'text-yellow-600 hover:text-yellow-700' 
                          : 'text-green-600 hover:text-green-700'
                      }`}
                    >
                      {schedule.status === 'active' ? 'Pause' : 'Resume'}
                    </button>
                    <Link
                      href={`/schedules/${schedule.schedule_id}`}
                      className="text-sm text-indigo-600 hover:text-indigo-700"
                    >
                      Edit
                    </Link>
                    <button
                      onClick={() => deleteSchedule(schedule.schedule_id)}
                      className="text-sm text-red-500 hover:text-red-600"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
