/**
 * Analytics API Client
 * 
 * Handles all analytics and performance tracking:
 * - Overview dashboard metrics
 * - Content performance
 * - Account analytics
 * - Platform comparison
 */

import { getApiClient } from './client';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface AnalyticsOverview {
  // Current period metrics
  total_views: number;
  total_likes: number;
  total_comments: number;
  total_shares: number;
  total_followers: number;
  avg_engagement_rate: number;
  
  // Comparison with previous period
  views_change: number;
  likes_change: number;
  comments_change: number;
  followers_change: number;
  engagement_change: number;
  
  // Platform breakdown
  platform_stats: Array<{
    platform: string;
    views: number;
    engagement_rate: number;
    followers: number;
  }>;
  
  // Top performing content
  top_content: Array<{
    id: string;
    title: string;
    views: number;
    engagement_rate: number;
    platform: string;
  }>;
  
  // Growth chart data
  growth_data: Array<{
    date: string;
    views: number;
    followers: number;
    engagement_rate: number;
  }>;
}

export interface ContentAnalytics {
  content_id: string;
  platform: string;
  
  // Engagement metrics
  views: number;
  likes: number;
  comments: number;
  shares: number;
  saves: number;
  reach: number;
  impressions: number;
  
  // Performance metrics
  engagement_rate: number;
  completion_rate?: number;
  avg_watch_time?: number;
  click_through_rate?: number;
  
  // Audience metrics
  audience_demographics?: {
    age_ranges: Record<string, number>;
    gender: Record<string, number>;
    locations: Record<string, number>;
  };
  
  // Time series data
  performance_over_time: Array<{
    timestamp: string;
    views: number;
    likes: number;
    comments: number;
  }>;
  
  // Comment intelligence
  top_comments?: Array<{
    text: string;
    likes: number;
    is_question: boolean;
    sentiment: number;
  }>;
  sentiment_breakdown?: {
    positive: number;
    neutral: number;
    negative: number;
  };
}

export interface AccountAnalytics {
  account_id: string;
  platform: string;
  
  // Current metrics
  followers_count: number;
  following_count: number;
  total_posts: number;
  avg_engagement_rate: number;
  
  // Growth metrics
  followers_gained: number;
  followers_lost: number;
  net_growth: number;
  growth_rate: number;
  
  // Content performance
  total_views: number;
  total_likes: number;
  total_comments: number;
  
  // Audience insights
  audience_demographics?: {
    age_ranges: Record<string, number>;
    gender: Record<string, number>;
    top_locations: string[];
    interests: string[];
  };
  
  // Best posting times
  optimal_posting_times?: Array<{
    day: string;
    hour: number;
    engagement_rate: number;
  }>;
  
  // Historical data
  historical_data: Array<{
    date: string;
    followers: number;
    engagement_rate: number;
    posts: number;
  }>;
}

export interface AnalyticsParams {
  start_date?: string;
  end_date?: string;
  platform?: string;
  compare_previous?: boolean;
}

// ═══════════════════════════════════════════════════════════════════════════════
// API FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Get analytics overview
 */
export async function getAnalyticsOverview(
  params?: AnalyticsParams
): Promise<AnalyticsOverview> {
  const client = getApiClient();
  const queryParams = new URLSearchParams();
  
  if (params?.start_date) queryParams.append('start_date', params.start_date);
  if (params?.end_date) queryParams.append('end_date', params.end_date);
  if (params?.platform) queryParams.append('platform', params.platform);
  if (params?.compare_previous !== undefined) {
    queryParams.append('compare_previous', params.compare_previous.toString());
  }
  
  const url = `/api/v1/analytics/overview${queryParams.toString() ? `?${queryParams}` : ''}`;
  return client.get<AnalyticsOverview>(url);
}

/**
 * Get content analytics
 */
export async function getContentAnalytics(
  contentId: string,
  params?: AnalyticsParams
): Promise<ContentAnalytics> {
  const client = getApiClient();
  const queryParams = new URLSearchParams();
  
  if (params?.start_date) queryParams.append('start_date', params.start_date);
  if (params?.end_date) queryParams.append('end_date', params.end_date);
  
  const url = `/api/v1/analytics/content/${contentId}${
    queryParams.toString() ? `?${queryParams}` : ''
  }`;
  return client.get<ContentAnalytics>(url);
}

/**
 * Get account analytics
 */
export async function getAccountAnalytics(
  accountId: string,
  params?: AnalyticsParams
): Promise<AccountAnalytics> {
  const client = getApiClient();
  const queryParams = new URLSearchParams();
  
  if (params?.start_date) queryParams.append('start_date', params.start_date);
  if (params?.end_date) queryParams.append('end_date', params.end_date);
  
  const url = `/api/v1/analytics/accounts/${accountId}${
    queryParams.toString() ? `?${queryParams}` : ''
  }`;
  return client.get<AccountAnalytics>(url);
}

/**
 * Get comment intelligence for content
 */
export async function getCommentIntelligence(contentId: string): Promise<{
  top_questions: Array<{ question: string; count: number }>;
  most_requested_topics: string[];
  sentiment_clusters: Array<{
    sentiment: 'positive' | 'neutral' | 'negative';
    count: number;
    examples: string[];
  }>;
  viral_comments: Array<{
    text: string;
    likes: number;
    should_reply: boolean;
    suggested_reply?: string;
  }>;
}> {
  const client = getApiClient();
  return client.get(`/api/v1/analytics/content/${contentId}/comments/intelligence`);
}
