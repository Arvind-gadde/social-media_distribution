/**
 * Collaborations Hooks
 * 
 * React Query hooks for collaboration operations
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listCollaborations,
  getCollaboration,
  createCollaboration,
  updateCollaboration,
  deleteCollaboration,
  generateContract,
  getContract,
  updateCollaborationStatus,
  getCollaborationStats,
  type CollaborationListParams,
  type CollaborationCreate,
  type CollaborationUpdate,
} from '@contentflow/api-client';
import { toast } from '@/lib/toast';

// ═══════════════════════════════════════════════════════════════════════════════
// QUERY KEYS
// ═══════════════════════════════════════════════════════════════════════════════

export const collaborationKeys = {
  all: ['collaborations'] as const,
  lists: () => [...collaborationKeys.all, 'list'] as const,
  list: (params?: CollaborationListParams) => [...collaborationKeys.lists(), params] as const,
  details: () => [...collaborationKeys.all, 'detail'] as const,
  detail: (id: string) => [...collaborationKeys.details(), id] as const,
  contract: (id: string) => [...collaborationKeys.all, 'contract', id] as const,
  stats: () => [...collaborationKeys.all, 'stats'] as const,
};

// ═══════════════════════════════════════════════════════════════════════════════
// HOOKS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * List collaborations
 */
export function useCollaborationsList(params?: CollaborationListParams) {
  return useQuery({
    queryKey: collaborationKeys.list(params),
    queryFn: () => listCollaborations(params),
  });
}

/**
 * Get single collaboration
 */
export function useCollaboration(id: string) {
  return useQuery({
    queryKey: collaborationKeys.detail(id),
    queryFn: () => getCollaboration(id),
    enabled: !!id,
  });
}

/**
 * Get collaboration statistics
 */
export function useCollaborationStats() {
  return useQuery({
    queryKey: collaborationKeys.stats(),
    queryFn: getCollaborationStats,
  });
}

/**
 * Get contract for collaboration
 */
export function useContract(collaborationId: string) {
  return useQuery({
    queryKey: collaborationKeys.contract(collaborationId),
    queryFn: () => getContract(collaborationId),
    enabled: !!collaborationId,
  });
}

/**
 * Create collaboration
 */
export function useCreateCollaboration() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CollaborationCreate) => createCollaboration(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: collaborationKeys.lists() });
      queryClient.invalidateQueries({ queryKey: collaborationKeys.stats() });
      toast.success('Collaboration created successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to create collaboration: ${error.message}`);
    },
  });
}

/**
 * Update collaboration
 */
export function useUpdateCollaboration() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: CollaborationUpdate }) =>
      updateCollaboration(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: collaborationKeys.detail(variables.id) });
      queryClient.invalidateQueries({ queryKey: collaborationKeys.lists() });
      toast.success('Collaboration updated successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to update collaboration: ${error.message}`);
    },
  });
}

/**
 * Delete collaboration
 */
export function useDeleteCollaboration() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteCollaboration(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: collaborationKeys.lists() });
      queryClient.invalidateQueries({ queryKey: collaborationKeys.stats() });
      toast.success('Collaboration deleted successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to delete collaboration: ${error.message}`);
    },
  });
}

/**
 * Update collaboration status
 */
export function useUpdateCollaborationStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      updateCollaborationStatus(id, status),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: collaborationKeys.detail(variables.id) });
      queryClient.invalidateQueries({ queryKey: collaborationKeys.lists() });
      queryClient.invalidateQueries({ queryKey: collaborationKeys.stats() });
      toast.success('Status updated successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to update status: ${error.message}`);
    },
  });
}

/**
 * Generate contract
 */
export function useGenerateContract() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (collaborationId: string) => generateContract(collaborationId),
    onSuccess: (_, collaborationId) => {
      queryClient.invalidateQueries({ queryKey: collaborationKeys.contract(collaborationId) });
      toast.success('Contract generated successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to generate contract: ${error.message}`);
    },
  });
}

