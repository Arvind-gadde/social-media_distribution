/**
 * Shared TypeScript types for ContentFlow
 * 
 * These types mirror the Pydantic schemas from the FastAPI backend
 * and are used across web and mobile apps.
 */

// ═══════════════════════════════════════════════════════════════════════════════
// Core Domain Types
// ═══════════════════════════════════════════════════════════════════════════════

export interface User {
  id: string;
  email: string;
  name: string | null;
  username: string | null;
  avatar_url: string | null;
  workspace_id: string;
  created_at: string;
}

export interface Workspace {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  plan_tier: 'free' | 'pro' | 'business' | 'enterprise';
  timezone: string;
  locale: string;
  avatar_url: string | null;
  created_at: string;
}

export interface Niche {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  icon: string | null;
  color: string | null;
  keywords: string[];
  hashtags: string[];
}

// ═══════════════════════════════════════════════════════════════════════════════
// Content Types
// ═══════════════════════════════════════════════════════════════════════════════

export interface ContentVariant {
  id: string;
  workspace_id: string;
  title: string | null;
  caption: string | null;
  script: string | null;
  content_type: string;
  target_platform: string;
  status: 'draft' | 'review' | 'scheduled' | 'published' | 'archived';
  scheduled_at: string | null;
  published_at: string | null;
  media_urls: string[];
  thumbnail_url: string | null;
  hashtags: string[];
  created_at: string;
}

export interface PublishJob {
  id: string;
  workspace_id: string;
  content_variant_id: string;
  target_platform: string;
  scheduled_at: string;
  status: 'queued' | 'leased' | 'running' | 'completed' | 'failed';
  created_at: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Analytics Types
// ═══════════════════════════════════════════════════════════════════════════════

export interface ContentAnalytics {
  content_id: string;
  platform: string;
  views: number;
  likes: number;
  comments: number;
  shares: number;
  engagement_rate: number;
  recorded_at: string;
}

export interface AccountAnalytics {
  social_account_id: string;
  platform: string;
  followers_count: number;
  followers_gained: number;
  avg_engagement_rate: number;
  recorded_at: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Agent & Intelligence Types
// ═══════════════════════════════════════════════════════════════════════════════

export interface WorkspaceInsight {
  id: string;
  workspace_id: string;
  insight_type: string;
  title: string;
  body: string;
  action_url: string | null;
  action_label: string | null;
  priority: number;
  is_read: boolean;
  created_at: string;
}

export interface Trend {
  id: string;
  niche_id: string | null;
  platform: string | null;
  trend_type: string;
  title: string;
  description: string | null;
  hashtags: string[];
  trend_score: number;
  status: 'rising' | 'peak' | 'declining' | 'dead' | 'evergreen';
  created_at: string;
}

export interface CompetitorProfile {
  id: string;
  workspace_id: string;
  platform: string;
  platform_username: string;
  display_name: string | null;
  avatar_url: string | null;
  followers_count: number;
  avg_engagement_rate: number;
  is_active: boolean;
  created_at: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Business Types (Phase 8)
// ═══════════════════════════════════════════════════════════════════════════════

export interface DMInbox {
  id: string;
  workspace_id: string;
  platform: string;
  sender_username: string;
  sender_display_name: string | null;
  sender_followers_count: number | null;
  message_text: string;
  is_business_inquiry: boolean;
  ai_category: string | null;
  ai_priority: number;
  ai_summary: string | null;
  ai_suggested_reply: string | null;
  is_read: boolean;
  collaboration_id: string | null;
  received_at: string;
}

export interface Collaboration {
  id: string;
  workspace_id: string;
  collab_type: string;
  status: 'inquiry' | 'negotiating' | 'contract_sent' | 'in_progress' | 'completed';
  brand_name: string;
  contact_handle: string | null;
  title: string | null;
  deliverables: any[] | null;
  offered_amount: number | null;
  final_amount: number | null;
  currency: string;
  ai_score: number | null;
  ai_recommendation: string | null;
  created_at: string;
}

export interface ContractDraft {
  id: string;
  collaboration_id: string;
  title: string | null;
  content: string;
  status: 'draft' | 'sent' | 'signed';
  created_at: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Goal Types
// ═══════════════════════════════════════════════════════════════════════════════

export interface CreatorGoal {
  id: string;
  workspace_id: string;
  title: string;
  description: string | null;
  goal_type: string;
  period: 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly';
  target_value: number;
  current_value: number;
  unit: string;
  status: 'active' | 'paused' | 'completed' | 'failed';
  starts_at: string;
  ends_at: string;
  created_at: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// API Response Types
// ═══════════════════════════════════════════════════════════════════════════════

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface ApiError {
  detail: string;
  status_code: number;
}

export interface ApiSuccess {
  message: string;
  data?: any;
}

// ═══════════════════════════════════════════════════════════════════════════════
// WebSocket Types
// ═══════════════════════════════════════════════════════════════════════════════

export interface AgentStatusUpdate {
  agent_type: string;
  status: 'idle' | 'running' | 'completed' | 'failed';
  progress: number;
  message: string;
  timestamp: string;
}

export interface NotificationEvent {
  id: string;
  type: string;
  title: string;
  body: string;
  data: any;
  created_at: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Form Types
// ═══════════════════════════════════════════════════════════════════════════════

export interface LoginRequest {
  email: string;
  password: string;
}

export interface CreateContentRequest {
  title: string;
  caption: string;
  content_type: string;
  target_platforms: string[];
  scheduled_at?: string;
}

export interface UpdateGoalRequest {
  current_value: number;
  note?: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Utility Types
// ═══════════════════════════════════════════════════════════════════════════════

export type Platform = 
  | 'instagram'
  | 'youtube'
  | 'tiktok'
  | 'twitter'
  | 'linkedin'
  | 'facebook'
  | 'pinterest';

export type ContentType =
  | 'reel'
  | 'short'
  | 'post'
  | 'carousel'
  | 'story'
  | 'thread'
  | 'blog'
  | 'video';

export type AgentType =
  | 'trend_detection'
  | 'goal_accountability'
  | 'competitor_intelligence'
  | 'analytics_intelligence'
  | 'smart_scheduling'
  | 'niche_intelligence'
  | 'content_research'
  | 'collaboration_business'
  | 'news_research'
  | 'tips_algorithm'
  | 'growth_engagement'
  | 'video_intelligence'
  | 'predictive_virality';
