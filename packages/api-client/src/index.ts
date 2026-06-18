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

// Export trends API
export { trendsApi } from './trends';
export type * from './trends';

// Export content API
export * from './content';

// Export goals API
export * from './goals';

// Export competitors API
export * from './competitors';

// Export agents API
export * from './agents';

// Export analytics API
export * from './analytics';

// Export inbox API
export * from './inbox';

// Export collaborations API
export * from './collaborations';

// Export social accounts API
export * from './social-accounts';

// Export billing API
export * from './billing';

// Export media API
export * from './media';

// Export news API
export * from './news';
