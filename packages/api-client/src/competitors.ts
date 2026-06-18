/**
 * Competitors API Client
 * 
 * Handles all competitor tracking and intelligence operations:
 * - Add, remove competitors
 * - Track competitor content
 * - Get AI analysis
 * - Performance comparison
 */

import { getApiClient, PaginatedResponse } from './client';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface Competitor {
  id: string;
  platform: string;
  platform_username: string;
  display_name?: string;
  avatar_url?: string;
  profile_url?: string;
  niche_id?: string;
  followers_count: number;
  following_count?: number;
  posts_count?: number;
  avg_engagement_rate: number;
  posting_frequency: number;
  is_active: boolean;
  tracking_since: string;
  last_tracked_at?: string;
  created_at: string;
}

export interface CompetitorCreate {
  platform: string;
  platform_username: string;
  niche_id?: string;
}

export interface CompetitorContent {
  id: string;
  competitor_id: string;
  observation_type: string;
  platform_post_id?: string;
  content_type?: string;
  content_summary?: string;
  caption?: string;
  hashtags?: string[];
  engagement_metrics?: Record<string, number>;
  viral_score: number;
  ai_analysis?: string;
  content_gaps?: string[];
  posted_at?: string;
  created_at: string;
}

export interface CompetitorAnalysis {
  competitor_id: string;
  platform: string;
  username: string;
  
  // Performance metrics
  avg_engagement_rate: number;
  posting_frequency: number;
  total_posts_tracked: number;
  
  // Content analysis
  top_performing_content_types: Array<{
    type: string;
    count: number;
    avg_viral_score: number;
  }>;
  common_hashtags: string[];
  posting_times: Record<string, number>;
  
  // AI insights
  content_strategy_summary: string;
  strengths: string[];
  weaknesses: string[];
  opportunities_for_you: string[];
  content_gaps?: string[];
  why_it_worked?: string;
  topics?: string[];
  
  // Trend analysis
  engagement_trend: 'increasing' | 'stable' | 'decreasing' | 'insufficient_data';
  follower_growth_estimate: number;
}

export interface CompetitorListParams {
  page?: number;
  page_size?: number;
  platform?: string;
  niche_id?: string;
  active_only?: boolean;
}

export interface CompetitorContentParams {
  page?: number;
  page_size?: number;
  min_viral_score?: number;
}

// ═══════════════════════════════════════════════════════════════════════════════
// API FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * List competitors
 */
export async function listCompetitors(
  params?: CompetitorListParams
): Promise<PaginatedResponse<Competitor>> {
  const client = getApiClient();
  const queryParams = new URLSearchParams();
  
  if (params?.page) queryParams.append('page', params.page.toString());
  if (params?.page_size) queryParams.append('page_size', params.page_size.toString());
  if (params?.platform) queryParams.append('platform', params.platform);
  if (params?.niche_id) queryParams.append('niche_id', params.niche_id);
  if (params?.active_only !== undefined) {
    queryParams.append('active_only', params.active_only.toString());
  }
  
  const url = `/api/v1/competitors${queryParams.toString() ? `?${queryParams}` : ''}`;
  return client.get<PaginatedResponse<Competitor>>(url);
}

/**
 * Add competitor to track
 */
export async function addCompetitor(data: CompetitorCreate): Promise<Competitor> {
  const client = getApiClient();
  return client.post<Competitor>('/api/v1/competitors', data);
}

/**
 * Get single competitor by ID
 */
export async function getCompetitor(id: string): Promise<Competitor> {
  const client = getApiClient();
  return client.get<Competitor>(`/api/v1/competitors/${id}`);
}

/**
 * Remove competitor (stop tracking)
 */
export async function removeCompetitor(id: string): Promise<void> {
  const client = getApiClient();
  return client.delete<void>(`/api/v1/competitors/${id}`);
}

/**
 * Get competitor content
 */
export async function getCompetitorContent(
  competitorId: string,
  params?: CompetitorContentParams
): Promise<PaginatedResponse<CompetitorContent>> {
  const client = getApiClient();
  const queryParams = new URLSearchParams();
  
  if (params?.page) queryParams.append('page', params.page.toString());
  if (params?.page_size) queryParams.append('page_size', params.page_size.toString());
  if (params?.min_viral_score) {
    queryParams.append('min_viral_score', params.min_viral_score.toString());
  }
  
  const url = `/api/v1/competitors/${competitorId}/content${
    queryParams.toString() ? `?${queryParams}` : ''
  }`;
  return client.get<PaginatedResponse<CompetitorContent>>(url);
}

/**
 * Get AI-powered competitor analysis
 */
export async function getCompetitorAnalysis(competitorId: string): Promise<CompetitorAnalysis> {
  const client = getApiClient();
  return client.get<CompetitorAnalysis>(`/api/v1/competitors/${competitorId}/analysis`);
}
