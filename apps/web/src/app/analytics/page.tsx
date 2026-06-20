'use client';

import { useState } from 'react';
import { BarChart2, Download, RefreshCw, TrendingUp } from 'lucide-react';
import { useAnalyticsOverview } from '@/hooks/useAnalytics';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { Spinner } from '@/components/ui/spinner';
import { cn } from '@/lib/utils';

type TimeRange = '7d' | '30d' | '90d' | 'all';
type Platform = 'all' | 'instagram' | 'youtube' | 'tiktok' | 'twitter';

export default function AnalyticsPage() {
  const [timeRange, setTimeRange] = useState<TimeRange>('30d');
  const [selectedPlatform, setSelectedPlatform] = useState<Platform>('all');

  const getDateRange = () => {
    const end = new Date();
    const start = new Date();
    switch (timeRange) {
      case '7d': start.setDate(start.getDate() - 7); break;
      case '30d': start.setDate(start.getDate() - 30); break;
      case '90d': start.setDate(start.getDate() - 90); break;
      default: return {};
    }
    return { start_date: start.toISOString(), end_date: end.toISOString() };
  };

  const { data, isLoading, error, refetch } = useAnalyticsOverview({
    ...getDateRange(),
    platform: selectedPlatform === 'all' ? undefined : selectedPlatform,
    compare_previous: true,
  });

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
          icon={<BarChart2 />}
          iconColor="error"
          title="Failed to load analytics"
          description={error instanceof Error ? error.message : 'Something went wrong'}
          actions={
            <Button onClick={() => refetch()} leadingIcon={<RefreshCw className="h-4 w-4" />}>
              Retry
            </Button>
          }
        />
      </div>
    );
  }

  const formatNumber = (num: number) => {
    if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
    return num.toString();
  };

  const getPlatformIcon = (platform: string) => {
    const icons: Record<string, string> = { instagram: '📷', youtube: '▶️', tiktok: '🎵', twitter: '🐦' };
    return icons[platform] || '📱';
  };

  const getChangeColor = (change: number) =>
    change > 0 ? 'text-success-600 dark:text-success-400' : change < 0 ? 'text-error-600 dark:text-error-400' : 'text-gray-500 dark:text-gray-400';

  const getChangeIcon = (change: number) => (change > 0 ? '↑' : change < 0 ? '↓' : '→');

  const stats = {
    totalViews: data?.total_views ?? 0,
    engagementRate: data?.avg_engagement_rate ?? 0,
    followers: data?.total_followers ?? 0,
    avgViewDuration: 0,
  };

  const platformStats = (data?.platform_stats ?? []).map((p) => ({
    platform: p.platform,
    followers: p.followers ?? 0,
    posts: 0,
    engagement: p.engagement_rate ?? 0,
  }));

  const recentPosts = (data?.top_content ?? []).map((post) => ({
    id: post.id,
    title: post.title,
    platform: post.platform,
    postedAt: 'Recent',
    views: post.views ?? 0,
    likes: 0,
    comments: 0,
    engagement: post.engagement_rate ?? 0,
  }));

  const timeRangeLabels: Record<TimeRange, string> = {
    '7d': 'Last 7 Days', '30d': 'Last 30 Days', '90d': 'Last 90 Days', all: 'All Time',
  };

  const platformLabels: Record<Platform, string> = {
    all: 'All Platforms', instagram: '📷 Instagram', youtube: '▶️ YouTube', tiktok: '🎵 TikTok', twitter: '🐦 Twitter',
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-10 space-y-8 animate-fade-in">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="space-y-1">
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">
              Analytics
            </h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Track your performance across all platforms.
            </p>
          </div>
          <Button
            variant="secondary"
            leadingIcon={<Download className="h-4 w-4" />}
          >
            Export Report
          </Button>
        </header>

        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          <div className="flex gap-1 rounded-lg border border-gray-200 dark:border-gray-800 p-1">
            {(['7d', '30d', '90d', 'all'] as TimeRange[]).map((range) => (
              <button
                key={range}
                type="button"
                onClick={() => setTimeRange(range)}
                className={cn(
                  'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                  timeRange === range
                    ? 'bg-brand-600 text-white'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                )}
              >
                {timeRangeLabels[range]}
              </button>
            ))}
          </div>
          <div className="flex gap-1 rounded-lg border border-gray-200 dark:border-gray-800 p-1">
            {(['all', 'instagram', 'youtube', 'tiktok'] as Platform[]).map((platform) => (
              <button
                key={platform}
                type="button"
                onClick={() => setSelectedPlatform(platform)}
                className={cn(
                  'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                  selectedPlatform === platform
                    ? 'bg-brand-600 text-white'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                )}
              >
                {platformLabels[platform]}
              </button>
            ))}
          </div>
        </div>

        {/* KPI row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {[
            { label: 'Total Views', value: formatNumber(stats.totalViews), delta: '+12.5%', icon: '👁️' },
            { label: 'Engagement Rate', value: `${(stats.engagementRate * 100).toFixed(2)}%`, delta: '+2.3%', icon: '❤️' },
            { label: 'Total Followers', value: formatNumber(stats.followers), delta: '+1,240', icon: '👥' },
            { label: 'Avg Watch Time', value: `${stats.avgViewDuration}s`, delta: '+5s', icon: '⏱️' },
          ].map((kpi) => (
            <Card key={kpi.label} className="p-6">
              <div className="flex items-center justify-between mb-3">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{kpi.label}</p>
                <span className="text-xl">{kpi.icon}</span>
              </div>
              <p className="text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">{kpi.value}</p>
              <p className="mt-1 text-xs text-success-600 dark:text-success-400">{kpi.delta} vs last period</p>
            </Card>
          ))}
        </div>

        {/* Platform breakdown */}
        <Card>
          <CardHeader>
            <CardTitle>Platform Performance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {platformStats.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400 py-6 text-center">No platform data yet.</p>
              ) : platformStats.map((p) => (
                <div
                  key={p.platform}
                  className="flex items-center justify-between rounded-lg bg-gray-100 dark:bg-gray-800 px-4 py-3"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{getPlatformIcon(p.platform)}</span>
                    <div>
                      <p className="font-medium text-gray-900 dark:text-gray-50 capitalize">{p.platform}</p>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {formatNumber(p.followers)} followers · {p.posts} posts
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-semibold text-gray-900 dark:text-gray-50">
                      {(p.engagement * 100).toFixed(2)}%
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Engagement</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Top content */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Posts Performance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {recentPosts.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400 py-6 text-center">No posts yet.</p>
              ) : recentPosts.map((post) => (
                <div
                  key={post.id}
                  className="flex items-center justify-between rounded-lg bg-gray-100 dark:bg-gray-800 px-4 py-3"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="text-xl shrink-0">{getPlatformIcon(post.platform)}</span>
                    <div className="min-w-0">
                      <p className="font-medium text-gray-900 dark:text-gray-50 truncate">{post.title}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">{post.postedAt}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-6 text-sm shrink-0 ml-4">
                    {[
                      { label: 'Views', value: formatNumber(post.views) },
                      { label: 'Likes', value: formatNumber(post.likes) },
                      { label: 'Comments', value: String(post.comments) },
                    ].map((stat) => (
                      <div key={stat.label} className="text-center hidden sm:block">
                        <p className="font-semibold text-gray-900 dark:text-gray-50">{stat.value}</p>
                        <p className="text-gray-500 dark:text-gray-400">{stat.label}</p>
                      </div>
                    ))}
                    <div className="text-center">
                      <p className="font-semibold text-brand-600 dark:text-brand-400">
                        {(post.engagement * 100).toFixed(2)}%
                      </p>
                      <p className="text-gray-500 dark:text-gray-400">Engagement</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Growth chart placeholder */}
        <Card>
          <CardHeader>
            <CardTitle>Growth Over Time</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex h-64 items-center justify-center rounded-lg bg-gray-100 dark:bg-gray-800">
              <div className="text-center">
                <TrendingUp className="h-10 w-10 text-gray-400 dark:text-gray-600 mx-auto mb-3" />
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Interactive charts coming soon</p>
                <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                  Followers growth · Engagement trends · Views over time
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
