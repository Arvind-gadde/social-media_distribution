/**
 * Billing API Client
 * 
 * Handles subscription and payment operations
 */

import { getApiClient } from './client';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface CheckoutRequest {
  price_id: string;
  success_url: string;
  cancel_url: string;
}

export interface CheckoutResponse {
  url: string;
}

export interface PortalRequest {
  return_url: string;
}

export interface PortalResponse {
  url: string;
}

export interface UsageResponse {
  posts_this_month: number;
  posts_limit: number;
  platforms_connected: number;
  platforms_limit: number;
}

// ═══════════════════════════════════════════════════════════════════════════════
// API FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Create Stripe checkout session
 */
export async function createCheckoutSession(data: CheckoutRequest): Promise<CheckoutResponse> {
  const client = getApiClient();
  return await client.post<CheckoutResponse>('/api/v1/billing/checkout', data);
}

/**
 * Create Stripe customer portal session
 */
export async function createPortalSession(data: PortalRequest): Promise<PortalResponse> {
  const client = getApiClient();
  return await client.post<PortalResponse>('/api/v1/billing/portal', data);
}

/**
 * Get current usage vs limits
 */
export async function getUsage(): Promise<UsageResponse> {
  const client = getApiClient();
  return await client.get<UsageResponse>('/api/v1/billing/usage');
}
