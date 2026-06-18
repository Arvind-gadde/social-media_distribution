/**
 * Authentication API Client
 */

import { getApiClient } from './client';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface User {
  id: string;
  email: string;
  name: string | null;
  username: string | null;
  display_name: string | null;
  avatar_url: string | null;
  cover_url: string | null;
  bio: string | null;
  timezone: string;
  locale: string;
  subscription_tier: string;
  subscription_expires_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}

export interface ProfileUpdateRequest {
  display_name?: string;
  username?: string;
  bio?: string;
  timezone?: string;
  locale?: string;
}

export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
}

export interface AuthResponse {
  user: User;
  access_token: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// API FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

export const authApi = {
  /**
   * Login with email and password
   */
  async login(data: LoginRequest): Promise<AuthResponse> {
    try {
      const client = getApiClient();
      return await client.post<AuthResponse>('/api/v1/auth/login', data);
    } catch (error) {
      throw error;
    }
  },

  /**
   * Register new user
   */
  async register(data: RegisterRequest): Promise<AuthResponse> {
    try {
      const client = getApiClient();
      return await client.post<AuthResponse>('/api/v1/auth/register', data);
    } catch (error) {
      throw error;
    }
  },

  /**
   * Logout current user
   */
  async logout(): Promise<void> {
    try {
      const client = getApiClient();
      await client.post<void>('/api/v1/auth/logout');
      client.setAccessToken(null);
      
      // Clear localStorage
      if (typeof window !== 'undefined') {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
      }
    } catch (error) {
      throw error;
    }
  },

  /**
   * Get current user
   */
  async me(): Promise<AuthResponse> {
    try {
      const client = getApiClient();
      return await client.get<AuthResponse>('/api/v1/auth/me');
    } catch (error) {
      throw error;
    }
  },

  /**
   * Refresh access token
   */
  async refresh(): Promise<AuthResponse> {
    try {
      const client = getApiClient();
      return await client.post<AuthResponse>('/api/v1/auth/refresh');
    } catch (error) {
      throw error;
    }
  },

  /**
   * Update user profile
   */
  async updateProfile(data: ProfileUpdateRequest): Promise<User> {
    try {
      const client = getApiClient();
      const response = await client.patch<User>('/api/v1/auth/profile', data);
      
      // Update localStorage
      if (typeof window !== 'undefined') {
        const storedUser = localStorage.getItem('user');
        if (storedUser) {
          const user = JSON.parse(storedUser);
          localStorage.setItem('user', JSON.stringify({ ...user, ...response }));
        }
      }
      
      return response;
    } catch (error) {
      throw error;
    }
  },

  /**
   * Change password
   */
  async changePassword(data: PasswordChangeRequest): Promise<void> {
    try {
      const client = getApiClient();
      await client.post<void>('/api/v1/auth/change-password', data);
    } catch (error) {
      throw error;
    }
  },

  /**
   * Upload avatar
   */
  async uploadAvatar(file: File): Promise<{ avatar_url: string }> {
    try {
      const client = getApiClient();
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await client.post<{ avatar_url: string }>(
        '/api/v1/auth/avatar',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );
      
      return response;
    } catch (error) {
      throw error;
    }
  },

  /**
   * Delete account
   */
  async deleteAccount(password: string): Promise<void> {
    try {
      const client = getApiClient();
      await client.post<void>('/api/v1/auth/delete-account', { password });
      client.setAccessToken(null);
      
      // Clear localStorage
      if (typeof window !== 'undefined') {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
      }
    } catch (error) {
      throw error;
    }
  },
};
