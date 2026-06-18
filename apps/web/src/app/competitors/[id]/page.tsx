/**
 * Competitor Detail Page
 * 
 * Deep dive into competitor analytics and content
 */

'use client';

import { use } from 'react';
import { useRouter } from 'next/navigation';
import { useCompetitor, useCompetitorContent, useCompetitorAnalysis, useRemoveCompetitor } from '@/hooks/useCompetitors';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export default function CompetitorDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();

  // Fetch competitor data
  const { data: competitor, isLoading, error, refetch } = useCompetitor(id);
  const { data: contentData } = useCompetitorContent(id);
  const { data: analysis } = useCompetitorAnalysis(id);
  const removeCompetitor = useRemoveCompetitor();

  // Handle remove
  const handleRemove = async () => {
    if (!confirm('Are you sure you want to remove this competitor?')) return;
    
    try {
      await removeCompetitor.mutateAsync(id);
      router.push('/competitors');
    } catch (error) {
      console.error('Failed to remove:', error);
      alert('Failed to remove competitor');
    }
  };

  const formatNumberLegacy = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const getContentTypeIconLegacy = (type: string) => {
    const icons: Record<string, string> = {
      reel: '🎬',
      carousel: '🖼️',
      post: '📝',
      story: '📖',
    };
    return icons[type] || '📄';
  };

  const getPlatformIcon = (platform: string) => {
    const icons: Record<string, string> = {
      instagram: '📷',
      youtube: '▶️',
      tiktok: '🎵',
      twitter: '🐦',
      linkedin: '💼',
    };
    return icons[platform?.toLowerCase()] || '📱';
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-tech mx-auto mb-4" />
              <p className="text-muted-foreground">Loading competitor...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !competitor) {
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="text-error text-5xl mb-4">⚠️</div>
              <h2 className="text-2xl font-bold mb-2">Failed to load competitor</h2>
              <p className="text-muted-foreground mb-4">
                {error instanceof Error ? error.message : 'Competitor not found'}
              </p>
              <div className="flex gap-2 justify-center">
                <Button onClick={() => refetch()}>Retry</Button>
                <Button variant="outline" onClick={() => router.push('/competitors')}>
                  Back to Competitors
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const recentPosts = contentData?.items || [];

  // Mock competitor data - will be replaced with real API
  const mockCompetitor = {
    id,
    username: 'techcreator',
    displayName: 'Tech Creator',
    platform: 'Instagram',
    followers: 25000,
    following: 892,
    posts: 234,
    avgEngagement: 0.0567,
    postingFrequency: 4.5,
    lastPost: '2 hours ago',
    bio: 'Tech content creator | AI enthusiast | Helping creators grow',
    avatar: '👨‍💻',
    
    // Growth stats
    followersGrowth: {
      '7d': 450,
      '30d': 1820,
      '90d': 5200,
    },
    
    // Recent posts
    recentPosts: [
      {
        id: '1',
        title: 'AI Tools for Content Creation',
        type: 'reel',
        postedAt: '2 hours ago',
        views: 12400,
        likes: 890,
        comments: 67,
        engagement: 0.0772,
      },
      {
        id: '2',
        title: 'Behind the Scenes Setup Tour',
        type: 'reel',
        postedAt: '1 day ago',
        views: 18900,
        likes: 1240,
        comments: 92,
        engagement: 0.0705,
      },
      {
        id: '3',
        title: 'Top 5 Productivity Hacks',
        type: 'carousel',
        postedAt: '3 days ago',
        views: 9200,
        likes: 620,
        comments: 45,
        engagement: 0.0723,
      },
    ],
    
    // Content analysis
    topTopics: [
      { topic: 'AI Tools', count: 45, engagement: 0.0812 },
      { topic: 'Productivity', count: 38, engagement: 0.0756 },
      { topic: 'Tech Reviews', count: 32, engagement: 0.0689 },
      { topic: 'Behind the Scenes', count: 28, engagement: 0.0734 },
    ],
    
    // Best performing content
    bestContent: {
      title: 'ChatGPT Prompts That Changed My Life',
      views: 45200,
      engagement: 0.0923,
      postedAt: '2 weeks ago',
    },
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const getContentTypeIcon = (type: string) => {
    const icons: Record<string, string> = {
      reel: '🎬',
      carousel: '🖼️',
      post: '📝',
      story: '📖',
    };
    return icons[type] || '📄';
  };

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <Button variant="outline" onClick={() => router.push('/competitors')} className="mb-4">
            ← Back to Competitors
          </Button>
          
          <div className="flex items-start gap-6">
            {/* Avatar */}
            <div className="w-24 h-24 rounded-full bg-surface flex items-center justify-center text-5xl overflow-hidden">
              {competitor.avatar_url ? (
                <img src={competitor.avatar_url} alt={competitor.display_name} className="w-full h-full object-cover" />
              ) : (
                '👤'
              )}
            </div>

            {/* Info */}
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-4xl font-bold gradient-text">{competitor.display_name || competitor.platform_username}</h1>
                <Badge variant="default">{getPlatformIcon(competitor.platform)} {competitor.platform}</Badge>
              </div>
              <div className="text-muted-foreground mb-3">@{competitor.platform_username}</div>
              {competitor.profile_url && (
                <a href={competitor.profile_url} target="_blank" rel="noopener noreferrer" className="text-sm text-tech hover:underline mb-4 block">
                  View on {competitor.platform} →
                </a>
              )}
              
              <div className="flex items-center gap-6 text-sm">
                <div>
                  <span className="font-semibold">{formatNumber(competitor.followers_count || 0)}</span>
                  <span className="text-muted-foreground"> followers</span>
                </div>
                <div>
                  <span className="font-semibold">{formatNumber(competitor.following_count || 0)}</span>
                  <span className="text-muted-foreground"> following</span>
                </div>
                <div>
                  <span className="font-semibold">{competitor.posts_count || 0}</span>
                  <span className="text-muted-foreground"> posts</span>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-2">
              <Button variant="outline">🔔 Alerts</Button>
              <Button 
                variant="outline" 
                className="text-error"
                onClick={handleRemove}
                disabled={removeCompetitor.isPending}
              >
                {removeCompetitor.isPending ? 'Removing...' : 'Remove'}
              </Button>
            </div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold">{((competitor.avg_engagement_rate || 0) * 100).toFixed(2)}%</div>
              <div className="text-sm text-muted-foreground">Avg Engagement</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold">{competitor.posting_frequency || 0}</div>
              <div className="text-sm text-muted-foreground">Posts/Week</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold text-success">
                {competitor.last_tracked_at 
                  ? new Date(competitor.last_tracked_at).toLocaleDateString()
                  : 'Never'
                }
              </div>
              <div className="text-sm text-muted-foreground">Last Tracked</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold">
                {competitor.tracking_since 
                  ? new Date(competitor.tracking_since).toLocaleDateString()
                  : 'Unknown'
                }
              </div>
              <div className="text-sm text-muted-foreground">Tracking Since</div>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Recent Posts */}
            <Card>
              <CardHeader>
                <CardTitle>Recent Posts</CardTitle>
              </CardHeader>
              <CardContent>
                {recentPosts.length > 0 ? (
                  <div className="space-y-4">
                    {recentPosts.map((post: any) => (
                      <div key={post.id} className="flex items-center justify-between p-4 bg-surface rounded-lg">
                        <div className="flex items-center gap-4 flex-1">
                          <span className="text-3xl">{getContentTypeIcon(post.content_type)}</span>
                          <div className="flex-1">
                            <div className="font-semibold mb-1">{post.caption?.substring(0, 50) || 'Untitled'}</div>
                            <div className="text-sm text-muted-foreground">
                              Posted {post.posted_at ? new Date(post.posted_at).toLocaleDateString() : 'Unknown'}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-6 text-sm">
                          <div className="text-center">
                            <div className="font-semibold">{formatNumber(post.views || 0)}</div>
                            <div className="text-muted-foreground">Views</div>
                          </div>
                          <div className="text-center">
                            <div className="font-semibold">{formatNumber(post.likes || 0)}</div>
                            <div className="text-muted-foreground">Likes</div>
                          </div>
                          <div className="text-center">
                            <div className="font-semibold text-tech">{((post.engagement_rate || 0) * 100).toFixed(2)}%</div>
                            <div className="text-muted-foreground">Engagement</div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    No posts tracked yet
                  </div>
                )}
              </CardContent>
            </Card>

            {/* AI Analysis */}
            {analysis && (
              <Card>
                <CardHeader>
                  <CardTitle>AI Analysis</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4 text-sm">
                    {analysis.content_gaps && analysis.content_gaps.length > 0 && (
                      <div className="p-3 bg-tech/10 border border-tech/20 rounded-lg">
                        <div className="font-medium text-tech mb-2">💡 Content Opportunities</div>
                        <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                          {analysis.content_gaps.map((gap: string, i: number) => (
                            <li key={i}>{gap}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    
                    {analysis.why_it_worked && (
                      <div className="p-3 bg-success/10 border border-success/20 rounded-lg">
                        <div className="font-medium text-success mb-1">✓ What's Working</div>
                        <p className="text-muted-foreground">{analysis.why_it_worked}</p>
                      </div>
                    )}
                    
                    {analysis.topics && analysis.topics.length > 0 && (
                      <div className="p-3 bg-surface border border-border rounded-lg">
                        <div className="font-medium mb-2">📊 Top Topics</div>
                        <div className="flex flex-wrap gap-2">
                          {analysis.topics.map((topic: string, i: number) => (
                            <Badge key={i} variant="outline">{topic}</Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Metadata */}
            <Card>
              <CardHeader>
                <CardTitle>Tracking Info</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Status</span>
                  <Badge variant={competitor.is_active ? 'success' : 'default'}>
                    {competitor.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Platform</span>
                  <span className="font-semibold">{competitor.platform}</span>
                </div>
                {competitor.niche_id && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Niche</span>
                    <Badge variant="outline">Same as yours</Badge>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Quick Stats */}
            <Card>
              <CardHeader>
                <CardTitle>Quick Stats</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Followers</span>
                  <span className="font-semibold">{formatNumber(competitor.followers_count || 0)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Following</span>
                  <span className="font-semibold">{formatNumber(competitor.following_count || 0)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Posts</span>
                  <span className="font-semibold">{competitor.posts_count || 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Engagement</span>
                  <span className="font-semibold text-tech">{((competitor.avg_engagement_rate || 0) * 100).toFixed(2)}%</span>
                </div>
              </CardContent>
            </Card>

            {/* Actions */}
            <Card>
              <CardHeader>
                <CardTitle>Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <Button className="w-full" variant="outline">
                  📊 View Full Report
                </Button>
                <Button className="w-full" variant="outline">
                  🔄 Refresh Data
                </Button>
                {competitor.profile_url && (
                  <Button 
                    className="w-full" 
                    variant="outline"
                    onClick={() => window.open(competitor.profile_url, '_blank')}
                  >
                    🔗 Open Profile
                  </Button>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
