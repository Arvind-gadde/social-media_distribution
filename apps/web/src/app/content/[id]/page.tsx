'use client';

import { use } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, RefreshCw, FileText, BarChart2, Sparkles } from 'lucide-react';
import { useContent, useDeleteContent, useUpdateContent } from '@/hooks/useContent';
import { useContentAnalytics } from '@/hooks/useAnalytics';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { EmptyState } from '@/components/ui/empty-state';
import { Spinner } from '@/components/ui/spinner';
import { cn } from '@/lib/utils';
import {
  Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbLink, BreadcrumbSeparator, BreadcrumbPage,
} from '@/components/ui/breadcrumb';

const statusVariant: Record<string, 'gray' | 'success' | 'warning' | 'error' | 'blue'> = {
  draft: 'gray', scheduled: 'warning', published: 'success', failed: 'error',
};

const getPlatformIcon = (platform: string) => {
  const icons: Record<string, string> = { Instagram: '📷', TikTok: '🎵', YouTube: '▶️', Twitter: '🐦', instagram: '📷', tiktok: '🎵', youtube: '▶️', twitter: '🐦' };
  return icons[platform] || '📱';
};

const formatNumber = (num: number) => {
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
  return num.toString();
};

const mockPlatformStats = [
  { platform: 'Instagram', views: 8920, likes: 520, comments: 42, shares: 18, engagement: 0.0651 },
  { platform: 'TikTok', views: 6500, likes: 372, comments: 25, shares: 16, engagement: 0.0635 },
];

