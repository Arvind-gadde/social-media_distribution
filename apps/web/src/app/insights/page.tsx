/**
 * Agent Insights Feed Page
 * 
 * Full insights list with pagination, filters, and actions
 * Now with real-time WebSocket updates!
 */

'use client';

import { useState } from 'react';
import { useAgentInsights, useMarkInsightRead, useDismissInsight } from '@/hooks/useAgents';
import { useLiveInsights } from '@/hooks/useWebSocketEvents';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatRelativeTime } from '@/lib/utils';
import type { AgentInsight } from '@contentflow/api-client';

export default function InsightsPage() {
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({
    unread_only: false,
    is_read: undefined as boolean | undefined,
    agent_type: undefined as string | undefined,
    insight_type: undefined as string | undefined,
  });

  // Fetch insights
  const { data, isLoading, error, refetch } = useAgentInsights({
    page,
    page_size: 20,
    is_read: filters.unread_only ? false : filters.is_read,
    agent_type: filters.agent_type as any,
    insight_type: filters.insight_type,
  });

  // Real-time WebSocket connection
  const { isConnected, liveInsights } = useLiveInsights();

  // Mutations
  const markAsRead = useMarkInsightRead();
  const dismiss = useDismissInsight();

  // Handle mark as read
  const handleMarkAsRead = async (id: string) => {
    try {
      await markAsRead.mutateAsync(id);
    } catch (error) {
      console.error('Failed to mark as read:', error);
    }
  };

  // Handle dismiss
  const handleDismiss = async (id: string) => {
    try {
      await dismiss.mutateAsync(id);
    } catch (error) {
      console.error('Failed to dismiss:', error);
    }
  };

  // Get agent icon
  const getAgentIcon = (agentType: string) => {
    const icons: Record<string, string> = {
      trend_detection: '📈',
      competitor_intelligence: '🔍',
      content_research: '💡',
      goal_reminder: '🎯',
      analytics: '📊',
      news_fetcher: '📰',
      collaboration: '🤝',
      scheduling: '⏰',
    };
    return icons[agentType] || '🤖';
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-tech mx-auto mb-4" />
              <p className="text-muted-foreground">Loading insights...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    console.error('Insights error:', error);
    
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-4xl font-bold mb-2 gradient-text">Agent Insights</h1>
            <p className="text-muted-foreground">
              AI-powered insights from your agent team
            </p>
          </div>

          {/* Empty state instead of error */}
          <Card>
            <CardContent className="py-12">
              <div className="text-center">
                <div className="text-6xl mb-4">✨</div>
                <h3 className="text-xl font-semibold mb-2">No insights yet</h3>
                <p className="text-muted-foreground mb-4">
                  Your AI agents are getting ready. Check back soon!
                </p>
                <p className="text-sm text-muted-foreground">
                  Agents will analyze trends, competitors, and content opportunities for you.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  const insights = data?.items || [];
  const hasMore = data?.has_more || false;

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold mb-2 gradient-text">Agent Insights</h1>
              <p className="text-muted-foreground">
                AI-powered insights from your agent team
              </p>
            </div>
            
            {/* Live indicator */}
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`} />
              <span className="text-sm text-muted-foreground">
                {isConnected ? 'Live' : 'Offline'}
              </span>
            </div>
          </div>
        </div>

        {/* Filters */}
        <Card className="mb-6">
          <CardContent className="pt-6">
            <div className="flex flex-wrap gap-4">
              {/* Live insights count */}
              {liveInsights.length > 0 && (
                <Badge variant="info" className="animate-pulse">
                  {liveInsights.length} new insight{liveInsights.length > 1 ? 's' : ''}
                </Badge>
              )}
              
              <Button
                variant={filters.unread_only ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilters({ ...filters, unread_only: !filters.unread_only })}
              >
                {filters.unread_only ? '✓ ' : ''}Unread Only
              </Button>
              
              <select
                className="px-3 py-2 bg-surface rounded-md text-sm border border-input"
                value={filters.agent_type}
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
                className="px-3 py-2 bg-surface rounded-md text-sm border border-input"
                value={filters.insight_type}
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
                  variant="ghost"
                  size="sm"
                  onClick={() => setFilters({
                    unread_only: false,
                    is_read: undefined,
                    agent_type: '',
                    insight_type: '',
                  })}
                >
                  Clear Filters
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Insights List */}
        {insights.length > 0 ? (
          <div className="space-y-4">
            {insights.map((insight: AgentInsight) => (
              <Card key={insight.id} className={insight.is_read ? 'opacity-60' : ''}>
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-start gap-3 flex-1">
                      <span className="text-3xl">{getAgentIcon(insight.agent_type)}</span>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-semibold text-lg">{insight.title}</h3>
                          {!insight.is_read && (
                            <Badge variant="info">New</Badge>
                          )}
                          {insight.priority >= 8 && (
                            <Badge variant="error">High Priority</Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground mb-2">
                          {insight.agent_type.replace(/_/g, ' ')} • {formatRelativeTime(insight.created_at)}
                        </p>
                        <p className="text-sm text-muted-foreground">{insight.body}</p>
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 mt-4 pt-4 border-t border-border">
                    {insight.action_type && (
                      <Button size="sm" variant="default">
                        {insight.action_type.replace(/_/g, ' ')} →
                      </Button>
                    )}
                    {!insight.is_read && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleMarkAsRead(insight.id)}
                        disabled={markAsRead.isPending}
                      >
                        Mark as Read
                      </Button>
                    )}
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDismiss(insight.id)}
                      disabled={dismiss.isPending}
                    >
                      Dismiss
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="py-12">
              <div className="text-center">
                <div className="text-6xl mb-4">✨</div>
                <h3 className="text-xl font-semibold mb-2">No insights found</h3>
                <p className="text-muted-foreground">
                  {filters.unread_only || filters.agent_type || filters.insight_type
                    ? 'Try adjusting your filters'
                    : 'Your agents are working hard. Check back soon!'}
                </p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Pagination */}
        {insights.length > 0 && (
          <div className="flex items-center justify-between mt-6">
            <p className="text-sm text-muted-foreground">
              Page {page} • {data?.total || 0} total insights
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
