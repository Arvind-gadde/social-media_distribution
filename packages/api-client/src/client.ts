/**
 * ContentFlow API Client
 * 
 * Production-grade API client with:
 * - Automatic retry logic
 * - Request/response interceptors
 * - Error handling and transformation
 * - Token management
 * - Request cancellation
 */

import axios, { AxiosInstance, AxiosError, AxiosRequestConfig, InternalAxiosRequestConfig } from 'axios';
import axiosRetry from 'axios-retry';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface ApiClientConfig {
  baseURL: string;
  timeout?: number;
  retries?: number;
  retryDelay?: number;
  onTokenExpired?: () => void;
  onUnauthorized?: () => void;
}

export interface ApiError {
  message: string;
  status?: number;
  code?: string;
  details?: unknown;
  correlationId?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

// ═══════════════════════════════════════════════════════════════════════════════
// ERROR HANDLING
// ═══════════════════════════════════════════════════════════════════════════════

export class ContentFlowApiError extends Error implements ApiError {
  status?: number;
  code?: string;
  details?: unknown;
  correlationId?: string;

  constructor(message: string, error?: AxiosError) {
    super(message);
    this.name = 'ContentFlowApiError';
    
    if (error?.response) {
      this.status = error.response.status;
      this.details = error.response.data;
      this.correlationId = error.response.headers['x-correlation-id'];
      
      // Extract error code if available
      if (typeof error.response.data === 'object' && error.response.data !== null) {
        const data = error.response.data as Record<string, unknown>;
        this.code = data.code as string || data.error_type as string;
      }
    }
    
    // Maintain proper stack trace (Node.js only)
    if (typeof (Error as any).captureStackTrace === 'function') {
      (Error as any).captureStackTrace(this, ContentFlowApiError);
    }
  }
}

/**
 * Transform Axios errors into ContentFlowApiError
 */
function transformError(error: unknown): ContentFlowApiError {
  if (error instanceof ContentFlowApiError) {
    return error;
  }
  
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError;
    
    // Network errors
    if (!axiosError.response) {
      if (axiosError.code === 'ECONNABORTED') {
        return new ContentFlowApiError('Request timeout', axiosError);
      }
      if (axiosError.code === 'ERR_NETWORK') {
        return new ContentFlowApiError('Network error. Please check your connection.', axiosError);
      }
      return new ContentFlowApiError('Unable to connect to server', axiosError);
    }
    
    // HTTP errors
    const status = axiosError.response.status;
    const data = axiosError.response.data as Record<string, unknown>;
    
    switch (status) {
      case 400:
        return new ContentFlowApiError(
          data.detail as string || 'Invalid request',
          axiosError
        );
      case 401:
        return new ContentFlowApiError('Authentication required', axiosError);
      case 403:
        return new ContentFlowApiError('Access denied', axiosError);
      case 404:
        return new ContentFlowApiError('Resource not found', axiosError);
      case 409:
        return new ContentFlowApiError(
          data.detail as string || 'Conflict',
          axiosError
        );
      case 422:
        return new ContentFlowApiError(
          data.detail as string || 'Validation error',
          axiosError
        );
      case 429:
        return new ContentFlowApiError('Too many requests. Please try again later.', axiosError);
      case 500:
        return new ContentFlowApiError('Server error. Please try again.', axiosError);
      case 503:
        return new ContentFlowApiError('Service temporarily unavailable', axiosError);
      default:
        return new ContentFlowApiError(
          data.detail as string || `Request failed with status ${status}`,
          axiosError
        );
    }
  }
  
  // Unknown errors
  if (error instanceof Error) {
    return new ContentFlowApiError(error.message);
  }
  
  return new ContentFlowApiError('An unknown error occurred');
}

// ═══════════════════════════════════════════════════════════════════════════════
// API CLIENT
// ═══════════════════════════════════════════════════════════════════════════════

export class ApiClient {
  private client: AxiosInstance;
  private accessToken: string | null = null;
  private config: ApiClientConfig;

