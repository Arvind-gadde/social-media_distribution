'use client';

import { useState } from 'react';
import { TrendingUp, RefreshCw, Zap } from 'lucide-react';
import { useTrends, useTrendStats, useCreateContentFromTrend } from '@/hooks/useTrends';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { EmptyState } from '@/components/ui/empty-state';
import { Spinner } from '@/components/ui/spinner';
import { formatRelativeTime, formatCompactNumber, cn } from '@/lib/utils';
import type { Trend } from '@contentflow/api-client';

const selectCls = 'rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500/24';

export default function TrendsPage() {
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({
    status: 'rising' as 'rising' | 'peak' | 'declining' | 'dead' | 'evergreen' | '',
    platform: '',
    min_score: 0,
  });
  const [selectedTrend, setSelectedTrend] = useState<Trend | null>(null);

  const { data, isLoading, error, refetch } = useTrends({
    page,
    page_size: 12,
    status: filters.status || undefined,
    platform: filters.platform || undefined,
    min_score: filters.min_score,
  });

  const { data: stats } = useTrendStats();
  const createContent = useCreateContentFromTrend();

  const getHeatColor = (score: number) => {
    if (score >= 80) return 'text-error-600 dark:text-error-400';
    if (score >= 60) return 'text-warning-600 dark:text-warning-400';
    if (score >= 40) return 'text-brand-600 dark:text-brand-400';
    return 'text-gray-500 dark:text-gray-400';
  };

  const getStatusVariant = (status: string): 'success' | 'warning' | 'error' | 'gray' => {
    if (status === 'rising') return 'success';
    if (status === 'peak') return 'warning';
    if (status === 'declining') return 'error';
    return 'gray';
  };

  const handleCreateContent = async (trendId: string, title: string) => {
    try {
      await createContent.mutateAsync({ trendId, data: { title, content_type: 'reel' } });
      alert('Content project created successfully!');
      setSelectedTrend(null);
    } catch (e) {
      console.error('Failed to create content:', e);
      alert('Failed to create content');
    }
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
          icon={<TrendingUp />}
          iconColor="error"
          title="Failed to load trends"
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

  const trends = data?.items || [];
  const hasMore = data?.has_more || false;

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-10 space-y-8 animate-fade-in">
        <header className="space-y-1">
          <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">
            Trending Now
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Real-time trend detection across all platforms.
          </p>
        </header>

        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Active Trends', value: stats.total_active, color: '' },
              { label: 'Avg Score', value: stats.average_score.toFixed(1), color: '' },
              { label: 'Rising', value: stats.status_counts.rising ?? 0, color: 'text-success-600 dark:text-success-400' },
              { label: 'Peak', value: stats.status_counts.peak ?? 0, color: 'text-warning-600 dark:text-warning-400' },
            ].map((stat) => (
              <Card key={stat.label} className="p-5">
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">{stat.label}</p>
                <p className={cn('text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-50', stat.color)}>
                  {stat.value}
                </p>
              </Card>
            ))}
          </div>
        )}

        {/* Filters */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-wrap gap-3 items-center">
              <select className={selectCls} value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value as any })}>
                <option value="">All Status</option>
                <option value="rising">Rising</option>
                <option value="peak">Peak</option>
                <option value="declining">Declining</option>
                <option value="evergreen">Evergreen</option>
              </select>
              <select className={selectCls} value={filters.platform} onChange={(e) => setFilters({ ...filters, platform: e.target.value })}>
                <option value="">All Platforms</option>
                <option value="instagram">Instagram</option>
                <option value="tiktok">TikTok</option>
                <option value="youtube">YouTube</option>
                <option value="twitter">Twitter</option>
              </select>
              <select className={selectCls} value={filters.min_score} onChange={(e) => setFilters({ ...filters, min_score: Number(e.target.value) })}>
                <option value="0">All Scores</option>
                <option value="50">50+ Score</option>
                <option value="70">70+ Score</option>
                <option value="80">80+ Score</option>
              </select>
              {(filters.status || filters.platform || filters.min_score > 0) && (
                <Button variant="tertiary" size="sm" onClick={() => setFilters({ status: '', platform: '', min_score: 0 })}>
                  Clear
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {trends.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {trends.map((trend: Trend) => (
              <Card
                key={trend.id}
                className="flex flex-col cursor-pointer transition-all duration-200 hover:scale-[1.02] hover:shadow-lg"
                onClick={() => setSelectedTrend(trend)}
              >
                <CardHeader>
                  <div className="flex items-start justify-between mb-2">
                    <Badge variant={getStatusVariant(trend.status)}>{trend.status}</Badge>
                    <span className={cn('text-2xl font-bold', getHeatColor(trend.trend_score))}>
                      {trend.trend_score.toFixed(0)}
                    </span>
                  </div>
                  <CardTitle className="text-base line-clamp-2">{trend.title}</CardTitle>
                </CardHeader>
                <CardContent className="flex-1 flex flex-col">
                  {trend.description && (
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-4 line-clamp-2">
                      {trend.description}
                    </p>
                  )}
                  <div className="space-y-2 text-sm flex-1">
                    <div className="flex items-center justify-between">
                      <span className="text-gray-500 dark:text-gray-400">Platform</span>
                      <span className="font-medium text-gray-900 dark:text-gray-50">{trend.platform || 'Global'}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-gray-500 dark:text-gray-400">Velocity</span>
                      <span className="font-medium text-gray-900 dark:text-gray-50">{trend.trend_velocity.toFixed(1)}/hr</span>
                    </div>
                    {trend.started_at && (
                      <div className="flex items-center justify-between">
                        <span className="text-gray-500 dark:text-gray-400">Started</span>
                        <span className="font-medium text-gray-900 dark:text-gray-50">{formatRelativeTime(trend.started_at)}</span>
                      </div>
                    )}
                  </div>
                  {trend.hashtags && trend.hashtags.length > 0 && (
                    <div className="mt-4 flex flex-wrap gap-2">
                      {trend.hashtags.slice(0, 3).map((tag, i) => (
                        <span key={i} className="text-xs text-brand-600 dark:text-brand-400">#{tag}</span>
                      ))}
                    </div>
                  )}
                  <Button
                    variant="primary"
                    className="w-full mt-4"
                    size="sm"
                    leadingIcon={<Zap className="h-3.5 w-3.5" />}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleCreateContent(trend.id, `Content based on: ${trend.title}`);
                    }}
                    disabled={createContent.isPending}
                  >
                    Create Content
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <EmptyState
            icon={<TrendingUp />}
            iconColor="brand"
            title="No trends found"
            description={
              filters.status || filters.platform || filters.min_score > 0
                ? 'Try adjusting your filters.'
                : 'Agents are scanning for trends. Check back soon!'
            }
          />
        )}

        {trends.length > 0 && (
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Page {page} · {data?.total ?? 0} total trends
            </p>
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={() => setPage((p) => p - 1)} disabled={page === 1}>Previous</Button>
              <Button variant="secondary" size="sm" onClick={() => setPage((p) => p + 1)} disabled={!hasMore}>Next</Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
