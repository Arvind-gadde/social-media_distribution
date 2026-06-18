/**
 * News page — niche-aware article feed with "create content" pipe.
 */
'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  createContentFromNews,
  listNews,
  type NewsArticle,
} from '@contentflow/api-client';
import { formatRelativeTime } from '@/lib/utils';

export default function NewsPage() {
  const [page, setPage] = useState(1);
  const [threshold, setThreshold] = useState(0.3);
  const queryClient = useQueryClient();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['news', page, threshold],
    queryFn: () => listNews({ page, page_size: 24, relevance_threshold: threshold }),
  });

  const createMutation = useMutation({
    mutationFn: createContentFromNews,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['content'] }),
  });

  const items: NewsArticle[] = data?.items ?? [];

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-end justify-between mb-8 flex-wrap gap-4">
          <div>
            <h1 className="text-4xl font-bold mb-2 gradient-text">📰 News</h1>
            <p className="text-muted-foreground">
              Articles ranked for your niche {data?.niche ? `(${data.niche})` : ''}.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <label className="text-sm text-muted-foreground">Relevance ≥</label>
            <select
              className="px-3 py-2 bg-surface rounded-md text-sm border border-input"
              value={threshold}
              onChange={(e) => {
                setThreshold(Number(e.target.value));
                setPage(1);
              }}
            >
              <option value="0.1">0.1</option>
              <option value="0.3">0.3</option>
              <option value="0.5">0.5</option>
              <option value="0.7">0.7</option>
            </select>
            <Button variant="ghost" size="sm" onClick={() => refetch()}>
              Refresh
            </Button>
          </div>
        </div>

        {isLoading && <p className="text-muted-foreground">Fetching latest…</p>}
        {error && (
          <p className="text-error">
            Failed to load news: {(error as Error).message}
          </p>
        )}

        {!isLoading && items.length === 0 && (
          <Card>
            <CardContent className="py-12 text-center">
              <div className="text-6xl mb-4">🗞️</div>
              <h3 className="text-xl font-semibold mb-2">No articles yet</h3>
              <p className="text-muted-foreground">
                Lower the relevance threshold or wait for the news fetcher to refresh.
              </p>
            </CardContent>
          </Card>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {items.map((article) => (
            <Card key={article.id} className="card-hover">
              <CardContent className="p-5 flex flex-col h-full">
                <div className="flex items-center justify-between mb-3">
                  <Badge variant="default">
                    {article.source ?? 'unknown'}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {Math.round(article.relevance_score * 100)}% match
                  </span>
                </div>
                <h3 className="font-semibold mb-2 line-clamp-2">{article.title}</h3>
                {article.description && (
                  <p className="text-sm text-muted-foreground mb-3 line-clamp-3">
                    {article.description}
                  </p>
                )}
                <div className="text-xs text-muted-foreground mb-4">
                  {article.published_at
                    ? formatRelativeTime(article.published_at)
                    : 'recent'}
                </div>
                <div className="mt-auto flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => window.open(article.url, '_blank')}
                  >
                    Read
                  </Button>
                  <Button
                    size="sm"
                    className="flex-1"
                    disabled={createMutation.isPending}
                    onClick={() =>
                      createMutation.mutate({
                        title: article.title,
                        description: article.description ?? undefined,
                        url: article.url,
                      })
                    }
                  >
                    Create →
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {data && data.has_more && (
          <div className="flex justify-between mt-6">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              Previous
            </Button>
            <Button variant="outline" size="sm" onClick={() => setPage((p) => p + 1)}>
              Next
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
