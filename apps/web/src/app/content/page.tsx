/**
 * Content Calendar Page
 * 
 * Visual calendar for scheduling and managing content across platforms
 */

'use client';

import { useState } from 'react';
import { useContentList, useDeleteContent } from '@/hooks/useContent';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatDate } from '@/lib/utils';
import Link from 'next/link';
import type { ContentItem } from '@contentflow/api-client';

type ContentStatus = 'all' | 'draft' | 'scheduled' | 'published' | 'failed';
type ViewMode = 'calendar' | 'list';

export default function ContentPage() {
  const [selectedStatus, setSelectedStatus] = useState<ContentStatus>('all');
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [page, setPage] = useState(1);

  // Fetch content
  const { data, isLoading, error, refetch } = useContentList({
    page,
    page_size: 20,
    status: selectedStatus === 'all' ? undefined : selectedStatus,
  });

  const deleteContent = useDeleteContent();

  // Handle delete
  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this content?')) return;
    
    try {
      await deleteContent.mutateAsync(id);
    } catch (error) {
      console.error('Failed to delete:', error);
    }
  };

  // Get status color
  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      draft: 'bg-gray-500',
      scheduled: 'bg-blue-500',
      published: 'bg-green-500',
      failed: 'bg-red-500',
    };
    return colors[status] || 'bg-gray-500';
  };

  // Get status badge variant
  const getStatusVariant = (status: string): 'default' | 'success' | 'warning' | 'error' => {
    const variants: Record<string, 'default' | 'success' | 'warning' | 'error'> = {
      draft: 'default',
      scheduled: 'warning',
      published: 'success',
      failed: 'error',
    };
    return variants[status] || 'default';
  };

  // Get platform icon
  const getPlatformIcon = (platform: string) => {
    const icons: Record<string, string> = {
      instagram: '📷',
      youtube: '▶️',
      tiktok: '🎵',
      twitter: '🐦',
      linkedin: '💼',
    };
    return icons[platform] || '📱';
  };

  // Get content type icon
  const getContentTypeIcon = (type: string) => {
    const icons: Record<string, string> = {
      reel: '🎬',
      short: '⚡',
      post: '📝',
      carousel: '🖼️',
      story: '📖',
      video: '🎥',
    };
    return icons[type] || '📄';
  };

  // Format number with K/M suffix
  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-tech mx-auto mb-4" />
              <p className="text-muted-foreground">Loading content...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="text-error text-5xl mb-4">⚠️</div>
              <h2 className="text-2xl font-bold mb-2">Failed to load content</h2>
              <p className="text-muted-foreground mb-4">
                {error instanceof Error ? error.message : 'Something went wrong'}
              </p>
              <Button onClick={() => refetch()}>Retry</Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const content = data?.items || [];
  const total = data?.total || 0;

  // Calculate stats
  const draftCount = content.filter(c => c.status === 'draft').length;
  const scheduledCount = content.filter(c => c.status === 'scheduled').length;
  const publishedCount = content.filter(c => c.status === 'published').length;
  const totalViews = content.reduce((sum, c) => sum + (c.total_views || 0), 0);

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-4xl font-bold gradient-text">Content Calendar</h1>
              <p className="text-muted-foreground mt-2">
                Manage and schedule your content across all platforms
              </p>
            </div>
            <Link href="/content/create">
              <Button size="lg">
                <span className="mr-2">+</span>
                Create Content
              </Button>
            </Link>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">{draftCount}</div>
                <div className="text-sm text-muted-foreground">Drafts</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">{scheduledCount}</div>
                <div className="text-sm text-muted-foreground">Scheduled</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">{publishedCount}</div>
                <div className="text-sm text-muted-foreground">Published</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">{formatNumber(totalViews)}</div>
                <div className="text-sm text-muted-foreground">Total Views</div>
              </CardContent>
            </Card>
          </div>

          {/* Filters */}
          <div className="flex items-center justify-between">
            <div className="flex gap-2">
              {(['all', 'draft', 'scheduled', 'published', 'failed'] as ContentStatus[]).map(status => (
                <Button
                  key={status}
                  variant={selectedStatus === status ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSelectedStatus(status)}
                >
                  {status.charAt(0).toUpperCase() + status.slice(1)}
                </Button>
              ))}
            </div>

            <div className="flex gap-2">
              <Button
                variant={viewMode === 'list' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('list')}
              >
                📋 List
              </Button>
              <Button
                variant={viewMode === 'calendar' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('calendar')}
              >
                📅 Calendar
              </Button>
            </div>
          </div>
        </div>

        {/* Content List */}
        {viewMode === 'list' && (
          <div className="space-y-4">
            {content.length > 0 ? (
              content.map((item: ContentItem) => (
                <Card key={item.id} className="card-hover">
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <span className="text-2xl">{getContentTypeIcon(item.content_type)}</span>
                          <div>
                            <h3 className="text-lg font-semibold">{item.title}</h3>
                            <div className="flex items-center gap-2 mt-1">
                              <Badge variant={getStatusVariant(item.status)}>
                                {item.status}
                              </Badge>
                              <span className="text-sm text-muted-foreground">
                                {item.content_type}
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center gap-4 mt-4">
                          {/* Platforms */}
                          <div className="flex items-center gap-2">
                            <span className="text-sm text-muted-foreground">Platforms:</span>
                            <div className="flex gap-1">
                              {item.platforms.map((platform) => (
                                <span key={platform} className="text-lg" title={platform}>
                                  {getPlatformIcon(platform)}
                                </span>
                              ))}
                            </div>
                          </div>

                          {/* Date */}
                          {item.published_at && (
                            <div className="flex items-center gap-2">
                              <span className="text-sm text-muted-foreground">Published:</span>
                              <span className="text-sm">{formatDate(item.published_at)}</span>
                            </div>
                          )}
                          {item.scheduled_at && (
                            <div className="flex items-center gap-2">
                              <span className="text-sm text-muted-foreground">Scheduled:</span>
                              <span className="text-sm">{formatDate(item.scheduled_at)}</span>
                            </div>
                          )}

                          {/* Stats */}
                          {item.status === 'published' && (
                            <>
                              <div className="flex items-center gap-2">
                                <span className="text-sm text-muted-foreground">Views:</span>
                                <span className="text-sm font-medium">{formatNumber(item.total_views)}</span>
                              </div>
                              <div className="flex items-center gap-2">
                                <span className="text-sm text-muted-foreground">Likes:</span>
                                <span className="text-sm font-medium">{formatNumber(item.total_likes)}</span>
                              </div>
                              <div className="flex items-center gap-2">
                                <span className="text-sm text-muted-foreground">Engagement:</span>
                                <span className="text-sm font-medium">
                                  {(item.engagement_rate * 100).toFixed(2)}%
                                </span>
                              </div>
                            </>
                          )}
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex gap-2">
                        <Link href={`/content/${item.id}`}>
                          <Button variant="outline" size="sm">
                            View
                          </Button>
                        </Link>
                        {item.status === 'draft' && (
                          <Button size="sm">
                            Schedule
                          </Button>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            ) : (
              <Card>
                <CardContent className="py-12">
                  <div className="text-center">
                    <div className="text-6xl mb-4">📝</div>
                    <h3 className="text-xl font-semibold mb-2">No content found</h3>
                    <p className="text-muted-foreground mb-6">
                      {selectedStatus === 'all' 
                        ? 'Create your first piece of content to get started'
                        : `No ${selectedStatus} content found`
                      }
                    </p>
                    <Link href="/content/create">
                      <Button>Create Content</Button>
                    </Link>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {/* Calendar View */}
        {viewMode === 'calendar' && (
          <Card>
            <CardContent className="py-12">
              <div className="text-center">
                <div className="text-6xl mb-4">📅</div>
                <h3 className="text-xl font-semibold mb-2">Calendar View Coming Soon</h3>
                <p className="text-muted-foreground mb-6">
                  Visual calendar with drag-and-drop scheduling will be available soon
                </p>
                <Button variant="outline" onClick={() => setViewMode('list')}>
                  Switch to List View
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
