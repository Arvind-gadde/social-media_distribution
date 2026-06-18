/**
 * Social Accounts Hooks
 * 
 * React Query hooks for social media account operations
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listSocialAccounts,
  getSocialAccount,
  connectSocialAccount,
  disconnectSocialAccount,
  setPrimaryAccount,
  checkAccountHealth,
  type SocialAccountsListParams,
  type SocialAccountCreate,
} from '@contentflow/api-client';
import { toast } from '@/lib/toast';

// ═══════════════════════════════════════════════════════════════════════════════
// QUERY KEYS
// ═══════════════════════════════════════════════════════════════════════════════

export const socialAccountKeys = {
  all: ['social-accounts'] as const,
  lists: () => [...socialAccountKeys.all, 'list'] as const,
  list: (params?: SocialAccountsListParams) => [...socialAccountKeys.lists(), params] as const,
  details: () => [...socialAccountKeys.all, 'detail'] as const,
  detail: (id: string) => [...socialAccountKeys.details(), id] as const,
  health: (id: string) => [...socialAccountKeys.all, 'health', id] as const,
};

// ═══════════════════════════════════════════════════════════════════════════════
// HOOKS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * List social accounts
 */
export function useSocialAccountsList(params?: SocialAccountsListParams) {
  return useQuery({
    queryKey: socialAccountKeys.list(params),
    queryFn: () => listSocialAccounts(params),
  });
}

/**
 * Get single social account
 */
export function useSocialAccount(id: string) {
  return useQuery({
    queryKey: socialAccountKeys.detail(id),
    queryFn: () => getSocialAccount(id),
    enabled: !!id,
  });
}

/**
 * Check account health
 */
export function useAccountHealth(id: string) {
  return useQuery({
    queryKey: socialAccountKeys.health(id),
    queryFn: () => checkAccountHealth(id),
    enabled: !!id,
    refetchInterval: 60000, // Refetch every minute
  });
}

/**
 * Connect social account
 */
export function useConnectAccount() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: SocialAccountCreate) => connectSocialAccount(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: socialAccountKeys.lists() });
      toast.success('Account connected successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to connect account: ${error.message}`);
    },
  });
}

/**
 * Disconnect social account
 */
export function useDisconnectAccount() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => disconnectSocialAccount(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: socialAccountKeys.lists() });
      toast.success('Account disconnected successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to disconnect account: ${error.message}`);
    },
  });
}

/**
 * Set primary account
 */
export function useSetPrimaryAccount() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => setPrimaryAccount(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: socialAccountKeys.lists() });
      toast.success('Primary account updated');
    },
    onError: (error: Error) => {
      toast.error(`Failed to set primary account: ${error.message}`);
    },
  });
}
