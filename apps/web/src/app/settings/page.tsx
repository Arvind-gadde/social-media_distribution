import Link from 'next/link';
import { User, Link2, Bot, CreditCard, Bell, Shield } from 'lucide-react';
import { Card } from '@/components/ui/card';

const sections = [
  { href: '/settings/profile', icon: User, label: 'Profile', description: 'Manage your personal information and preferences' },
  { href: '/settings/accounts', icon: Link2, label: 'Connected Accounts', description: 'Manage your social media platform connections' },
  { href: '/settings/agents', icon: Bot, label: 'AI Agents', description: 'Configure and customize your AI agents' },
  { href: '/settings/billing', icon: CreditCard, label: 'Billing & Subscription', description: 'Manage your subscription and payment methods' },
  { href: '/settings/security', icon: Shield, label: 'Security & Privacy', description: 'Password, 2FA, and privacy settings' },
  { href: '/settings/notifications', icon: Bell, label: 'Notifications', description: 'Control how and when you receive notifications' },
];

export default function SettingsPage() {
  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-10 space-y-8 animate-fade-in">
        <header className="space-y-1">
          <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">
            Settings
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Manage your account and preferences.
          </p>
        </header>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {sections.map((s) => {
            const Icon = s.icon;
            return (
              <Link key={s.href} href={s.href}>
                <Card className="group flex items-start gap-4 p-5 hover:border-brand-300 dark:hover:border-brand-700 transition-colors cursor-pointer h-full">
                  <div className="shrink-0 rounded-lg bg-brand-50 dark:bg-brand-950/40 p-2.5">
                    <Icon className="h-5 w-5 text-brand-600 dark:text-brand-400" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900 dark:text-gray-50 group-hover:text-brand-700 dark:group-hover:text-brand-300 transition-colors">
                      {s.label}
                    </p>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{s.description}</p>
                  </div>
                </Card>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
