/**
 * Content Management Hooks
 * 
 * React Query hooks for content operations
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listContent,
  getContent,
  createContent,
  updateContent,
  deleteContent,
  publishContent,
  scheduleContent,
  listContentIdeas,
  generateContentIdeas,
  updateContentIdeaStatus,
  createContentFromIdea,
  analyzeContent,
  type ContentItem,
  type ContentCreate,
  type ContentUpdate,
  type ContentIdea,
  type ContentListParams,
  type ContentIdeasParams,
} from '@contentflow/api-client';
import { toast } from '@/lib/toast';

// ═══════════════════════════════════════════════════════════════════════════════
// QUERY KEYS
// ═══════════════════════════════════════════════════════════════════════════════

export const contentKeys = {
  all: ['content'] as const,
  lists: () => [...contentKeys.all, 'list'] as const,
  list: (params?: ContentListParams) => [...contentKeys.lists(), params] as const,
  details: () => [...contentKeys.all, 'detail'] as const,
  detail: (id: string) => [...contentKeys.details(), id] as const,
  ideas: () => [...contentKeys.all, 'ideas'] as const,
  ideaList: (params?: ContentIdeasParams) => [...contentKeys.ideas(), params] as const,
};

// ═══════════════════════════════════════════════════════════════════════════════
// HOOKS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * List content items
 */
export function useContentList(params?: ContentListParams) {
  return useQuery({
    queryKey: contentKeys.list(params),
    queryFn: () => listContent(params),
  });
}

/**
 * Get single content item
 */
export function useContent(id: string) {
  return useQuery({
    queryKey: contentKeys.detail(id),
    queryFn: () => getContent(id),
    enabled: !!id,
  });
}

/**
 * Create content
 */
export function useCreateContent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ContentCreate) => createContent(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: contentKeys.lists() });
      toast.success('Content created successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to create content: ${error.message}`);
    },
  });
}

/**
 * Update content
 */
export function useUpdateContent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ContentUpdate }) =>
      updateContent(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: contentKeys.detail(variables.id) });
      queryClient.invalidateQueries({ queryKey: contentKeys.lists() });
      toast.success('Content updated successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to update content: ${error.message}`);
    },
  });
}

/**
 * Delete content
 */
export function useDeleteContent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteContent(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: contentKeys.lists() });
      toast.success('Content deleted successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to delete content: ${error.message}`);
    },
  });
}

/**
 * Publish content
 */
export function usePublishContent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => publishContent(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: contentKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: contentKeys.lists() });
      toast.success('Content published successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to publish content: ${error.message}`);
    },
  });
}

/**
 * Schedule content
 */
export function useScheduleContent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, scheduledAt }: { id: string; scheduledAt: string }) =>
      scheduleContent(id, scheduledAt),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: contentKeys.detail(variables.id) });
      queryClient.invalidateQueries({ queryKey: contentKeys.lists() });
      toast.success('Content scheduled successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to schedule content: ${error.message}`);
    },
  });
}

/**
 * List content ideas
 */
export function useContentIdeas(params?: ContentIdeasParams) {
  return useQuery({
    queryKey: contentKeys.ideaList(params),
    queryFn: () => listContentIdeas(params),
  });
}

/**
 * Generate new content ideas
 */
export function useGenerateIdeas() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (count: number = 5) => generateContentIdeas(count),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: contentKeys.ideas() });
      toast.success('New ideas generated');
    },
    onError: (error: Error) => {
      toast.error(`Failed to generate ideas: ${error.message}`);
    },
  });
}

/**
 * Update content idea status
 */
export function useUpdateIdeaStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      status,
    }: {
      id: string;
      status: 'saved' | 'in_progress' | 'used' | 'dismissed';
    }) => updateContentIdeaStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: contentKeys.ideas() });
    },
    onError: (error: Error) => {
      toast.error(`Failed to update idea: ${error.message}`);
    },
  });
}

/**
 * Create content from idea
 */
export function useCreateFromIdea() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (ideaId: string) => createContentFromIdea(ideaId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: contentKeys.lists() });
      queryClient.invalidateQueries({ queryKey: contentKeys.ideas() });
      toast.success('Content created from idea');
    },
    onError: (error: Error) => {
      toast.error(`Failed to create content: ${error.message}`);
    },
  });
}

/**
 * Analyze content for virality
 */
export function useAnalyzeContent() {
  return useMutation({
    mutationFn: (id: string) => analyzeContent(id),
    onError: (error: Error) => {
      toast.error(`Failed to analyze content: ${error.message}`);
    },
  });
}
