/**
 * Billing Hooks
 * 
 * React Query hooks for billing and subscription operations
 */

import { useQuery, useMutation } from '@tanstack/react-query';
import {
  createCheckoutSession,
  createPortalSession,
  getUsage,
  type CheckoutRequest,
  type PortalRequest,
} from '@contentflow/api-client';
import { toast } from '@/lib/toast';
import { safeRedirectUrl } from '@/lib/safe-redirect';

// ═══════════════════════════════════════════════════════════════════════════════
// QUERY KEYS
// ═══════════════════════════════════════════════════════════════════════════════

export const billingKeys = {
  all: ['billing'] as const,
  usage: () => [...billingKeys.all, 'usage'] as const,
};

// ═══════════════════════════════════════════════════════════════════════════════
// HOOKS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Get current usage vs limits
 */
export function useUsage() {
  return useQuery({
    queryKey: billingKeys.usage(),
    queryFn: getUsage,
  });
}

/**
 * Create checkout session (redirects to Stripe)
 */
export function useCreateCheckout() {
  return useMutation({
    mutationFn: (data: CheckoutRequest) => createCheckoutSession(data),
    onSuccess: (response) => {
      window.location.href = safeRedirectUrl(response.url, '/settings/billing');
    },
    onError: (error: Error) => {
      toast.error(`Failed to create checkout: ${error.message}`);
    },
  });
}

/**
 * Create portal session (redirects to Stripe portal)
 */
export function useCreatePortal() {
  return useMutation({
    mutationFn: (data: PortalRequest) => createPortalSession(data),
    onSuccess: (response) => {
      window.location.href = safeRedirectUrl(response.url, '/settings/billing');
    },
    onError: (error: Error) => {
      toast.error(`Failed to open billing portal: ${error.message}`);
    },
  });
}
