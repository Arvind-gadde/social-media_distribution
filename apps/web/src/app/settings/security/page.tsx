'use client';

import { useState } from 'react';
import { Shield, RefreshCw, AlertTriangle } from 'lucide-react';
import { useCurrentUser, useChangePassword } from '@/hooks/useAuth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert } from '@/components/ui/alert';
import { EmptyState } from '@/components/ui/empty-state';
import { Spinner } from '@/components/ui/spinner';
import {
  Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbLink, BreadcrumbSeparator, BreadcrumbPage,
} from '@/components/ui/breadcrumb';

const inputCls = 'w-full rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-50 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-brand-500/24';
const selectCls = 'rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500/24';

const ToggleSwitch = ({ defaultChecked }: { defaultChecked?: boolean }) => (
  <label className="relative inline-flex items-center cursor-pointer">
    <input type="checkbox" className="sr-only peer" defaultChecked={defaultChecked} />
    <div className="w-11 h-6 bg-gray-300 dark:bg-gray-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-brand-600" />
  </label>
);

export default function SecuritySettingsPage() {
  const { data: userData, isLoading, error } = useCurrentUser();
  const changePassword = useChangePassword();

  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [passwordForm, setPasswordForm] = useState({ current_password: '', new_password: '', confirm_password: '' });

  const handleChangePassword = async () => {
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      alert('New passwords do not match');
      return;
    }
    if (passwordForm.new_password.length < 8) {
      alert('Password must be at least 8 characters');
      return;
    }
    try {
      await changePassword.mutateAsync({
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
      });
      setShowPasswordModal(false);
      setPasswordForm({ current_password: '', new_password: '', confirm_password: '' });
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
          icon={<Shield />}
          iconColor="error"
          title="Failed to load security settings"
          description={error instanceof Error ? error.message : 'Something went wrong'}
          actions={<Button onClick={() => window.location.reload()} leadingIcon={<RefreshCw className="h-4 w-4" />}>Retry</Button>}
        />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-10 space-y-8 animate-fade-in">
        <header>
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem><BreadcrumbLink href="/settings">Settings</BreadcrumbLink></BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem><BreadcrumbPage>Security & Privacy</BreadcrumbPage></BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
          <div className="mt-4 space-y-1">
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">Security & Privacy</h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">Manage your account security and privacy settings.</p>
          </div>
        </header>

        <Card>
          <CardHeader><CardTitle>Password</CardTitle></CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-sm text-gray-900 dark:text-gray-50">Change Password</p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Keep your account secure with a strong password</p>
              </div>
              <Button variant="primary" onClick={() => setShowPasswordModal(true)}>Change Password</Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Two-Factor Authentication</CardTitle></CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <p className="font-medium text-sm text-gray-900 dark:text-gray-50">2FA Status</p>
                  <Badge variant="warning">Not Configured</Badge>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400">Two-factor authentication will be available in Phase 20</p>
              </div>
              <Button variant="secondary" disabled>Coming Soon</Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Active Sessions</CardTitle></CardHeader>
          <CardContent>
            <div className="text-center py-8">
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">Session management will be available in Phase 20</p>
              <p className="text-xs text-gray-400 dark:text-gray-500">You can currently log out from the main menu</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Privacy Settings</CardTitle></CardHeader>
          <CardContent>
            <div className="divide-y divide-gray-100 dark:divide-gray-800">
              <div className="flex items-center justify-between py-4 first:pt-0">
                <div>
                  <p className="font-medium text-sm text-gray-900 dark:text-gray-50">Profile Visibility</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Control who can see your profile</p>
                </div>
                <select className={selectCls}>
                  <option>Public</option>
                  <option>Private</option>
                  <option>Team Only</option>
                </select>
              </div>

              <div className="flex items-center justify-between py-4">
                <div>
                  <p className="font-medium text-sm text-gray-900 dark:text-gray-50">Analytics Sharing</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Share anonymous usage data to improve the platform</p>
                </div>
                <ToggleSwitch defaultChecked />
              </div>

              <div className="flex items-center justify-between py-4 last:pb-0">
                <div>
                  <p className="font-medium text-sm text-gray-900 dark:text-gray-50">Marketing Emails</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Receive updates about new features and tips</p>
                </div>
                <ToggleSwitch defaultChecked />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Data Management</CardTitle></CardHeader>
          <CardContent>
            <div className="divide-y divide-gray-100 dark:divide-gray-800">
              <div className="flex items-center justify-between py-4 first:pt-0">
                <div>
                  <p className="font-medium text-sm text-gray-900 dark:text-gray-50">Export Your Data</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Download a copy of all your data</p>
                </div>
                <Button variant="secondary">Request Export</Button>
              </div>
              <div className="flex items-center justify-between py-4 last:pb-0">
                <div>
                  <p className="font-medium text-sm text-error-700 dark:text-error-400">Delete All Data</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Permanently delete all your data from our servers</p>
                </div>
                <Button variant="destructive">Delete Data</Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {showPasswordModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <Card className="w-full max-w-md">
              <CardHeader><CardTitle>Change Password</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                {[
                  { label: 'Current Password', key: 'current_password' as const, hint: undefined },
                  { label: 'New Password', key: 'new_password' as const, hint: 'Must be at least 8 characters' },
                  { label: 'Confirm New Password', key: 'confirm_password' as const, hint: undefined },
                ].map(({ label, key, hint }) => (
                  <div key={key}>
                    <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">{label}</label>
                    <input
                      type="password"
                      value={passwordForm[key]}
                      onChange={(e) => setPasswordForm({ ...passwordForm, [key]: e.target.value })}
                      className={inputCls}
                    />
                    {hint && <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{hint}</p>}
                  </div>
                ))}
                <div className="flex gap-2 pt-2">
                  <Button
                    variant="primary"
                    className="flex-1"
                    onClick={handleChangePassword}
                    disabled={changePassword.isPending || !passwordForm.current_password || !passwordForm.new_password}
                    loading={changePassword.isPending}
                  >
                    {changePassword.isPending ? 'Updating...' : 'Update Password'}
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setShowPasswordModal(false);
                      setPasswordForm({ current_password: '', new_password: '', confirm_password: '' });
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
