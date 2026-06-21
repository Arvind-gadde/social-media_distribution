'use client';

import { useState } from 'react';
import { Link2, RefreshCw } from 'lucide-react';
import {
  useSocialAccountsList,
  useDisconnectAccount,
  useSetPrimaryAccount,
  useConnectMastodon,
  useConnectBluesky,
} from '@/hooks/useSocialAccounts';
import { oauthApi } from '@contentflow/api-client';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { EmptyState } from '@/components/ui/empty-state';
import { Spinner } from '@/components/ui/spinner';
import {
  Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbLink, BreadcrumbSeparator, BreadcrumbPage,
} from '@/components/ui/breadcrumb';

// Platforms connected via redirect OAuth (handled server-side at /oauth/{p}/authorize).
const OAUTH_PLATFORMS = [
  { name: 'LinkedIn', key: 'linkedin' },
  { name: 'YouTube', key: 'youtube' },
  { name: 'Instagram', key: 'instagram' },
  { name: 'Facebook', key: 'facebook' },
  { name: 'Pinterest', key: 'pinterest' },
  { name: 'TikTok', key: 'tiktok' },
  { name: 'Twitter', key: 'twitter' },
];

// Platforms connected via pasted credentials (no central OAuth app).
const CREDENTIAL_PLATFORMS = [
  { name: 'Mastodon', key: 'mastodon' },
  { name: 'Bluesky', key: 'bluesky' },
];

const ALL_PLATFORM_KEYS = [...OAUTH_PLATFORMS, ...CREDENTIAL_PLATFORMS];

const inputClass =
  'w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm text-gray-900 dark:text-gray-50 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-tech/40';

export default function AccountsSettingsPage() {
  const { data, isLoading, error, refetch } = useSocialAccountsList({ include_inactive: true });
  const disconnectAccount = useDisconnectAccount();
  const setPrimary = useSetPrimaryAccount();
  const connectMastodon = useConnectMastodon();
  const connectBluesky = useConnectBluesky();

  const [credForm, setCredForm] = useState<'mastodon' | 'bluesky' | null>(null);
  // Mastodon fields
  const [mInstance, setMInstance] = useState('');
  const [mToken, setMToken] = useState('');
  // Bluesky fields
  const [bHandle, setBHandle] = useState('');
  const [bPassword, setBPassword] = useState('');

  const resetForm = () => {
    setCredForm(null);
    setMInstance(''); setMToken(''); setBHandle(''); setBPassword('');
  };

  const handleConnect = (platform: string) => {
    if (platform === 'mastodon' || platform === 'bluesky') {
      setCredForm(platform);
      return;
    }
    // Redirect OAuth — backend authorize endpoint 307-redirects to the platform.
    window.location.href = oauthApi.getAuthorizationUrl(platform);
  };

  const submitMastodon = async () => {
    try {
      await connectMastodon.mutateAsync({ instanceUrl: mInstance.trim(), accessToken: mToken.trim() });
      resetForm();
    } catch (e) { console.error(e); }
  };

  const submitBluesky = async () => {
    try {
      await connectBluesky.mutateAsync({ handle: bHandle.trim(), appPassword: bPassword.trim() });
      resetForm();
    } catch (e) { console.error(e); }
  };

  const handleDisconnect = async (accountId: string, platform: string) => {
    if (confirm(`Disconnect your ${platform} account?`)) {
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
    const icons: Record<string, string> = {
      instagram: '📷', youtube: '▶️', tiktok: '🎵', twitter: '🐦', linkedin: '💼',
      facebook: '👥', pinterest: '📌', mastodon: '🐘', bluesky: '🦋',
    };
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

  const allPlatforms = ALL_PLATFORM_KEYS.map((platform) => {
    const connected = accounts.find((a: any) => a.platform.toLowerCase() === platform.key && a.is_active);
    return { ...platform, account: connected, connected: !!connected };
  });

  const statCards = [
    { label: 'Connected Accounts', value: connectedAccounts.length },
    { label: 'Total Followers', value: formatNumber(totalFollowers) },
    { label: 'Available Platforms', value: ALL_PLATFORM_KEYS.length - connectedAccounts.length },
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

        {/* Credential connect modal (Mastodon / Bluesky) */}
        {credForm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={resetForm}>
            <Card className="w-full max-w-md" onClick={(e) => e.stopPropagation()}>
              <CardHeader>
                <CardTitle>
                  Connect {credForm === 'mastodon' ? 'Mastodon' : 'Bluesky'}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {credForm === 'mastodon' ? (
                  <>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      Create an access token in your instance (Preferences → Development → New application,
                      scope <code>write:statuses</code>), then paste it below.
                    </p>
                    <div className="space-y-1.5">
                      <label className="text-xs font-medium text-gray-700 dark:text-gray-300">Instance URL</label>
                      <input
                        className={inputClass}
                        placeholder="https://mastodon.social"
                        value={mInstance}
                        onChange={(e) => setMInstance(e.target.value)}
                      />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-xs font-medium text-gray-700 dark:text-gray-300">Access token</label>
                      <input
                        className={inputClass}
                        type="password"
                        placeholder="Your instance access token"
                        value={mToken}
                        onChange={(e) => setMToken(e.target.value)}
                      />
                    </div>
                    <div className="flex justify-end gap-2 pt-2">
                      <Button variant="secondary" size="sm" onClick={resetForm}>Cancel</Button>
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={submitMastodon}
                        disabled={connectMastodon.isPending || !mInstance.trim() || !mToken.trim()}
                      >
                        {connectMastodon.isPending ? 'Connecting…' : 'Connect'}
                      </Button>
                    </div>
                  </>
                ) : (
                  <>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      Use an app password (Bluesky → Settings → App Passwords), not your main password.
                    </p>
                    <div className="space-y-1.5">
                      <label className="text-xs font-medium text-gray-700 dark:text-gray-300">Handle</label>
                      <input
                        className={inputClass}
                        placeholder="you.bsky.social"
                        value={bHandle}
                        onChange={(e) => setBHandle(e.target.value)}
                      />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-xs font-medium text-gray-700 dark:text-gray-300">App password</label>
                      <input
                        className={inputClass}
                        type="password"
                        placeholder="xxxx-xxxx-xxxx-xxxx"
                        value={bPassword}
                        onChange={(e) => setBPassword(e.target.value)}
                      />
                    </div>
                    <div className="flex justify-end gap-2 pt-2">
                      <Button variant="secondary" size="sm" onClick={resetForm}>Cancel</Button>
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={submitBluesky}
                        disabled={connectBluesky.isPending || !bHandle.trim() || !bPassword.trim()}
                      >
                        {connectBluesky.isPending ? 'Connecting…' : 'Connect'}
                      </Button>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </div>
        )}

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
                You can revoke these permissions at any time by disconnecting the account. We never access your private messages or personal data beyond what&apos;s necessary for the service.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
