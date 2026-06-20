'use client';

import { useMutation } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Video, Clock, Save, Calendar, Wand2, Sparkles, Copy } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert } from '@/components/ui/alert';
import { createContent, type ContentCreate } from '@contentflow/api-client';
import { apiClient } from '@/lib/api';
import { cn } from '@/lib/utils';

const PLATFORMS = ['instagram', 'twitter', 'linkedin', 'youtube', 'tiktok', 'facebook', 'pinterest'] as const;
type Platform = (typeof PLATFORMS)[number];

const CONTENT_TYPES: ContentCreate['content_type'][] = [
  'reel', 'short', 'post', 'carousel', 'story', 'thread', 'blog',
];

const TONES = ['casual', 'professional', 'funny', 'inspirational', 'educational'] as const;
type Tone = (typeof TONES)[number];

interface RepurposeVariant {
  platform: string;
  hook: string;
  caption: string;
  hashtags: string[];
  rationale?: string | null;
}
interface RepurposeResult {
  variants: RepurposeVariant[];
}

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

  const [tone, setTone] = useState<Tone>('casual');
  const repurpose = useMutation({
    mutationFn: (input: { source_text: string; platforms: string[]; tone: string }) =>
      apiClient.post<RepurposeResult>('/api/v1/ai/repurpose', input),
  });

  function generateVariants() {
    if (!caption.trim() || platforms.length === 0) return;
    repurpose.mutate({ source_text: caption, platforms, tone });
  }

  function applyVariant(v: RepurposeVariant) {
    setCaption(v.caption);
    setHashtags(v.hashtags.map((h) => `#${h}`).join(' '));
    if (!platforms.includes(v.platform as Platform) && (PLATFORMS as readonly string[]).includes(v.platform)) {
      setPlatforms((curr) => [...curr, v.platform as Platform]);
    }
  }

  function togglePlatform(p: Platform) {
    setPlatforms((curr) =>
      curr.includes(p) ? curr.filter((x) => x !== p) : [...curr, p],
    );
  }

  function submit(status: 'draft' | 'scheduled') {
    const payload: ContentCreate = {
      title: title || undefined,
      caption: caption || undefined,
      content_type: contentType,
      platforms,
      status,
      hashtags: hashtags.split(/[\s,]+/).filter(Boolean).map((h) => h.replace(/^#/, '')),
    };
    if (status === 'scheduled' && scheduleAt) {
      payload.scheduled_at = new Date(scheduleAt).toISOString();
    }
    mutation.mutate(payload);
  }

  const canSchedule = platforms.length > 0 && !!scheduleAt && !!caption;
  const canDraft = platforms.length > 0 && (!!caption || !!title);

  const inputCls = 'w-full rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-50 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-brand-500/24';

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-10 space-y-8 animate-fade-in">
        <header className="space-y-1">
          <div className="flex items-center gap-2">
            <Video className="h-6 w-6 text-brand-600 dark:text-brand-400" />
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">
              Studio
            </h1>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Compose, hashtag, and schedule a post across every connected platform.
          </p>
        </header>

        <Card>
          <CardHeader>
            <CardTitle>Compose</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
                Title <span className="text-gray-400 dark:text-gray-500 font-normal">(internal)</span>
              </label>
              <input
                className={inputCls}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Internal reference name"
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
                Caption
              </label>
              <textarea
                className={cn(inputCls, 'min-h-32 resize-y')}
                value={caption}
                onChange={(e) => setCaption(e.target.value)}
                placeholder="What's the hook?"
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
                Hashtags
              </label>
              <input
                className={inputCls}
                value={hashtags}
                onChange={(e) => setHashtags(e.target.value)}
                placeholder="#ai, #productivity"
              />
            </div>

            <div className="flex flex-wrap gap-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Content type
                </label>
                <select
                  className="rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500/24"
                  value={contentType}
                  onChange={(e) => setContentType(e.target.value as ContentCreate['content_type'])}
                >
                  {CONTENT_TYPES.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1.5 flex items-center gap-1.5 text-sm font-medium text-gray-700 dark:text-gray-300">
                  <Clock className="h-3.5 w-3.5" /> Schedule for
                </label>
                <input
                  type="datetime-local"
                  className="rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500/24"
                  value={scheduleAt}
                  onChange={(e) => setScheduleAt(e.target.value)}
                />
              </div>
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
                Platforms
              </label>
              <div className="flex flex-wrap gap-2">
                {PLATFORMS.map((p) => {
                  const active = platforms.includes(p);
                  return (
                    <button
                      key={p}
                      type="button"
                      onClick={() => togglePlatform(p)}
                      className="focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/24 rounded-full"
                    >
                      <Badge variant={active ? 'brand' : 'gray'}>{p}</Badge>
                    </button>
                  );
                })}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Wand2 className="h-5 w-5 text-brand-600 dark:text-brand-400" /> AI Repurpose
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Turn the caption above into platform-native variants — a scroll-stopping hook,
              a tailored caption, and hashtags for each platform you selected.
            </p>
            <div className="flex flex-wrap items-end gap-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">Tone</label>
                <select
                  className="rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500/24"
                  value={tone}
                  onChange={(e) => setTone(e.target.value as Tone)}
                >
                  {TONES.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              <Button
                variant="primary"
                leadingIcon={<Sparkles className="h-4 w-4" />}
                disabled={!caption.trim() || platforms.length === 0 || repurpose.isPending}
                loading={repurpose.isPending}
                onClick={generateVariants}
              >
                Generate variants
              </Button>
            </div>

            {repurpose.isError && (
              <Alert variant="error" title="Couldn't generate" description={(repurpose.error as Error).message} />
            )}

            {repurpose.data && (
              <div className="grid gap-3 sm:grid-cols-2">
                {repurpose.data.variants.map((v, i) => (
                  <div key={i} className="rounded-lg border border-gray-200 dark:border-gray-700 p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <Badge variant="brand">{v.platform}</Badge>
                      <button
                        type="button"
                        aria-label="Copy"
                        onClick={() => navigator.clipboard?.writeText(
                          `${v.caption}\n\n${v.hashtags.map((h) => `#${h}`).join(' ')}`,
                        )}
                        className="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/24 rounded"
                      >
                        <Copy className="h-4 w-4" />
                      </button>
                    </div>
                    {v.hook && <p className="text-sm font-semibold text-gray-900 dark:text-gray-50">{v.hook}</p>}
                    <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{v.caption}</p>
                    {v.hashtags.length > 0 && (
                      <p className="text-xs text-brand-600 dark:text-brand-400">
                        {v.hashtags.map((h) => `#${h}`).join(' ')}
                      </p>
                    )}
                    <Button size="sm" variant="secondary" className="w-full" onClick={() => applyVariant(v)}>
                      Use as caption
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {mutation.isError && (
          <Alert
            variant="error"
            title="Failed to save"
            description={(mutation.error as Error).message}
          />
        )}

        <div className="flex justify-end gap-3">
          <Button
            variant="secondary"
            disabled={!canDraft || mutation.isPending}
            leadingIcon={<Save className="h-4 w-4" />}
            onClick={() => submit('draft')}
          >
            Save draft
          </Button>
          <Button
            variant="primary"
            disabled={!canSchedule || mutation.isPending}
            loading={mutation.isPending}
            leadingIcon={<Calendar className="h-4 w-4" />}
            onClick={() => submit('scheduled')}
          >
            Schedule
          </Button>
        </div>
      </div>
    </div>
  );
}
