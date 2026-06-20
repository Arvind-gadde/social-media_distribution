'use client';

import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Calendar, RefreshCw, List } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { Spinner } from '@/components/ui/spinner';
import { listContent } from '@contentflow/api-client';
import type { ContentItem } from '@contentflow/api-client';
import { formatRelativeTime } from '@/lib/utils';

type ViewMode = 'list' | 'week';

export default function SchedulePage() {
  const [view, setView] = useState<ViewMode>('list');

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['schedule-content'],
    queryFn: () => listContent({ status: 'scheduled', page_size: 100 }),
  });

  const items: ContentItem[] = (data?.items ?? []).slice().sort((a, b) =>
    (a.scheduled_at ?? '').localeCompare(b.scheduled_at ?? ''),
  );

  const grouped = groupByDay(items);

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-10 space-y-8 animate-fade-in">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="space-y-1">
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">
              Schedule
            </h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Upcoming posts across all connected platforms.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant={view === 'list' ? 'primary' : 'secondary'}
              size="sm"
              leadingIcon={<List className="h-4 w-4" />}
              onClick={() => setView('list')}
            >
              List
            </Button>
            <Button
              variant={view === 'week' ? 'primary' : 'secondary'}
              size="sm"
              leadingIcon={<Calendar className="h-4 w-4" />}
              onClick={() => setView('week')}
            >
              Week
            </Button>
            <Button
              variant="tertiary"
              size="sm"
              leadingIcon={<RefreshCw className="h-4 w-4" />}
              onClick={() => refetch()}
            >
              Refresh
            </Button>
          </div>
        </header>

        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <Spinner size="lg" color="primary" />
          </div>
        )}

        {error && (
          <p className="text-sm text-error-600 dark:text-error-400">
            Failed to load schedule: {(error as Error).message}
          </p>
        )}

        {!isLoading && !error && items.length === 0 && (
          <EmptyState
            icon={<Calendar />}
            iconColor="brand"
            title="Nothing scheduled"
            description="Schedule content from the Studio or Content Ideas to see it here."
          />
        )}

        {view === 'list' &&
          Object.entries(grouped).map(([day, dayItems]) => (
            <div key={day} className="space-y-2">
              <h2 className="text-xs font-medium uppercase tracking-widest text-gray-500 dark:text-gray-400">
                {day}
              </h2>
              <div className="space-y-2">
                {dayItems.map((item) => (
                  <Card key={item.id}>
                    <CardContent className="p-4 flex items-center justify-between">
                      <div>
                        <div className="font-medium text-gray-900 dark:text-gray-50">
                          {item.title}
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          {formatRelativeTime(item.scheduled_at ?? item.created_at)}
                        </div>
                      </div>
                      <Badge variant="gray">{item.platforms?.[0] ?? 'multi'}</Badge>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          ))}

        {view === 'week' && (
          <Card>
            <CardHeader>
              <CardTitle>Week view</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {items.length} posts queued. Calendar grid is coming — use list view for now.
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

function groupByDay(items: ContentItem[]): Record<string, ContentItem[]> {
  const acc: Record<string, ContentItem[]> = {};
  for (const item of items) {
    const when = item.scheduled_at ?? item.created_at;
    const day = new Date(when).toDateString();
    (acc[day] ??= []).push(item);
  }
  return acc;
}
