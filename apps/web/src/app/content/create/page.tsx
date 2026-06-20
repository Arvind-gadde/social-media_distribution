'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Sparkles, Upload, ArrowRight, ArrowLeft, Check } from 'lucide-react';
import { useCreateContent, useScheduleContent } from '@/hooks/useContent';
import { useMultipleMediaUpload, useFileDropzone, formatFileSize, validateFile } from '@/hooks/useMediaUpload';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import {
  Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbLink, BreadcrumbSeparator, BreadcrumbPage,
} from '@/components/ui/breadcrumb';

type ContentType = 'reel' | 'short' | 'post' | 'carousel' | 'story' | 'video';
type Platform = 'instagram' | 'youtube' | 'tiktok' | 'twitter' | 'linkedin';

const inputCls = 'w-full rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-50 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-brand-500/24';

const contentTypes: { type: ContentType; label: string; icon: string }[] = [
  { type: 'reel', label: 'Instagram Reel', icon: '🎬' },
  { type: 'short', label: 'YouTube Short', icon: '⚡' },
  { type: 'post', label: 'Social Post', icon: '📝' },
  { type: 'carousel', label: 'Carousel', icon: '🖼️' },
  { type: 'story', label: 'Story', icon: '📖' },
  { type: 'video', label: 'Long Video', icon: '🎥' },
];

const platforms: { id: Platform; label: string; icon: string }[] = [
  { id: 'instagram', label: 'Instagram', icon: '📷' },
  { id: 'youtube', label: 'YouTube', icon: '▶️' },
  { id: 'tiktok', label: 'TikTok', icon: '🎵' },
  { id: 'twitter', label: 'Twitter', icon: '🐦' },
  { id: 'linkedin', label: 'LinkedIn', icon: '💼' },
];

const steps = [
  { n: 1, label: 'Type & Platform' },
  { n: 2, label: 'Content Details' },
  { n: 3, label: 'Schedule & Publish' },
];

