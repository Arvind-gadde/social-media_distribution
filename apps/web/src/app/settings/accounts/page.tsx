'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Link2, RefreshCw, ArrowLeft } from 'lucide-react';
import { useSocialAccountsList, useDisconnectAccount, useSetPrimaryAccount } from '@/hooks/useSocialAccounts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { EmptyState } from '@/components/ui/empty-state';
import { Spinner } from '@/components/ui/spinner';
import {
  Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbLink, BreadcrumbSeparator, BreadcrumbPage,
} from '@/components/ui/breadcrumb';

export default function AccountsSettingsPage() {
  const { data, isLoading, error, refetch } = useSocialAccountsList({ include_inactive: true });
  const disconnectAccount = useDisconnectAccount();
  const setPrimary = useSetPrimaryAccount();

  const handleConnect = (platform: string) => {
    alert(`OAuth flow for ${platform} will be implemented in Phase 20`);
  };

  const handleDisconnect = async (accountId: string, platform: string) => {
    if (confirm(`Are you sure you want to disconnect your ${platform} account?`)) {
      try { await disconnectAccount.mutateAsync(accountId); } catch (e) { console.error(e); }
    }
  };

  const handleSetPrimary = async (accountId: string) => {
    try { await setPrimary.mutateAsync(accountId); } catch (e) { console.error(e); }
  };

  const formatNumber = (num: number) => {
    if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
    return num.toString();
  };

  const getPlatformIcon = (platform: string) => {
    const icons: Record<string, string> = { instagram: '📷', youtube: '▶️', tiktok: '🎵', twitter: '🐦', linkedin: '💼', facebook: '👥', pinterest: '📌' };
    return icons[platform?.toLowerCase()] || '📱';
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
          icon={<Link2 />}
          iconColor="error"
          title="Failed to load accounts"
          description={error instanceof Error ? error.message : 'Something went wrong'}
          actions={<Button onClick={() => refetch()} leadingIcon={<RefreshCw className="h-4 w-4" />}>Retry</Button>}
        />
      </div>
    );
  }

  const accounts = data?.accounts || [];
  const connectedAccounts = accounts.filter((a: any) => a.is_active);
  const totalFollowers = accounts.reduce((sum: number, a: any) => sum + (a.followers_count || 0), 0);

  const availablePlatforms = [
    { name: 'Instagram', key: 'instagram' },
    { name: 'YouTube', key: 'youtube' },
    { name: 'TikTok', key: 'tiktok' },
    { name: 'Twitter', key: 'twitter' },
    { name: 'LinkedIn', key: 'linkedin' },
  ];

  const allPlatforms = availablePlatforms.map(platform => {
    const connected = accounts.find((a: any) => a.platform.toLowerCase() === platform.key && a.is_active);
    return { ...platform, account: connected, connected: !!connected };
  });

  const statCards = [
    { label: 'Connected Accounts', value: connectedAccounts.length },
    { label: 'Total Followers', value: formatNumber(totalFollowers) },
    { label: 'Available Platforms', value: availablePlatforms.length - connectedAccounts.length },
  ];

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-10 space-y-8 animate-fade-in">
        <header>
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem><BreadcrumbLink href="/settings">Settings</BreadcrumbLink></BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem><BreadcrumbPage>Connected Accounts</BreadcrumbPage></BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
          <div className="mt-4 space-y-1">
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">Connected Accounts</h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">Manage your social media platform connections.</p>
          </div>
        </header>

        <div className="grid grid-cols-3 gap-4">
          {statCards.map((s) => (
            <Card key={s.label} className="p-4">
              <p className="text-2xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">{s.value}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{s.label}</p>
            </Card>
          ))}
        </div>

        <Card>
          <CardHeader><CardTitle>Your Accounts</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {allPlatforms.map((platform) => (
              <div
                key={platform.key}
                className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg"
              >
                <div className="flex items-center gap-4">
                  <span className="text-3xl">{getPlatformIcon(platform.key)}</span>
                  <div>
                    <p className="font-semibold text-sm text-gray-900 dark:text-gray-50">{platform.name}</p>
                    {platform.connected && platform.account ? (
                      <>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          @{(platform.account as any).platform_username || (platform.account as any).platform_display_name}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {formatNumber((platform.account as any).followers_count || 0)} followers
                        </p>
                      </>
                    ) : (
                      <p className="text-xs text-gray-500 dark:text-gray-400">Not connected</p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {platform.connected && platform.account ? (
                    <>
                      <Badge variant="success">Connected</Badge>
                      {(platform.account as any).is_primary && <Badge variant="gray">Primary</Badge>}
                      {!(platform.account as any).is_primary && (
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => handleSetPrimary((platform.account as any).id)}
                          disabled={setPrimary.isPending}
                        >
                          Set Primary
                        </Button>
                      )}
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleDisconnect((platform.account as any).id, platform.name)}
                        disabled={disconnectAccount.isPending}
                      >
                        Disconnect
                      </Button>
                    </>
                  ) : (
                    <Button variant="primary" size="sm" onClick={() => handleConnect(platform.key)}>
                      Connect
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Permissions & Data Access</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-3 text-sm">
              <p className="text-gray-500 dark:text-gray-400">
                When you connect a social media account, ContentFlow AI requests the following permissions:
              </p>
              <ul className="list-disc list-inside space-y-1.5 text-gray-500 dark:text-gray-400">
                <li>Read your profile information (username, followers, bio)</li>
                <li>Read your posts and their analytics (views, likes, comments)</li>
                <li>Post content on your behalf (when you schedule or publish)</li>
                <li>Read your audience demographics and insights</li>
              </ul>
              <p className="text-gray-500 dark:text-gray-400">
                You can revoke these permissions at any time by disconnecting the account. We never access your private messages or personal data beyond what's necessary for the service.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
