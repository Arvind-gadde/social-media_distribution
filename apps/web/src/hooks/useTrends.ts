/**
 * Trends Hooks
 * 
 * React Query hooks for trend-related API calls
 */

import { useQuery, useMutation, useQueryClient, type UseQueryOptions } from '@tanstack/react-query';
import { trendsApi, type Trend, type TrendStats, type ListTrendsParams, type CreateContentFromTrendRequest } from '@contentflow/api-client';

/**
 * List trends with filters
 */
export function useTrends(
  params: ListTrendsParams = {},
  options?: Omit<UseQueryOptions<any>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: ['trends', params],
    queryFn: () => trendsApi.list(params),
    ...options,
  });
}

/**
 * Get single trend details
 */
export function useTrend(
  trendId: string | null,
  options?: Omit<UseQueryOptions<Trend>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: ['trend', trendId],
    queryFn: () => trendsApi.get(trendId!),
    enabled: !!trendId,
    ...options,
  });
}

/**
 * Get trend statistics
 */
export function useTrendStats(options?: Omit<UseQueryOptions<TrendStats>, 'queryKey' | 'queryFn'>) {
  return useQuery({
    queryKey: ['trend-stats'],
    queryFn: () => trendsApi.getStats(),
    refetchInterval: 60000, // Refetch every minute
    ...options,
  });
}

/**
 * Create content from trend
 */
export function useCreateContentFromTrend() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ trendId, data }: { trendId: string; data: CreateContentFromTrendRequest }) =>
      trendsApi.createContent(trendId, data),
    onSuccess: () => {
      // Invalidate content queries if they exist
      queryClient.invalidateQueries({ queryKey: ['content'] });
    },
  });
}
