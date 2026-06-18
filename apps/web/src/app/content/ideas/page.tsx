/**
 * AI Content Ideas Page
 * 
 * Browse and manage AI-generated content ideas
 */

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useContentIdeas, useGenerateIdeas, useUpdateIdeaStatus, useCreateFromIdea } from '@/hooks/useContent';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

type IdeaStatus = 'all' | 'new' | 'saved' | 'used' | 'dismissed';

export default function ContentIdeasPage() {
  const router = useRouter();
  const [selectedStatus, setSelectedStatus] = useState<IdeaStatus>('all');

  // Fetch ideas
  const { data, isLoading, error, refetch } = useContentIdeas({
    status: selectedStatus === 'all' ? undefined : selectedStatus,
  });

  const generateIdeas = useGenerateIdeas();
  const updateStatus = useUpdateIdeaStatus();
  const createFromIdea = useCreateFromIdea();

  // Handle generate ideas
  const handleGenerateIdeas = async () => {
    try {
      await generateIdeas.mutateAsync(5);
    } catch (error) {
      console.error('Failed to generate ideas:', error);
    }
  };

  // Handle use idea
  const handleUseIdea = async (ideaId: string) => {
    try {
      const content = await createFromIdea.mutateAsync(ideaId);
      router.push(`/content/${content.id}`);
    } catch (error) {
      console.error('Failed to create content:', error);
      alert('Failed to create content from idea');
    }
  };

  // Handle save idea
  const handleSaveIdea = async (ideaId: string) => {
    try {
      await updateStatus.mutateAsync({ id: ideaId, status: 'saved' });
    } catch (error) {
      console.error('Failed to save idea:', error);
    }
  };

  // Handle dismiss idea
  const handleDismissIdea = async (ideaId: string) => {
    try {
      await updateStatus.mutateAsync({ id: ideaId, status: 'dismissed' });
    } catch (error) {
      console.error('Failed to dismiss idea:', error);
    }
  };

  const getViralityColor = (score: number) => {
    if (score >= 80) return 'text-success';
    if (score >= 60) return 'text-warning';
    return 'text-muted-foreground';
  };

  const getViralityLabel = (score: number) => {
    if (score >= 80) return 'High';
    if (score >= 60) return 'Medium';
    return 'Low';
  };

  const getPlatformIcon = (platform: string) => {
    const icons: Record<string, string> = {
      instagram: '📷',
      youtube: '▶️',
      tiktok: '🎵',
      twitter: '🐦',
      linkedin: '💼',
    };
    return icons[platform] || '📱';
  };

  const getContentTypeIcon = (type: string) => {
    const icons: Record<string, string> = {
      reel: '🎬',
      short: '⚡',
      post: '📝',
      carousel: '🖼️',
      story: '📖',
      video: '🎥',
    };
    return icons[type] || '📄';
  };

  const getSourceLabel = (source: string) => {
    const labels: Record<string, string> = {
      ai_generated: 'AI Generated',
      trend_derived: 'From Trend',
      competitor_inspired: 'Competitor Inspired',
      user_saved: 'User Saved',
      news: 'From News',
    };
    return labels[source] || source;
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-tech mx-auto mb-4" />
              <p className="text-muted-foreground">Loading ideas...</p>
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
              <h2 className="text-2xl font-bold mb-2">Failed to load ideas</h2>
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

  const ideas = data?.items || [];
  const total = data?.total || 0;

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-4xl font-bold gradient-text">AI Content Ideas</h1>
              <p className="text-muted-foreground mt-2">
                AI-powered content suggestions tailored to your niche
              </p>
            </div>
            <Button onClick={handleGenerateIdeas} disabled={generateIdeas.isPending}>
              {generateIdeas.isPending ? (
                <>
                  <span className="animate-spin mr-2">⚡</span>
                  Generating...
                </>
              ) : (
                <>
                  <span className="mr-2">✨</span>
                  Generate New Ideas
                </>
              )}
            </Button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">{total}</div>
                <div className="text-sm text-muted-foreground">Total Ideas</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">{ideas.filter((i: any) => i.status === 'new').length}</div>
                <div className="text-sm text-muted-foreground">New Ideas</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">{ideas.filter((i: any) => i.status === 'saved').length}</div>
                <div className="text-sm text-muted-foreground">Saved</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">{ideas.filter((i: any) => i.status === 'used').length}</div>
                <div className="text-sm text-muted-foreground">Used</div>
              </CardContent>
            </Card>
          </div>

          {/* Filters */}
          <div className="flex gap-2">
            {(['all', 'new', 'saved', 'used', 'dismissed'] as IdeaStatus[]).map(status => (
              <Button
                key={status}
                variant={selectedStatus === status ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSelectedStatus(status)}
              >
                {status.charAt(0).toUpperCase() + status.slice(1)}
              </Button>
            ))}
          </div>
        </div>

        {/* Ideas Grid */}
        {ideas.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {ideas.map((idea: any) => (
              <Card key={idea.id} className="card-hover">
                <CardHeader>
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-2xl">{getContentTypeIcon(idea.content_type)}</span>
                      <Badge variant="outline">{getSourceLabel(idea.source)}</Badge>
                    </div>
                    <div className={`text-sm font-semibold ${getViralityColor(idea.estimated_virality || 0)}`}>
                      🔥 {idea.estimated_virality || 0}% {getViralityLabel(idea.estimated_virality || 0)}
                    </div>
                  </div>
                  <CardTitle className="text-lg">{idea.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground mb-4">
                    {idea.description}
                  </p>

                  {/* Hook */}
                  {idea.hook && (
                    <div className="mb-4 p-3 bg-surface rounded-lg border border-border">
                      <div className="text-xs font-medium text-muted-foreground mb-1">
                        Suggested Hook:
                      </div>
                      <div className="text-sm italic">"{idea.hook}"</div>
                    </div>
                  )}

                  {/* Platforms */}
                  {idea.platforms && idea.platforms.length > 0 && (
                    <div className="mb-4">
                      <div className="text-xs font-medium text-muted-foreground mb-2">
                        Best Platforms:
                      </div>
                      <div className="flex gap-2">
                        {idea.platforms.map((platform: string) => (
                          <Badge key={platform} variant="default">
                            {getPlatformIcon(platform)}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Hashtags */}
                  {idea.hashtags && idea.hashtags.length > 0 && (
                    <div className="mb-4">
                      <div className="text-xs font-medium text-muted-foreground mb-2">
                        Suggested Hashtags:
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {idea.hashtags.map((tag: string, i: number) => (
                          <span key={i} className="text-xs text-tech">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex gap-2 pt-4 border-t border-border">
                    <Button
                      className="flex-1"
                      size="sm"
                      onClick={() => handleUseIdea(idea.id)}
                      disabled={createFromIdea.isPending}
                    >
                      {createFromIdea.isPending ? 'Creating...' : 'Use This Idea'}
                    </Button>
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => handleSaveIdea(idea.id)}
                      disabled={updateStatus.isPending}
                    >
                      💾
                    </Button>
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => handleDismissIdea(idea.id)}
                      disabled={updateStatus.isPending}
                    >
                      ✕
                    </Button>
                  </div>

                  <div className="text-xs text-muted-foreground mt-2">
                    Generated {new Date(idea.created_at).toLocaleDateString()}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="py-12">
              <div className="text-center">
                <div className="text-6xl mb-4">💡</div>
                <h3 className="text-xl font-semibold mb-2">No ideas found</h3>
                <p className="text-muted-foreground mb-6">
                  {selectedStatus === 'all'
                    ? 'Generate your first batch of AI-powered content ideas'
                    : `No ${selectedStatus} ideas found`}
                </p>
                <Button onClick={handleGenerateIdeas}>
                  Generate Ideas
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
