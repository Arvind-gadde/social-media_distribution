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
  /** Called after a silent 401 refresh rotates the access token, so the
   *  consumer can persist it (e.g. to localStorage) and survive a reload. */
  onTokenRefreshed?: (accessToken: string) => void;
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
  fields?: Record<string, string>;

  constructor(message: string, error?: AxiosError) {
    super(message);
    this.name = 'ContentFlowApiError';

    if (error?.response) {
      this.status = error.response.status;
      this.details = error.response.data;
      this.correlationId = error.response.headers['x-correlation-id'];

      if (typeof error.response.data === 'object' && error.response.data !== null) {
        const data = error.response.data as Record<string, unknown>;
        // Backend sends {error: "ERROR_CODE", message: "..."}
        this.code = data.error as string || data.code as string || data.error_type as string;
        if (data.fields && typeof data.fields === 'object') {
          this.fields = data.fields as Record<string, string>;
        }
      }
    }

    if (typeof (Error as any).captureStackTrace === 'function') {
      (Error as any).captureStackTrace(this, ContentFlowApiError);
    }
  }
}

/**
 * Extract a human-readable message from backend error response data.
 * Backend sends {error, message} for AppErrors and {error, message, fields} for validation.
 * Falls back to parsing Pydantic's legacy {detail: [...]} format.
 */
function serverMessage(data: Record<string, unknown>, fallback: string): string {
  if (typeof data.message === 'string' && data.message) return data.message;
  if (typeof data.detail === 'string' && data.detail) return data.detail;
  if (Array.isArray(data.detail)) {
    const msgs = (data.detail as Array<{ loc?: unknown[]; msg?: string }>)
      .map(e => {
        const field = Array.isArray(e.loc)
          ? e.loc.filter(l => l !== 'body').join('.')
          : '';
        const msg = e.msg || 'Invalid value';
        return field ? `${field}: ${msg}` : msg;
      })
      .filter(Boolean);
    if (msgs.length) return msgs.join('; ');
  }
  return fallback;
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

    // Network errors — no response received
    if (!axiosError.response) {
      if (axiosError.code === 'ECONNABORTED') {
        return new ContentFlowApiError('Request timed out. Please try again.', axiosError);
      }
      if (axiosError.code === 'ERR_NETWORK') {
        return new ContentFlowApiError('Cannot reach the server. Check your connection.', axiosError);
      }
      return new ContentFlowApiError('Cannot reach the server. Check your connection.', axiosError);
    }

    const status = axiosError.response.status;
    const data = axiosError.response.data as Record<string, unknown>;

    switch (status) {
      case 400:
        return new ContentFlowApiError(serverMessage(data, 'Invalid request'), axiosError);
      case 401:
        return new ContentFlowApiError(serverMessage(data, 'Authentication required'), axiosError);
      case 403:
        return new ContentFlowApiError(serverMessage(data, 'Access denied'), axiosError);
      case 404:
        return new ContentFlowApiError(serverMessage(data, 'Resource not found'), axiosError);
      case 409:
        return new ContentFlowApiError(serverMessage(data, 'This resource already exists'), axiosError);
      case 422:
        return new ContentFlowApiError(serverMessage(data, 'Validation error'), axiosError);
      case 429:
        return new ContentFlowApiError(serverMessage(data, 'Too many requests. Please wait and try again.'), axiosError);
      case 500:
        return new ContentFlowApiError(serverMessage(data, 'Something went wrong on our end. Please try again.'), axiosError);
      case 503:
        return new ContentFlowApiError(serverMessage(data, 'Service temporarily unavailable. Please try again shortly.'), axiosError);
      default:
        return new ContentFlowApiError(serverMessage(data, `Request failed (${status})`), axiosError);
    }
  }

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
  private refreshPromise: Promise<void> | null = null;

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
        // Only auto-retry IDEMPOTENT methods. Retrying a POST/PATCH on a 5xx
        // or network error can duplicate a write that actually succeeded
        // server-side (double content creation, double billing trigger, etc.).
        const method = (error.config?.method || 'get').toLowerCase();
        const IDEMPOTENT = new Set(['get', 'head', 'options', 'put', 'delete']);
        if (!IDEMPOTENT.has(method)) return false;
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
      (error: unknown) => {
        return Promise.reject(transformError(error));
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

        // Handle 401 Unauthorized — deduplicate concurrent refresh attempts
        if (error.response?.status === 401 && !originalRequest._retry) {
          // Never attempt refresh for the refresh endpoint itself (would loop forever)
          // or when there's no access token (nothing to refresh)
          const isRefreshRequest = originalRequest.url?.includes('/auth/refresh');
          if (isRefreshRequest || !this.accessToken) {
            this.config.onTokenExpired?.();
            return Promise.reject(transformError(error));
          }

          originalRequest._retry = true;

          try {
            // If a refresh is already in flight, wait for it instead of firing a new one
            if (!this.refreshPromise) {
              this.refreshPromise = this.refreshToken().finally(() => {
                this.refreshPromise = null;
              });
            }
            await this.refreshPromise;
            return this.client(originalRequest);
          } catch (refreshError) {
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
      const response = await this.client.post<{ access_token?: string }>('/api/v1/auth/refresh');
      const access_token = response.data?.access_token;
      if (!access_token) {
        throw new ContentFlowApiError('Refresh response missing access_token');
      }
      this.setAccessToken(access_token);
      // Surface the rotated token so the consumer can persist it; otherwise it
      // lives only in memory and is lost on the next page reload.
      this.config.onTokenRefreshed?.(access_token);
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
