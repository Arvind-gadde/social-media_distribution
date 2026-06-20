'use client';

import { use } from 'react';
import { useRouter } from 'next/navigation';
import { Search, RefreshCw, ExternalLink, Sparkles } from 'lucide-react';
import { useCompetitor, useCompetitorContent, useCompetitorAnalysis, useRemoveCompetitor } from '@/hooks/useCompetitors';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { EmptyState } from '@/components/ui/empty-state';
import { Spinner } from '@/components/ui/spinner';
import { safeExternalUrl } from '@/lib/safe-redirect';
import {
  Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbLink, BreadcrumbSeparator, BreadcrumbPage,
} from '@/components/ui/breadcrumb';

const getPlatformIcon = (platform: string) => {
  const icons: Record<string, string> = { instagram: '📷', youtube: '▶️', tiktok: '🎵', twitter: '🐦', linkedin: '💼', Instagram: '📷', YouTube: '▶️', TikTok: '🎵', Twitter: '🐦' };
  return icons[platform] || '📱';
};

const getContentTypeIcon = (type: string) => {
  const icons: Record<string, string> = { reel: '🎬', carousel: '🖼️', post: '📝', story: '📖' };
  return icons[type] || '📄';
};

const formatNumber = (num: number) => {
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
  return num.toString();
};

