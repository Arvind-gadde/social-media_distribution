/**
 * News API client — niche-aware article feed + create-content from article.
 */
import { getApiClient, PaginatedResponse } from './client';

export interface NewsArticle {
  id: string;
  title: string;
  description?: string | null;
  url: string;
  author?: string | null;
  published_at?: string | null;
  source?: string | null;
  source_url?: string | null;
  thumbnail_url?: string | null;
  relevance_score: number;
}

export interface NewsListResponse extends PaginatedResponse<NewsArticle> {
  niche?: string | null;
}

export interface ListNewsParams {
  page?: number;
  page_size?: number;
  niche?: string;
  relevance_threshold?: number;
}

export async function listNews(params: ListNewsParams = {}): Promise<NewsListResponse> {
  const client = getApiClient();
  const qs = new URLSearchParams();
  if (params.page) qs.append('page', params.page.toString());
  if (params.page_size) qs.append('page_size', params.page_size.toString());
  if (params.niche) qs.append('niche', params.niche);
  if (typeof params.relevance_threshold === 'number') {
    qs.append('relevance_threshold', params.relevance_threshold.toString());
  }
  const url = `/api/v1/news${qs.toString() ? `?${qs}` : ''}`;
  return client.get<NewsListResponse>(url);
}

export async function createContentFromNews(payload: {
  title: string;
  description?: string;
  url: string;
}): Promise<{ content_project_id: string }> {
  const client = getApiClient();
  return client.post<{ content_project_id: string }>('/api/v1/news/create-content', payload);
}
