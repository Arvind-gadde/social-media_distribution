/**
 * AI Agents Management Hooks
 * 
 * React Query hooks for AI agent operations
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listAgents,
  getAgent,
  updateAgent,
  runAgent,
  listAgentInsights,
  markInsightRead,
  dismissInsight,
  actionInsight,
  type AgentType,
  type AgentConfig,
  type AgentConfigUpdate,
  type AgentInsightListParams,
} from '@contentflow/api-client';
import { toast } from '@/lib/toast';

// ═══════════════════════════════════════════════════════════════════════════════
// QUERY KEYS
// ═══════════════════════════════════════════════════════════════════════════════

export const agentKeys = {
  all: ['agents'] as const,
  lists: () => [...agentKeys.all, 'list'] as const,
  list: () => [...agentKeys.lists()] as const,
  details: () => [...agentKeys.all, 'detail'] as const,
  detail: (type: AgentType) => [...agentKeys.details(), type] as const,
  insights: () => [...agentKeys.all, 'insights'] as const,
  insightList: (params?: AgentInsightListParams) => [...agentKeys.insights(), params] as const,
};

// ═══════════════════════════════════════════════════════════════════════════════
// HOOKS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * List all agents
 */
export function useAgentsList() {
  return useQuery({
    queryKey: agentKeys.list(),
    queryFn: () => listAgents(),
  });
}

/**
 * Get single agent
 */
export function useAgent(agentType: AgentType) {
  return useQuery({
    queryKey: agentKeys.detail(agentType),
    queryFn: () => getAgent(agentType),
    enabled: !!agentType,
  });
}

/**
 * Update agent configuration
 */
export function useUpdateAgent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ agentType, data }: { agentType: AgentType; data: AgentConfigUpdate }) =>
      updateAgent(agentType, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: agentKeys.detail(variables.agentType) });
      queryClient.invalidateQueries({ queryKey: agentKeys.list() });
      toast.success('Agent configuration updated');
    },
    onError: (error: Error) => {
      toast.error(`Failed to update agent: ${error.message}`);
    },
  });
}

/**
 * Run agent manually
 */
export function useRunAgent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ 
      agentType, 
      inputData 
    }: { 
      agentType: AgentType; 
      inputData?: Record<string, unknown> 
    }) => runAgent(agentType, inputData),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: agentKeys.detail(variables.agentType) });
      queryClient.invalidateQueries({ queryKey: agentKeys.insights() });
      toast.success('Agent started successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to run agent: ${error.message}`);
    },
  });
}

/**
 * List agent insights
 */
export function useAgentInsights(params?: AgentInsightListParams) {
  return useQuery({
    queryKey: agentKeys.insightList(params),
    queryFn: () => listAgentInsights(params),
    refetchInterval: 30000, // Refetch every 30 seconds for new insights
  });
}

/**
 * Mark insight as read
 */
export function useMarkInsightRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => markInsightRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.insights() });
    },
    onError: (error: Error) => {
      toast.error(`Failed to mark as read: ${error.message}`);
    },
  });
}

/**
 * Dismiss insight
 */
export function useDismissInsight() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => dismissInsight(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.insights() });
      toast.success('Insight dismissed');
    },
    onError: (error: Error) => {
      toast.error(`Failed to dismiss insight: ${error.message}`);
    },
  });
}

/**
 * Mark insight as actioned
 */
export function useActionInsight() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => actionInsight(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.insights() });
    },
    onError: (error: Error) => {
      toast.error(`Failed to mark as actioned: ${error.message}`);
    },
  });
}
