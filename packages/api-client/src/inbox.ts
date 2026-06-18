/**
 * DM Inbox API Client
 * 
 * Handles direct message inbox operations
 */

import { getApiClient } from './client';
import type { PaginatedResponse } from './client';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface DM {
  id: string;
  user_id: string;
  social_account_id: string;
  platform: string;
  sender_platform_id: string;
  sender_username: string;
  sender_display_name: string;
  sender_avatar_url?: string;
  sender_followers_count?: number;
  message_text: string;
  is_business_inquiry: boolean;
  ai_category?: string;
  ai_summary?: string;
  ai_sentiment?: number;
  ai_priority: number;
  ai_suggested_reply?: string;
  is_read: boolean;
  is_replied: boolean;
  collaboration_id?: string;
  received_at: string;
  platform_message_id: string;
  created_at: string;
}

export interface DMListParams {
  page?: number;
  page_size?: number;
  platform?: string;
  is_read?: boolean;
  is_business_inquiry?: boolean;
  ai_category?: string;
  min_priority?: number;
}

export interface DMReply {
  message: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// API FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * List DMs with optional filtering
 */
export async function listDMs(params?: DMListParams): Promise<PaginatedResponse<DM>> {
  const client = getApiClient();
  return await client.get<PaginatedResponse<DM>>('/api/v1/inbox/dms', { params });
}

/**
 * Get single DM by ID
 */
export async function getDM(id: string): Promise<DM> {
  const client = getApiClient();
  return await client.get<DM>(`/api/v1/inbox/dms/${id}`);
}

/**
 * Mark DM as read
 */
export async function markDMRead(id: string): Promise<DM> {
  const client = getApiClient();
  return await client.patch<DM>(`/api/v1/inbox/dms/${id}/read`);
}

/**
 * Mark DM as unread
 */
export async function markDMUnread(id: string): Promise<DM> {
  const client = getApiClient();
  return await client.patch<DM>(`/api/v1/inbox/dms/${id}/unread`);
}

/**
 * Reply to DM
 */
export async function replyToDM(id: string, data: DMReply): Promise<DM> {
  const client = getApiClient();
  return await client.post<DM>(`/api/v1/inbox/dms/${id}/reply`, data);
}

/**
 * Link DM to collaboration
 */
export async function linkDMToCollaboration(dmId: string, collaborationId: string): Promise<DM> {
  const client = getApiClient();
  return await client.patch<DM>(`/api/v1/inbox/dms/${dmId}/link`, {
    collaboration_id: collaborationId,
  });
}

/**
 * Get DM statistics
 */
export async function getDMStats(): Promise<{
  total_unread: number;
  total_business_inquiries: number;
  high_priority_count: number;
  by_platform: Record<string, number>;
  by_category: Record<string, number>;
}> {
  const client = getApiClient();
  return await client.get<{
    total_unread: number;
    total_business_inquiries: number;
    high_priority_count: number;
    by_platform: Record<string, number>;
    by_category: Record<string, number>;
  }>('/api/v1/inbox/dms/stats');
}

