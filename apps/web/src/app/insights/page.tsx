'use client';

import { useState } from 'react';
import { Sparkles, RefreshCw } from 'lucide-react';
import { useAgentInsights, useMarkInsightRead, useDismissInsight } from '@/hooks/useAgents';
import { useLiveInsights } from '@/hooks/useWebSocketEvents';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { EmptyState } from '@/components/ui/empty-state';
import { Spinner } from '@/components/ui/spinner';
import { formatRelativeTime, cn } from '@/lib/utils';
import type { AgentInsight } from '@contentflow/api-client';

const selectCls = 'rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500/24';

export default function InsightsPage() {
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({
    unread_only: false,
    is_read: undefined as boolean | undefined,
    agent_type: undefined as string | undefined,
    insight_type: undefined as string | undefined,
  });

  const { data, isLoading, error, refetch } = useAgentInsights({
    page,
    page_size: 20,
    is_read: filters.unread_only ? false : filters.is_read,
    agent_type: filters.agent_type as any,
    insight_type: filters.insight_type,
  });

  const { isConnected, liveInsights } = useLiveInsights();
  const markAsRead = useMarkInsightRead();
  const dismiss = useDismissInsight();

  const handleMarkAsRead = async (id: string) => {
    try { await markAsRead.mutateAsync(id); } catch (e) { console.error(e); }
  };

  const handleDismiss = async (id: string) => {
    try { await dismiss.mutateAsync(id); } catch (e) { console.error(e); }
  };

  const getAgentIcon = (agentType: string) => {
    const icons: Record<string, string> = {
      trend_detection: '📈', competitor_intelligence: '🔍', content_research: '💡',
      goal_reminder: '🎯', analytics: '📊', news_fetcher: '📰', collaboration: '🤝', scheduling: '⏰',
    };
    return icons[agentType] || '🤖';
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Spinner size="lg" color="primary" />
      </div>
    );
  }

  const header = (
    <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="space-y-1">
        <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">
          Agent Insights
        </h1>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          AI-powered signals from your agent team.
        </p>
      </div>
      <div className="flex items-center gap-2">
        <div className={cn('h-2 w-2 rounded-full', isConnected ? 'bg-success-500 animate-pulse' : 'bg-gray-400')} />
        <span className="text-sm text-gray-500 dark:text-gray-400">{isConnected ? 'Live' : 'Offline'}</span>
      </div>
    </header>
  );

  if (error) {
    return (
      <div className="min-h-screen bg-background">
        <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-10 space-y-8 animate-fade-in">
          {header}
          <EmptyState
            icon={<Sparkles />}
            iconColor="brand"
            title="No insights yet"
            description="Your AI agents are getting ready. Check back soon!"
          />
        </div>
      </div>
    );
  }

  const insights = data?.items || [];
  const hasMore = data?.has_more || false;

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-10 space-y-8 animate-fade-in">
        {header}

        {/* Filters */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-wrap gap-3 items-center">
              {liveInsights.length > 0 && (
                <Badge variant="brand" className="animate-pulse">
                  {liveInsights.length} new insight{liveInsights.length > 1 ? 's' : ''}
                </Badge>
              )}
              <Button
                variant={filters.unread_only ? 'primary' : 'secondary'}
                size="sm"
                onClick={() => setFilters({ ...filters, unread_only: !filters.unread_only })}
              >
                {filters.unread_only ? '✓ ' : ''}Unread Only
              </Button>
              <select
                className={selectCls}
                value={filters.agent_type ?? ''}
                onChange={(e) => setFilters({ ...filters, agent_type: e.target.value })}
              >
                <option value="">All Agents</option>
                <option value="trend_detection">Trend Detection</option>
                <option value="competitor_intelligence">Competitor Intelligence</option>
                <option value="content_research">Content Research</option>
                <option value="goal_reminder">Goal Reminder</option>
                <option value="analytics">Analytics</option>
              </select>
              <select
                className={selectCls}
                value={filters.insight_type ?? ''}
                onChange={(e) => setFilters({ ...filters, insight_type: e.target.value })}
              >
                <option value="">All Types</option>
                <option value="trend_alert">Trend Alert</option>
                <option value="competitor_move">Competitor Move</option>
                <option value="content_idea">Content Idea</option>
                <option value="goal_warning">Goal Warning</option>
              </select>
              {(filters.unread_only || filters.agent_type || filters.insight_type) && (
                <Button
                  variant="tertiary"
                  size="sm"
                  onClick={() => setFilters({ unread_only: false, is_read: undefined, agent_type: '', insight_type: '' })}
                >
                  Clear
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {insights.length > 0 ? (
          <div className="space-y-4">
            {insights.map((insight: AgentInsight) => (
              <Card key={insight.id} className={cn(insight.is_read && 'opacity-60')}>
                <CardContent className="pt-6">
                  <div className="flex items-start gap-3 mb-4">
                    <span className="text-2xl shrink-0">{getAgentIcon(insight.agent_type)}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <h3 className="font-semibold text-gray-900 dark:text-gray-50">{insight.title}</h3>
                        {!insight.is_read && <Badge variant="brand" size="sm">New</Badge>}
                        {insight.priority >= 8 && <Badge variant="error" size="sm">High Priority</Badge>}
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                        {insight.agent_type.replace(/_/g, ' ')} · {formatRelativeTime(insight.created_at)}
                      </p>
                      <p className="text-sm text-gray-600 dark:text-gray-400">{insight.body}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 pt-4 border-t border-gray-200 dark:border-gray-800">
                    {insight.action_type && (
                      <Button size="sm" variant="primary">
                        {insight.action_type.replace(/_/g, ' ')} →
                      </Button>
                    )}
                    {!insight.is_read && (
                      <Button size="sm" variant="secondary" onClick={() => handleMarkAsRead(insight.id)} disabled={markAsRead.isPending}>
                        Mark as Read
                      </Button>
                    )}
                    <Button size="sm" variant="tertiary" onClick={() => handleDismiss(insight.id)} disabled={dismiss.isPending}>
                      Dismiss
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <EmptyState
            icon={<Sparkles />}
            iconColor="brand"
            title="No insights found"
            description={
              filters.unread_only || filters.agent_type || filters.insight_type
                ? 'Try adjusting your filters.'
                : 'Your agents are working hard. Check back soon!'
            }
          />
        )}

        {insights.length > 0 && (
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Page {page} · {data?.total ?? 0} total
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
