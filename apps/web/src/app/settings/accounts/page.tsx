/**
 * Connected Accounts Settings Page
 * 
 * Manage social media platform connections
 */

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useSocialAccountsList, useDisconnectAccount, useSetPrimaryAccount } from '@/hooks/useSocialAccounts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export default function AccountsSettingsPage() {
  const router = useRouter();
  const { data, isLoading, error, refetch } = useSocialAccountsList({ include_inactive: true });
  const disconnectAccount = useDisconnectAccount();
  const setPrimary = useSetPrimaryAccount();

  const handleConnect = (platform: string) => {
    // TODO: Implement OAuth flow
    alert(`OAuth flow for ${platform} will be implemented in Phase 20`);
  };

  const handleDisconnect = async (accountId: string, platform: string) => {
    if (confirm(`Are you sure you want to disconnect your ${platform} account?`)) {
      try {
        await disconnectAccount.mutateAsync(accountId);
      } catch (error) {
        console.error('Failed to disconnect:', error);
      }
    }
  };

  const handleSetPrimary = async (accountId: string) => {
    try {
      await setPrimary.mutateAsync(accountId);
    } catch (error) {
      console.error('Failed to set primary:', error);
    }
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const getPlatformIcon = (platform: string) => {
    const icons: Record<string, string> = {
      instagram: '📷',
      youtube: '▶️',
      tiktok: '🎵',
      twitter: '🐦',
      linkedin: '💼',
      facebook: '👥',
      pinterest: '📌',
    };
    return icons[platform?.toLowerCase()] || '📱';
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-tech mx-auto mb-4" />
              <p className="text-muted-foreground">Loading accounts...</p>
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
              <h2 className="text-2xl font-bold mb-2">Failed to load accounts</h2>
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

  const accounts = data?.accounts || [];
  const connectedAccounts = accounts.filter(a => a.is_active);
  const totalFollowers = accounts.reduce((sum, a) => sum + (a.followers_count || 0), 0);

  // Available platforms (hardcoded list)
  const availablePlatforms = [
    { name: 'Instagram', key: 'instagram' },
    { name: 'YouTube', key: 'youtube' },
    { name: 'TikTok', key: 'tiktok' },
    { name: 'Twitter', key: 'twitter' },
    { name: 'LinkedIn', key: 'linkedin' },
  ];

  // Merge with connected accounts
  const allPlatforms = availablePlatforms.map(platform => {
    const connected = accounts.find(a => a.platform.toLowerCase() === platform.key && a.is_active);
    return {
      ...platform,
      account: connected,
      connected: !!connected,
    };
  });

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <Button variant="outline" onClick={() => router.push('/settings')} className="mb-4">
            ← Back to Settings
          </Button>
          <h1 className="text-4xl font-bold gradient-text">Connected Accounts</h1>
          <p className="text-muted-foreground mt-2">
            Manage your social media platform connections
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold">
                {connectedAccounts.length}
              </div>
              <div className="text-sm text-muted-foreground">Connected Accounts</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold">
                {formatNumber(totalFollowers)}
              </div>
              <div className="text-sm text-muted-foreground">Total Followers</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold">
                {availablePlatforms.length - connectedAccounts.length}
              </div>
              <div className="text-sm text-muted-foreground">Available Platforms</div>
            </CardContent>
          </Card>
        </div>

        {/* Connected Accounts */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Your Accounts</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {allPlatforms.map((platform) => (
                <div
                  key={platform.key}
                  className="flex items-center justify-between p-4 bg-surface rounded-lg"
                >
                  <div className="flex items-center gap-4">
                    <span className="text-3xl">{getPlatformIcon(platform.key)}</span>
                    <div>
                      <div className="font-semibold">{platform.name}</div>
                      {platform.connected && platform.account ? (
                        <>
                          <div className="text-sm text-muted-foreground">
                            @{platform.account.platform_username || platform.account.platform_display_name}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {formatNumber(platform.account.followers_count || 0)} followers
                          </div>
                        </>
                      ) : (
                        <div className="text-sm text-muted-foreground">
                          Not connected
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {platform.connected && platform.account ? (
                      <>
                        <Badge variant="success">Connected</Badge>
                        {platform.account.is_primary && (
                          <Badge variant="default">Primary</Badge>
                        )}
                        {!platform.account.is_primary && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleSetPrimary(platform.account!.id)}
                            disabled={setPrimary.isPending}
                          >
                            Set Primary
                          </Button>
                        )}
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDisconnect(platform.account!.id, platform.name)}
                          disabled={disconnectAccount.isPending}
                        >
                          Disconnect
                        </Button>
                      </>
                    ) : (
                      <Button
                        size="sm"
                        onClick={() => handleConnect(platform.key)}
                      >
                        Connect
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Permissions Info */}
        <Card>
          <CardHeader>
            <CardTitle>Permissions & Data Access</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4 text-sm">
              <p className="text-muted-foreground">
                When you connect a social media account, ContentFlow AI requests the following permissions:
              </p>
              <ul className="list-disc list-inside space-y-2 text-muted-foreground">
                <li>Read your profile information (username, followers, bio)</li>
                <li>Read your posts and their analytics (views, likes, comments)</li>
                <li>Post content on your behalf (when you schedule or publish)</li>
                <li>Read your audience demographics and insights</li>
              </ul>
              <p className="text-muted-foreground">
                You can revoke these permissions at any time by disconnecting the account.
                We never access your private messages or personal data beyond what's necessary
                for the service.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
