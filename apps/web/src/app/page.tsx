/**
 * Home Page - Dashboard Overview
 */

'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useGoalsList } from '@/hooks/useGoals';
import { useAgentInsights } from '@/hooks/useAgents';
import { useTrends } from '@/hooks/useTrends';

export default function HomePage() {
  const router = useRouter();

  // Check authentication
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      if (!token) {
        router.push('/login');
      }
    }
  }, [router]);

  // Fetch data
  const { data: goalsData } = useGoalsList({ status: 'active', page_size: 3 });
  const { data: insightsData } = useAgentInsights({ is_read: false, page_size: 5 });
  const { data: trendsData } = useTrends({ page_size: 3 });

  const goals = goalsData?.items || [];
  const insights = insightsData?.items || [];
  const trends = trendsData?.items || [];

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2 gradient-text">Welcome to ContentFlow</h1>
          <p className="text-muted-foreground">
            Your AI-powered creator operating system
          </p>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card className="card-hover cursor-pointer" onClick={() => router.push('/goals')}>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground">Active Goals</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{goals.length}</div>
              <p className="text-xs text-muted-foreground mt-1">Track your progress</p>
            </CardContent>
          </Card>

          <Card className="card-hover cursor-pointer" onClick={() => router.push('/insights')}>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground">New Insights</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{insights.length}</div>
              <p className="text-xs text-muted-foreground mt-1">From your AI agents</p>
            </CardContent>
          </Card>

          <Card className="card-hover cursor-pointer" onClick={() => router.push('/trends')}>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground">Trending Now</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{trends.length}</div>
              <p className="text-xs text-muted-foreground mt-1">Hot topics in your niche</p>
            </CardContent>
          </Card>
        </div>

        {/* Recent Activity */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Goals */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Recent Goals</CardTitle>
                <Button variant="ghost" size="sm" onClick={() => router.push('/goals')}>
                  View All →
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {goals.length > 0 ? (
                <div className="space-y-3">
                  {goals.slice(0, 3).map((goal: any) => (
                    <div key={goal.id} className="flex items-center justify-between p-3 bg-surface rounded-lg">
                      <div className="flex-1">
                        <p className="font-medium text-sm">{goal.title}</p>
                        <p className="text-xs text-muted-foreground">{goal.progress_pct}% complete</p>
                      </div>
                      <div className="text-2xl">{goal.progress_pct >= 75 ? '🔥' : '🎯'}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-muted-foreground mb-4">No active goals</p>
                  <Button size="sm" onClick={() => router.push('/goals')}>Create Your First Goal</Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Recent Insights */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Latest Insights</CardTitle>
                <Button variant="ghost" size="sm" onClick={() => router.push('/insights')}>
                  View All →
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {insights.length > 0 ? (
                <div className="space-y-3">
                  {insights.slice(0, 3).map((insight: any) => (
                    <div key={insight.id} className="p-3 bg-surface rounded-lg">
                      <p className="font-medium text-sm mb-1">{insight.title}</p>
                      <p className="text-xs text-muted-foreground line-clamp-2">{insight.body}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-muted-foreground">No new insights</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Button variant="outline" className="h-20 flex-col gap-2" onClick={() => router.push('/goals')}>
                <span className="text-2xl">🎯</span>
                <span className="text-sm">Create Goal</span>
              </Button>
              <Button variant="outline" className="h-20 flex-col gap-2" onClick={() => router.push('/trends')}>
                <span className="text-2xl">🔥</span>
                <span className="text-sm">View Trends</span>
              </Button>
              <Button variant="outline" className="h-20 flex-col gap-2" onClick={() => router.push('/insights')}>
                <span className="text-2xl">💡</span>
                <span className="text-sm">AI Insights</span>
              </Button>
              <Button variant="outline" className="h-20 flex-col gap-2">
                <span className="text-2xl">⚙️</span>
                <span className="text-sm">Settings</span>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
