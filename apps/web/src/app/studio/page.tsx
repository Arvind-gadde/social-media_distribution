/**
 * Studio page — caption / hashtag / scheduling composer.
 *
 * Phase 14 placeholder for the full editor. Wires to /api/v1/content-projects
 * POST with status="draft" and the optional scheduled_at field.
 */
'use client';

import { useMutation } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { createContent, type ContentCreate } from '@contentflow/api-client';

const PLATFORMS = ['instagram', 'twitter', 'linkedin', 'youtube', 'tiktok', 'facebook', 'pinterest'] as const;
type Platform = (typeof PLATFORMS)[number];

const CONTENT_TYPES: ContentCreate['content_type'][] = [
  'reel',
  'short',
  'post',
  'carousel',
  'story',
  'thread',
  'blog',
];

export default function StudioPage() {
  const router = useRouter();
  const [title, setTitle] = useState('');
  const [caption, setCaption] = useState('');
  const [hashtags, setHashtags] = useState('');
  const [contentType, setContentType] = useState<ContentCreate['content_type']>('post');
  const [platforms, setPlatforms] = useState<Platform[]>(['instagram']);
  const [scheduleAt, setScheduleAt] = useState('');

  const mutation = useMutation({
    mutationFn: createContent,
    onSuccess: (item) => router.push(`/content/${item.id}`),
  });

  function togglePlatform(p: Platform) {
    setPlatforms((current) =>
      current.includes(p) ? current.filter((x) => x !== p) : [...current, p],
    );
  }

  function submit(status: 'draft' | 'scheduled') {
    const payload: ContentCreate = {
      title: title || undefined,
      caption: caption || undefined,
      content_type: contentType,
      platforms,
      status,
      hashtags: hashtags
        .split(/[\s,]+/)
        .filter(Boolean)
        .map((h) => h.replace(/^#/, '')),
    };
    if (status === 'scheduled' && scheduleAt) {
      payload.scheduled_at = new Date(scheduleAt).toISOString();
    }
    mutation.mutate(payload);
  }

  const canSchedule = platforms.length > 0 && !!scheduleAt && !!caption;
  const canDraft = platforms.length > 0 && (!!caption || !!title);

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-5xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2 gradient-text">🎬 Studio</h1>
          <p className="text-muted-foreground">
            Compose, hashtag, and schedule a post across every connected platform.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Compose</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm text-muted-foreground mb-1 block">Title (internal)</label>
              <input
                className="w-full px-3 py-2 bg-surface rounded-md border border-input"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground mb-1 block">Caption</label>
              <textarea
                className="w-full px-3 py-2 bg-surface rounded-md border border-input min-h-32"
                value={caption}
                onChange={(e) => setCaption(e.target.value)}
                placeholder="What's the hook?"
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground mb-1 block">Hashtags</label>
              <input
                className="w-full px-3 py-2 bg-surface rounded-md border border-input"
                value={hashtags}
                onChange={(e) => setHashtags(e.target.value)}
                placeholder="#ai, #productivity"
              />
            </div>
            <div className="flex flex-wrap gap-4">
              <div>
                <label className="text-sm text-muted-foreground mb-1 block">Content type</label>
                <select
                  className="px-3 py-2 bg-surface rounded-md border border-input"
                  value={contentType}
                  onChange={(e) =>
                    setContentType(e.target.value as ContentCreate['content_type'])
                  }
                >
                  {CONTENT_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm text-muted-foreground mb-1 block">Schedule for</label>
                <input
                  type="datetime-local"
                  className="px-3 py-2 bg-surface rounded-md border border-input"
                  value={scheduleAt}
                  onChange={(e) => setScheduleAt(e.target.value)}
                />
              </div>
            </div>
            <div>
              <label className="text-sm text-muted-foreground mb-2 block">Platforms</label>
              <div className="flex flex-wrap gap-2">
                {PLATFORMS.map((p) => {
                  const active = platforms.includes(p);
                  return (
                    <button
                      key={p}
                      type="button"
                      onClick={() => togglePlatform(p)}
                      className="focus:outline-none"
                    >
                      <Badge variant={active ? 'success' : 'default'}>{p}</Badge>
                    </button>
                  );
                })}
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end gap-2 mt-6">
          <Button
            variant="outline"
            disabled={!canDraft || mutation.isPending}
            onClick={() => submit('draft')}
          >
            Save draft
          </Button>
          <Button disabled={!canSchedule || mutation.isPending} onClick={() => submit('scheduled')}>
            Schedule
          </Button>
        </div>

        {mutation.isError && (
          <p className="text-error mt-3">
            Failed to save: {(mutation.error as Error).message}
          </p>
        )}
      </div>
    </div>
  );
}