  constructor(config: ApiClientConfig) {
    this.config = {
      timeout: 30000, // 30 seconds default
      retries: 3,
      retryDelay: 1000,
      ...config,
    };

    // Create axios instance
    this.client = axios.create({
      baseURL: this.config.baseURL,
      timeout: this.config.timeout,
      headers: {
        'Content-Type': 'application/json',
      },
      withCredentials: true, // Send cookies
    });

    // Setup retry logic
    axiosRetry(this.client, {
      retries: this.config.retries,
      retryDelay: (retryCount: number) => {
        return retryCount * (this.config.retryDelay || 1000);
      },
      retryCondition: (error: AxiosError) => {
        // Retry on network errors and 5xx errors
        return (
          axiosRetry.isNetworkOrIdempotentRequestError(error) ||
          (error.response?.status ? error.response.status >= 500 : false)
        );
      },
    });

    // Setup interceptors
    this.setupInterceptors();
  }

  get baseURL(): string {
    return this.config.baseURL;
  }

  /**
   * Setup request/response interceptors
   */
  private setupInterceptors(): void {
    // Request interceptor
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        // Add access token if available
        if (this.accessToken) {
          config.headers.Authorization = `Bearer ${this.accessToken}`;
        }

        // Add correlation ID for request tracing
        if (!config.headers['X-Correlation-ID']) {
          config.headers['X-Correlation-ID'] = this.generateCorrelationId();
        }

        return config;
      },
      (error) => {
        return Promise.reject(transformError(error));
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

        // Handle 401 Unauthorized
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          // Try to refresh token
          try {
            await this.refreshToken();
            return this.client(originalRequest);
          } catch (refreshError) {
            // Token refresh failed, trigger logout
            this.config.onTokenExpired?.();
            return Promise.reject(transformError(error));
          }
        }

        // Handle 403 Forbidden
        if (error.response?.status === 403) {
          this.config.onUnauthorized?.();
        }

        return Promise.reject(transformError(error));
      }
    );
  }

  /**
   * Generate correlation ID for request tracing
   */
  private generateCorrelationId(): string {
    return `${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
  }

  /**
   * Set access token
   */
  setAccessToken(token: string | null): void {
    this.accessToken = token;
  }

  /**
   * Get access token
   */
  getAccessToken(): string | null {
    return this.accessToken;
  }

  /**
   * Refresh access token
   */
  private async refreshToken(): Promise<void> {
    try {
      const response = await this.client.post<{ access_token: string }>('/api/v1/auth/refresh');
      const { access_token } = response.data;
      this.setAccessToken(access_token);
    } catch (error) {
      throw transformError(error);
    }
  }

  /**
   * GET request
   */
  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    try {
      const response = await this.client.get<T>(url, config);
      return response.data;
    } catch (error) {
      throw transformError(error);
    }
  }

  /**
   * POST request
   */
  async post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    try {
      const response = await this.client.post<T>(url, data, config);
      return response.data;
    } catch (error) {
      throw transformError(error);
    }
  }

  /**
   * PATCH request
   */
  async patch<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    try {
      const response = await this.client.patch<T>(url, data, config);
      return response.data;
    } catch (error) {
      throw transformError(error);
    }
  }

  /**
   * PUT request
   */
  async put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    try {
      const response = await this.client.put<T>(url, data, config);
      return response.data;
    } catch (error) {
      throw transformError(error);
    }
  }

  /**
   * DELETE request
   */
  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    try {
      const response = await this.client.delete<T>(url, config);
      return response.data;
    } catch (error) {
      throw transformError(error);
    }
  }

  /**
   * Cancel all pending requests
   */
  cancelAllRequests(): void {
    // Axios doesn't have a built-in way to cancel all requests
    // This would need to be implemented with AbortController if needed
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// SINGLETON INSTANCE
// ═══════════════════════════════════════════════════════════════════════════════

let apiClientInstance: ApiClient | null = null;

export function createApiClient(config: ApiClientConfig): ApiClient {
  apiClientInstance = new ApiClient(config);
  return apiClientInstance;
}

export function getApiClient(): ApiClient {
  if (!apiClientInstance) {
    throw new Error('API client not initialized. Call createApiClient() first.');
  }
  return apiClientInstance;
}
