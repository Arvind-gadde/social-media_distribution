/**
 * Content Detail Page
 * 
 * View and edit individual content item with analytics
 */

'use client';

import { use } from 'react';
import { useRouter } from 'next/navigation';
import { useContent, useDeleteContent, useUpdateContent } from '@/hooks/useContent';
import { useContentAnalytics } from '@/hooks/useAnalytics';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export default function ContentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  
  // Fetch content and analytics
  const { data: content, isLoading, error, refetch } = useContent(id);
  const { data: analytics } = useContentAnalytics(id);
  const deleteContent = useDeleteContent();
  const updateContent = useUpdateContent();

  // Handle delete
  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this content?')) return;
    
    try {
      await deleteContent.mutateAsync(id);
      router.push('/content');
    } catch (error) {
      console.error('Failed to delete:', error);
      alert('Failed to delete content');
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
      tiktok: '🎵',
      youtube: '▶️',
      twitter: '🐦',
      linkedin: '💼',
    };
    return icons[platform.toLowerCase()] || '📱';
  };

  const getStatusColorLegacy = (status: string) => {
    const colors: Record<string, 'default' | 'success' | 'warning' | 'error'> = {
      draft: 'default',
      scheduled: 'warning',
      published: 'success',
      failed: 'error',
    };
    return colors[status] || 'default';
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-tech mx-auto mb-4" />
              <p className="text-muted-foreground">Loading content...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !content) {
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="text-error text-5xl mb-4">⚠️</div>
              <h2 className="text-2xl font-bold mb-2">Failed to load content</h2>
              <p className="text-muted-foreground mb-4">
                {error instanceof Error ? error.message : 'Content not found'}
              </p>
              <div className="flex gap-2 justify-center">
                <Button onClick={() => refetch()}>Retry</Button>
                <Button variant="outline" onClick={() => router.push('/content')}>
                  Back to Content
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Mock content data - will be replaced with real API
  const mockContent = {
    id,
    title: 'Top 5 AI Tools for Creators',
    caption: 'These AI tools save me 10 hours every week! 🚀 #AITools #ContentCreator #Productivity',
    contentType: 'reel',
    status: 'published',
    platforms: ['instagram', 'tiktok'],
    publishedAt: '2 days ago',
    scheduledAt: null,
    hashtags: ['#AITools', '#ContentCreator', '#Productivity', '#AI', '#CreatorEconomy'],
    mentions: ['@openai', '@anthropic'],
    
    // Analytics
    totalViews: 15420,
    totalLikes: 892,
    totalComments: 67,
    totalShares: 34,
    totalSaves: 156,
    engagementRate: 0.0648,
    reach: 18900,
    impressions: 22400,
    
    // Platform breakdown
    platformStats: [
      {
        platform: 'Instagram',
        views: 8920,
        likes: 520,
        comments: 42,
        shares: 18,
        engagement: 0.0651,
      },
      {
        platform: 'TikTok',
        views: 6500,
        likes: 372,
        comments: 25,
        shares: 16,
        engagement: 0.0635,
      },
    ],
    
    // Top comments
    topComments: [
      { author: '@user1', text: 'This is amazing! What camera do you use?', likes: 45 },
      { author: '@user2', text: 'Can you make a tutorial on this?', likes: 32 },
      { author: '@user3', text: 'Love your content! Keep it up 🔥', likes: 28 },
    ],
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const getPlatformIcon = (platform: string) => {
    const icons: Record<string, string> = {
      Instagram: '📷',
      TikTok: '🎵',
      YouTube: '▶️',
      Twitter: '🐦',
    };
    return icons[platform] || '📱';
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, 'default' | 'success' | 'warning' | 'error'> = {
      draft: 'default',
      scheduled: 'warning',
      published: 'success',
      failed: 'error',
    };
    return colors[status] || 'default';
  };

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <Button variant="outline" onClick={() => router.push('/content')} className="mb-4">
            ← Back to Content
          </Button>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-4xl font-bold gradient-text mb-2">{content.title || 'Untitled Content'}</h1>
              <div className="flex items-center gap-3">
                <Badge variant={getStatusColor(content.status)}>
                  {content.status}
                </Badge>
                <span className="text-muted-foreground">
                  {content.published_at 
                    ? `Published ${new Date(content.published_at).toLocaleDateString()}` 
                    : content.scheduled_at 
                    ? `Scheduled for ${new Date(content.scheduled_at).toLocaleDateString()}`
                    : 'Draft'
                  }
                </span>
              </div>
            </div>
            <div className="flex gap-2">
              <Button variant="outline">Edit</Button>
              <Button variant="outline">Duplicate</Button>
              <Button 
                variant="outline" 
                className="text-error"
                onClick={handleDelete}
                disabled={deleteContent.isPending}
              >
                {deleteContent.isPending ? 'Deleting...' : 'Delete'}
              </Button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Content Preview */}
            <Card>
              <CardHeader>
                <CardTitle>Content Preview</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="aspect-[9/16] bg-surface rounded-lg flex items-center justify-center mb-4">
                  <div className="text-center">
                    <div className="text-6xl mb-2">🎬</div>
                    <div className="text-muted-foreground">Video Preview</div>
                  </div>
                </div>
                
                <div className="space-y-4">
                  <div>
                    <div className="text-sm font-medium mb-2">Caption</div>
                    <p className="text-sm">{content.caption || 'No caption'}</p>
                  </div>
                  
                  {content.hashtags && content.hashtags.length > 0 && (
                    <div>
                      <div className="text-sm font-medium mb-2">Hashtags</div>
                      <div className="flex flex-wrap gap-2">
                        {content.hashtags.map((tag, i) => (
                          <Badge key={i} variant="outline">{tag}</Badge>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  <div>
                    <div className="text-sm font-medium mb-2">Platforms</div>
                    <div className="flex gap-2">
                      {content.platforms.map((platform, i) => (
                        <Badge key={i} variant="default">
                          {getPlatformIcon(platform)} {platform}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Performance Analytics */}
            {content.status === 'published' && (
              <Card>
                <CardHeader>
                  <CardTitle>Performance Analytics</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    <div className="text-center p-4 bg-surface rounded-lg">
                      <div className="text-2xl font-bold">{formatNumber(content.total_views || 0)}</div>
                      <div className="text-sm text-muted-foreground">Views</div>
                    </div>
                    <div className="text-center p-4 bg-surface rounded-lg">
                      <div className="text-2xl font-bold">{formatNumber(content.total_likes || 0)}</div>
                      <div className="text-sm text-muted-foreground">Likes</div>
                    </div>
                    <div className="text-center p-4 bg-surface rounded-lg">
                      <div className="text-2xl font-bold">{content.total_comments || 0}</div>
                      <div className="text-sm text-muted-foreground">Comments</div>
                    </div>
                    <div className="text-center p-4 bg-surface rounded-lg">
                      <div className="text-2xl font-bold">{((content.engagement_rate || 0) * 100).toFixed(2)}%</div>
                      <div className="text-sm text-muted-foreground">Engagement</div>
                    </div>
                  </div>

                  {/* Platform Breakdown - using mock data for now */}
                  <div className="space-y-3">
                    <div className="text-sm font-medium">Platform Breakdown</div>
                    {mockContent.platformStats.map((stat, i) => (
                      <div key={i} className="flex items-center justify-between p-3 bg-surface rounded-lg">
                        <div className="flex items-center gap-3">
                          <span className="text-2xl">{getPlatformIcon(stat.platform)}</span>
                          <div>
                            <div className="font-medium">{stat.platform}</div>
                            <div className="text-sm text-muted-foreground">
                              {formatNumber(stat.views)} views
                            </div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="font-semibold">{(stat.engagement * 100).toFixed(2)}%</div>
                          <div className="text-sm text-muted-foreground">Engagement</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Top Comments */}
            {content.status === 'published' && (
              <Card>
                <CardHeader>
                  <CardTitle>Top Comments</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {(content.topComments ?? []).map((comment, i) => (
                      <div key={i} className="p-3 bg-surface rounded-lg">
                        <div className="flex items-start justify-between mb-2">
                          <div className="font-medium">{comment.author}</div>
                          <div className="text-sm text-muted-foreground">
                            ❤️ {comment.likes}
                          </div>
                        </div>
                        <p className="text-sm">{comment.text}</p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Quick Stats */}
            <Card>
              <CardHeader>
                <CardTitle>Quick Stats</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Reach</span>
                  <span className="font-semibold">{formatNumber(content.reach || 0)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Impressions</span>
                  <span className="font-semibold">{formatNumber(content.impressions || 0)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Saves</span>
                  <span className="font-semibold">{formatNumber(content.total_saves || 0)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Shares</span>
                  <span className="font-semibold">{formatNumber(content.total_shares || 0)}</span>
                </div>
              </CardContent>
            </Card>

            {/* AI Insights */}
            <Card>
              <CardHeader>
                <CardTitle>AI Insights</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4 text-sm">
                  <div className="p-3 bg-success/10 border border-success/20 rounded-lg">
                    <div className="font-medium text-success mb-1">✓ Strong Performance</div>
                    <p className="text-muted-foreground">
                      This content is performing 23% above your average engagement rate
                    </p>
                  </div>
                  
                  <div className="p-3 bg-tech/10 border border-tech/20 rounded-lg">
                    <div className="font-medium text-tech mb-1">💡 Recommendation</div>
                    <p className="text-muted-foreground">
                      Create similar content about AI tools. This topic resonates well with your audience.
                    </p>
                  </div>
                  
                  <div className="p-3 bg-surface border border-border rounded-lg">
                    <div className="font-medium mb-1">📊 Best Time</div>
                    <p className="text-muted-foreground">
                      Most engagement happened between 2-4 PM EST
                    </p>
                  </div>
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
                  📊 View Full Analytics
                </Button>
                <Button className="w-full" variant="outline">
                  🔄 Repost to Other Platforms
                </Button>
                <Button className="w-full" variant="outline">
                  📥 Download Content
                </Button>
                <Button className="w-full" variant="outline">
                  📋 Copy Link
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
