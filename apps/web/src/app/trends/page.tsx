/**
 * Trends Dashboard Page
 * 
 * Displays trending content with heat scores and velocity tracking
 */

'use client';

import { useState } from 'react';
import { useTrends, useTrendStats, useCreateContentFromTrend } from '@/hooks/useTrends';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatRelativeTime, formatCompactNumber } from '@/lib/utils';
import type { Trend } from '@contentflow/api-client';

export default function TrendsPage() {
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({
    status: 'rising' as 'rising' | 'peak' | 'declining' | 'dead' | 'evergreen' | '',
    platform: '',
    min_score: 0,
  });
  const [selectedTrend, setSelectedTrend] = useState<Trend | null>(null);

  // Fetch data
  const { data, isLoading, error, refetch } = useTrends({
    page,
    page_size: 12,
    status: filters.status || undefined,
    platform: filters.platform || undefined,
    min_score: filters.min_score,
  });

  const { data: stats } = useTrendStats();
  const createContent = useCreateContentFromTrend();

  // Get heat color based on score
  const getHeatColor = (score: number) => {
    if (score >= 80) return 'text-error';
    if (score >= 60) return 'text-warning';
    if (score >= 40) return 'text-tech';
    return 'text-muted-foreground';
  };

  // Get status badge variant
  const getStatusVariant = (status: string): 'success' | 'warning' | 'error' | 'default' => {
    if (status === 'rising') return 'success';
    if (status === 'peak') return 'warning';
    if (status === 'declining') return 'error';
    return 'default';
  };

  // Handle create content
  const handleCreateContent = async (trendId: string, title: string) => {
    try {
      await createContent.mutateAsync({
        trendId,
        data: {
          title,
          content_type: 'reel',
        },
      });
      alert('Content project created successfully!');
      setSelectedTrend(null);
    } catch (error) {
      console.error('Failed to create content:', error);
      alert('Failed to create content');
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-tech mx-auto mb-4" />
              <p className="text-muted-foreground">Loading trends...</p>
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
              <h2 className="text-2xl font-bold mb-2">Failed to load trends</h2>
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

  const trends = data?.items || [];
  const hasMore = data?.has_more || false;

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2 gradient-text">🔥 Trending Now</h1>
          <p className="text-muted-foreground">
            Real-time trend detection across all platforms
          </p>
        </div>

        {/* Stats Grid */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <Card>
              <CardContent className="pt-6">
                <div className="text-sm text-muted-foreground mb-1">Active Trends</div>
                <div className="text-3xl font-bold">{stats.total_active}</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-sm text-muted-foreground mb-1">Avg Score</div>
                <div className="text-3xl font-bold">{stats.average_score.toFixed(1)}</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-sm text-muted-foreground mb-1">Rising</div>
                <div className="text-3xl font-bold text-success">
                  {stats.status_counts.rising || 0}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-sm text-muted-foreground mb-1">Peak</div>
                <div className="text-3xl font-bold text-warning">
                  {stats.status_counts.peak || 0}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Filters */}
        <Card className="mb-6">
          <CardContent className="pt-6">
            <div className="flex flex-wrap gap-4">
              <select
                className="px-3 py-2 bg-surface rounded-md text-sm border border-input"
                value={filters.status}
                onChange={(e) => setFilters({ ...filters, status: e.target.value as any })}
              >
                <option value="">All Status</option>
                <option value="rising">Rising</option>
                <option value="peak">Peak</option>
                <option value="declining">Declining</option>
                <option value="evergreen">Evergreen</option>
              </select>

              <select
                className="px-3 py-2 bg-surface rounded-md text-sm border border-input"
                value={filters.platform}
                onChange={(e) => setFilters({ ...filters, platform: e.target.value })}
              >
                <option value="">All Platforms</option>
                <option value="instagram">Instagram</option>
                <option value="tiktok">TikTok</option>
                <option value="youtube">YouTube</option>
                <option value="twitter">Twitter</option>
              </select>

              <select
                className="px-3 py-2 bg-surface rounded-md text-sm border border-input"
                value={filters.min_score}
                onChange={(e) => setFilters({ ...filters, min_score: Number(e.target.value) })}
              >
                <option value="0">All Scores</option>
                <option value="50">50+ Score</option>
                <option value="70">70+ Score</option>
                <option value="80">80+ Score</option>
              </select>

              {(filters.status || filters.platform || filters.min_score > 0) && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setFilters({ status: '', platform: '', min_score: 0 })}
                >
                  Clear Filters
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Trends Grid */}
        {trends.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {trends.map((trend: Trend) => (
              <Card key={trend.id} className="card-hover cursor-pointer" onClick={() => setSelectedTrend(trend)}>
                <CardHeader>
                  <div className="flex items-start justify-between mb-2">
                    <Badge variant={getStatusVariant(trend.status)}>
                      {trend.status}
                    </Badge>
                    <div className={`text-2xl font-bold ${getHeatColor(trend.trend_score)}`}>
                      {trend.trend_score.toFixed(0)}
                    </div>
                  </div>
                  <CardTitle className="text-lg line-clamp-2">{trend.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  {trend.description && (
                    <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
                      {trend.description}
                    </p>
                  )}
                  
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Platform</span>
                      <span className="font-medium">{trend.platform || 'Global'}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Velocity</span>
                      <span className="font-medium">{trend.trend_velocity.toFixed(1)}/hr</span>
                    </div>
                    {trend.started_at && (
                      <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">Started</span>
                        <span className="font-medium">{formatRelativeTime(trend.started_at)}</span>
                      </div>
                    )}
                  </div>

                  {trend.hashtags && trend.hashtags.length > 0 && (
                    <div className="mt-4 flex flex-wrap gap-2">
                      {trend.hashtags.slice(0, 3).map((tag, i) => (
                        <span key={i} className="text-xs text-tech">#{tag}</span>
                      ))}
                    </div>
                  )}

                  <Button
                    className="w-full mt-4"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleCreateContent(trend.id, `Content based on: ${trend.title}`);
                    }}
                    disabled={createContent.isPending}
                  >
                    Create Content →
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="py-12">
              <div className="text-center">
                <div className="text-6xl mb-4">🔍</div>
                <h3 className="text-xl font-semibold mb-2">No trends found</h3>
                <p className="text-muted-foreground">
                  {filters.status || filters.platform || filters.min_score > 0
                    ? 'Try adjusting your filters'
                    : 'Agents are scanning for trends. Check back soon!'}
                </p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Pagination */}
        {trends.length > 0 && (
          <div className="flex items-center justify-between mt-6">
            <p className="text-sm text-muted-foreground">
              Page {page} • {data?.total || 0} total trends
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(page - 1)}
                disabled={page === 1}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(page + 1)}
                disabled={!hasMore}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
