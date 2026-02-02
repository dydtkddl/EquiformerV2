'use client';

import Link from 'next/link';
import { Card, CardContent, CardHeader, Button } from '@/components/ui';
import { Zap, Activity, Plus } from 'lucide-react';

export function QuickActions() {
  return (
    <Card>
      <CardHeader>
        <h3 className="font-semibold text-gray-900 dark:text-white">
          Quick Actions
        </h3>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <Link href="/screening/new" className="block">
            <Button
              variant="outline"
              className="w-full justify-start gap-3"
              icon={<Zap className="w-4 h-4 text-yellow-500" />}
            >
              New Screening
            </Button>
          </Link>

          <Link href="/md/new" className="block">
            <Button
              variant="outline"
              className="w-full justify-start gap-3"
              icon={<Activity className="w-4 h-4 text-blue-500" />}
            >
              New MD Simulation
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
