/**
 * Notifications Settings Page
 * 
 * Configure notification preferences
 */

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useCurrentUser } from '@/hooks/useAuth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export default function NotificationsSettingsPage() {
  const router = useRouter();
  const { data: userData, isLoading, error } = useCurrentUser();
  const [saving, setSaving] = useState(false);

  // Notification settings - will be persisted to backend in Phase 20
  const [settings, setSettings] = useState({
    // Email notifications
    emailTrendAlerts: true,
    emailGoalReminders: true,
    emailCompetitorMoves: true,
    emailBrandDeals: true,
    emailWeeklyReport: true,
    emailProductUpdates: false,
    
    // Push notifications
    pushTrendAlerts: true,
    pushGoalReminders: true,
    pushCompetitorMoves: false,
    pushBrandDeals: true,
    pushContentPublished: true,
    pushComments: false,
    
    // In-app notifications
    inAppTrendAlerts: true,
    inAppGoalReminders: true,
    inAppCompetitorMoves: true,
    inAppBrandDeals: true,
    inAppContentPublished: true,
    
    // Notification timing
    quietHoursEnabled: true,
    quietHoursStart: '22:00',
    quietHoursEnd: '08:00',
    timezone: 'America/New_York',
  });

  const handleSave = async () => {
    setSaving(true);
    // TODO: Implement notification preferences API in Phase 20
    // For now, settings are stored in local state
    await new Promise(resolve => setTimeout(resolve, 500));
    setSaving(false);
    alert('Notification settings saved! (Note: Full notification API coming in Phase 20)');
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-tech mx-auto mb-4" />
              <p className="text-muted-foreground">Loading settings...</p>
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
              <h2 className="text-2xl font-bold mb-2">Failed to load settings</h2>
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

  const toggleSetting = (key: keyof typeof settings) => {
    setSettings(prev => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const ToggleSwitch = ({ enabled, onChange }: { enabled: boolean; onChange: () => void }) => (
    <label className="relative inline-flex items-center cursor-pointer">
      <input
        type="checkbox"
        className="sr-only peer"
        checked={enabled}
        onChange={onChange}
      />
      <div className="w-11 h-6 bg-gray-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-tech"></div>
    </label>
  );

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <Button variant="outline" onClick={() => router.push('/settings')} className="mb-4">
            ← Back to Settings
          </Button>
          <h1 className="text-4xl font-bold gradient-text">Notification Settings</h1>
          <p className="text-muted-foreground mt-2">
            Control how and when you receive notifications
          </p>
        </div>

        {/* Email Notifications */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Email Notifications</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">Trend Alerts</div>
                <div className="text-sm text-muted-foreground">
                  Get notified when new trends match your niche
                </div>
              </div>
              <ToggleSwitch
                enabled={settings.emailTrendAlerts}
                onChange={() => toggleSetting('emailTrendAlerts')}
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">Goal Reminders</div>
                <div className="text-sm text-muted-foreground">
                  Reminders to help you stay on track with your goals
                </div>
              </div>
              <ToggleSwitch
                enabled={settings.emailGoalReminders}
                onChange={() => toggleSetting('emailGoalReminders')}
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">Competitor Activity</div>
                <div className="text-sm text-muted-foreground">
                  Updates when competitors post new content
                </div>
              </div>
              <ToggleSwitch
                enabled={settings.emailCompetitorMoves}
                onChange={() => toggleSetting('emailCompetitorMoves')}
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">Brand Deal Inquiries</div>
                <div className="text-sm text-muted-foreground">
                  Notifications for potential brand partnerships
                </div>
              </div>
              <ToggleSwitch
                enabled={settings.emailBrandDeals}
                onChange={() => toggleSetting('emailBrandDeals')}
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">Weekly Report</div>
                <div className="text-sm text-muted-foreground">
                  Summary of your performance and insights
                </div>
              </div>
              <ToggleSwitch
                enabled={settings.emailWeeklyReport}
                onChange={() => toggleSetting('emailWeeklyReport')}
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">Product Updates</div>
                <div className="text-sm text-muted-foreground">
                  News about new features and improvements
                </div>
              </div>
              <ToggleSwitch
                enabled={settings.emailProductUpdates}
                onChange={() => toggleSetting('emailProductUpdates')}
              />
            </div>
          </CardContent>
        </Card>

        {/* Push Notifications */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Push Notifications</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">Trend Alerts</div>
                <div className="text-sm text-muted-foreground">
                  Instant alerts for hot trending topics
                </div>
              </div>
              <ToggleSwitch
                enabled={settings.pushTrendAlerts}
                onChange={() => toggleSetting('pushTrendAlerts')}
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">Goal Reminders</div>
                <div className="text-sm text-muted-foreground">
                  Push reminders for your content goals
                </div>
              </div>
              <ToggleSwitch
                enabled={settings.pushGoalReminders}
                onChange={() => toggleSetting('pushGoalReminders')}
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">Competitor Activity</div>
                <div className="text-sm text-muted-foreground">
                  Real-time competitor updates
                </div>
              </div>
              <ToggleSwitch
                enabled={settings.pushCompetitorMoves}
                onChange={() => toggleSetting('pushCompetitorMoves')}
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">Brand Deal Inquiries</div>
                <div className="text-sm text-muted-foreground">
                  Instant notifications for new opportunities
                </div>
              </div>
              <ToggleSwitch
                enabled={settings.pushBrandDeals}
                onChange={() => toggleSetting('pushBrandDeals')}
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">Content Published</div>
                <div className="text-sm text-muted-foreground">
                  Confirmation when your content goes live
                </div>
              </div>
              <ToggleSwitch
                enabled={settings.pushContentPublished}
                onChange={() => toggleSetting('pushContentPublished')}
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">Comments & Engagement</div>
                <div className="text-sm text-muted-foreground">
                  Notifications for comments and interactions
                </div>
              </div>
              <ToggleSwitch
                enabled={settings.pushComments}
                onChange={() => toggleSetting('pushComments')}
              />
            </div>
          </CardContent>
        </Card>

        {/* Quiet Hours */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Quiet Hours</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">Enable Quiet Hours</div>
                <div className="text-sm text-muted-foreground">
                  Pause notifications during specific hours
                </div>
              </div>
              <ToggleSwitch
                enabled={settings.quietHoursEnabled}
                onChange={() => toggleSetting('quietHoursEnabled')}
              />
            </div>

            {settings.quietHoursEnabled && (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Start Time
                    </label>
                    <input
                      type="time"
                      value={settings.quietHoursStart}
                      onChange={(e) => setSettings({ ...settings, quietHoursStart: e.target.value })}
                      className="w-full px-3 py-2 bg-surface rounded-md border border-input"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      End Time
                    </label>
                    <input
                      type="time"
                      value={settings.quietHoursEnd}
                      onChange={(e) => setSettings({ ...settings, quietHoursEnd: e.target.value })}
                      className="w-full px-3 py-2 bg-surface rounded-md border border-input"
                    />
                  </div>
                </div>

                <div className="p-3 bg-surface rounded-lg border border-border text-sm text-muted-foreground">
                  Notifications will be paused from {settings.quietHoursStart} to {settings.quietHoursEnd} in your timezone
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Notification Channels */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Notification Channels</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4 text-sm">
              <div className="flex items-center justify-between p-3 bg-surface rounded-lg">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">📧</span>
                  <div>
                    <div className="font-medium">Email</div>
                    <div className="text-muted-foreground">{user?.email || 'Not set'}</div>
                  </div>
                </div>
                <Badge variant="success">Connected</Badge>
              </div>

              <div className="flex items-center justify-between p-3 bg-surface rounded-lg">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">📱</span>
                  <div>
                    <div className="font-medium">Push Notifications</div>
                    <div className="text-muted-foreground">Browser & Mobile</div>
                  </div>
                </div>
                <Button variant="outline" size="sm">
                  Enable
                </Button>
              </div>

              <div className="flex items-center justify-between p-3 bg-surface rounded-lg">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">💬</span>
                  <div>
                    <div className="font-medium">SMS (Coming Soon)</div>
                    <div className="text-muted-foreground">Text message notifications</div>
                  </div>
                </div>
                <Badge variant="default">Soon</Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="flex gap-2">
          <Button onClick={handleSave} disabled={saving}>
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
          <Button variant="outline" onClick={() => router.push('/settings')}>
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}
