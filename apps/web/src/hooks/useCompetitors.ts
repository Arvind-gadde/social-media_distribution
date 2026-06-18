/**
 * Competitors Management Hooks
 * 
 * React Query hooks for competitor tracking and intelligence
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listCompetitors,
  getCompetitor,
  addCompetitor,
  removeCompetitor,
  getCompetitorContent,
  getCompetitorAnalysis,
  type Competitor,
  type CompetitorCreate,
  type CompetitorListParams,
  type CompetitorContentParams,
} from '@contentflow/api-client';
import { toast } from '@/lib/toast';

// ═══════════════════════════════════════════════════════════════════════════════
// QUERY KEYS
// ═══════════════════════════════════════════════════════════════════════════════

export const competitorKeys = {
  all: ['competitors'] as const,
  lists: () => [...competitorKeys.all, 'list'] as const,
  list: (params?: CompetitorListParams) => [...competitorKeys.lists(), params] as const,
  details: () => [...competitorKeys.all, 'detail'] as const,
  detail: (id: string) => [...competitorKeys.details(), id] as const,
  content: (id: string, params?: CompetitorContentParams) => 
    [...competitorKeys.all, 'content', id, params] as const,
  analysis: (id: string) => [...competitorKeys.all, 'analysis', id] as const,
};

// ═══════════════════════════════════════════════════════════════════════════════
// HOOKS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * List competitors
 */
export function useCompetitorsList(params?: CompetitorListParams) {
  return useQuery({
    queryKey: competitorKeys.list(params),
    queryFn: () => listCompetitors(params),
  });
}

/**
 * Get single competitor
 */
export function useCompetitor(id: string) {
  return useQuery({
    queryKey: competitorKeys.detail(id),
    queryFn: () => getCompetitor(id),
    enabled: !!id,
  });
}

/**
 * Add competitor
 */
export function useAddCompetitor() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CompetitorCreate) => addCompetitor(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: competitorKeys.lists() });
      toast.success('Competitor added successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to add competitor: ${error.message}`);
    },
  });
}

/**
 * Remove competitor
 */
export function useRemoveCompetitor() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => removeCompetitor(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: competitorKeys.lists() });
      toast.success('Competitor removed');
    },
    onError: (error: Error) => {
      toast.error(`Failed to remove competitor: ${error.message}`);
    },
  });
}

/**
 * Get competitor content
 */
export function useCompetitorContent(
  competitorId: string,
  params?: CompetitorContentParams
) {
  return useQuery({
    queryKey: competitorKeys.content(competitorId, params),
    queryFn: () => getCompetitorContent(competitorId, params),
    enabled: !!competitorId,
  });
}

/**
 * Get competitor analysis
 */
export function useCompetitorAnalysis(competitorId: string) {
  return useQuery({
    queryKey: competitorKeys.analysis(competitorId),
    queryFn: () => getCompetitorAnalysis(competitorId),
    enabled: !!competitorId,
    staleTime: 5 * 60 * 1000, // 5 minutes - analysis is expensive
  });
}
