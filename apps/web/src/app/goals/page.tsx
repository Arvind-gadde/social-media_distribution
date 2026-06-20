'use client';

import { useState } from 'react';
import { Target, RefreshCw } from 'lucide-react';
import { useGoalsList, useCreateCheckIn } from '@/hooks/useGoals';
import { useLiveGoalMilestones } from '@/hooks/useWebSocketEvents';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { EmptyState } from '@/components/ui/empty-state';
import { Spinner } from '@/components/ui/spinner';
import { GoalRings } from '@/components/goals/GoalRings';
import { formatDate, cn } from '@/lib/utils';
import type { Goal } from '@contentflow/api-client';

export default function GoalsPage() {
  const [selectedGoal, setSelectedGoal] = useState<Goal | null>(null);
  const [checkInValue, setCheckInValue] = useState('');

  const { data, isLoading, error, refetch } = useGoalsList({ status: 'active' });
  const { isConnected, milestones } = useLiveGoalMilestones();
  const createCheckIn = useCreateCheckIn();

  const handleCheckIn = async (goalId: string) => {
    if (!checkInValue) return;
    try {
      await createCheckIn.mutateAsync({
        goalId,
        data: { value_at_checkin: Number(checkInValue), note: 'Manual check-in' },
      });
      setCheckInValue('');
      setSelectedGoal(null);
      alert('Progress updated!');
    } catch (error) {
      console.error('Failed to check in:', error);
      alert('Failed to update progress');
    }
  };

  const getStatusColor = (isOnTrack: boolean) => (isOnTrack ? '#7f56d9' : '#f59e0b');

  const getGoalIcon = (goalType: string) => {
    const icons: Record<string, string> = {
      content_count: '📝',
      followers: '👥',
      views: '👁️',
      revenue: '💰',
      engagement: '❤️',
    };
    return icons[goalType] || '🎯';
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
          icon={<Target />}
          iconColor="error"
          title="Failed to load goals"
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

  const goals = data?.items || [];

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-10 space-y-8 animate-fade-in">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="space-y-1">
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">
              Goals &amp; Progress
            </h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Track your creator goals and stay accountable.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className={cn('h-2 w-2 rounded-full', isConnected ? 'bg-success-500 animate-pulse' : 'bg-gray-400')} />
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {isConnected ? 'Live' : 'Offline'}
            </span>
            {milestones.length > 0 && (
              <Badge variant="success" className="ml-2">
                🎉 {milestones.length} milestone{milestones.length > 1 ? 's' : ''}!
              </Badge>
            )}
          </div>
        </header>

        {goals.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {goals.map((goal: Goal) => (
              <Card
                key={goal.id}
                className="flex flex-col transition-all duration-200 hover:scale-[1.02] hover:shadow-lg"
              >
                <CardHeader>
                  <div className="flex items-start justify-between mb-2">
                    <span className="text-3xl">{getGoalIcon(goal.goal_type)}</span>
                    <Badge variant={goal.is_on_track ? 'success' : 'warning'}>
                      {goal.is_on_track ? 'On Track' : 'Behind'}
                    </Badge>
                  </div>
                  <CardTitle className="text-lg">{goal.title}</CardTitle>
                  {goal.description && (
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      {goal.description}
                    </p>
                  )}
                </CardHeader>
                <CardContent className="flex-1 flex flex-col">
                  <div className="flex justify-center mb-6">
                    <GoalRings
                      progress={goal.progress_pct}
                      color={getStatusColor(goal.is_on_track)}
                      size={120}
                    />
                  </div>

                  <div className="space-y-3 text-sm flex-1">
                    <div className="flex items-center justify-between">
                      <span className="text-gray-500 dark:text-gray-400">Progress</span>
                      <span className="font-medium text-gray-900 dark:text-gray-50">
                        {goal.current_value} / {goal.target_value} {goal.unit}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-gray-500 dark:text-gray-400">Period</span>
                      <span className="font-medium text-gray-900 dark:text-gray-50 capitalize">
                        {goal.period}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-gray-500 dark:text-gray-400">Days Left</span>
                      <span className="font-medium text-gray-900 dark:text-gray-50">
                        {goal.days_remaining} days
                      </span>
                    </div>
                    {goal.streak_count > 0 && (
                      <div className="flex items-center justify-between">
                        <span className="text-gray-500 dark:text-gray-400">Streak</span>
                        <span className="font-medium text-gray-900 dark:text-gray-50">
                          🔥 {goal.streak_count} days
                        </span>
                      </div>
                    )}
                  </div>

                  <div className="mt-6 space-y-2">
                    <Button
                      variant="primary"
                      className="w-full"
                      size="sm"
                      onClick={() => setSelectedGoal(goal)}
                    >
                      Check In Progress
                    </Button>
                    <Button variant="secondary" className="w-full" size="sm">
                      View History
                    </Button>
                  </div>

                  <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-800 text-xs text-gray-500 dark:text-gray-400">
                    <div className="flex justify-between">
                      <span>Started: {formatDate(goal.starts_at)}</span>
                      <span>Ends: {formatDate(goal.ends_at)}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <EmptyState
            icon={<Target />}
            iconColor="brand"
            iconSize="lg"
            title="No active goals"
            description="Set your first goal to start tracking your progress."
            actions={<Button variant="primary">Create Your First Goal</Button>}
          />
        )}

        {selectedGoal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <Card className="w-full max-w-md">
              <CardHeader>
                <CardTitle>Check In Progress</CardTitle>
                <p className="text-sm text-gray-500 dark:text-gray-400">{selectedGoal.title}</p>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <label className="text-sm font-medium mb-2 block text-gray-700 dark:text-gray-300">
                      Current Value ({selectedGoal.unit})
                    </label>
                    <input
                      type="number"
                      className="w-full rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500/24"
                      placeholder={`Enter ${selectedGoal.unit}...`}
                      value={checkInValue}
                      onChange={(e) => setCheckInValue(e.target.value)}
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="primary"
                      className="flex-1"
                      onClick={() => handleCheckIn(selectedGoal.id)}
                      disabled={!checkInValue || createCheckIn.isPending}
                      loading={createCheckIn.isPending}
                    >
                      {createCheckIn.isPending ? 'Updating...' : 'Update Progress'}
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => {
                        setSelectedGoal(null);
                        setCheckInValue('');
                      }}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
