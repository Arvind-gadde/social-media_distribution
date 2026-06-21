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
   * Connect a Mastodon account via instance URL + access token (no redirect OAuth).
   */
  async connectMastodon(
    instanceUrl: string,
    accessToken: string
  ): Promise<{ id: string; platform: string; username: string; instance: string }> {
    const client = getApiClient();
    return await client.post<{ id: string; platform: string; username: string; instance: string }>(
      '/api/v1/oauth/mastodon/connect',
      { instance_url: instanceUrl, access_token: accessToken }
    );
  },

  /**
   * Connect a Bluesky account via handle + app-password (no redirect OAuth).
   */
  async connectBluesky(
    handle: string,
    appPassword: string,
    pdsUrl?: string
  ): Promise<{ id: string; platform: string; handle: string; did: string }> {
    const client = getApiClient();
    return await client.post<{ id: string; platform: string; handle: string; did: string }>(
      '/api/v1/oauth/bluesky/connect',
      { handle, app_password: appPassword, pds_url: pdsUrl }
    );
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