export default function CompetitorDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();

  const { data: competitor, isLoading, error, refetch } = useCompetitor(id);
  const { data: contentData } = useCompetitorContent(id);
  const { data: analysis } = useCompetitorAnalysis(id);
  const removeCompetitor = useRemoveCompetitor();

  const handleRemove = async () => {
    if (!confirm('Are you sure you want to remove this competitor?')) return;
    try {
      await removeCompetitor.mutateAsync(id);
      router.push('/competitors');
    } catch (e) {
      console.error(e);
      alert('Failed to remove competitor');
    }
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Spinner size="lg" color="primary" />
      </div>
    );
  }

  if (error || !competitor) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <EmptyState
          icon={<Search />}
          iconColor="error"
          title="Failed to load competitor"
          description={error instanceof Error ? error.message : 'Competitor not found'}
          actions={
            <div className="flex gap-2">
              <Button onClick={() => refetch()} leadingIcon={<RefreshCw className="h-4 w-4" />}>Retry</Button>
              <Button variant="secondary" onClick={() => router.push('/competitors')}>Back to Competitors</Button>
            </div>
          }
        />
      </div>
    );
  }

  const recentPosts = contentData?.items || [];

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-10 space-y-8 animate-fade-in">
        <header className="space-y-4">
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem><BreadcrumbLink href="/competitors">Competitors</BreadcrumbLink></BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage>{competitor.display_name || competitor.platform_username}</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>

          <div className="flex items-start gap-6">
            <div className="h-20 w-20 shrink-0 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-4xl overflow-hidden">
              {competitor.avatar_url
                ? <img src={competitor.avatar_url} alt={competitor.display_name} className="w-full h-full object-cover" />
                : '👤'}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 mb-1 flex-wrap">
                <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">
                  {competitor.display_name || competitor.platform_username}
                </h1>
                <Badge variant="gray">{getPlatformIcon(competitor.platform)} {competitor.platform}</Badge>
              </div>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">@{competitor.platform_username}</p>
              {competitor.profile_url && (
                <a
                  href={safeExternalUrl(competitor.profile_url) ?? '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-sm text-brand-600 dark:text-brand-400 hover:underline mb-3"
                >
                  View on {competitor.platform} <ExternalLink className="h-3.5 w-3.5" />
                </a>
              )}
              <div className="flex items-center gap-6 text-sm">
                <div>
                  <span className="font-semibold text-gray-900 dark:text-gray-50">{formatNumber(competitor.followers_count || 0)}</span>
                  <span className="text-gray-500 dark:text-gray-400"> followers</span>
                </div>
                <div>
                  <span className="font-semibold text-gray-900 dark:text-gray-50">{formatNumber(competitor.following_count || 0)}</span>
                  <span className="text-gray-500 dark:text-gray-400"> following</span>
                </div>
                <div>
                  <span className="font-semibold text-gray-900 dark:text-gray-50">{competitor.posts_count || 0}</span>
                  <span className="text-gray-500 dark:text-gray-400"> posts</span>
                </div>
              </div>
            </div>

            <div className="flex gap-2 shrink-0">
              <Button variant="secondary">🔔 Alerts</Button>
              <Button variant="destructive" onClick={handleRemove} disabled={removeCompetitor.isPending} loading={removeCompetitor.isPending}>
                {removeCompetitor.isPending ? 'Removing...' : 'Remove'}
              </Button>
            </div>
          </div>
        </header>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Avg Engagement', value: `${((competitor.avg_engagement_rate || 0) * 100).toFixed(2)}%` },
            { label: 'Posts/Week', value: competitor.posting_frequency || 0 },
            { label: 'Last Tracked', value: competitor.last_tracked_at ? new Date(competitor.last_tracked_at).toLocaleDateString() : 'Never' },
            { label: 'Tracking Since', value: competitor.tracking_since ? new Date(competitor.tracking_since).toLocaleDateString() : 'Unknown' },
          ].map((s) => (
            <Card key={s.label} className="p-4">
              <p className="text-xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">{s.value}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{s.label}</p>
            </Card>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader><CardTitle>Recent Posts</CardTitle></CardHeader>
              <CardContent>
                {recentPosts.length > 0 ? (
                  <div className="space-y-3">
                    {recentPosts.map((post: any) => (
                      <div key={post.id} className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                        <div className="flex items-center gap-4 flex-1 min-w-0">
                          <span className="text-2xl shrink-0">{getContentTypeIcon(post.content_type)}</span>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-sm text-gray-900 dark:text-gray-50 truncate mb-0.5">
                              {post.caption?.substring(0, 50) || 'Untitled'}
                            </p>
                            <p className="text-xs text-gray-500 dark:text-gray-400">
                              Posted {post.posted_at ? new Date(post.posted_at).toLocaleDateString() : 'Unknown'}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-4 text-xs shrink-0">
                          <div className="text-center">
                            <p className="font-semibold text-gray-900 dark:text-gray-50">{formatNumber(post.views || 0)}</p>
                            <p className="text-gray-500 dark:text-gray-400">Views</p>
                          </div>
                          <div className="text-center">
                            <p className="font-semibold text-gray-900 dark:text-gray-50">{formatNumber(post.likes || 0)}</p>
                            <p className="text-gray-500 dark:text-gray-400">Likes</p>
                          </div>
                          <div className="text-center">
                            <p className="font-semibold text-brand-600 dark:text-brand-400">{((post.engagement_rate || 0) * 100).toFixed(2)}%</p>
                            <p className="text-gray-500 dark:text-gray-400">Eng.</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-8">No posts tracked yet</p>
                )}
              </CardContent>
            </Card>

            {analysis && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-1.5">
                    <Sparkles className="h-4 w-4 text-brand-600 dark:text-brand-400" /> AI Analysis
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  {analysis.content_gaps && analysis.content_gaps.length > 0 && (
                    <div className="rounded-lg bg-brand-50 dark:bg-brand-950/40 border border-brand-200 dark:border-brand-800 p-3">
                      <p className="font-medium text-brand-700 dark:text-brand-300 mb-2">💡 Content Opportunities</p>
                      <ul className="list-disc list-inside space-y-1 text-gray-600 dark:text-gray-400">
                        {analysis.content_gaps.map((gap: string, i: number) => <li key={i}>{gap}</li>)}
                      </ul>
                    </div>
                  )}
                  {analysis.why_it_worked && (
                    <div className="rounded-lg bg-success-50 dark:bg-success-950/40 border border-success-200 dark:border-success-800 p-3">
                      <p className="font-medium text-success-700 dark:text-success-400 mb-1">✓ What's Working</p>
                      <p className="text-gray-600 dark:text-gray-400">{analysis.why_it_worked}</p>
                    </div>
                  )}
                  {analysis.topics && analysis.topics.length > 0 && (
                    <div className="rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-3">
                      <p className="font-medium text-gray-900 dark:text-gray-50 mb-2">📊 Top Topics</p>
                      <div className="flex flex-wrap gap-1.5">
                        {analysis.topics.map((topic: string, i: number) => <Badge key={i} variant="gray" size="sm">{topic}</Badge>)}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader><CardTitle>Tracking Info</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500 dark:text-gray-400">Status</span>
                  <Badge variant={competitor.is_active ? 'success' : 'gray'}>
                    {competitor.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500 dark:text-gray-400">Platform</span>
                  <span className="font-semibold text-sm text-gray-900 dark:text-gray-50">{competitor.platform}</span>
                </div>
                {competitor.niche_id && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-500 dark:text-gray-400">Niche</span>
                    <Badge variant="gray">Same as yours</Badge>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>Quick Stats</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                {[
                  { label: 'Followers', value: formatNumber(competitor.followers_count || 0) },
                  { label: 'Following', value: formatNumber(competitor.following_count || 0) },
                  { label: 'Posts', value: competitor.posts_count || 0 },
                ].map((s) => (
                  <div key={s.label} className="flex items-center justify-between">
                    <span className="text-sm text-gray-500 dark:text-gray-400">{s.label}</span>
                    <span className="font-semibold text-sm text-gray-900 dark:text-gray-50">{s.value}</span>
                  </div>
                ))}
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500 dark:text-gray-400">Engagement</span>
                  <span className="font-semibold text-sm text-brand-600 dark:text-brand-400">
                    {((competitor.avg_engagement_rate || 0) * 100).toFixed(2)}%
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>Actions</CardTitle></CardHeader>
              <CardContent className="space-y-2">
                <Button className="w-full" variant="secondary">View Full Report</Button>
                <Button className="w-full" variant="secondary">Refresh Data</Button>
                {competitor.profile_url && (
                  <Button
                    className="w-full"
                    variant="secondary"
                    leadingIcon={<ExternalLink className="h-4 w-4" />}
                    onClick={() => {
                      const u = safeExternalUrl(competitor.profile_url);
                      if (u) window.open(u, '_blank', 'noopener,noreferrer');
                    }}
                  >
                    Open Profile
                  </Button>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
