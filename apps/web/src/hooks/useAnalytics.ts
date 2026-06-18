/**
 * Analytics Hooks
 * 
 * React Query hooks for analytics and performance tracking
 */

import { useQuery } from '@tanstack/react-query';
import {
  getAnalyticsOverview,
  getContentAnalytics,
  getAccountAnalytics,
  getCommentIntelligence,
  type AnalyticsParams,
} from '@contentflow/api-client';

// ═══════════════════════════════════════════════════════════════════════════════
// QUERY KEYS
// ═══════════════════════════════════════════════════════════════════════════════

export const analyticsKeys = {
  all: ['analytics'] as const,
  overview: (params?: AnalyticsParams) => [...analyticsKeys.all, 'overview', params] as const,
  content: (id: string, params?: AnalyticsParams) => 
    [...analyticsKeys.all, 'content', id, params] as const,
  account: (id: string, params?: AnalyticsParams) => 
    [...analyticsKeys.all, 'account', id, params] as const,
  comments: (contentId: string) => [...analyticsKeys.all, 'comments', contentId] as const,
};

// ═══════════════════════════════════════════════════════════════════════════════
// HOOKS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Get analytics overview
 */
export function useAnalyticsOverview(params?: AnalyticsParams) {
  return useQuery({
    queryKey: analyticsKeys.overview(params),
    queryFn: () => getAnalyticsOverview(params),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

/**
 * Get content analytics
 */
export function useContentAnalytics(contentId: string, params?: AnalyticsParams) {
  return useQuery({
    queryKey: analyticsKeys.content(contentId, params),
    queryFn: () => getContentAnalytics(contentId, params),
    enabled: !!contentId,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

/**
 * Get account analytics
 */
export function useAccountAnalytics(accountId: string, params?: AnalyticsParams) {
  return useQuery({
    queryKey: analyticsKeys.account(accountId, params),
    queryFn: () => getAccountAnalytics(accountId, params),
    enabled: !!accountId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Get comment intelligence
 */
export function useCommentIntelligence(contentId: string) {
  return useQuery({
    queryKey: analyticsKeys.comments(contentId),
    queryFn: () => getCommentIntelligence(contentId),
    enabled: !!contentId,
    staleTime: 10 * 60 * 1000, // 10 minutes - expensive operation
  });
}
