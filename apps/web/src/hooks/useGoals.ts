/**
 * Goals Management Hooks
 * 
 * React Query hooks for goal tracking and accountability
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listGoals,
  getGoal,
  createGoal,
  updateGoal,
  deleteGoal,
  createCheckIn,
  getGoalHistory,
  type Goal,
  type GoalCreate,
  type GoalUpdate,
  type GoalCheckInCreate,
  type GoalListParams,
} from '@contentflow/api-client';
import { toast } from '@/lib/toast';

// ═══════════════════════════════════════════════════════════════════════════════
// QUERY KEYS
// ═══════════════════════════════════════════════════════════════════════════════

export const goalKeys = {
  all: ['goals'] as const,
  lists: () => [...goalKeys.all, 'list'] as const,
  list: (params?: GoalListParams) => [...goalKeys.lists(), params] as const,
  details: () => [...goalKeys.all, 'detail'] as const,
  detail: (id: string) => [...goalKeys.details(), id] as const,
  history: (id: string) => [...goalKeys.all, 'history', id] as const,
};

// ═══════════════════════════════════════════════════════════════════════════════
// HOOKS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * List goals
 */
export function useGoalsList(params?: GoalListParams) {
  return useQuery({
    queryKey: goalKeys.list(params),
    queryFn: () => listGoals(params),
  });
}

/**
 * Get single goal
 */
export function useGoal(id: string) {
  return useQuery({
    queryKey: goalKeys.detail(id),
    queryFn: () => getGoal(id),
    enabled: !!id,
  });
}

/**
 * Create goal
 */
export function useCreateGoal() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: GoalCreate) => createGoal(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: goalKeys.lists() });
      toast.success('Goal created successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to create goal: ${error.message}`);
    },
  });
}

/**
 * Update goal
 */
export function useUpdateGoal() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: GoalUpdate }) =>
      updateGoal(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: goalKeys.detail(variables.id) });
      queryClient.invalidateQueries({ queryKey: goalKeys.lists() });
      toast.success('Goal updated successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to update goal: ${error.message}`);
    },
  });
}

/**
 * Delete goal
 */
export function useDeleteGoal() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteGoal(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: goalKeys.lists() });
      toast.success('Goal deleted successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to delete goal: ${error.message}`);
    },
  });
}

/**
 * Create check-in
 */
export function useCreateCheckIn() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ goalId, data }: { goalId: string; data: GoalCheckInCreate }) =>
      createCheckIn(goalId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: goalKeys.detail(variables.goalId) });
      queryClient.invalidateQueries({ queryKey: goalKeys.history(variables.goalId) });
      queryClient.invalidateQueries({ queryKey: goalKeys.lists() });
      toast.success('Progress updated');
    },
    onError: (error: Error) => {
      toast.error(`Failed to update progress: ${error.message}`);
    },
  });
}

/**
 * Get goal history
 */
export function useGoalHistory(goalId: string, limit: number = 50) {
  return useQuery({
    queryKey: goalKeys.history(goalId),
    queryFn: () => getGoalHistory(goalId, limit),
    enabled: !!goalId,
  });
}
