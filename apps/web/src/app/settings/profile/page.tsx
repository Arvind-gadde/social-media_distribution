'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { User, RefreshCw, AlertTriangle } from 'lucide-react';
import { useCurrentUser, useUpdateProfile, useUploadAvatar, useDeleteAccount } from '@/hooks/useAuth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert } from '@/components/ui/alert';
import { EmptyState } from '@/components/ui/empty-state';
import { Spinner } from '@/components/ui/spinner';
import {
  Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbLink, BreadcrumbSeparator, BreadcrumbPage,
} from '@/components/ui/breadcrumb';

const inputCls = 'w-full rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-50 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-brand-500/24 disabled:opacity-50 disabled:cursor-not-allowed';

export default function ProfileSettingsPage() {
  const router = useRouter();
  const { data: userData, isLoading, error, refetch } = useCurrentUser();
  const updateProfile = useUpdateProfile();
  const uploadAvatar = useUploadAvatar();
  const deleteAccount = useDeleteAccount();

  const [formData, setFormData] = useState({
    display_name: '', username: '', bio: '', timezone: 'America/New_York', locale: 'en',
  });
  const [deletePassword, setDeletePassword] = useState('');
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

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
    try { await updateProfile.mutateAsync(formData); } catch (e) { console.error(e); }
  };

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) { alert('File size must be less than 2MB'); return; }
    if (!['image/jpeg', 'image/png', 'image/gif'].includes(file.type)) { alert('File must be JPG, PNG, or GIF'); return; }
    try { await uploadAvatar.mutateAsync(file); } catch (e) { console.error(e); }
  };

  const handleDeleteAccount = async () => {
    if (!deletePassword) { alert('Please enter your password to confirm'); return; }
    try {
      await deleteAccount.mutateAsync(deletePassword);
      router.push('/login');
    } catch (e) { console.error(e); }
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Spinner size="lg" color="primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <EmptyState
          icon={<User />}
          iconColor="error"
          title="Failed to load profile"
          description={error instanceof Error ? error.message : 'Something went wrong'}
          actions={<Button onClick={() => refetch()} leadingIcon={<RefreshCw className="h-4 w-4" />}>Retry</Button>}
        />
      </div>
    );
  }

  const user = userData?.user;

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-10 space-y-8 animate-fade-in">
        <header>
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem><BreadcrumbLink href="/settings">Settings</BreadcrumbLink></BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem><BreadcrumbPage>Profile</BreadcrumbPage></BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
          <div className="mt-4 space-y-1">
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">Profile Settings</h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">Manage your personal information.</p>
          </div>
        </header>

        <Card>
          <CardHeader><CardTitle>Personal Information</CardTitle></CardHeader>
          <CardContent className="space-y-6">
            {/* Avatar */}
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">Profile Picture</label>
              <div className="flex items-center gap-4">
                <div className="h-20 w-20 shrink-0 rounded-full bg-brand-50 dark:bg-brand-950/40 flex items-center justify-center text-3xl overflow-hidden">
                  {user?.avatar_url ? (
                    <img src={user.avatar_url} alt="Avatar" className="w-full h-full object-cover" />
                  ) : '👤'}
                </div>
                <div>
                  <input type="file" id="avatar-upload" accept="image/jpeg,image/png,image/gif" onChange={handleAvatarUpload} className="hidden" />
                  <Button variant="secondary" size="sm" disabled={uploadAvatar.isPending} loading={uploadAvatar.isPending} onClick={() => document.getElementById('avatar-upload')?.click()}>
                    {uploadAvatar.isPending ? 'Uploading...' : 'Upload New Photo'}
                  </Button>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">JPG, PNG or GIF. Max 2MB.</p>
                </div>
              </div>
            </div>

            {[
              { label: 'Display Name', key: 'display_name', placeholder: 'Your display name', hint: undefined },
              { label: 'Username', key: 'username', placeholder: 'username', hint: 'Your unique username for ContentFlow AI' },
            ].map((field) => (
              <div key={field.key}>
                <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">{field.label}</label>
                <input
                  type="text"
                  className={inputCls}
                  placeholder={field.placeholder}
                  value={(formData as any)[field.key]}
                  onChange={(e) => setFormData({ ...formData, [field.key]: e.target.value })}
                />
                {field.hint && <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{field.hint}</p>}
              </div>
            ))}

            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">Email Address</label>
              <input type="email" value={user?.email || ''} disabled className={inputCls} />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Email cannot be changed. Contact support if needed.</p>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">Bio</label>
              <textarea
                className={`${inputCls} min-h-[100px] resize-y`}
                value={formData.bio}
                onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
                placeholder="Tell us about yourself..."
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{formData.bio.length}/500 characters</p>
            </div>

            {[
              {
                label: 'Timezone', key: 'timezone',
                options: [
                  { value: 'America/New_York', label: 'Eastern Time (ET)' },
                  { value: 'America/Chicago', label: 'Central Time (CT)' },
                  { value: 'America/Denver', label: 'Mountain Time (MT)' },
                  { value: 'America/Los_Angeles', label: 'Pacific Time (PT)' },
                  { value: 'Europe/London', label: 'London (GMT)' },
                  { value: 'Europe/Paris', label: 'Paris (CET)' },
                  { value: 'Asia/Tokyo', label: 'Tokyo (JST)' },
                ],
              },
              {
                label: 'Language', key: 'locale',
                options: [
                  { value: 'en', label: 'English' },
                  { value: 'es', label: 'Español' },
                  { value: 'fr', label: 'Français' },
                  { value: 'de', label: 'Deutsch' },
                  { value: 'ja', label: '日本語' },
                ],
              },
            ].map((sel) => (
              <div key={sel.key}>
                <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">{sel.label}</label>
                <select
                  className={inputCls}
                  value={(formData as any)[sel.key]}
                  onChange={(e) => setFormData({ ...formData, [sel.key]: e.target.value })}
                >
                  {sel.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
            ))}

            <div className="flex gap-2 pt-2">
              <Button variant="primary" onClick={handleSave} disabled={updateProfile.isPending} loading={updateProfile.isPending}>
                {updateProfile.isPending ? 'Saving...' : 'Save Changes'}
              </Button>
              <Button variant="secondary" onClick={() => router.push('/settings')}>Cancel</Button>
            </div>
          </CardContent>
        </Card>

        {/* Danger Zone */}
        <Card className="border-error-200 dark:border-error-800">
          <CardHeader>
            <CardTitle className="text-error-700 dark:text-error-400 flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" /> Danger Zone
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!showDeleteConfirm ? (
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900 dark:text-gray-50">Delete Account</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Permanently delete your account and all data.</p>
                </div>
                <Button variant="destructive" onClick={() => setShowDeleteConfirm(true)}>Delete Account</Button>
              </div>
            ) : (
              <div className="space-y-4">
                <Alert
                  variant="error"
                  title="This action cannot be undone"
                  description="All your data, content, and settings will be permanently deleted."
                />
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">Enter your password to confirm</label>
                  <input
                    type="password"
                    className={inputCls}
                    value={deletePassword}
                    onChange={(e) => setDeletePassword(e.target.value)}
                    placeholder="Your password"
                  />
                </div>
                <div className="flex gap-2">
                  <Button variant="destructive" onClick={handleDeleteAccount} disabled={deleteAccount.isPending || !deletePassword} loading={deleteAccount.isPending}>
                    {deleteAccount.isPending ? 'Deleting...' : 'Confirm Delete'}
                  </Button>
                  <Button variant="secondary" onClick={() => { setShowDeleteConfirm(false); setDeletePassword(''); }}>Cancel</Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
