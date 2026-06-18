/**
 * Auth & Profile Hooks
 * 
 * React Query hooks for authentication and profile operations
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { authApi, type ProfileUpdateRequest, type PasswordChangeRequest } from '@contentflow/api-client';
import { toast } from '@/lib/toast';

// ═══════════════════════════════════════════════════════════════════════════════
// QUERY KEYS
// ═══════════════════════════════════════════════════════════════════════════════

export const authKeys = {
  all: ['auth'] as const,
  me: () => [...authKeys.all, 'me'] as const,
};

// ═══════════════════════════════════════════════════════════════════════════════
// HOOKS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Get current user
 */
export function useCurrentUser() {
  return useQuery({
    queryKey: authKeys.me(),
    queryFn: () => authApi.me(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Update user profile
 */
export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ProfileUpdateRequest) => authApi.updateProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: authKeys.me() });
      toast.success('Profile updated successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to update profile: ${error.message}`);
    },
  });
}

/**
 * Change password
 */
export function useChangePassword() {
  return useMutation({
    mutationFn: (data: PasswordChangeRequest) => authApi.changePassword(data),
    onSuccess: () => {
      toast.success('Password changed successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to change password: ${error.message}`);
    },
  });
}

/**
 * Upload avatar
 */
export function useUploadAvatar() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) => authApi.uploadAvatar(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: authKeys.me() });
      toast.success('Avatar uploaded successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to upload avatar: ${error.message}`);
    },
  });
}

/**
 * Delete account
 */
export function useDeleteAccount() {
  return useMutation({
    mutationFn: (password: string) => authApi.deleteAccount(password),
    onSuccess: () => {
      toast.success('Account deleted successfully');
      // Redirect will be handled by the component
    },
    onError: (error: Error) => {
      toast.error(`Failed to delete account: ${error.message}`);
    },
  });
}

/**
 * Logout
 */
export function useLogout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => authApi.logout(),
    onSuccess: () => {
      queryClient.clear();
      toast.success('Logged out successfully');
      // Redirect will be handled by the component
    },
    onError: (error: Error) => {
      toast.error(`Failed to logout: ${error.message}`);
    },
  });
}
