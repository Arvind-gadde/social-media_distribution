/**
 * Profile Settings Page
 * 
 * Manage personal information and preferences
 */

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useCurrentUser, useUpdateProfile, useUploadAvatar, useDeleteAccount } from '@/hooks/useAuth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export default function ProfileSettingsPage() {
  const router = useRouter();
  const { data: userData, isLoading, error, refetch } = useCurrentUser();
  const updateProfile = useUpdateProfile();
  const uploadAvatar = useUploadAvatar();
  const deleteAccount = useDeleteAccount();

  const [formData, setFormData] = useState({
    display_name: '',
    username: '',
    bio: '',
    timezone: 'America/New_York',
    locale: 'en',
  });

  const [deletePassword, setDeletePassword] = useState('');
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // Update form data when user data loads
  useEffect(() => {
    if (userData?.user) {
      setFormData({
        display_name: userData.user.display_name || '',
        username: userData.user.username || '',
        bio: userData.user.bio || '',
        timezone: userData.user.timezone || 'America/New_York',
        locale: userData.user.locale || 'en',
      });
    }
  }, [userData]);

  const handleSave = async () => {
    try {
      await updateProfile.mutateAsync(formData);
    } catch (error) {
      console.error('Failed to update profile:', error);
    }
  };

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file size (max 2MB)
    if (file.size > 2 * 1024 * 1024) {
      alert('File size must be less than 2MB');
      return;
    }

    // Validate file type
    if (!['image/jpeg', 'image/png', 'image/gif'].includes(file.type)) {
      alert('File must be JPG, PNG, or GIF');
      return;
    }

    try {
      await uploadAvatar.mutateAsync(file);
    } catch (error) {
      console.error('Failed to upload avatar:', error);
    }
  };

  const handleDeleteAccount = async () => {
    if (!deletePassword) {
      alert('Please enter your password to confirm');
      return;
    }

    try {
      await deleteAccount.mutateAsync(deletePassword);
      router.push('/login');
    } catch (error) {
      console.error('Failed to delete account:', error);
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-tech mx-auto mb-4" />
              <p className="text-muted-foreground">Loading profile...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="text-error text-5xl mb-4">⚠️</div>
              <h2 className="text-2xl font-bold mb-2">Failed to load profile</h2>
              <p className="text-muted-foreground mb-4">
                {error instanceof Error ? error.message : 'Something went wrong'}
              </p>
              <Button onClick={() => refetch()}>Retry</Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const user = userData?.user;

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <Button variant="outline" onClick={() => router.push('/settings')} className="mb-4">
            ← Back to Settings
          </Button>
          <h1 className="text-4xl font-bold gradient-text">Profile Settings</h1>
          <p className="text-muted-foreground mt-2">
            Manage your personal information
          </p>
        </div>

        {/* Profile Form */}
        <Card>
          <CardHeader>
            <CardTitle>Personal Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Avatar */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Profile Picture
              </label>
              <div className="flex items-center gap-4">
                <div className="w-20 h-20 rounded-full bg-tech/20 flex items-center justify-center text-3xl overflow-hidden">
                  {user?.avatar_url ? (
                    <img src={user.avatar_url} alt="Avatar" className="w-full h-full object-cover" />
                  ) : (
                    '👤'
                  )}
                </div>
                <div>
                  <input
                    type="file"
                    id="avatar-upload"
                    accept="image/jpeg,image/png,image/gif"
                    onChange={handleAvatarUpload}
                    className="hidden"
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => document.getElementById('avatar-upload')?.click()}
                    disabled={uploadAvatar.isPending}
                  >
                    {uploadAvatar.isPending ? 'Uploading...' : 'Upload New Photo'}
                  </Button>
                  <p className="text-xs text-muted-foreground mt-1">
                    JPG, PNG or GIF. Max 2MB.
                  </p>
                </div>
              </div>
            </div>

            {/* Display Name */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Display Name
              </label>
              <input
                type="text"
                value={formData.display_name}
                onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                className="w-full px-3 py-2 bg-surface rounded-md border border-input focus:outline-none focus:ring-2 focus:ring-tech"
                placeholder="Your display name"
              />
            </div>

            {/* Username */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Username
              </label>
              <input
                type="text"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                className="w-full px-3 py-2 bg-surface rounded-md border border-input focus:outline-none focus:ring-2 focus:ring-tech"
                placeholder="username"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Your unique username for ContentFlow AI
              </p>
            </div>

            {/* Email (read-only) */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Email Address
              </label>
              <input
                type="email"
                value={user?.email || ''}
                disabled
                className="w-full px-3 py-2 bg-surface/50 rounded-md border border-input opacity-60 cursor-not-allowed"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Email cannot be changed. Contact support if needed.
              </p>
            </div>

            {/* Bio */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Bio
              </label>
              <textarea
                value={formData.bio}
                onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
                className="w-full px-3 py-2 bg-surface rounded-md border border-input focus:outline-none focus:ring-2 focus:ring-tech min-h-[100px]"
                placeholder="Tell us about yourself..."
              />
              <p className="text-xs text-muted-foreground mt-1">
                {formData.bio.length}/500 characters
              </p>
            </div>

            {/* Timezone */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Timezone
              </label>
              <select
                value={formData.timezone}
                onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
                className="w-full px-3 py-2 bg-surface rounded-md border border-input focus:outline-none focus:ring-2 focus:ring-tech"
              >
                <option value="America/New_York">Eastern Time (ET)</option>
                <option value="America/Chicago">Central Time (CT)</option>
                <option value="America/Denver">Mountain Time (MT)</option>
                <option value="America/Los_Angeles">Pacific Time (PT)</option>
                <option value="Europe/London">London (GMT)</option>
                <option value="Europe/Paris">Paris (CET)</option>
                <option value="Asia/Tokyo">Tokyo (JST)</option>
              </select>
            </div>

            {/* Language */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Language
              </label>
              <select
                value={formData.locale}
                onChange={(e) => setFormData({ ...formData, locale: e.target.value })}
                className="w-full px-3 py-2 bg-surface rounded-md border border-input focus:outline-none focus:ring-2 focus:ring-tech"
              >
                <option value="en">English</option>
                <option value="es">Español</option>
                <option value="fr">Français</option>
                <option value="de">Deutsch</option>
                <option value="ja">日本語</option>
              </select>
            </div>

            {/* Actions */}
            <div className="flex gap-2 pt-4">
              <Button 
                onClick={handleSave} 
                disabled={updateProfile.isPending}
              >
                {updateProfile.isPending ? 'Saving...' : 'Save Changes'}
              </Button>
              <Button variant="outline" onClick={() => router.push('/settings')}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Danger Zone */}
        <Card className="mt-6 border-error">
          <CardHeader>
            <CardTitle className="text-error">Danger Zone</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {!showDeleteConfirm ? (
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">Delete Account</div>
                    <div className="text-sm text-muted-foreground">
                      Permanently delete your account and all data
                    </div>
                  </div>
                  <Button 
                    variant="outline" 
                    className="border-error text-error hover:bg-error/10"
                    onClick={() => setShowDeleteConfirm(true)}
                  >
                    Delete Account
                  </Button>
                </div>
              ) : (
                <div className="space-y-4">
                  <div>
                    <div className="font-medium text-error mb-2">⚠️ Confirm Account Deletion</div>
                    <p className="text-sm text-muted-foreground mb-4">
                      This action cannot be undone. All your data, content, and settings will be permanently deleted.
                    </p>
                    <label className="block text-sm font-medium mb-2">
                      Enter your password to confirm
                    </label>
                    <input
                      type="password"
                      value={deletePassword}
                      onChange={(e) => setDeletePassword(e.target.value)}
                      className="w-full px-3 py-2 bg-surface rounded-md border border-input focus:outline-none focus:ring-2 focus:ring-error"
                      placeholder="Your password"
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button 
                      variant="outline" 
                      className="border-error text-error hover:bg-error/10"
                      onClick={handleDeleteAccount}
                      disabled={deleteAccount.isPending || !deletePassword}
                    >
                      {deleteAccount.isPending ? 'Deleting...' : 'Confirm Delete'}
                    </Button>
                    <Button 
                      variant="outline"
                      onClick={() => {
                        setShowDeleteConfirm(false);
                        setDeletePassword('');
                      }}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
