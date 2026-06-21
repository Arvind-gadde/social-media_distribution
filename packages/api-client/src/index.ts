/**
 * ContentFlow API Client
 * 
 * Main entry point for the API client package
 */

// Export core client
export {
  ApiClient,
  createApiClient,
  getApiClient,
  ContentFlowApiError,
  type ApiClientConfig,
  type ApiError,
  type PaginatedResponse,
} from './client';

// Export auth API
export { authApi } from './auth';
export type * from './auth';

// Export content API
export * from './content';

// Export goals API
export * from './goals';

// Export analytics API
export * from './analytics';

// Export inbox API
export * from './inbox';

// Export OAuth API
export * from './oauth';

// Export social accounts API
export * from './social-accounts';

// Export billing API
export * from './billing';

// Export media API
export * from './media';