export default function CreateContentPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [contentType, setContentType] = useState<ContentType | null>(null);
  const [selectedPlatforms, setSelectedPlatforms] = useState<Platform[]>([]);
  const [title, setTitle] = useState('');
  const [caption, setCaption] = useState('');
  const [hashtags, setHashtags] = useState('');
  const [scheduleDate, setScheduleDate] = useState('');
  const [scheduleTime, setScheduleTime] = useState('');
  const [aiGenerating, setAiGenerating] = useState(false);

  const createContent = useCreateContent();
  const scheduleContent = useScheduleContent();
  const { uploadFiles, uploads, reset: resetUploads, isUploading } = useMultipleMediaUpload();
  const { isDragging, files: selectedFiles, handleDragEnter, handleDragLeave, handleDragOver, handleDrop, handleFileSelect, clearFiles } = useFileDropzone();

  const togglePlatform = (platform: Platform) => {
    setSelectedPlatforms(prev =>
      prev.includes(platform) ? prev.filter(p => p !== platform) : [...prev, platform]
    );
  };

  const generateAICaption = async () => {
    setAiGenerating(true);
    await new Promise(resolve => setTimeout(resolve, 2000));
    setCaption(`Check out this amazing content! 🚀\n\nThis is an AI-generated caption optimized for engagement. It includes relevant hashtags and a clear call-to-action.\n\nWhat do you think? Let me know in the comments! 👇`);
    setHashtags('#ContentCreation #AI #SocialMedia #CreatorEconomy #ContentMarketing');
    setAiGenerating(false);
  };

  const handleSubmit = async (action: 'draft' | 'schedule' | 'publish') => {
    if (!contentType || selectedPlatforms.length === 0) {
      alert('Please select content type and at least one platform');
      return;
    }
    try {
      let mediaUrls: string[] = [];
      if (selectedFiles.length > 0) {
        // Enforce validation before upload — the per-file badges are only a
        // display hint; without this an invalid file is uploaded anyway.
        const invalid = selectedFiles
          .map((f) => ({ name: f.name, v: validateFile(f) }))
          .filter((x) => !x.v.valid);
        if (invalid.length > 0) {
          alert(
            'Some files cannot be uploaded:\n' +
              invalid.map((x) => `• ${x.name}: ${x.v.error ?? 'invalid file'}`).join('\n')
          );
          return;
        }
        const uploadedMedia = await uploadFiles(selectedFiles);
        mediaUrls = uploadedMedia.map((m: any) => m.url);
      }
      const result = await createContent.mutateAsync({
        title: title || undefined,
        caption: caption || undefined,
        content_type: contentType,
        platforms: selectedPlatforms,
        hashtags: hashtags ? hashtags.split(' ').filter(h => h.startsWith('#')) : undefined,
        status: action === 'publish' ? 'published' : 'draft',
        media_urls: mediaUrls.length > 0 ? mediaUrls : undefined,
      });
      if (action === 'schedule' && scheduleDate && scheduleTime) {
        await scheduleContent.mutateAsync({
          id: result.id,
          scheduledAt: new Date(`${scheduleDate}T${scheduleTime}`).toISOString(),
        });
      }
      clearFiles();
      resetUploads();
      router.push('/content');
    } catch (e) {
      console.error(e);
      alert('Failed to create content. Please try again.');
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-10 space-y-8 animate-fade-in">
        <header className="space-y-4">
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem><BreadcrumbLink href="/content">Content</BreadcrumbLink></BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem><BreadcrumbPage>Create</BreadcrumbPage></BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>

          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">Create Content</h1>
              <p className="text-sm text-gray-600 dark:text-gray-400">Create and schedule content with AI assistance.</p>
            </div>
            <Button variant="secondary" onClick={() => router.push('/content')}>Cancel</Button>
          </div>

          {/* Progress steps */}
          <div className="flex items-center gap-3 mt-2">
            {steps.map((s, i) => (
              <div key={s.n} className="flex items-center gap-3">
                <div className="flex items-center gap-2">
                  <div className={cn(
                    'w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-colors',
                    step > s.n ? 'bg-brand-600 text-white' : step === s.n ? 'bg-brand-600 text-white' : 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400'
                  )}>
                    {step > s.n ? <Check className="h-4 w-4" /> : s.n}
                  </div>
                  <span className={cn(
                    'text-sm font-medium hidden sm:block',
                    step >= s.n ? 'text-gray-900 dark:text-gray-50' : 'text-gray-500 dark:text-gray-400'
                  )}>
                    {s.label}
                  </span>
                </div>
                {i < steps.length - 1 && <div className="w-8 h-0.5 bg-gray-200 dark:bg-gray-700" />}
              </div>
            ))}
          </div>
        </header>

        {/* Step 1 */}
        {step === 1 && (
          <div className="space-y-6">
            <Card>
              <CardHeader><CardTitle>Select Content Type</CardTitle></CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {contentTypes.map(type => (
                    <button
                      key={type.type}
                      type="button"
                      onClick={() => setContentType(type.type)}
                      className={cn(
                        'p-5 rounded-lg border-2 text-left transition-all',
                        contentType === type.type
                          ? 'border-brand-500 bg-brand-50 dark:bg-brand-950/20'
                          : 'border-gray-200 dark:border-gray-700 hover:border-brand-300 dark:hover:border-brand-700'
                      )}
                    >
                      <div className="text-3xl mb-2">{type.icon}</div>
                      <p className="font-medium text-sm text-gray-900 dark:text-gray-50">{type.label}</p>
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>Select Platforms</CardTitle></CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {platforms.map(platform => (
                    <button
                      key={platform.id}
                      type="button"
                      onClick={() => togglePlatform(platform.id)}
                      className={cn(
                        'p-5 rounded-lg border-2 text-left transition-all',
                        selectedPlatforms.includes(platform.id)
                          ? 'border-brand-500 bg-brand-50 dark:bg-brand-950/20'
                          : 'border-gray-200 dark:border-gray-700 hover:border-brand-300 dark:hover:border-brand-700'
                      )}
                    >
                      <div className="text-3xl mb-2">{platform.icon}</div>
                      <p className="font-medium text-sm text-gray-900 dark:text-gray-50">{platform.label}</p>
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>

            <div className="flex justify-end">
              <Button
                variant="primary"
                size="lg"
                leadingIcon={<ArrowRight className="h-4 w-4" />}
                onClick={() => setStep(2)}
                disabled={!contentType || selectedPlatforms.length === 0}
              >
                Next: Content Details
              </Button>
            </div>
          </div>
        )}

        {/* Step 2 */}
        {step === 2 && (
          <div className="space-y-6">
            <Card>
              <CardHeader><CardTitle>Content Details</CardTitle></CardHeader>
              <CardContent className="space-y-5">
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">Title (Optional)</label>
                  <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} className={inputCls} placeholder="Give your content a title..." />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Caption</label>
                    <Button
                      size="sm"
                      variant="secondary"
                      leadingIcon={<Sparkles className="h-3.5 w-3.5" />}
                      onClick={generateAICaption}
                      disabled={aiGenerating}
                      loading={aiGenerating}
                    >
                      {aiGenerating ? 'Generating...' : 'AI Generate'}
                    </Button>
                  </div>
                  <textarea
                    value={caption}
                    onChange={(e) => setCaption(e.target.value)}
                    className={`${inputCls} min-h-[150px] resize-y`}
                    placeholder="Write your caption here..."
                  />
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{caption.length} characters</p>
                </div>

                <div>
                  <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">Hashtags</label>
                  <input type="text" value={hashtags} onChange={(e) => setHashtags(e.target.value)} className={inputCls} placeholder="#hashtag1 #hashtag2 #hashtag3" />
                </div>

                <div>
                  <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">Media Upload</label>

                  <div
                    onDragEnter={handleDragEnter}
                    onDragLeave={handleDragLeave}
                    onDragOver={handleDragOver}
                    onDrop={handleDrop}
                    onClick={() => document.getElementById('file-input')?.click()}
                    className={cn(
                      'border-2 border-dashed rounded-lg p-10 text-center cursor-pointer transition-colors',
                      isDragging
                        ? 'border-brand-500 bg-brand-50 dark:bg-brand-950/20'
                        : 'border-gray-300 dark:border-gray-600 hover:border-brand-300 dark:hover:border-brand-700'
                    )}
                  >
                    <input id="file-input" type="file" multiple accept="image/*,video/*" onChange={handleFileSelect} className="hidden" />
                    <Upload className="h-8 w-8 mx-auto mb-3 text-gray-400" />
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {isDragging ? 'Drop files here' : 'Click to upload or drag and drop'}
                    </p>
                    <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Video, Image, or GIF (Max 100MB per file)</p>
                  </div>

                  {selectedFiles.length > 0 && (
                    <div className="mt-4 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-900 dark:text-gray-50">
                          {selectedFiles.length} file{selectedFiles.length > 1 ? 's' : ''} selected
                        </span>
                        <Button size="sm" variant="tertiary" onClick={(e) => { e.stopPropagation(); clearFiles(); }}>Clear</Button>
                      </div>
                      {selectedFiles.map((file, idx) => {
                        const validation = validateFile(file);
                        return (
                          <div key={idx} className="flex items-center justify-between p-2.5 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                            <div className="flex items-center gap-2.5 flex-1 min-w-0">
                              <span className="text-xl">{file.type.startsWith('video/') ? '🎥' : '🖼️'}</span>
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium truncate text-gray-900 dark:text-gray-50">{file.name}</p>
                                <p className="text-xs text-gray-500 dark:text-gray-400">{formatFileSize(file.size)}</p>
                              </div>
                            </div>
                            {!validation.valid && (
                              <Badge variant="error" size="sm" className="text-xs shrink-0">{validation.error}</Badge>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {uploads.length > 0 && (
                    <div className="mt-4 space-y-2">
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-50">Upload Progress</p>
                      {uploads.map((upload: any, idx: number) => (
                        <div key={idx} className="space-y-1">
                          <div className="flex items-center justify-between text-xs">
                            <span className="truncate flex-1 text-gray-700 dark:text-gray-300">{upload.file.name}</span>
                            <span className="text-gray-500 dark:text-gray-400 ml-2">
                              {upload.status === 'success' && '✅'}
                              {upload.status === 'error' && '❌'}
                              {upload.status === 'uploading' && `${upload.progress}%`}
                              {upload.status === 'pending' && '⏳'}
                            </span>
                          </div>
                          {upload.status === 'uploading' && (
                            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                              <div className="bg-brand-600 h-1.5 rounded-full transition-all" style={{ width: `${upload.progress}%` }} />
                            </div>
                          )}
                          {upload.error && <p className="text-xs text-error-600 dark:text-error-400">{upload.error}</p>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            <div className="flex justify-between">
              <Button variant="secondary" leadingIcon={<ArrowLeft className="h-4 w-4" />} onClick={() => setStep(1)}>Back</Button>
              <Button variant="primary" size="lg" leadingIcon={<ArrowRight className="h-4 w-4" />} onClick={() => setStep(3)}>
                Next: Schedule & Publish
              </Button>
            </div>
          </div>
        )}

        {/* Step 3 */}
        {step === 3 && (
          <div className="space-y-6">
            <Card>
              <CardHeader><CardTitle>Schedule & Publish</CardTitle></CardHeader>
              <CardContent className="space-y-5">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">Date</label>
                    <input type="date" value={scheduleDate} onChange={(e) => setScheduleDate(e.target.value)} className={inputCls} />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">Time</label>
                    <input type="time" value={scheduleTime} onChange={(e) => setScheduleTime(e.target.value)} className={inputCls} />
                  </div>
                </div>

                <div className="rounded-lg bg-brand-50 dark:bg-brand-950/40 border border-brand-200 dark:border-brand-800 p-4">
                  <p className="text-sm font-medium text-brand-700 dark:text-brand-300 mb-1 flex items-center gap-1.5">
                    <Sparkles className="h-4 w-4" /> AI Recommendation
                  </p>
                  <p className="text-sm text-gray-700 dark:text-gray-300">
                    Based on your audience activity, the best time to post is{' '}
                    <span className="font-semibold text-brand-600 dark:text-brand-400">Tuesday at 2:00 PM</span>
                  </p>
                </div>

                <div className="rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-4">
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Publishing to:</p>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedPlatforms.map(platform => {
                      const p = platforms.find(pl => pl.id === platform);
                      return (
                        <Badge key={platform} variant="gray">
                          {p?.icon} {p?.label}
                        </Badge>
                      );
                    })}
                  </div>
                </div>
              </CardContent>
            </Card>

            <div className="flex items-center justify-between">
              <Button variant="secondary" leadingIcon={<ArrowLeft className="h-4 w-4" />} onClick={() => setStep(2)}>Back</Button>
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  onClick={() => handleSubmit('draft')}
                  disabled={createContent.isPending || isUploading}
                  loading={isUploading || createContent.isPending}
                >
                  {isUploading ? 'Uploading...' : createContent.isPending ? 'Saving...' : 'Save as Draft'}
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => handleSubmit('schedule')}
                  disabled={createContent.isPending || isUploading || !scheduleDate || !scheduleTime}
                  loading={isUploading || createContent.isPending}
                >
                  {isUploading ? 'Uploading...' : createContent.isPending ? 'Scheduling...' : 'Schedule'}
                </Button>
                <Button
                  variant="primary"
                  onClick={() => handleSubmit('publish')}
                  disabled={createContent.isPending || isUploading}
                  loading={isUploading || createContent.isPending}
                >
                  {isUploading ? 'Uploading...' : createContent.isPending ? 'Publishing...' : 'Publish Now'}
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
