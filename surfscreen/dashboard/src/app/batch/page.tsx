'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

interface BatchJob {
  batch_id: string;
  name: string;
  status: string;
  job_type: string;
  progress: {
    total: number;
    completed: number;
    failed: number;
    percentage: number;
  };
  created_at: string;
  completed_at?: string;
}

export default function BatchPage() {
  const [batches, setBatches] = useState<BatchJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    fetchBatches();
    const interval = setInterval(fetchBatches, 5000);
    return () => clearInterval(interval);
  }, []);

  async function fetchBatches() {
    try {
      const res = await fetch('/api/v1/batch');
      if (res.ok) {
        const data = await res.json();
        setBatches(data.batches || []);
      }
    } catch (error) {
      console.error('Failed to fetch batches:', error);
    } finally {
      setLoading(false);
    }
  }

  const filteredBatches = filter === 'all' 
    ? batches 
    : batches.filter(b => b.status === filter);

  const statusColors: Record<string, string> = {
    pending: 'bg-gray-100 text-gray-800',
    running: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    partial: 'bg-yellow-100 text-yellow-800',
    failed: 'bg-red-100 text-red-800',
    cancelled: 'bg-gray-100 text-gray-600',
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Batch Processing
        </h1>
        <Link
          href="/batch/new"
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition"
        >
          + New Batch
        </Link>
      </div>

      {/* Filter Tabs */}
      <div className="flex space-x-2 mb-6">
        {['all', 'running', 'completed', 'failed'].map(status => (
          <button
            key={status}
            onClick={() => setFilter(status)}
            className={`px-4 py-2 rounded-lg capitalize ${
              filter === status
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
            }`}
          >
            {status}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-indigo-500 border-t-transparent"></div>
        </div>
      ) : filteredBatches.length === 0 ? (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          <p>No batch jobs found</p>
          <Link href="/batch/new" className="text-indigo-600 hover:underline mt-2 inline-block">
            Create your first batch
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredBatches.map(batch => (
            <div
              key={batch.batch_id}
              className="bg-white dark:bg-gray-800 rounded-lg shadow p-4"
            >
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-white">
                    {batch.name || `Batch ${batch.batch_id.slice(0, 8)}`}
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {batch.job_type} • Created {new Date(batch.created_at).toLocaleString()}
                  </p>
                </div>
                <span className={`px-3 py-1 rounded-full text-sm ${statusColors[batch.status] || 'bg-gray-100'}`}>
                  {batch.status}
                </span>
              </div>

              {/* Progress Bar */}
              <div className="mb-2">
                <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-indigo-500 transition-all duration-300"
                    style={{ width: `${batch.progress.percentage}%` }}
                  ></div>
                </div>
              </div>

              <div className="flex justify-between text-sm">
                <span className="text-gray-600 dark:text-gray-400">
                  {batch.progress.completed}/{batch.progress.total} completed
                  {batch.progress.failed > 0 && (
                    <span className="text-red-500 ml-2">
                      ({batch.progress.failed} failed)
                    </span>
                  )}
                </span>
                <span className="text-gray-500 dark:text-gray-400">
                  {batch.progress.percentage.toFixed(1)}%
                </span>
              </div>

              <div className="mt-3 flex space-x-2">
                <Link
                  href={`/batch/${batch.batch_id}`}
                  className="text-sm text-indigo-600 hover:underline"
                >
                  View Details
                </Link>
                {batch.status === 'running' && (
                  <button className="text-sm text-red-500 hover:underline">
                    Cancel
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
