/**
 * Goals API Client
 * 
 * Handles all goal tracking and accountability operations:
 * - Create, update, delete goals
 * - Track progress
 * - Check-ins
 * - Goal history
 */

import { getApiClient, PaginatedResponse } from './client';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface Goal {
  id: string;
  title: string;
  description?: string;
  goal_type: 'content_count' | 'followers' | 'views' | 'revenue' | 'engagement';
  period: 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly';
  target_value: number;
  current_value: number;
  unit: string;
  platform?: string;
  status: 'active' | 'paused' | 'completed' | 'failed' | 'archived';
  starts_at: string;
  ends_at: string;
  reminder_enabled: boolean;
  reminder_schedule?: {
    days: string[];
    time: string;
    timezone: string;
  };
  completed_at?: string;
  streak_count: number;
  best_streak: number;
  created_at: string;
  updated_at: string;
  
  // Computed fields
  progress_pct: number;
  days_remaining: number;
  is_on_track: boolean;
}

export interface GoalCreate {
  title: string;
  description?: string;
  goal_type: 'content_count' | 'followers' | 'views' | 'revenue' | 'engagement';
  period: 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly';
  target_value: number;
  unit: string;
  platform?: string;
  starts_at: string;
  ends_at: string;
  reminder_enabled?: boolean;
  reminder_schedule?: {
    days: string[];
    time: string;
    timezone?: string;
  };
}

export interface GoalUpdate {
  title?: string;
  description?: string;
  target_value?: number;
  status?: 'active' | 'paused' | 'completed' | 'failed' | 'archived';
  reminder_enabled?: boolean;
  reminder_schedule?: {
    days: string[];
    time: string;
    timezone?: string;
  };
}

export interface GoalCheckIn {
  id: string;
  goal_id: string;
  value_at_checkin: number;
  progress_pct: number;
  note?: string;
  agent_analysis?: string;
  checked_at: string;
}

export interface GoalCheckInCreate {
  value_at_checkin: number;
  note?: string;
}

export interface GoalHistory {
  goal_id: string;
  check_ins: GoalCheckIn[];
  total_check_ins: number;
}

export interface GoalListParams {
  page?: number;
  page_size?: number;
  status?: string;
  goal_type?: string;
  platform?: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// API FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * List goals
 */
export async function listGoals(
  params?: GoalListParams
): Promise<PaginatedResponse<Goal>> {
  const client = getApiClient();
  const queryParams = new URLSearchParams();
  
  if (params?.page) queryParams.append('page', params.page.toString());
  if (params?.page_size) queryParams.append('page_size', params.page_size.toString());
  if (params?.status) queryParams.append('status', params.status);
  if (params?.goal_type) queryParams.append('goal_type', params.goal_type);
  if (params?.platform) queryParams.append('platform', params.platform);
  
  const url = `/api/v1/goals${queryParams.toString() ? `?${queryParams}` : ''}`;
  return client.get<PaginatedResponse<Goal>>(url);
}

/**
 * Get goal by ID
 */
export async function getGoal(id: string): Promise<Goal> {
  const client = getApiClient();
  return client.get<Goal>(`/api/v1/goals/${id}`);
}

/**
 * Create new goal
 */
export async function createGoal(data: GoalCreate): Promise<Goal> {
  const client = getApiClient();
  return client.post<Goal>('/api/v1/goals', data);
}

/**
 * Update goal
 */
export async function updateGoal(id: string, data: GoalUpdate): Promise<Goal> {
  const client = getApiClient();
  return client.patch<Goal>(`/api/v1/goals/${id}`, data);
}

/**
 * Delete goal
 */
export async function deleteGoal(id: string): Promise<void> {
  const client = getApiClient();
  return client.delete<void>(`/api/v1/goals/${id}`);
}

/**
 * Create manual check-in
 */
export async function createCheckIn(
  goalId: string,
  data: GoalCheckInCreate
): Promise<GoalCheckIn> {
  const client = getApiClient();
  return client.post<GoalCheckIn>(`/api/v1/goals/${goalId}/check-in`, data);
}

/**
 * Get goal history
 */
export async function getGoalHistory(
  goalId: string,
  limit: number = 50
): Promise<GoalHistory> {
  const client = getApiClient();
  return client.get<GoalHistory>(`/api/v1/goals/${goalId}/history?limit=${limit}`);
}
