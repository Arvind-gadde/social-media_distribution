/**
 * Settings Overview Page
 * 
 * Main settings hub with navigation to all settings sections
 */

'use client';

import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function SettingsPage() {
  const settingsSections = [
    {
      id: 'profile',
      title: 'Profile Settings',
      description: 'Manage your personal information and preferences',
      icon: '👤',
      href: '/settings/profile',
    },
    {
      id: 'accounts',
      title: 'Connected Accounts',
      description: 'Manage your social media platform connections',
      icon: '🔗',
      href: '/settings/accounts',
    },
    {
      id: 'agents',
      title: 'AI Agents',
      description: 'Configure and customize your AI agents',
      icon: '🤖',
      href: '/settings/agents',
    },
    {
      id: 'billing',
      title: 'Billing & Subscription',
      description: 'Manage your subscription and payment methods',
      icon: '💳',
      href: '/settings/billing',
    },
    {
      id: 'security',
      title: 'Security & Privacy',
      description: 'Password, 2FA, and privacy settings',
      icon: '🔒',
      href: '/settings/security',
    },
    {
      id: 'notifications',
      title: 'Notifications',
      description: 'Control how and when you receive notifications',
      icon: '🔔',
      href: '/settings/notifications',
    },
  ];

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold gradient-text">Settings</h1>
          <p className="text-muted-foreground mt-2">
            Manage your account and preferences
          </p>
        </div>

        {/* Settings Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {settingsSections.map(section => (
            <Link key={section.id} href={section.href}>
              <Card className="card-hover h-full">
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <span className="text-4xl">{section.icon}</span>
                    <CardTitle className="text-lg">{section.title}</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    {section.description}
                  </p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
