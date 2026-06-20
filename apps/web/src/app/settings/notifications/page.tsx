'use client';

import { useState } from 'react';
import { Bell, RefreshCw } from 'lucide-react';
import { useCurrentUser } from '@/hooks/useAuth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { EmptyState } from '@/components/ui/empty-state';
import { Spinner } from '@/components/ui/spinner';
import {
  Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbLink, BreadcrumbSeparator, BreadcrumbPage,
} from '@/components/ui/breadcrumb';

const inputCls = 'w-full rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500/24';

const ToggleSwitch = ({ enabled, onChange }: { enabled: boolean; onChange: () => void }) => (
  <label className="relative inline-flex items-center cursor-pointer">
    <input type="checkbox" className="sr-only peer" checked={enabled} onChange={onChange} />
    <div className="w-11 h-6 bg-gray-300 dark:bg-gray-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-brand-600" />
  </label>
);

export default function NotificationsSettingsPage() {
  const { data: userData, isLoading, error } = useCurrentUser();
  const [saving, setSaving] = useState(false);

  const [settings, setSettings] = useState({
    emailTrendAlerts: true,
    emailGoalReminders: true,
    emailCompetitorMoves: true,
    emailBrandDeals: true,
    emailWeeklyReport: true,
    emailProductUpdates: false,
    pushTrendAlerts: true,
    pushGoalReminders: true,
    pushCompetitorMoves: false,
    pushBrandDeals: true,
    pushContentPublished: true,
    pushComments: false,
    inAppTrendAlerts: true,
    inAppGoalReminders: true,
    inAppCompetitorMoves: true,
    inAppBrandDeals: true,
    inAppContentPublished: true,
    quietHoursEnabled: true,
    quietHoursStart: '22:00',
    quietHoursEnd: '08:00',
  });

  const toggleSetting = (key: keyof typeof settings) => {
    setSettings(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const handleSave = async () => {
    setSaving(true);
    await new Promise(resolve => setTimeout(resolve, 500));
    setSaving(false);
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
          icon={<Bell />}
          iconColor="error"
          title="Failed to load settings"
          description={error instanceof Error ? error.message : 'Something went wrong'}
          actions={<Button onClick={() => window.location.reload()} leadingIcon={<RefreshCw className="h-4 w-4" />}>Retry</Button>}
        />
      </div>
    );
  }

  const user = userData?.user;

  const emailNotifications = [
    { key: 'emailTrendAlerts' as const, label: 'Trend Alerts', desc: 'Get notified when new trends match your niche' },
    { key: 'emailGoalReminders' as const, label: 'Goal Reminders', desc: 'Reminders to help you stay on track with your goals' },
    { key: 'emailCompetitorMoves' as const, label: 'Competitor Activity', desc: 'Updates when competitors post new content' },
    { key: 'emailBrandDeals' as const, label: 'Brand Deal Inquiries', desc: 'Notifications for potential brand partnerships' },
    { key: 'emailWeeklyReport' as const, label: 'Weekly Report', desc: 'Summary of your performance and insights' },
    { key: 'emailProductUpdates' as const, label: 'Product Updates', desc: 'News about new features and improvements' },
  ];

  const pushNotifications = [
    { key: 'pushTrendAlerts' as const, label: 'Trend Alerts', desc: 'Instant alerts for hot trending topics' },
    { key: 'pushGoalReminders' as const, label: 'Goal Reminders', desc: 'Push reminders for your content goals' },
    { key: 'pushCompetitorMoves' as const, label: 'Competitor Activity', desc: 'Real-time competitor updates' },
    { key: 'pushBrandDeals' as const, label: 'Brand Deal Inquiries', desc: 'Instant notifications for new opportunities' },
    { key: 'pushContentPublished' as const, label: 'Content Published', desc: 'Confirmation when your content goes live' },
    { key: 'pushComments' as const, label: 'Comments & Engagement', desc: 'Notifications for comments and interactions' },
  ];

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-10 space-y-8 animate-fade-in">
        <header>
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem><BreadcrumbLink href="/settings">Settings</BreadcrumbLink></BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem><BreadcrumbPage>Notifications</BreadcrumbPage></BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
          <div className="mt-4 space-y-1">
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">Notification Settings</h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">Control how and when you receive notifications.</p>
          </div>
        </header>

        <Card>
          <CardHeader><CardTitle>Email Notifications</CardTitle></CardHeader>
          <CardContent className="divide-y divide-gray-100 dark:divide-gray-800">
            {emailNotifications.map(({ key, label, desc }) => (
              <div key={key} className="flex items-center justify-between py-4 first:pt-0 last:pb-0">
                <div>
                  <p className="font-medium text-sm text-gray-900 dark:text-gray-50">{label}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{desc}</p>
                </div>
                <ToggleSwitch enabled={settings[key] as boolean} onChange={() => toggleSetting(key)} />
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Push Notifications</CardTitle></CardHeader>
          <CardContent className="divide-y divide-gray-100 dark:divide-gray-800">
            {pushNotifications.map(({ key, label, desc }) => (
              <div key={key} className="flex items-center justify-between py-4 first:pt-0 last:pb-0">
                <div>
                  <p className="font-medium text-sm text-gray-900 dark:text-gray-50">{label}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{desc}</p>
                </div>
                <ToggleSwitch enabled={settings[key] as boolean} onChange={() => toggleSetting(key)} />
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Quiet Hours</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-sm text-gray-900 dark:text-gray-50">Enable Quiet Hours</p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Pause notifications during specific hours</p>
              </div>
              <ToggleSwitch enabled={settings.quietHoursEnabled} onChange={() => toggleSetting('quietHoursEnabled')} />
            </div>

            {settings.quietHoursEnabled && (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">Start Time</label>
                    <input type="time" value={settings.quietHoursStart} onChange={(e) => setSettings({ ...settings, quietHoursStart: e.target.value })} className={inputCls} />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">End Time</label>
                    <input type="time" value={settings.quietHoursEnd} onChange={(e) => setSettings({ ...settings, quietHoursEnd: e.target.value })} className={inputCls} />
                  </div>
                </div>
                <p className="text-sm text-gray-500 dark:text-gray-400 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-4 py-3">
                  Notifications will be paused from {settings.quietHoursStart} to {settings.quietHoursEnd} in your timezone.
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Notification Channels</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {[
              {
                icon: '📧', label: 'Email', desc: user?.email || 'Not set',
                action: <Badge variant="success">Connected</Badge>,
              },
              {
                icon: '📱', label: 'Push Notifications', desc: 'Browser & Mobile',
                action: <Button variant="secondary" size="sm">Enable</Button>,
              },
              {
                icon: '💬', label: 'SMS (Coming Soon)', desc: 'Text message notifications',
                action: <Badge variant="gray">Soon</Badge>,
              },
            ].map(({ icon, label, desc, action }) => (
              <div key={label} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{icon}</span>
                  <div>
                    <p className="font-medium text-sm text-gray-900 dark:text-gray-50">{label}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">{desc}</p>
                  </div>
                </div>
                {action}
              </div>
            ))}
          </CardContent>
        </Card>

        <div className="flex gap-2 pb-4">
          <Button variant="primary" onClick={handleSave} disabled={saving} loading={saving}>
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
          <Button variant="secondary" asChild>
            <a href="/settings">Cancel</a>
          </Button>
        </div>
      </div>
    </div>
  );
}
