import api from "./client";

export type SourceType = "x" | "linkedin" | "rss" | "github" | "reddit" | "hackernews" | "youtube" | "other";

export interface BrollAsset {
  type: string;
  url: string;
  label: string;
}

export interface ContentItem {
  id: string;
  source_key: string;
  source_label: string;
  source_url: string | null;
  source_type: SourceType;
  title: string;
  summary: string | null;
  key_points: string[];
  raw_content: string | null;
  category: string;
  relevance_score: number;
  is_trending: boolean;
  author: string | null;
  published_at: string | null;
  fetched_at: string;
  // Enriched insight fields
  virality_score: number;
  is_value_gap: boolean;
  suggested_angle: string | null;
  fact_check_passed: boolean | null;
  sentiment_breakdown: Record<string, number>;
  broll_assets: BrollAsset[];
}

export interface GeneratedPost {
  id: string;
  content_item_id: string;
  platform: string;
  hook: string | null;
  caption: string | null;
  hashtags: string[];
  call_to_action: string | null;
  script_outline: string | null;
  thread_tweets: string[];
  engagement_tips: string[];
  created_at: string;
  source_title: string | null;
  source_url: string | null;
}

export interface AgentStats {
  items_collected_24h: number;
  top_stories_24h: number;
  content_generated_7d: number;
  trending_now: number;
}

export interface FeedResponse {
  items: ContentItem[];
  total: number;
  trending_count: number;
  categories: string[];
  source_types: SourceType[];
}

export interface GenerateResponse {
  content_item: ContentItem;
  generated: Record<string, GeneratedPost>;
  platforms_generated: string[];
}

export const getAgentFeed = (params?: {
  category?: string;
  source_type?: string;
  min_score?: number;
  hours_back?: number;
  limit?: number;
  offset?: number;
}) => api.get<FeedResponse>("/agent/feed", { params });

export const getAgentStats = () => api.get<AgentStats>("/agent/stats");

export const generateContent = (content_item_id: string, platform: string = "all") =>
  api.post<GenerateResponse>("/agent/generate", { content_item_id, platform });

export const getGeneratedPosts = (params?: { platform?: string; limit?: number; offset?: number }) =>
  api.get<{ posts: GeneratedPost[]; total: number }>("/agent/posts", { params });

export const deleteGeneratedPost = (id: string) => api.delete(`/agent/posts/${id}`);

export const triggerCollection = () => api.post("/agent/run-collection");
