import api from "./client";

export interface ContentItem {
  id: string;
  source_key: string;
  source_label: string;
  source_url: string | null;
  title: string;
  summary: string | null;
  key_points: string[];
  category: string;
  relevance_score: number;
  is_trending: boolean;
  author: string | null;
  published_at: string | null;
  fetched_at: string;
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
}

export interface GenerateResponse {
  content_item: ContentItem;
  generated: Record<string, GeneratedPost>;
  platforms_generated: string[];
}

export const getAgentFeed = (params?: {
  category?: string;
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
