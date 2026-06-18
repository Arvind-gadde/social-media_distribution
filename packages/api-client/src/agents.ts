/**
 * Agents API Client
 * 
 * Handles all AI agent operations:
 * - List and configure agents
 * - Trigger manual runs
 * - Get agent insights
 * - Monitor agent status
 */

import { getApiClient, PaginatedResponse } from './client';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export type AgentType =
  | 'niche_intelligence'
  | 'trend_detection'
  | 'analytics_intelligence'
  | 'competitor_intelligence'
  | 'content_research'
  | 'goal_reminder'
  | 'collaboration'
  | 'news_fetcher'
  | 'tips_tricks'
  | 'scheduling'
  | 'growth'
  | 'video_editor'
  | 'predictive_virality'
  | 'orchestrator';

export interface AgentConfig {
  id: string;
  agent_type: AgentType;
  agent_name: string;
  is_enabled: boolean;
  run_frequency: 'hourly' | 'every_6h' | 'daily' | 'weekly' | 'on_demand' | 'real_time';
  last_run_at?: string;
  next_run_at?: string;
  run_count: number;
  success_count: number;
  error_count: number;
  config: Record<string, unknown>;
  llm_model: string;
  temperature: number;
  max_tokens: number;
  created_at: string;
  updated_at: string;
}

export interface AgentConfigUpdate {
  is_enabled?: boolean;
  run_frequency?: 'hourly' | 'every_6h' | 'daily' | 'weekly' | 'on_demand' | 'real_time';
  config?: Record<string, unknown>;
  llm_model?: string;
  temperature?: number;
  max_tokens?: number;
}

export interface AgentRun {
  id: string;
  agent_config_id: string;
  status: 'running' | 'success' | 'failed' | 'cancelled';
  started_at: string;
  completed_at?: string;
  duration_ms?: number;
  input_data: Record<string, unknown>;
  output_data: Record<string, unknown>;
  error_message?: string;
  tokens_used: number;
  cost_usd: number;
  steps: Array<Record<string, unknown>>;
  created_at: string;
}

export interface AgentInsight {
  id: string;
  agent_type: AgentType;
  agent_run_id?: string;
  insight_type: string;
  title: string;
  body: string;
  action_type?: string;
  action_url?: string;
  action_label?: string;
  priority: number;
  is_read: boolean;
  is_dismissed: boolean;
  is_actioned: boolean;
  expires_at?: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface AgentInsightListParams {
  page?: number;
  page_size?: number;
  agent_type?: AgentType;
  insight_type?: string;
  is_read?: boolean;
  unread_only?: boolean;
  is_dismissed?: boolean;
  min_priority?: number;
}

// ═══════════════════════════════════════════════════════════════════════════════
// API FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * List all agent configurations
 */
export async function listAgents(): Promise<AgentConfig[]> {
  const client = getApiClient();
  return client.get<AgentConfig[]>('/api/v1/agents');
}

/**
 * Get agent configuration by type
 */
export async function getAgent(agentType: AgentType): Promise<AgentConfig> {
  const client = getApiClient();
  return client.get<AgentConfig>(`/api/v1/agents/${agentType}`);
}

/**
 * Update agent configuration
 */
export async function updateAgent(
  agentType: AgentType,
  data: AgentConfigUpdate
): Promise<AgentConfig> {
  const client = getApiClient();
  return client.patch<AgentConfig>(`/api/v1/agents/${agentType}`, data);
}

/**
 * Trigger manual agent run
 */
export async function runAgent(
  agentType: AgentType,
  inputData?: Record<string, unknown>
): Promise<AgentRun> {
  const client = getApiClient();
  return client.post<AgentRun>(`/api/v1/agents/${agentType}/run`, inputData || {});
}

/**
 * Get agent insights
 */
export async function listAgentInsights(
  params?: AgentInsightListParams
): Promise<PaginatedResponse<AgentInsight>> {
  const client = getApiClient();
  const queryParams = new URLSearchParams();
  
  if (params?.page) queryParams.append('page', params.page.toString());
  if (params?.page_size) queryParams.append('page_size', params.page_size.toString());
  if (params?.agent_type) queryParams.append('agent_type', params.agent_type);
  if (params?.insight_type) queryParams.append('insight_type', params.insight_type);
  if (params?.is_read !== undefined) queryParams.append('is_read', params.is_read.toString());
  if (params?.is_dismissed !== undefined) {
    queryParams.append('is_dismissed', params.is_dismissed.toString());
  }
  if (params?.min_priority) queryParams.append('min_priority', params.min_priority.toString());
  
  const url = `/api/v1/agents/insights${queryParams.toString() ? `?${queryParams}` : ''}`;
  return client.get<PaginatedResponse<AgentInsight>>(url);
}

/**
 * Mark insight as read
 */
export async function markInsightRead(id: string): Promise<AgentInsight> {
  const client = getApiClient();
  return client.patch<AgentInsight>(`/api/v1/agents/insights/${id}/read`, {});
}

/**
 * Dismiss insight
 */
export async function dismissInsight(id: string): Promise<AgentInsight> {
  const client = getApiClient();
  return client.patch<AgentInsight>(`/api/v1/agents/insights/${id}/dismiss`, {});
}

/**
 * Mark insight as actioned
 */
export async function actionInsight(id: string): Promise<AgentInsight> {
  const client = getApiClient();
  return client.patch<AgentInsight>(`/api/v1/agents/insights/${id}/action`, {});
}