export default function ContentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();

  const { data: content, isLoading, error, refetch } = useContent(id);
  const { data: analytics } = useContentAnalytics(id);
  const deleteContent = useDeleteContent();

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this content?')) return;
    try {
      await deleteContent.mutateAsync(id);
      router.push('/content');
    } catch (e) {
      console.error(e);
      alert('Failed to delete content');
    }
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Spinner size="lg" color="primary" />
      </div>
    );
  }

  if (error || !content) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <EmptyState
          icon={<FileText />}
          iconColor="error"
          title="Failed to load content"
          description={error instanceof Error ? error.message : 'Content not found'}
          actions={
            <div className="flex gap-2">
              <Button onClick={() => refetch()} leadingIcon={<RefreshCw className="h-4 w-4" />}>Retry</Button>
              <Button variant="secondary" onClick={() => router.push('/content')}>Back to Content</Button>
            </div>
          }
        />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-10 space-y-8 animate-fade-in">
        <header className="space-y-4">
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem><BreadcrumbLink href="/content">Content</BreadcrumbLink></BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem><BreadcrumbPage>{content.title || 'Untitled'}</BreadcrumbPage></BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>

          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="space-y-2">
              <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">
                {content.title || 'Untitled Content'}
              </h1>
              <div className="flex items-center gap-3 flex-wrap">
                <Badge variant={statusVariant[content.status] ?? 'gray'}>{content.status}</Badge>
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  {content.published_at
                    ? `Published ${new Date(content.published_at).toLocaleDateString()}`
                    : content.scheduled_at
                    ? `Scheduled for ${new Date(content.scheduled_at).toLocaleDateString()}`
                    : 'Draft'}
                </span>
              </div>
            </div>
            <div className="flex gap-2 shrink-0">
              <Button variant="secondary">Edit</Button>
              <Button variant="secondary">Duplicate</Button>
              <Button
                variant="destructive"
                onClick={handleDelete}
                disabled={deleteContent.isPending}
                loading={deleteContent.isPending}
              >
                {deleteContent.isPending ? 'Deleting...' : 'Delete'}
              </Button>
            </div>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main content */}
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader><CardTitle>Content Preview</CardTitle></CardHeader>
              <CardContent>
                <div className="aspect-[9/16] bg-gray-100 dark:bg-gray-800 rounded-lg flex items-center justify-center mb-4 max-h-64">
                  <div className="text-center">
                    <div className="text-5xl mb-2">🎬</div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Video Preview</p>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Caption</p>
                    <p className="text-sm text-gray-900 dark:text-gray-50">{content.caption || 'No caption'}</p>
                  </div>

                  {content.hashtags && content.hashtags.length > 0 && (
                    <div>
                      <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Hashtags</p>
                      <div className="flex flex-wrap gap-1.5">
                        {content.hashtags.map((tag: string, i: number) => (
                          <span key={i} className="text-xs text-brand-600 dark:text-brand-400">{tag}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  <div>
                    <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Platforms</p>
                    <div className="flex gap-2 flex-wrap">
                      {content.platforms?.map((platform: string, i: number) => (
                        <Badge key={i} variant="gray">{getPlatformIcon(platform)} {platform}</Badge>
                      ))}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {content.status === 'published' && (
              <Card>
                <CardHeader><CardTitle>Performance Analytics</CardTitle></CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    {[
                      { label: 'Views', value: formatNumber(content.total_views || 0) },
                      { label: 'Likes', value: formatNumber(content.total_likes || 0) },
                      { label: 'Comments', value: content.total_comments || 0 },
                      { label: 'Engagement', value: `${((content.engagement_rate || 0) * 100).toFixed(2)}%` },
                    ].map((stat) => (
                      <div key={stat.label} className="text-center p-4 bg-gray-100 dark:bg-gray-800 rounded-lg">
                        <p className="text-xl font-semibold text-gray-900 dark:text-gray-50">{stat.value}</p>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{stat.label}</p>
                      </div>
                    ))}
                  </div>

                  <div className="space-y-3">
                    <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Platform Breakdown</p>
                    {mockPlatformStats.map((stat, i) => (
                      <div key={i} className="flex items-center justify-between p-3 bg-gray-100 dark:bg-gray-800 rounded-lg">
                        <div className="flex items-center gap-3">
                          <span className="text-xl">{getPlatformIcon(stat.platform)}</span>
                          <div>
                            <p className="font-medium text-sm text-gray-900 dark:text-gray-50">{stat.platform}</p>
                            <p className="text-xs text-gray-500 dark:text-gray-400">{formatNumber(stat.views)} views</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="font-semibold text-sm text-gray-900 dark:text-gray-50">{(stat.engagement * 100).toFixed(2)}%</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">Engagement</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {content.status === 'published' && (
              <Card>
                <CardHeader><CardTitle>Top Comments</CardTitle></CardHeader>
                <CardContent>
                  {(content.topComments ?? []).length > 0 ? (
                    <div className="space-y-3">
                      {(content.topComments ?? []).map((comment: any, i: number) => (
                        <div key={i} className="p-3 bg-gray-100 dark:bg-gray-800 rounded-lg">
                          <div className="flex items-center justify-between mb-1.5">
                            <p className="font-medium text-sm text-gray-900 dark:text-gray-50">{comment.author}</p>
                            <p className="text-xs text-gray-500 dark:text-gray-400">❤️ {comment.likes}</p>
                          </div>
                          <p className="text-sm text-gray-700 dark:text-gray-300">{comment.text}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-6">No comments tracked yet</p>
                  )}
                </CardContent>
              </Card>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            <Card>
              <CardHeader><CardTitle>Quick Stats</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                {[
                  { label: 'Reach', value: formatNumber(content.reach || 0) },
                  { label: 'Impressions', value: formatNumber(content.impressions || 0) },
                  { label: 'Saves', value: formatNumber(content.total_saves || 0) },
                  { label: 'Shares', value: formatNumber(content.total_shares || 0) },
                ].map((stat) => (
                  <div key={stat.label} className="flex items-center justify-between">
                    <span className="text-sm text-gray-500 dark:text-gray-400">{stat.label}</span>
                    <span className="font-semibold text-sm text-gray-900 dark:text-gray-50">{stat.value}</span>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-1.5">
                  <Sparkles className="h-4 w-4 text-brand-600 dark:text-brand-400" /> AI Insights
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="p-3 bg-success-50 dark:bg-success-950/40 border border-success-200 dark:border-success-800 rounded-lg">
                  <p className="font-medium text-success-700 dark:text-success-400 mb-1">✓ Strong Performance</p>
                  <p className="text-gray-600 dark:text-gray-400">This content is performing 23% above your average engagement rate</p>
                </div>
                <div className="p-3 bg-brand-50 dark:bg-brand-950/40 border border-brand-200 dark:border-brand-800 rounded-lg">
                  <p className="font-medium text-brand-700 dark:text-brand-300 mb-1">💡 Recommendation</p>
                  <p className="text-gray-600 dark:text-gray-400">Create similar content about AI tools. This topic resonates well with your audience.</p>
                </div>
                <div className="p-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
                  <p className="font-medium text-gray-900 dark:text-gray-50 mb-1">📊 Best Time</p>
                  <p className="text-gray-500 dark:text-gray-400">Most engagement happened between 2–4 PM EST</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>Actions</CardTitle></CardHeader>
              <CardContent className="space-y-2">
                <Button className="w-full" variant="secondary">View Full Analytics</Button>
                <Button className="w-full" variant="secondary">Repost to Other Platforms</Button>
                <Button className="w-full" variant="secondary">Download Content</Button>
                <Button className="w-full" variant="secondary">Copy Link</Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
