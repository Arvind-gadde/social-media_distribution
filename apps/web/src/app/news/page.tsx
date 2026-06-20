'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Newspaper, RefreshCw, ExternalLink, Zap } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { Spinner } from '@/components/ui/spinner';
import { safeExternalUrl } from '@/lib/safe-redirect';
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
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-10 space-y-8 animate-fade-in">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="space-y-1">
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">
              News
            </h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Articles ranked for your niche{data?.niche ? ` (${data.niche})` : ''}.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <label className="text-sm text-gray-500 dark:text-gray-400">Relevance ≥</label>
            <select
              className="rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500/24"
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
            <Button
              variant="tertiary"
              size="sm"
              leadingIcon={<RefreshCw className="h-4 w-4" />}
              onClick={() => refetch()}
            >
              Refresh
            </Button>
          </div>
        </header>

        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <Spinner size="lg" color="primary" />
          </div>
        )}

        {error && (
          <p className="text-sm text-error-600 dark:text-error-400">
            Failed to load news: {(error as Error).message}
          </p>
        )}

        {!isLoading && items.length === 0 && (
          <EmptyState
            icon={<Newspaper />}
            iconColor="brand"
            title="No articles yet"
            description="Lower the relevance threshold or wait for the news fetcher to refresh."
          />
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {items.map((article) => (
            <Card
              key={article.id}
              className="flex flex-col transition-all duration-200 hover:shadow-md"
            >
              <CardContent className="p-5 flex flex-col h-full">
                <div className="flex items-center justify-between mb-3">
                  <Badge variant="gray">{article.source ?? 'unknown'}</Badge>
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {Math.round(article.relevance_score * 100)}% match
                  </span>
                </div>
                <h3 className="font-semibold text-gray-900 dark:text-gray-50 mb-2 line-clamp-2">
                  {article.title}
                </h3>
                {article.description && (
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-3 line-clamp-3">
                    {article.description}
                  </p>
                )}
                <div className="text-xs text-gray-400 dark:text-gray-500 mb-4">
                  {article.published_at ? formatRelativeTime(article.published_at) : 'recent'}
                </div>
                <div className="mt-auto flex gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    className="flex-1"
                    leadingIcon={<ExternalLink className="h-3.5 w-3.5" />}
                    onClick={() => {
                      const u = safeExternalUrl(article.url);
                      if (u) window.open(u, '_blank', 'noopener,noreferrer');
                    }}
                  >
                    Read
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    className="flex-1"
                    leadingIcon={<Zap className="h-3.5 w-3.5" />}
                    disabled={createMutation.isPending}
                    onClick={() =>
                      createMutation.mutate({
                        title: article.title,
                        description: article.description ?? undefined,
                        url: article.url,
                      })
                    }
                  >
                    Create
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {(page > 1 || data?.has_more) && (
          <div className="flex justify-between">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              Previous
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setPage((p) => p + 1)}
              disabled={!data?.has_more}
            >
              Next
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
