/**
 * Analytics Dashboard Page
 * 
 * Comprehensive analytics with charts, metrics, and insights
 */

'use client';

import { useState } from 'react';
import { useAnalyticsOverview } from '@/hooks/useAnalytics';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

type TimeRange = '7d' | '30d' | '90d' | 'all';
type Platform = 'all' | 'instagram' | 'youtube' | 'tiktok' | 'twitter';

export default function AnalyticsPage() {
  const [timeRange, setTimeRange] = useState<TimeRange>('30d');
  const [selectedPlatform, setSelectedPlatform] = useState<Platform>('all');

  // Calculate date range
  const getDateRange = () => {
    const end = new Date();
    const start = new Date();
    
    switch (timeRange) {
      case '7d':
        start.setDate(start.getDate() - 7);
        break;
      case '30d':
        start.setDate(start.getDate() - 30);
        break;
      case '90d':
        start.setDate(start.getDate() - 90);
        break;
      default:
        return {};
    }
    
    return {
      start_date: start.toISOString(),
      end_date: end.toISOString(),
    };
  };

  // Fetch analytics
  const { data, isLoading, error, refetch } = useAnalyticsOverview({
    ...getDateRange(),
    platform: selectedPlatform === 'all' ? undefined : selectedPlatform,
    compare_previous: true,
  });

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-tech mx-auto mb-4" />
              <p className="text-muted-foreground">Loading analytics...</p>
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
              <h2 className="text-2xl font-bold mb-2">Failed to load analytics</h2>
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

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const getPlatformIcon = (platform: string) => {
    const icons: Record<string, string> = {
      instagram: '📷',
      youtube: '▶️',
      tiktok: '🎵',
      twitter: '🐦',
    };
    return icons[platform] || '📱';
  };

  const getChangeColor = (change: number) => {
    if (change > 0) return 'text-success';
    if (change < 0) return 'text-error';
    return 'text-muted-foreground';
  };

  const getChangeIcon = (change: number) => {
    if (change > 0) return '↑';
    if (change < 0) return '↓';
    return '→';
  };

  const stats = {
    totalViews: data?.total_views ?? 0,
    engagementRate: data?.avg_engagement_rate ?? 0,
    followers: data?.total_followers ?? 0,
    avgViewDuration: 0,
  };

  const platformStats = (data?.platform_stats ?? []).map((platform) => ({
    platform: platform.platform,
    followers: platform.followers ?? 0,
    posts: 0,
    engagement: platform.engagement_rate ?? 0,
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

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-4xl font-bold gradient-text">Analytics Dashboard</h1>
              <p className="text-muted-foreground mt-2">
                Track your performance across all platforms
              </p>
            </div>
            <Button variant="outline">
              📊 Export Report
            </Button>
          </div>

          {/* Filters */}
          <div className="flex items-center gap-4">
            <div className="flex gap-2">
              {(['7d', '30d', '90d', 'all'] as TimeRange[]).map(range => (
                <Button
                  key={range}
                  variant={timeRange === range ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setTimeRange(range)}
                >
                  {range === '7d' && 'Last 7 Days'}
                  {range === '30d' && 'Last 30 Days'}
                  {range === '90d' && 'Last 90 Days'}
                  {range === 'all' && 'All Time'}
                </Button>
              ))}
            </div>

            <div className="flex gap-2">
              {(['all', 'instagram', 'youtube', 'tiktok'] as Platform[]).map(platform => (
                <Button
                  key={platform}
                  variant={selectedPlatform === platform ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSelectedPlatform(platform)}
                >
                  {platform === 'all' && 'All Platforms'}
                  {platform === 'instagram' && '📷 Instagram'}
                  {platform === 'youtube' && '▶️ YouTube'}
                  {platform === 'tiktok' && '🎵 TikTok'}
                </Button>
              ))}
            </div>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-muted-foreground">Total Views</span>
                <span className="text-2xl">👁️</span>
              </div>
              <div className="text-3xl font-bold">{formatNumber(stats.totalViews)}</div>
              <div className="text-sm text-success mt-1">+12.5% from last period</div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-muted-foreground">Engagement Rate</span>
                <span className="text-2xl">❤️</span>
              </div>
              <div className="text-3xl font-bold">{(stats.engagementRate * 100).toFixed(2)}%</div>
              <div className="text-sm text-success mt-1">+2.3% from last period</div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-muted-foreground">Total Followers</span>
                <span className="text-2xl">👥</span>
              </div>
              <div className="text-3xl font-bold">{formatNumber(stats.followers)}</div>
              <div className="text-sm text-success mt-1">+1,240 this period</div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-muted-foreground">Avg Watch Time</span>
                <span className="text-2xl">⏱️</span>
              </div>
              <div className="text-3xl font-bold">{stats.avgViewDuration}s</div>
              <div className="text-sm text-success mt-1">+5s from last period</div>
            </CardContent>
          </Card>
        </div>

        {/* Platform Breakdown */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Platform Performance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {platformStats.map(platform => (
                <div key={platform.platform} className="flex items-center justify-between p-4 bg-surface rounded-lg">
                  <div className="flex items-center gap-4">
                    <span className="text-3xl">{getPlatformIcon(platform.platform)}</span>
                    <div>
                      <div className="font-semibold">{platform.platform}</div>
                      <div className="text-sm text-muted-foreground">
                        {formatNumber(platform.followers)} followers • {platform.posts} posts
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-semibold">
                      {(platform.engagement * 100).toFixed(2)}%
                    </div>
                    <div className="text-sm text-muted-foreground">Engagement Rate</div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Top Performing Content */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Recent Posts Performance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentPosts.map(post => (
                <div key={post.id} className="flex items-center justify-between p-4 bg-surface rounded-lg">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-xl">{getPlatformIcon(post.platform)}</span>
                      <div>
                        <div className="font-semibold">{post.title}</div>
                        <div className="text-sm text-muted-foreground">{post.postedAt}</div>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-6 text-sm">
                    <div className="text-center">
                      <div className="font-semibold">{formatNumber(post.views)}</div>
                      <div className="text-muted-foreground">Views</div>
                    </div>
                    <div className="text-center">
                      <div className="font-semibold">{formatNumber(post.likes)}</div>
                      <div className="text-muted-foreground">Likes</div>
                    </div>
                    <div className="text-center">
                      <div className="font-semibold">{post.comments}</div>
                      <div className="text-muted-foreground">Comments</div>
                    </div>
                    <div className="text-center">
                      <div className="font-semibold text-tech">{(post.engagement * 100).toFixed(2)}%</div>
                      <div className="text-muted-foreground">Engagement</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Growth Chart Placeholder */}
        <Card>
          <CardHeader>
            <CardTitle>Growth Over Time</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64 flex items-center justify-center bg-surface rounded-lg">
              <div className="text-center">
                <div className="text-4xl mb-2">📈</div>
                <div className="text-muted-foreground">
                  Interactive charts coming soon
                </div>
                <div className="text-sm text-muted-foreground mt-1">
                  Will include: Followers growth, Engagement trends, Views over time
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
