'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Search, Plus, RefreshCw, X } from 'lucide-react';
import { useCompetitorsList, useAddCompetitor, useRemoveCompetitor } from '@/hooks/useCompetitors';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { Spinner } from '@/components/ui/spinner';
import { cn } from '@/lib/utils';

const inputCls = 'w-full rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-50 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-brand-500/24';

export default function CompetitorsPage() {
  const [showAddModal, setShowAddModal] = useState(false);
  const [newCompetitor, setNewCompetitor] = useState({ platform: 'instagram', username: '' });

  const { data, isLoading, error, refetch } = useCompetitorsList();
  const addCompetitor = useAddCompetitor();
  const removeCompetitor = useRemoveCompetitor();

  const handleAddCompetitor = async () => {
    if (!newCompetitor.username) { alert('Please enter a username'); return; }
    try {
      await addCompetitor.mutateAsync({
        platform: newCompetitor.platform as any,
        platform_username: newCompetitor.username,
      });
      setShowAddModal(false);
      setNewCompetitor({ platform: 'instagram', username: '' });
    } catch (e) {
      console.error('Failed to add competitor:', e);
      alert('Failed to add competitor');
    }
  };

  const formatNumber = (num: number) => {
    if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
    return num.toString();
  };

  const getPlatformIcon = (platform: string) => {
    const icons: Record<string, string> = { Instagram: '📷', YouTube: '▶️', TikTok: '🎵', Twitter: '🐦', LinkedIn: '💼', instagram: '📷', youtube: '▶️', tiktok: '🎵', twitter: '🐦', linkedin: '💼' };
    return icons[platform] || '📱';
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
          icon={<Search />}
          iconColor="error"
          title="Failed to load competitors"
          description={error instanceof Error ? error.message : 'Something went wrong'}
          actions={<Button onClick={() => refetch()} leadingIcon={<RefreshCw className="h-4 w-4" />}>Retry</Button>}
        />
      </div>
    );
  }

  const competitors = data?.items || [];

  const statCards = [
    { label: 'Tracked', value: competitors.length },
    { label: 'Combined Followers', value: formatNumber(competitors.reduce((s: number, c: any) => s + (c.followers_count || 0), 0)) },
    { label: 'Avg Engagement', value: `${competitors.length > 0 ? (competitors.reduce((s: number, c: any) => s + (c.avg_engagement_rate || 0), 0) / competitors.length * 100).toFixed(2) : 0}%` },
    { label: 'Avg Posts/Week', value: competitors.length > 0 ? (competitors.reduce((s: number, c: any) => s + (c.posting_frequency || 0), 0) / competitors.length).toFixed(1) : '0' },
  ];

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-10 space-y-8 animate-fade-in">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="space-y-1">
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">
              Competitor Intelligence
            </h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Track competitors and learn from their success.
            </p>
          </div>
          <Button variant="primary" leadingIcon={<Plus className="h-4 w-4" />} onClick={() => setShowAddModal(true)}>
            Add Competitor
          </Button>
        </header>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {statCards.map((s) => (
            <Card key={s.label} className="p-5">
              <p className="text-2xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">{s.value}</p>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{s.label}</p>
            </Card>
          ))}
        </div>

        <div className="space-y-4">
          {competitors.length > 0 ? competitors.map((competitor: any) => (
            <Card key={competitor.id} className="transition-all duration-150 hover:shadow-sm">
              <CardContent className="p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-4 flex-1 min-w-0">
                    <div className="h-14 w-14 shrink-0 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-2xl overflow-hidden">
                      {competitor.avatar_url ? (
                        <img src={competitor.avatar_url} alt={competitor.display_name} className="w-full h-full object-cover" />
                      ) : '👤'}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <h3 className="font-semibold text-gray-900 dark:text-gray-50 truncate">
                          {competitor.display_name || competitor.platform_username}
                        </h3>
                        <Badge variant="gray">{getPlatformIcon(competitor.platform)} {competitor.platform}</Badge>
                      </div>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
                        @{competitor.platform_username}
                      </p>
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                        {[
                          { label: 'Followers', value: formatNumber(competitor.followers_count || 0) },
                          { label: 'Engagement', value: `${((competitor.avg_engagement_rate || 0) * 100).toFixed(2)}%` },
                          { label: 'Posts/Week', value: String(competitor.posting_frequency || 0) },
                          { label: 'Last Tracked', value: competitor.last_tracked_at ? new Date(competitor.last_tracked_at).toLocaleDateString() : 'Never' },
                        ].map((stat) => (
                          <div key={stat.label}>
                            <p className="text-gray-500 dark:text-gray-400">{stat.label}</p>
                            <p className="font-semibold text-gray-900 dark:text-gray-50 mt-0.5">{stat.value}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2 shrink-0">
                    <Button asChild variant="secondary" size="sm"><Link href={`/competitors/${competitor.id}`}>View</Link></Button>
                    <Button
                      variant="tertiary"
                      size="sm"
                      leadingIcon={<X className="h-4 w-4" />}
                      disabled={removeCompetitor.isPending}
                      onClick={async () => {
                        if (confirm('Remove this competitor?')) {
                          try { await removeCompetitor.mutateAsync(competitor.id); } catch (e) { console.error(e); }
                        }
                      }}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          )) : (
            <EmptyState
              icon={<Search />}
              iconColor="brand"
              title="No competitors tracked yet"
              description="Start tracking competitors to learn from their success."
              actions={
                <Button variant="primary" leadingIcon={<Plus className="h-4 w-4" />} onClick={() => setShowAddModal(true)}>
                  Add Your First Competitor
                </Button>
              }
            />
          )}
        </div>

        {showAddModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <Card className="w-full max-w-md">
              <CardHeader>
                <CardTitle>Add Competitor</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">Platform</label>
                  <select
                    className={inputCls}
                    value={newCompetitor.platform}
                    onChange={(e) => setNewCompetitor({ ...newCompetitor, platform: e.target.value })}
                  >
                    <option value="instagram">Instagram</option>
                    <option value="youtube">YouTube</option>
                    <option value="tiktok">TikTok</option>
                    <option value="twitter">Twitter</option>
                    <option value="linkedin">LinkedIn</option>
                  </select>
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">Username</label>
                  <input
                    type="text"
                    className={inputCls}
                    placeholder="@username"
                    value={newCompetitor.username}
                    onChange={(e) => setNewCompetitor({ ...newCompetitor, username: e.target.value })}
                  />
                </div>
                <div className="flex gap-2">
                  <Button variant="primary" className="flex-1" onClick={handleAddCompetitor} disabled={addCompetitor.isPending} loading={addCompetitor.isPending}>
                    {addCompetitor.isPending ? 'Adding...' : 'Add Competitor'}
                  </Button>
                  <Button variant="secondary" onClick={() => setShowAddModal(false)}>Cancel</Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
