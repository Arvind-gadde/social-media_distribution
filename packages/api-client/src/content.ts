/**
 * Content API Client
 * 
 * Handles all content management operations:
 * - List, create, update, delete content
 * - Content ideas generation
 * - Content analytics
 * - Publishing and scheduling
 */

import { getApiClient, PaginatedResponse } from './client';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface ContentItem {
  id: string;
  title: string;
  caption?: string;
  script?: string;
  content_type: 'reel' | 'short' | 'post' | 'carousel' | 'story' | 'thread' | 'blog';
  status: 'draft' | 'review' | 'scheduled' | 'published' | 'archived' | 'failed';
  platforms: string[];
  scheduled_at?: string;
  published_at?: string;
  media_urls?: string[];
  thumbnail_url?: string;
  hashtags?: string[];
  total_views: number;
  total_likes: number;
  total_comments: number;
  total_shares: number;
  total_saves?: number;
  engagement_rate: number;
  reach?: number;
  impressions?: number;
  topComments?: Array<{
    author?: string;
    text: string;
    likes: number;
  }>;
  ai_generated: boolean;
  ai_score?: number;
  created_at: string;
  updated_at: string;
}

export interface ContentCreate {
  title?: string;
  caption?: string;
  script?: string;
  content_type: 'reel' | 'short' | 'post' | 'carousel' | 'story' | 'thread' | 'blog' | 'video';
  platforms: string[];
  status?: 'draft' | 'review' | 'scheduled' | 'published';
  scheduled_at?: string;
  hashtags?: string[];
  media_urls?: string[];
  thumbnail_url?: string;
}

export interface ContentUpdate {
  title?: string;
  caption?: string;
  script?: string;
  status?: 'draft' | 'review' | 'scheduled' | 'published' | 'archived';
  scheduled_at?: string;
  hashtags?: string[];
  platforms?: string[];
}

export interface ContentIdea {
  id: string;
  title: string;
  description?: string;
  hook?: string;
  content_type: string;
  platforms: string[];
  hashtags?: string[];
  estimated_virality: number;
  ai_rationale?: string;
  source: string;
  status: 'new' | 'saved' | 'in_progress' | 'used' | 'dismissed';
  created_at: string;
}

export interface ContentListParams {
  page?: number;
  page_size?: number;
  status?: string;
  content_type?: string;
  platform?: string;
  search?: string;
}

export interface ContentIdeasParams {
  page?: number;
  page_size?: number;
  status?: string;
  min_virality?: number;
}

// ═══════════════════════════════════════════════════════════════════════════════
// API FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * List content items
 */
export async function listContent(
  params?: ContentListParams
): Promise<PaginatedResponse<ContentItem>> {
  const client = getApiClient();
  const queryParams = new URLSearchParams();
  
  if (params?.page) queryParams.append('page', params.page.toString());
  if (params?.page_size) queryParams.append('page_size', params.page_size.toString());
  if (params?.status) queryParams.append('status', params.status);
  if (params?.content_type) queryParams.append('content_type', params.content_type);
  if (params?.platform) queryParams.append('platform', params.platform);
  if (params?.search) queryParams.append('search', params.search);
  
  const url = `/api/v1/content-projects${queryParams.toString() ? `?${queryParams}` : ''}`;
  return client.get<PaginatedResponse<ContentItem>>(url);
}

/**
 * Get content item by ID
 */
export async function getContent(id: string): Promise<ContentItem> {
  const client = getApiClient();
  return client.get<ContentItem>(`/api/v1/content-projects/${id}`);
}

/**
 * Create new content item
 */
export async function createContent(data: ContentCreate): Promise<ContentItem> {
  const client = getApiClient();
  return client.post<ContentItem>('/api/v1/content-projects', data);
}

/**
 * Update content item
 */
export async function updateContent(id: string, data: ContentUpdate): Promise<ContentItem> {
  const client = getApiClient();
  return client.patch<ContentItem>(`/api/v1/content-projects/${id}`, data);
}

/**
 * Delete content item
 */
export async function deleteContent(id: string): Promise<void> {
  const client = getApiClient();
  return client.delete<void>(`/api/v1/content-projects/${id}`);
}

/**
 * Publish content immediately
 */
export async function publishContent(id: string): Promise<ContentItem> {
  const client = getApiClient();
  return client.post<ContentItem>(`/api/v1/content-projects/${id}/publish`);
}

/**
 * Schedule content for later
 */
export async function scheduleContent(id: string, scheduledAt: string): Promise<ContentItem> {
  const client = getApiClient();
  return client.post<ContentItem>(`/api/v1/content-projects/${id}/schedule`, {
    scheduled_at: scheduledAt,
  });
}

/**
 * Get AI-generated content ideas
 */
export async function listContentIdeas(
  params?: ContentIdeasParams
): Promise<PaginatedResponse<ContentIdea>> {
  const client = getApiClient();
  const queryParams = new URLSearchParams();
  
  if (params?.page) queryParams.append('page', params.page.toString());
  if (params?.page_size) queryParams.append('page_size', params.page_size.toString());
  if (params?.status) queryParams.append('status', params.status);
  if (params?.min_virality) queryParams.append('min_virality', params.min_virality.toString());
  
  const url = `/api/v1/ideas${queryParams.toString() ? `?${queryParams}` : ''}`;
  return client.get<PaginatedResponse<ContentIdea>>(url);
}

/**
 * Generate new content ideas
 */
export async function generateContentIdeas(count: number = 5): Promise<ContentIdea[]> {
  const client = getApiClient();
  return client.post<ContentIdea[]>('/api/v1/ideas/generate', { count });
}

/**
 * Update content idea status
 */
export async function updateContentIdeaStatus(
  id: string,
  status: 'saved' | 'in_progress' | 'used' | 'dismissed'
): Promise<ContentIdea> {
  const client = getApiClient();
  return client.patch<ContentIdea>(`/api/v1/ideas/${id}/status`, { status });
}

/**
 * Create content from idea
 */
export async function createContentFromIdea(ideaId: string): Promise<ContentItem> {
  const client = getApiClient();
  return client.post<ContentItem>(`/api/v1/ideas/${ideaId}/create-content`);
}

/**
 * Analyze content for virality prediction
 */
export async function analyzeContent(id: string): Promise<{
  virality_score: number;
  strengths: string[];
  improvements: string[];
  predicted_views: number;
  predicted_engagement: number;
}> {
  const client = getApiClient();
  return client.post(`/api/v1/content-projects/${id}/analyze`);
}
