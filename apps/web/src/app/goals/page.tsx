/**
 * Goals & Accountability Page
 * 
 * Goal tracking with iOS-style activity rings and progress charts
 * Now with real-time milestone notifications!
 */

'use client';

import { useState } from 'react';
import { useGoalsList, useCreateCheckIn } from '@/hooks/useGoals';
import { useLiveGoalMilestones } from '@/hooks/useWebSocketEvents';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { GoalRings } from '@/components/goals/GoalRings';
import { formatDate } from '@/lib/utils';
import type { Goal } from '@contentflow/api-client';

export default function GoalsPage() {
  const [selectedGoal, setSelectedGoal] = useState<Goal | null>(null);
  const [checkInValue, setCheckInValue] = useState('');

  // Fetch goals
  const { data, isLoading, error, refetch } = useGoalsList({
    status: 'active',
  });

  // Real-time milestone notifications
  const { isConnected, milestones } = useLiveGoalMilestones();

  const createCheckIn = useCreateCheckIn();

  // Handle check-in
  const handleCheckIn = async (goalId: string) => {
    if (!checkInValue) return;

    try {
      await createCheckIn.mutateAsync({
        goalId,
        data: {
          value_at_checkin: Number(checkInValue),
          note: 'Manual check-in',
        },
      });
      setCheckInValue('');
      setSelectedGoal(null);
      alert('Progress updated!');
    } catch (error) {
      console.error('Failed to check in:', error);
      alert('Failed to update progress');
    }
  };

  // Get status color
  const getStatusColor = (isOnTrack: boolean) => {
    return isOnTrack ? '#10b981' : '#f59e0b';
  };

  // Get goal type icon
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

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-tech mx-auto mb-4" />
              <p className="text-muted-foreground">Loading goals...</p>
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
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="text-error text-5xl mb-4">⚠️</div>
              <h2 className="text-2xl font-bold mb-2">Failed to load goals</h2>
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

  const goals = data?.items || [];

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold mb-2 gradient-text">Goals & Progress</h1>
              <p className="text-muted-foreground">
                Track your creator goals and stay accountable
              </p>
            </div>
            
            {/* Live indicator */}
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`} />
              <span className="text-sm text-muted-foreground">
                {isConnected ? 'Live' : 'Offline'}
              </span>
              {milestones.length > 0 && (
                <Badge variant="success" className="ml-2">
                  🎉 {milestones.length} milestone{milestones.length > 1 ? 's' : ''}!
                </Badge>
              )}
            </div>
          </div>
        </div>

        {/* Goals Grid */}
        {goals.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {goals.map((goal: Goal) => (
              <Card key={goal.id} className="card-hover">
                <CardHeader>
                  <div className="flex items-start justify-between mb-2">
                    <span className="text-3xl">{getGoalIcon(goal.goal_type)}</span>
                    <Badge variant={goal.is_on_track ? 'success' : 'warning'}>
                      {goal.is_on_track ? 'On Track' : 'Behind'}
                    </Badge>
                  </div>
                  <CardTitle className="text-lg">{goal.title}</CardTitle>
                  {goal.description && (
                    <p className="text-sm text-muted-foreground mt-1">
                      {goal.description}
                    </p>
                  )}
                </CardHeader>
                <CardContent>
                  {/* Progress Ring */}
                  <div className="flex justify-center mb-6">
                    <GoalRings
                      progress={goal.progress_pct}
                      color={getStatusColor(goal.is_on_track)}
                      size={120}
                    />
                  </div>

                  {/* Stats */}
                  <div className="space-y-3 text-sm">
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Progress</span>
                      <span className="font-medium">
                        {goal.current_value} / {goal.target_value} {goal.unit}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Period</span>
                      <span className="font-medium capitalize">{goal.period}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Days Left</span>
                      <span className="font-medium">{goal.days_remaining} days</span>
                    </div>
                    {goal.streak_count > 0 && (
                      <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">Streak</span>
                        <span className="font-medium">🔥 {goal.streak_count} days</span>
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="mt-6 space-y-2">
                    <Button
                      className="w-full"
                      size="sm"
                      onClick={() => setSelectedGoal(goal)}
                    >
                      Check In Progress
                    </Button>
                    <Button
                      className="w-full"
                      size="sm"
                      variant="outline"
                    >
                      View History
                    </Button>
                  </div>

                  {/* Dates */}
                  <div className="mt-4 pt-4 border-t border-border text-xs text-muted-foreground">
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
          <Card>
            <CardContent className="py-12">
              <div className="text-center">
                <div className="text-6xl mb-4">🎯</div>
                <h3 className="text-xl font-semibold mb-2">No active goals</h3>
                <p className="text-muted-foreground mb-6">
                  Set your first goal to start tracking your progress
                </p>
                <Button>Create Your First Goal</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Check-in Modal */}
        {selectedGoal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <Card className="w-full max-w-md">
              <CardHeader>
                <CardTitle>Check In Progress</CardTitle>
                <p className="text-sm text-muted-foreground">{selectedGoal.title}</p>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <label className="text-sm font-medium mb-2 block">
                      Current Value ({selectedGoal.unit})
                    </label>
                    <input
                      type="number"
                      className="w-full px-3 py-2 bg-surface rounded-md border border-input"
                      placeholder={`Enter ${selectedGoal.unit}...`}
                      value={checkInValue}
                      onChange={(e) => setCheckInValue(e.target.value)}
                    />
                  </div>

                  <div className="flex gap-2">
                    <Button
                      className="flex-1"
                      onClick={() => handleCheckIn(selectedGoal.id)}
                      disabled={!checkInValue || createCheckIn.isPending}
                    >
                      {createCheckIn.isPending ? 'Updating...' : 'Update Progress'}
                    </Button>
                    <Button
                      variant="outline"
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
