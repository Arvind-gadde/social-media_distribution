'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Lightbulb, Sparkles, Bookmark, X, RefreshCw } from 'lucide-react';
import { useContentIdeas, useGenerateIdeas, useUpdateIdeaStatus, useCreateFromIdea } from '@/hooks/useContent';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { EmptyState } from '@/components/ui/empty-state';
import { Spinner } from '@/components/ui/spinner';
import { cn } from '@/lib/utils';

type IdeaStatus = 'all' | 'new' | 'saved' | 'used' | 'dismissed';

export default function ContentIdeasPage() {
  const router = useRouter();
  const [selectedStatus, setSelectedStatus] = useState<IdeaStatus>('all');

  const { data, isLoading, error, refetch } = useContentIdeas({
    status: selectedStatus === 'all' ? undefined : selectedStatus,
  });

  const generateIdeas = useGenerateIdeas();
  const updateStatus = useUpdateIdeaStatus();
  const createFromIdea = useCreateFromIdea();

  const handleGenerateIdeas = async () => {
    try { await generateIdeas.mutateAsync(5); } catch (e) { console.error(e); }
  };

  const handleUseIdea = async (ideaId: string) => {
    try {
      const content = await createFromIdea.mutateAsync(ideaId);
      router.push(`/content/${content.id}`);
    } catch (e) {
      console.error(e);
      alert('Failed to create content from idea');
    }
  };

  const handleSaveIdea = async (ideaId: string) => {
    try { await updateStatus.mutateAsync({ id: ideaId, status: 'saved' }); } catch (e) { console.error(e); }
  };

  const handleDismissIdea = async (ideaId: string) => {
    try { await updateStatus.mutateAsync({ id: ideaId, status: 'dismissed' }); } catch (e) { console.error(e); }
  };

  const getViralityColor = (score: number) =>
    score >= 80 ? 'text-success-600 dark:text-success-400' : score >= 60 ? 'text-warning-600 dark:text-warning-400' : 'text-gray-500 dark:text-gray-400';

  const getViralityLabel = (score: number) => score >= 80 ? 'High' : score >= 60 ? 'Medium' : 'Low';

  const getPlatformIcon = (platform: string) => {
    const icons: Record<string, string> = { instagram: '📷', youtube: '▶️', tiktok: '🎵', twitter: '🐦', linkedin: '💼' };
    return icons[platform] || '📱';
  };

  const getContentTypeIcon = (type: string) => {
    const icons: Record<string, string> = { reel: '🎬', short: '⚡', post: '📝', carousel: '🖼️', story: '📖', video: '🎥' };
    return icons[type] || '📄';
  };

  const getSourceLabel = (source: string) => {
    const labels: Record<string, string> = { ai_generated: 'AI Generated', trend_derived: 'From Trend', competitor_inspired: 'Competitor Inspired', user_saved: 'User Saved', news: 'From News' };
    return labels[source] || source;
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
          icon={<Lightbulb />}
          iconColor="error"
          title="Failed to load ideas"
          description={error instanceof Error ? error.message : 'Something went wrong'}
          actions={<Button onClick={() => refetch()} leadingIcon={<RefreshCw className="h-4 w-4" />}>Retry</Button>}
        />
      </div>
    );
  }

  const ideas = data?.items || [];
  const total = data?.total || 0;

  const statCards = [
    { label: 'Total Ideas', value: total },
    { label: 'New', value: ideas.filter((i: any) => i.status === 'new').length },
    { label: 'Saved', value: ideas.filter((i: any) => i.status === 'saved').length },
    { label: 'Used', value: ideas.filter((i: any) => i.status === 'used').length },
  ];

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-10 space-y-8 animate-fade-in">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="space-y-1">
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">
              AI Content Ideas
            </h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              AI-powered content suggestions tailored to your niche.
            </p>
          </div>
          <Button
            variant="primary"
            leadingIcon={<Sparkles className="h-4 w-4" />}
            onClick={handleGenerateIdeas}
            disabled={generateIdeas.isPending}
            loading={generateIdeas.isPending}
          >
            {generateIdeas.isPending ? 'Generating...' : 'Generate New Ideas'}
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

        <div className="flex flex-wrap gap-1 rounded-lg border border-gray-200 dark:border-gray-800 p-1 w-fit">
          {(['all', 'new', 'saved', 'used', 'dismissed'] as IdeaStatus[]).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setSelectedStatus(s)}
              className={cn(
                'rounded-md px-3 py-1.5 text-sm font-medium capitalize transition-colors',
                selectedStatus === s
                  ? 'bg-brand-600 text-white'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
              )}
            >
              {s}
            </button>
          ))}
        </div>

        {ideas.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {ideas.map((idea: any) => (
              <Card key={idea.id} className="flex flex-col transition-all duration-200 hover:shadow-md">
                <CardHeader>
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-2xl">{getContentTypeIcon(idea.content_type)}</span>
                      <Badge variant="gray" size="sm">{getSourceLabel(idea.source)}</Badge>
                    </div>
                    <span className={cn('text-sm font-semibold', getViralityColor(idea.estimated_virality || 0))}>
                      🔥 {idea.estimated_virality || 0}% {getViralityLabel(idea.estimated_virality || 0)}
                    </span>
                  </div>
                  <CardTitle className="text-base">{idea.title}</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-col flex-1">
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">{idea.description}</p>

                  {idea.hook && (
                    <div className="mb-4 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-3">
                      <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Suggested Hook:</p>
                      <p className="text-sm italic text-gray-700 dark:text-gray-300">"{idea.hook}"</p>
                    </div>
                  )}

                  {idea.platforms?.length > 0 && (
                    <div className="mb-4">
                      <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">Best Platforms:</p>
                      <div className="flex gap-1">
                        {idea.platforms.map((p: string) => (
                          <Badge key={p} variant="gray" size="sm">{getPlatformIcon(p)}</Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {idea.hashtags?.length > 0 && (
                    <div className="mb-4">
                      <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">Suggested Hashtags:</p>
                      <div className="flex flex-wrap gap-1">
                        {idea.hashtags.map((tag: string, i: number) => (
                          <span key={i} className="text-xs text-brand-600 dark:text-brand-400">{tag}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="mt-auto pt-4 border-t border-gray-200 dark:border-gray-800 flex gap-2">
                    <Button
                      variant="primary"
                      className="flex-1"
                      size="sm"
                      onClick={() => handleUseIdea(idea.id)}
                      disabled={createFromIdea.isPending}
                      loading={createFromIdea.isPending}
                    >
                      Use This Idea
                    </Button>
                    <Button variant="secondary" size="sm" leadingIcon={<Bookmark className="h-3.5 w-3.5" />} onClick={() => handleSaveIdea(idea.id)} disabled={updateStatus.isPending} />
                    <Button variant="tertiary" size="sm" leadingIcon={<X className="h-3.5 w-3.5" />} onClick={() => handleDismissIdea(idea.id)} disabled={updateStatus.isPending} />
                  </div>
                  <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
                    Generated {new Date(idea.created_at).toLocaleDateString()}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <EmptyState
            icon={<Lightbulb />}
            iconColor="brand"
            title="No ideas found"
            description={
              selectedStatus === 'all'
                ? 'Generate your first batch of AI-powered content ideas.'
                : `No ${selectedStatus} ideas found.`
            }
            actions={
              <Button variant="primary" leadingIcon={<Sparkles className="h-4 w-4" />} onClick={handleGenerateIdeas}>
                Generate Ideas
              </Button>
            }
          />
        )}
      </div>
    </div>
  );
}
