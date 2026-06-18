/**
 * Trends API Client
 * 
 * Handles all trend-related API calls with proper error handling
 */

import { getApiClient, PaginatedResponse } from './client';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface Trend {
  id: string;
  niche_id: string | null;
  platform: string | null;
  trend_type: string;
  title: string;
  description: string | null;
  hashtags: string[] | null;
  example_urls: string[] | null;
  trend_score: number;
  trend_velocity: number;
  peak_predicted_at: string | null;
  started_at: string | null;
  peaked_at: string | null;
  status: string;
  region: string;
  source: string | null;
  created_at: string;
  updated_at: string;
}

export interface TrendStats {
  status_counts: Record<string, number>;
  average_score: number;
  top_platforms: Array<{ platform: string; count: number }>;
  hot_trends: Array<{
    id: string;
    title: string;
    score: number;
    velocity: number;
    platform: string | null;
  }>;
  total_active: number;
}

export interface CreateContentFromTrendRequest {
  title: string;
  description?: string;
  content_type?: string;
  target_platforms?: string[];
}

export interface CreateContentFromTrendResponse {
  content_project_id: string;
  trend_id: string;
  title: string;
  status: string;
}

export interface ListTrendsParams {
  page?: number;
  page_size?: number;
  status?: 'rising' | 'peak' | 'declining' | 'dead' | 'evergreen';
  trend_type?: 'hashtag' | 'sound' | 'format' | 'topic' | 'challenge' | 'meme';
  platform?: string;
  niche_id?: string;
  min_score?: number;
}

// ═══════════════════════════════════════════════════════════════════════════════
// API FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

export const trendsApi = {
  /**
   * List trends with filters
   */
  async list(params: ListTrendsParams = {}): Promise<PaginatedResponse<Trend>> {
    try {
      const client = getApiClient();
      return await client.get<PaginatedResponse<Trend>>('/api/v1/trends', {
        params,
      });
    } catch (error) {
      throw error;
    }
  },

  /**
   * Get single trend details
   */
  async get(trendId: string): Promise<Trend> {
    try {
      const client = getApiClient();
      return await client.get<Trend>(`/api/v1/trends/${trendId}`);
    } catch (error) {
      throw error;
    }
  },

  /**
   * Create content project from trend
   */
  async createContent(
    trendId: string,
    data: CreateContentFromTrendRequest
  ): Promise<CreateContentFromTrendResponse> {
    try {
      const client = getApiClient();
      return await client.post<CreateContentFromTrendResponse>(
        `/api/v1/trends/${trendId}/create-content`,
        data
      );
    } catch (error) {
      throw error;
    }
  },

  /**
   * Get trend statistics
   */
  async getStats(): Promise<TrendStats> {
    try {
      const client = getApiClient();
      return await client.get<TrendStats>('/api/v1/trends/stats/summary');
    } catch (error) {
      throw error;
    }
  },
};
