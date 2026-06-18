/**
 * Competitors Overview Page
 * 
 * Track and analyze competitor performance
 */

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useCompetitorsList, useAddCompetitor, useRemoveCompetitor } from '@/hooks/useCompetitors';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

export default function CompetitorsPage() {
  const [showAddModal, setShowAddModal] = useState(false);
  const [newCompetitor, setNewCompetitor] = useState({
    platform: 'instagram',
    username: '',
  });

  // Fetch competitors
  const { data, isLoading, error, refetch } = useCompetitorsList();
  const addCompetitor = useAddCompetitor();
  const removeCompetitor = useRemoveCompetitor();

  // Handle add competitor
  const handleAddCompetitor = async () => {
    if (!newCompetitor.username) {
      alert('Please enter a username');
      return;
    }

    try {
      await addCompetitor.mutateAsync({
        platform: newCompetitor.platform as any,
        platform_username: newCompetitor.username,
      });
      setShowAddModal(false);
      setNewCompetitor({ platform: 'instagram', username: '' });
    } catch (error) {
      console.error('Failed to add competitor:', error);
      alert('Failed to add competitor');
    }
  };

  const formatNumberLegacy = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const getPlatformIconLegacy = (platform: string) => {
    const icons: Record<string, string> = {
      instagram: '📷',
      youtube: '▶️',
      tiktok: '🎵',
      twitter: '🐦',
      linkedin: '💼',
    };
    return icons[platform.toLowerCase()] || '📱';
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-tech mx-auto mb-4" />
              <p className="text-muted-foreground">Loading competitors...</p>
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
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="text-error text-5xl mb-4">⚠️</div>
              <h2 className="text-2xl font-bold mb-2">Failed to load competitors</h2>
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

  const competitors = data?.items || [];

  // Mock data - will be replaced with real API calls
  const mockCompetitors = [
    {
      id: '1',
      username: 'techcreator',
      displayName: 'Tech Creator',
      platform: 'Instagram',
      followers: 25000,
      avgEngagement: 0.0567,
      postingFrequency: 4.5,
      lastPost: '2 hours ago',
      trend: 'up',
      avatar: '👨‍💻',
    },
    {
      id: '2',
      username: 'aiexplainer',
      displayName: 'AI Explainer',
      platform: 'YouTube',
      followers: 18500,
      avgEngagement: 0.0823,
      postingFrequency: 2.0,
      lastPost: '1 day ago',
      trend: 'up',
      avatar: '🤖',
    },
    {
      id: '3',
      username: 'contentpro',
      displayName: 'Content Pro',
      platform: 'TikTok',
      followers: 52000,
      avgEngagement: 0.0445,
      postingFrequency: 6.0,
      lastPost: '5 hours ago',
      trend: 'down',
      avatar: '🎬',
    },
  ];

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const getPlatformIcon = (platform: string) => {
    const icons: Record<string, string> = {
      Instagram: '📷',
      YouTube: '▶️',
      TikTok: '🎵',
      Twitter: '🐦',
      LinkedIn: '💼',
    };
    return icons[platform] || '📱';
  };

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-4xl font-bold gradient-text">Competitor Intelligence</h1>
              <p className="text-muted-foreground mt-2">
                Track competitors and learn from their success
              </p>
            </div>
            <Button onClick={() => setShowAddModal(true)}>
              <span className="mr-2">+</span>
              Add Competitor
            </Button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">{competitors.length}</div>
                <div className="text-sm text-muted-foreground">Tracked Competitors</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">
                  {formatNumber(competitors.reduce((sum: number, c: any) => sum + (c.followers_count || 0), 0))}
                </div>
                <div className="text-sm text-muted-foreground">Combined Followers</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">
                  {competitors.length > 0 
                    ? (competitors.reduce((sum: number, c: any) => sum + (c.avg_engagement_rate || 0), 0) / competitors.length * 100).toFixed(2)
                    : 0}%
                </div>
                <div className="text-sm text-muted-foreground">Avg Engagement</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">
                  {competitors.length > 0
                    ? (competitors.reduce((sum: number, c: any) => sum + (c.posting_frequency || 0), 0) / competitors.length).toFixed(1)
                    : 0}
                </div>
                <div className="text-sm text-muted-foreground">Avg Posts/Week</div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Competitors List */}
        <div className="space-y-4">
          {competitors.length > 0 ? competitors.map((competitor: any) => (
            <Card key={competitor.id} className="card-hover">
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4 flex-1">
                    {/* Avatar */}
                    <div className="w-16 h-16 rounded-full bg-surface flex items-center justify-center text-3xl">
                      {competitor.avatar_url ? (
                        <img src={competitor.avatar_url} alt={competitor.display_name} className="w-full h-full rounded-full" />
                      ) : (
                        '👤'
                      )}
                    </div>

                    {/* Info */}
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-xl font-semibold">{competitor.display_name || competitor.platform_username}</h3>
                        <Badge variant="default">
                          {getPlatformIcon(competitor.platform)} {competitor.platform}
                        </Badge>
                      </div>
                      <div className="text-sm text-muted-foreground mb-4">
                        @{competitor.platform_username}
                      </div>

                      {/* Stats */}
                      <div className="grid grid-cols-4 gap-6">
                        <div>
                          <div className="text-sm text-muted-foreground">Followers</div>
                          <div className="text-lg font-semibold">{formatNumber(competitor.followers_count || 0)}</div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">Engagement</div>
                          <div className="text-lg font-semibold">{((competitor.avg_engagement_rate || 0) * 100).toFixed(2)}%</div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">Posts/Week</div>
                          <div className="text-lg font-semibold">{competitor.posting_frequency || 0}</div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">Last Tracked</div>
                          <div className="text-lg font-semibold">
                            {competitor.last_tracked_at 
                              ? new Date(competitor.last_tracked_at).toLocaleDateString()
                              : 'Never'
                            }
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2">
                    <Link href={`/competitors/${competitor.id}`}>
                      <Button variant="outline" size="sm">
                        View Details
                      </Button>
                    </Link>
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={async () => {
                        if (confirm('Remove this competitor?')) {
                          try {
                            await removeCompetitor.mutateAsync(competitor.id);
                          } catch (error) {
                            console.error('Failed to remove:', error);
                          }
                        }
                      }}
                      disabled={removeCompetitor.isPending}
                    >
                      ✕
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )) : (
            <Card>
              <CardContent className="py-12">
                <div className="text-center">
                  <div className="text-6xl mb-4">🔍</div>
                  <h3 className="text-xl font-semibold mb-2">No competitors tracked yet</h3>
                  <p className="text-muted-foreground mb-6">
                    Start tracking competitors to learn from their success
                  </p>
                  <Button onClick={() => setShowAddModal(true)}>
                    Add Your First Competitor
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Add Competitor Modal */}
        {showAddModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <Card className="w-full max-w-md">
              <CardHeader>
                <CardTitle>Add Competitor</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Platform
                    </label>
                    <select 
                      className="w-full px-3 py-2 bg-surface rounded-md border border-input"
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
                    <label className="block text-sm font-medium mb-2">
                      Username
                    </label>
                    <input
                      type="text"
                      className="w-full px-3 py-2 bg-surface rounded-md border border-input"
                      placeholder="@username"
                      value={newCompetitor.username}
                      onChange={(e) => setNewCompetitor({ ...newCompetitor, username: e.target.value })}
                    />
                  </div>

                  <div className="flex gap-2">
                    <Button 
                      className="flex-1"
                      onClick={handleAddCompetitor}
                      disabled={addCompetitor.isPending}
                    >
                      {addCompetitor.isPending ? 'Adding...' : 'Add Competitor'}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => setShowAddModal(false)}
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
