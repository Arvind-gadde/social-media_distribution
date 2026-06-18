/**
 * DM Inbox Hooks
 * 
 * React Query hooks for inbox operations
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listDMs,
  getDM,
  markDMRead,
  markDMUnread,
  replyToDM,
  linkDMToCollaboration,
  getDMStats,
  type DMListParams,
  type DMReply,
} from '@contentflow/api-client';
import { toast } from '@/lib/toast';

// ═══════════════════════════════════════════════════════════════════════════════
// QUERY KEYS
// ═══════════════════════════════════════════════════════════════════════════════

export const inboxKeys = {
  all: ['inbox'] as const,
  lists: () => [...inboxKeys.all, 'list'] as const,
  list: (params?: DMListParams) => [...inboxKeys.lists(), params] as const,
  details: () => [...inboxKeys.all, 'detail'] as const,
  detail: (id: string) => [...inboxKeys.details(), id] as const,
  stats: () => [...inboxKeys.all, 'stats'] as const,
};

// ═══════════════════════════════════════════════════════════════════════════════
// HOOKS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * List DMs
 */
export function useDMList(params?: DMListParams) {
  return useQuery({
    queryKey: inboxKeys.list(params),
    queryFn: () => listDMs(params),
  });
}

/**
 * Get single DM
 */
export function useDM(id: string) {
  return useQuery({
    queryKey: inboxKeys.detail(id),
    queryFn: () => getDM(id),
    enabled: !!id,
  });
}

/**
 * Get DM statistics
 */
export function useDMStats() {
  return useQuery({
    queryKey: inboxKeys.stats(),
    queryFn: getDMStats,
  });
}

/**
 * Mark DM as read
 */
export function useMarkDMRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => markDMRead(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: inboxKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: inboxKeys.lists() });
      queryClient.invalidateQueries({ queryKey: inboxKeys.stats() });
    },
    onError: (error: Error) => {
      toast.error(`Failed to mark as read: ${error.message}`);
    },
  });
}

/**
 * Mark DM as unread
 */
export function useMarkDMUnread() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => markDMUnread(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: inboxKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: inboxKeys.lists() });
      queryClient.invalidateQueries({ queryKey: inboxKeys.stats() });
    },
    onError: (error: Error) => {
      toast.error(`Failed to mark as unread: ${error.message}`);
    },
  });
}

/**
 * Reply to DM
 */
export function useReplyToDM() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: DMReply }) => replyToDM(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: inboxKeys.detail(variables.id) });
      queryClient.invalidateQueries({ queryKey: inboxKeys.lists() });
      toast.success('Reply sent successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to send reply: ${error.message}`);
    },
  });
}

/**
 * Link DM to collaboration
 */
export function useLinkDMToCollaboration() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ dmId, collaborationId }: { dmId: string; collaborationId: string }) =>
      linkDMToCollaboration(dmId, collaborationId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: inboxKeys.detail(variables.dmId) });
      queryClient.invalidateQueries({ queryKey: inboxKeys.lists() });
      toast.success('Linked to collaboration');
    },
    onError: (error: Error) => {
      toast.error(`Failed to link: ${error.message}`);
    },
  });
}

