/**
 * Media Upload API Client
 */

import { getApiClient } from './client';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface MediaItem {
  id: string;
  user_id: string;
  filename: string;
  original_filename: string;
  file_type: string;
  file_size: number;
  mime_type: string;
  url: string;
  thumbnail_url: string | null;
  width: number | null;
  height: number | null;
  duration: number | null;
  metadata: Record<string, any>;
  created_at: string;
}

export interface PresignedUrlResponse {
  upload_url: string;
  file_url: string;
  file_id: string;
  expires_at: string;
}

export interface MediaListParams {
  page?: number;
  page_size?: number;
  file_type?: 'image' | 'video' | 'audio' | 'document';
  sort_by?: 'created_at' | 'filename' | 'file_size';
  sort_order?: 'asc' | 'desc';
}

export interface MediaListResponse {
  items: MediaItem[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface UploadProgressCallback {
  (progress: number): void;
}

// ═══════════════════════════════════════════════════════════════════════════════
// API FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

export const mediaApi = {
  /**
   * Get presigned URL for direct upload to S3/R2
   */
  async getPresignedUrl(filename: string, contentType: string): Promise<PresignedUrlResponse> {
    try {
      const client = getApiClient();
      return await client.post<PresignedUrlResponse>('/api/v1/media/presigned-url', {
        filename,
        content_type: contentType,
      });
    } catch (error) {
      throw error;
    }
  },

  /**
   * Upload file directly (multipart/form-data)
   */
  async uploadMedia(
    file: File,
    onProgress?: UploadProgressCallback
  ): Promise<MediaItem> {
    try {
      const client = getApiClient();
      const formData = new FormData();
      formData.append('file', file);

      const response = await client.post<MediaItem>(
        '/api/v1/media/upload',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          onUploadProgress: (progressEvent: { loaded: number; total?: number }) => {
            if (onProgress && progressEvent.total) {
              const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
              onProgress(progress);
            }
          },
        }
      );

      return response;
    } catch (error) {
      throw error;
    }
  },

  /**
   * Upload multiple files
   */
  async uploadMultipleMedia(
    files: File[],
    onProgress?: (fileIndex: number, progress: number) => void
  ): Promise<MediaItem[]> {
    try {
      const uploadPromises = files.map((file, index) =>
        this.uploadMedia(file, (progress) => {
          if (onProgress) {
            onProgress(index, progress);
          }
        })
      );

      return await Promise.all(uploadPromises);
    } catch (error) {
      throw error;
    }
  },

  /**
   * Upload to presigned URL (for large files)
   */
  async uploadToPresignedUrl(
    presignedUrl: string,
    file: File,
    onProgress?: UploadProgressCallback
  ): Promise<void> {
    try {
      const xhr = new XMLHttpRequest();

      return new Promise((resolve, reject) => {
        xhr.upload.addEventListener('progress', (e) => {
          if (e.lengthComputable && onProgress) {
            const progress = Math.round((e.loaded * 100) / e.total);
            onProgress(progress);
          }
        });

        xhr.addEventListener('load', () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve();
          } else {
            reject(new Error(`Upload failed with status ${xhr.status}`));
          }
        });

        xhr.addEventListener('error', () => {
          reject(new Error('Upload failed'));
        });

        xhr.open('PUT', presignedUrl);
        xhr.setRequestHeader('Content-Type', file.type);
        xhr.send(file);
      });
    } catch (error) {
      throw error;
    }
  },

  /**
   * List user's media library
   */
  async listMedia(params?: MediaListParams): Promise<MediaListResponse> {
    try {
      const client = getApiClient();
      return await client.get<MediaListResponse>('/api/v1/media', { params });
    } catch (error) {
      throw error;
    }
  },

  /**
   * Get single media item
   */
  async getMedia(id: string): Promise<MediaItem> {
    try {
      const client = getApiClient();
      return await client.get<MediaItem>(`/api/v1/media/${id}`);
    } catch (error) {
      throw error;
    }
  },

  /**
   * Delete media item
   */
  async deleteMedia(id: string): Promise<void> {
    try {
      const client = getApiClient();
      await client.delete<void>(`/api/v1/media/${id}`);
    } catch (error) {
      throw error;
    }
  },

  /**
   * Delete multiple media items
   */
  async deleteMultipleMedia(ids: string[]): Promise<void> {
    try {
      const client = getApiClient();
      await client.post<void>('/api/v1/media/delete-multiple', { ids });
    } catch (error) {
      throw error;
    }
  },

  /**
   * Process video (extract thumbnail, metadata, etc.)
   */
  async processVideo(id: string): Promise<MediaItem> {
    try {
      const client = getApiClient();
      return await client.post<MediaItem>(`/api/v1/media/${id}/process`);
    } catch (error) {
      throw error;
    }
  },

  /**
   * Generate thumbnail for video
   */
  async generateThumbnail(id: string, timeInSeconds?: number): Promise<{ thumbnail_url: string }> {
    try {
      const client = getApiClient();
      return await client.post<{ thumbnail_url: string }>(
        `/api/v1/media/${id}/thumbnail`,
        { time: timeInSeconds }
      );
    } catch (error) {
      throw error;
    }
  },
};
