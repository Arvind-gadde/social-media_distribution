/**
 * OAuth API Client
 */

import { getApiClient } from './client';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface OAuthPlatform {
  key: string;
  name: string;
  scopes: string[];
  supports_publishing: boolean;
  supports_analytics: boolean;
}

export interface OAuthPlatformsResponse {
  platforms: OAuthPlatform[];
}

// ═══════════════════════════════════════════════════════════════════════════════
// API FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

export const oauthApi = {
  /**
   * List all supported OAuth platforms
   */
  async listPlatforms(): Promise<OAuthPlatformsResponse> {
    try {
      const client = getApiClient();
      return await client.get<OAuthPlatformsResponse>('/api/v1/oauth/platforms');
    } catch (error) {
      throw error;
    }
  },

  /**
   * Initiate OAuth flow for a platform
   * Returns the authorization URL to redirect to
   */
  getAuthorizationUrl(platform: string): string {
    const client = getApiClient();
    return `${client.baseURL}/api/v1/oauth/${platform}/authorize`;
  },

  /**
   * Refresh OAuth token for an account
   */
  async refreshToken(platform: string, accountId: string): Promise<{ refreshed: boolean; account_id: string }> {
    try {
      const client = getApiClient();
      return await client.post<{ refreshed: boolean; account_id: string }>(
        `/api/v1/oauth/${platform}/refresh`,
        { account_id: accountId }
      );
    } catch (error) {
      throw error;
    }
  },

  /**
   * Revoke OAuth token for an account
   */
  async revokeToken(platform: string, accountId: string): Promise<{ revoked: boolean; account_id: string }> {
    try {
      const client = getApiClient();
      return await client.delete<{ revoked: boolean; account_id: string }>(
        `/api/v1/oauth/${platform}/revoke`,
        { data: { account_id: accountId } }
      );
    } catch (error) {
      throw error;
    }
  },
};