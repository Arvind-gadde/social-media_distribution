/**
 * Social Accounts API Client
 * 
 * Handles social media platform connections
 */

import { getApiClient } from './client';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface SocialAccount {
  id: string;
  platform: string;
  platform_username?: string;
  platform_display_name?: string;
  platform_avatar_url?: string;
  platform_url?: string;
  token_status: string;
  followers_count: number;
  following_count: number;
  posts_count: number;
  engagement_rate: number;
  is_active: boolean;
  is_primary: boolean;
  last_synced_at?: string;
  last_validated_at?: string;
  created_at: string;
}

export interface SocialAccountsListParams {
  platform?: string;
  include_inactive?: boolean;
}

export interface SocialAccountCreate {
  platform: string;
  platform_user_id: string;
  platform_username?: string;
  platform_display_name?: string;
  platform_avatar_url?: string;
  platform_url?: string;
  access_token?: string;
  refresh_token?: string;
}

export interface AccountHealth {
  account_id: string;
  platform: string;
  is_healthy: boolean;
  token_status: string;
  needs_refresh: boolean;
  needs_reauth: boolean;
  last_validated_at?: string;
  rate_limit_state?: Record<string, any>;
}

// ═══════════════════════════════════════════════════════════════════════════════
// API FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * List all connected social accounts
 */
export async function listSocialAccounts(
  params?: SocialAccountsListParams
): Promise<{ accounts: SocialAccount[]; total: number }> {
  const client = getApiClient();
  return await client.get<{ accounts: SocialAccount[]; total: number }>(
    '/api/v1/social-accounts',
    { params },
  );
}

/**
 * Get single social account by ID
 */
export async function getSocialAccount(id: string): Promise<{ account: SocialAccount }> {
  const client = getApiClient();
  return await client.get<{ account: SocialAccount }>(`/api/v1/social-accounts/${id}`);
}

/**
 * Connect new social account (for dev/testing)
 */
export async function connectSocialAccount(
  data: SocialAccountCreate
): Promise<{ account: SocialAccount }> {
  const client = getApiClient();
  return await client.post<{ account: SocialAccount }>('/api/v1/social-accounts', data);
}

/**
 * Disconnect social account
 */
export async function disconnectSocialAccount(id: string): Promise<{ disconnected: boolean; account_id: string }> {
  const client = getApiClient();
  return await client.delete<{ disconnected: boolean; account_id: string }>(
    `/api/v1/social-accounts/${id}`,
  );
}

/**
 * Set account as primary for its platform
 */
export async function setPrimaryAccount(id: string): Promise<{ primary: boolean; account_id: string }> {
  const client = getApiClient();
  return await client.post<{ primary: boolean; account_id: string }>(
    `/api/v1/social-accounts/${id}/set-primary`,
  );
}

/**
 * Check account health
 */
export async function checkAccountHealth(id: string): Promise<AccountHealth> {
  const client = getApiClient();
  return await client.get<AccountHealth>(`/api/v1/social-accounts/${id}/health`);
}
