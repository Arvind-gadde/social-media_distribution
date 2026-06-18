/**
 * Media Upload Hooks
 * 
 * React Query hooks for media upload and management
 */

import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { mediaApi, type MediaListParams, type MediaItem } from '@contentflow/api-client';
import { toast } from '@/lib/toast';

// ═══════════════════════════════════════════════════════════════════════════════
// QUERY KEYS
// ═══════════════════════════════════════════════════════════════════════════════

export const mediaKeys = {
  all: ['media'] as const,
  lists: () => [...mediaKeys.all, 'list'] as const,
  list: (params?: MediaListParams) => [...mediaKeys.lists(), params] as const,
  detail: (id: string) => [...mediaKeys.all, 'detail', id] as const,
};

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface UploadProgress {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
  result?: MediaItem;
}

// ═══════════════════════════════════════════════════════════════════════════════
// HOOKS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * List media library
 */
export function useMediaList(params?: MediaListParams) {
  return useQuery({
    queryKey: mediaKeys.list(params),
    queryFn: () => mediaApi.listMedia(params),
  });
}

/**
 * Get single media item
 */
export function useMedia(id: string) {
  return useQuery({
    queryKey: mediaKeys.detail(id),
    queryFn: () => mediaApi.getMedia(id),
    enabled: !!id,
  });
}

/**
 * Upload single file with progress tracking
 */
export function useMediaUpload() {
  const queryClient = useQueryClient();
  const [progress, setProgress] = useState(0);

  const mutation = useMutation({
    mutationFn: (file: File) => {
      setProgress(0);
      return mediaApi.uploadMedia(file, (p) => setProgress(p));
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: mediaKeys.lists() });
      toast.success('File uploaded successfully');
      setProgress(0);
    },
    onError: (error: Error) => {
      toast.error(`Upload failed: ${error.message}`);
      setProgress(0);
    },
  });

  return {
    ...mutation,
    progress,
  };
}

/**
 * Upload multiple files with individual progress tracking
 */
export function useMultipleMediaUpload() {
  const queryClient = useQueryClient();
  const [uploads, setUploads] = useState<UploadProgress[]>([]);

  const uploadFiles = useCallback(async (files: File[]) => {
    // Initialize upload progress for all files
    const initialUploads: UploadProgress[] = files.map(file => ({
      file,
      progress: 0,
      status: 'pending',
    }));
    setUploads(initialUploads);

    // Upload files sequentially (can be changed to parallel if needed)
    const results: MediaItem[] = [];
    
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      
      try {
        // Update status to uploading
        setUploads(prev => prev.map((upload, idx) =>
          idx === i ? { ...upload, status: 'uploading' } : upload
        ));

        // Upload file
        const result = await mediaApi.uploadMedia(file, (progress) => {
          setUploads(prev => prev.map((upload, idx) =>
            idx === i ? { ...upload, progress } : upload
          ));
        });

        // Update status to success
        setUploads(prev => prev.map((upload, idx) =>
          idx === i ? { ...upload, status: 'success', result } : upload
        ));

        results.push(result);
      } catch (error) {
        // Update status to error
        setUploads(prev => prev.map((upload, idx) =>
          idx === i ? {
            ...upload,
            status: 'error',
            error: error instanceof Error ? error.message : 'Upload failed',
          } : upload
        ));
      }
    }

    // Invalidate queries
    queryClient.invalidateQueries({ queryKey: mediaKeys.lists() });

    // Show summary toast
    const successCount = results.length;
    const failCount = files.length - successCount;
    
    if (failCount === 0) {
      toast.success(`All ${successCount} files uploaded successfully`);
    } else if (successCount === 0) {
      toast.error(`All ${failCount} files failed to upload`);
    } else {
      toast.info(`${successCount} uploaded, ${failCount} failed`);
    }

    return results;
  }, [queryClient]);

  const reset = useCallback(() => {
    setUploads([]);
  }, []);

  return {
    uploadFiles,
    uploads,
    reset,
    isUploading: uploads.some(u => u.status === 'uploading'),
    allComplete: uploads.length > 0 && uploads.every(u => u.status === 'success' || u.status === 'error'),
  };
}

/**
 * Delete media item
 */
export function useDeleteMedia() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => mediaApi.deleteMedia(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: mediaKeys.lists() });
      toast.success('Media deleted successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to delete: ${error.message}`);
    },
  });
}

/**
 * Delete multiple media items
 */
export function useDeleteMultipleMedia() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (ids: string[]) => mediaApi.deleteMultipleMedia(ids),
    onSuccess: (_, ids) => {
      queryClient.invalidateQueries({ queryKey: mediaKeys.lists() });
      toast.success(`${ids.length} items deleted successfully`);
    },
    onError: (error: Error) => {
      toast.error(`Failed to delete: ${error.message}`);
    },
  });
}

/**
 * Process video (extract metadata, thumbnail, etc.)
 */
export function useProcessVideo() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => mediaApi.processVideo(id),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: mediaKeys.detail(result.id) });
      queryClient.invalidateQueries({ queryKey: mediaKeys.lists() });
      toast.success('Video processed successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to process video: ${error.message}`);
    },
  });
}

/**
 * Generate video thumbnail
 */
export function useGenerateThumbnail() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, time }: { id: string; time?: number }) =>
      mediaApi.generateThumbnail(id, time),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: mediaKeys.detail(id) });
      toast.success('Thumbnail generated successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to generate thumbnail: ${error.message}`);
    },
  });
}

/**
 * Hook for drag-and-drop file upload
 */
export function useFileDropzone() {
  const [isDragging, setIsDragging] = useState(false);
  const [files, setFiles] = useState<File[]>([]);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const droppedFiles = Array.from(e.dataTransfer.files);
    setFiles(droppedFiles);
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files ? Array.from(e.target.files) : [];
    setFiles(selectedFiles);
  }, []);

  const clearFiles = useCallback(() => {
    setFiles([]);
  }, []);

  return {
    isDragging,
    files,
    handleDragEnter,
    handleDragLeave,
    handleDragOver,
    handleDrop,
    handleFileSelect,
    clearFiles,
  };
}

/**
 * Validate file before upload
 */
export function validateFile(
  file: File,
  options: {
    maxSize?: number; // in bytes
    allowedTypes?: string[]; // MIME types
  } = {}
): { valid: boolean; error?: string } {
  const { maxSize = 100 * 1024 * 1024, allowedTypes } = options; // Default 100MB

  // Check file size
  if (file.size > maxSize) {
    return {
      valid: false,
      error: `File size exceeds ${Math.round(maxSize / 1024 / 1024)}MB limit`,
    };
  }

  // Check file type
  if (allowedTypes && !allowedTypes.includes(file.type)) {
    return {
      valid: false,
      error: `File type ${file.type} is not allowed`,
    };
  }

  return { valid: true };
}

/**
 * Format file size for display
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}
