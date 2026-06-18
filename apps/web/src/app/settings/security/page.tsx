/**
 * Security & Privacy Settings Page
 * 
 * Manage password, 2FA, and privacy settings
 */

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useCurrentUser, useChangePassword } from '@/hooks/useAuth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export default function SecuritySettingsPage() {
  const router = useRouter();
  const { data: userData, isLoading, error } = useCurrentUser();
  const changePassword = useChangePassword();

  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });

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
    } catch (error) {
      console.error('Failed to change password:', error);
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-tech mx-auto mb-4" />
              <p className="text-muted-foreground">Loading security settings...</p>
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
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="text-error text-5xl mb-4">⚠️</div>
              <h2 className="text-2xl font-bold mb-2">Failed to load security settings</h2>
              <p className="text-muted-foreground mb-4">
                {error instanceof Error ? error.message : 'Something went wrong'}
              </p>
              <Button onClick={() => window.location.reload()}>Retry</Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const user = userData?.user;

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <Button variant="outline" onClick={() => router.push('/settings')} className="mb-4">
            ← Back to Settings
          </Button>
          <h1 className="text-4xl font-bold gradient-text">Security & Privacy</h1>
          <p className="text-muted-foreground mt-2">
            Manage your account security and privacy settings
          </p>
        </div>

        {/* Password */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Password</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">Change Password</div>
                <div className="text-sm text-muted-foreground">
                  Keep your account secure with a strong password
                </div>
              </div>
              <Button onClick={() => setShowPasswordModal(true)}>
                Change Password
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Two-Factor Authentication - Coming in Phase 20 */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Two-Factor Authentication</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <div className="font-medium">2FA Status</div>
                  <Badge variant="warning">Not Configured</Badge>
                </div>
                <div className="text-sm text-muted-foreground">
                  Two-factor authentication will be available in Phase 20
                </div>
              </div>
              <Button variant="outline" disabled>
                Coming Soon
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Active Sessions - Coming in Phase 20 */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Active Sessions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center py-8">
              <div className="text-4xl mb-4">🔐</div>
              <p className="text-muted-foreground mb-4">
                Session management will be available in Phase 20
              </p>
              <p className="text-sm text-muted-foreground">
                You can currently log out from the main menu
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Privacy Settings */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Privacy Settings</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium">Profile Visibility</div>
                  <div className="text-sm text-muted-foreground">
                    Control who can see your profile
                  </div>
                </div>
                <select className="px-3 py-2 bg-surface rounded-md border border-input">
                  <option>Public</option>
                  <option>Private</option>
                  <option>Team Only</option>
                </select>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium">Analytics Sharing</div>
                  <div className="text-sm text-muted-foreground">
                    Share anonymous usage data to improve the platform
                  </div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" defaultChecked />
                  <div className="w-11 h-6 bg-gray-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-tech"></div>
                </label>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium">Marketing Emails</div>
                  <div className="text-sm text-muted-foreground">
                    Receive updates about new features and tips
                  </div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" defaultChecked />
                  <div className="w-11 h-6 bg-gray-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-tech"></div>
                </label>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Data Export */}
        <Card>
          <CardHeader>
            <CardTitle>Data Management</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium">Export Your Data</div>
                  <div className="text-sm text-muted-foreground">
                    Download a copy of all your data
                  </div>
                </div>
                <Button variant="outline">
                  Request Export
                </Button>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-error">Delete All Data</div>
                  <div className="text-sm text-muted-foreground">
                    Permanently delete all your data from our servers
                  </div>
                </div>
                <Button variant="outline" className="text-error border-error">
                  Delete Data
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Change Password Modal */}
        {showPasswordModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <Card className="w-full max-w-md">
              <CardHeader>
                <CardTitle>Change Password</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Current Password
                    </label>
                    <input
                      type="password"
                      value={passwordForm.current_password}
                      onChange={(e) => setPasswordForm({ ...passwordForm, current_password: e.target.value })}
                      className="w-full px-3 py-2 bg-surface rounded-md border border-input focus:outline-none focus:ring-2 focus:ring-tech"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      New Password
                    </label>
                    <input
                      type="password"
                      value={passwordForm.new_password}
                      onChange={(e) => setPasswordForm({ ...passwordForm, new_password: e.target.value })}
                      className="w-full px-3 py-2 bg-surface rounded-md border border-input focus:outline-none focus:ring-2 focus:ring-tech"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Must be at least 8 characters
                    </p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Confirm New Password
                    </label>
                    <input
                      type="password"
                      value={passwordForm.confirm_password}
                      onChange={(e) => setPasswordForm({ ...passwordForm, confirm_password: e.target.value })}
                      className="w-full px-3 py-2 bg-surface rounded-md border border-input focus:outline-none focus:ring-2 focus:ring-tech"
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button 
                      className="flex-1"
                      onClick={handleChangePassword}
                      disabled={changePassword.isPending || !passwordForm.current_password || !passwordForm.new_password}
                    >
                      {changePassword.isPending ? 'Updating...' : 'Update Password'}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => {
                        setShowPasswordModal(false);
                        setPasswordForm({ current_password: '', new_password: '', confirm_password: '' });
                      }}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
