'use client';

import { useState } from 'react';
import { Plus, List, Calendar, FileText, RefreshCw, Trash2 } from 'lucide-react';
import Link from 'next/link';
import { useContentList, useDeleteContent } from '@/hooks/useContent';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { EmptyState } from '@/components/ui/empty-state';
import { Spinner } from '@/components/ui/spinner';
import { formatDate, cn } from '@/lib/utils';
import type { ContentItem } from '@contentflow/api-client';

type ContentStatus = 'all' | 'draft' | 'scheduled' | 'published' | 'failed';
type ViewMode = 'calendar' | 'list';

const statusVariant: Record<string, 'gray' | 'success' | 'warning' | 'error' | 'blue'> = {
  draft: 'gray', scheduled: 'blue', published: 'success', failed: 'error',
};

export default function ContentPage() {
  const [selectedStatus, setSelectedStatus] = useState<ContentStatus>('all');
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [page, setPage] = useState(1);

  const { data, isLoading, error, refetch } = useContentList({
    page, page_size: 20, status: selectedStatus === 'all' ? undefined : selectedStatus,
  });
  const deleteContent = useDeleteContent();

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this content?')) return;
    try { await deleteContent.mutateAsync(id); } catch (e) { console.error(e); }
  };

  const getPlatformIcon = (platform: string) => {
    const icons: Record<string, string> = { instagram: '📷', youtube: '▶️', tiktok: '🎵', twitter: '🐦', linkedin: '💼' };
    return icons[platform] || '📱';
  };

  const getContentTypeIcon = (type: string) => {
    const icons: Record<string, string> = { reel: '🎬', short: '⚡', post: '📝', carousel: '🖼️', story: '📖', video: '🎥' };
    return icons[type] || '📄';
  };

  const formatNumber = (num: number) => {
    if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
    return num.toString();
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Spinner size="lg" color="primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <EmptyState
          icon={<FileText />}
          iconColor="error"
          title="Failed to load content"
          description={error instanceof Error ? error.message : 'Something went wrong'}
          actions={<Button onClick={() => refetch()} leadingIcon={<RefreshCw className="h-4 w-4" />}>Retry</Button>}
        />
      </div>
    );
  }

  const content = data?.items || [];
  const total = data?.total || 0;

  const draftCount = content.filter((c) => c.status === 'draft').length;
  const scheduledCount = content.filter((c) => c.status === 'scheduled').length;
  const publishedCount = content.filter((c) => c.status === 'published').length;
  const totalViews = content.reduce((sum, c) => sum + (c.total_views || 0), 0);

  const statCards = [
    { label: 'Drafts', value: draftCount },
    { label: 'Scheduled', value: scheduledCount },
    { label: 'Published', value: publishedCount },
    { label: 'Total Views', value: formatNumber(totalViews) },
  ];

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-10 space-y-8 animate-fade-in">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="space-y-1">
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">
              Content
            </h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Manage and schedule your content across all platforms.
            </p>
          </div>
          <Button asChild variant="primary" size="md" leadingIcon={<Plus className="h-4 w-4" />}>
            <Link href="/content/create">Create Content</Link>
          </Button>
        </header>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {statCards.map((s) => (
            <Card key={s.label} className="p-5">
              <p className="text-2xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">{s.value}</p>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{s.label}</p>
            </Card>
          ))}
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-1 rounded-lg border border-gray-200 dark:border-gray-800 p-1">
            {(['all', 'draft', 'scheduled', 'published', 'failed'] as ContentStatus[]).map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => { setSelectedStatus(s); setPage(1); }}
                className={cn(
                  'rounded-md px-3 py-1.5 text-sm font-medium transition-colors capitalize',
                  selectedStatus === s
                    ? 'bg-brand-600 text-white'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                )}
              >
                {s}
              </button>
            ))}
          </div>
          <div className="flex gap-1">
            <Button variant={viewMode === 'list' ? 'primary' : 'secondary'} size="sm" leadingIcon={<List className="h-4 w-4" />} onClick={() => setViewMode('list')}>List</Button>
            <Button variant={viewMode === 'calendar' ? 'primary' : 'secondary'} size="sm" leadingIcon={<Calendar className="h-4 w-4" />} onClick={() => setViewMode('calendar')}>Calendar</Button>
          </div>
        </div>

        {viewMode === 'list' && (
          <div className="space-y-3">
            {content.length > 0 ? content.map((item: ContentItem) => (
              <Card key={item.id} className="transition-all duration-150 hover:shadow-sm">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3 min-w-0 flex-1">
                      <span className="text-2xl shrink-0">{getContentTypeIcon(item.content_type)}</span>
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2 mb-1">
                          <h3 className="font-semibold text-gray-900 dark:text-gray-50 truncate">{item.title}</h3>
                          <Badge variant={statusVariant[item.status] ?? 'gray'}>{item.status}</Badge>
                          <span className="text-xs text-gray-500 dark:text-gray-400">{item.content_type}</span>
                        </div>
                        <div className="flex flex-wrap items-center gap-4 text-sm mt-2">
                          <div className="flex items-center gap-1">
                            {item.platforms.map((p) => (
                              <span key={p} title={p}>{getPlatformIcon(p)}</span>
                            ))}
                          </div>
                          {item.published_at && (
                            <span className="text-gray-500 dark:text-gray-400">Published {formatDate(item.published_at)}</span>
                          )}
                          {item.scheduled_at && (
                            <span className="text-gray-500 dark:text-gray-400">Scheduled {formatDate(item.scheduled_at)}</span>
                          )}
                          {item.status === 'published' && (
                            <>
                              <span className="text-gray-500 dark:text-gray-400">{formatNumber(item.total_views)} views</span>
                              <span className="text-gray-500 dark:text-gray-400">{(item.engagement_rate * 100).toFixed(2)}% eng.</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-2 shrink-0">
                      <Button asChild variant="secondary" size="sm"><Link href={`/content/${item.id}`}>View</Link></Button>
                      {item.status === 'draft' && <Button variant="primary" size="sm">Schedule</Button>}
                    </div>
                  </div>
                </CardContent>
              </Card>
            )) : (
              <EmptyState
                icon={<FileText />}
                iconColor="brand"
                title="No content found"
                description={
                  selectedStatus === 'all'
                    ? 'Create your first piece of content to get started.'
                    : `No ${selectedStatus} content found.`
                }
                actions={
                  <Button asChild variant="primary" leadingIcon={<Plus className="h-4 w-4" />}>
                    <Link href="/content/create">Create Content</Link>
                  </Button>
                }
              />
            )}
          </div>
        )}

        {viewMode === 'calendar' && (
          <EmptyState
            icon={<Calendar />}
            iconColor="brand"
            title="Calendar view coming soon"
            description="Visual calendar with drag-and-drop scheduling will be available soon."
            actions={
              <Button variant="secondary" onClick={() => setViewMode('list')}>
                Switch to List View
              </Button>
            }
          />
        )}
      </div>
    </div>
  );
}
