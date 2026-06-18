/**
 * Schedule page — calendar/list view of scheduled content.
 */
'use client';

import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
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
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-start justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold mb-2 gradient-text">Schedule</h1>
            <p className="text-muted-foreground">
              Upcoming posts across all connected platforms.
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              variant={view === 'list' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setView('list')}
            >
              List
            </Button>
            <Button
              variant={view === 'week' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setView('week')}
            >
              Week
            </Button>
            <Button variant="ghost" size="sm" onClick={() => refetch()}>
              Refresh
            </Button>
          </div>
        </div>

        {isLoading && <p className="text-muted-foreground">Loading…</p>}
        {error && (
          <p className="text-error">
            Failed to load schedule: {(error as Error).message}
          </p>
        )}

        {!isLoading && !error && items.length === 0 && (
          <Card>
            <CardContent className="py-12 text-center">
              <div className="text-6xl mb-4">📅</div>
              <h3 className="text-xl font-semibold mb-2">Nothing scheduled</h3>
              <p className="text-muted-foreground">
                Schedule content from the Studio or Content Ideas to see it here.
              </p>
            </CardContent>
          </Card>
        )}

        {view === 'list' &&
          Object.entries(grouped).map(([day, dayItems]) => (
            <div key={day} className="mb-6">
              <h2 className="text-sm uppercase tracking-wide text-muted-foreground mb-3">
                {day}
              </h2>
              <div className="space-y-2">
                {dayItems.map((item) => (
                  <Card key={item.id}>
                    <CardContent className="p-4 flex items-center justify-between">
                      <div>
                        <div className="font-medium">{item.title}</div>
                        <div className="text-sm text-muted-foreground">
                          {formatRelativeTime(item.scheduled_at ?? item.created_at)}
                        </div>
                      </div>
                      <Badge variant="default">{item.platforms?.[0] ?? 'multi'}</Badge>
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
              <p className="text-muted-foreground">
                {items.length} posts queued. Calendar grid is coming — use list view for
                now.
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
