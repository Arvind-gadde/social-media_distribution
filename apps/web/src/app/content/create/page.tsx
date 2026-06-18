/**
 * Content Creator Page
 * 
 * Create and schedule content with AI assistance
 */

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useCreateContent, useScheduleContent } from '@/hooks/useContent';
import { useMultipleMediaUpload, useFileDropzone, formatFileSize, validateFile } from '@/hooks/useMediaUpload';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

type ContentType = 'reel' | 'short' | 'post' | 'carousel' | 'story' | 'video';
type Platform = 'instagram' | 'youtube' | 'tiktok' | 'twitter' | 'linkedin';

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
  
  // File upload
  const { uploadFiles, uploads, reset: resetUploads, isUploading } = useMultipleMediaUpload();
  const {
    isDragging,
    files: selectedFiles,
    handleDragEnter,
    handleDragLeave,
    handleDragOver,
    handleDrop,
    handleFileSelect,
    clearFiles,
  } = useFileDropzone();

  const contentTypes: { type: ContentType; label: string; icon: string; platforms: Platform[] }[] = [
    { type: 'reel', label: 'Instagram Reel', icon: '🎬', platforms: ['instagram'] },
    { type: 'short', label: 'YouTube Short', icon: '⚡', platforms: ['youtube'] },
    { type: 'post', label: 'Social Post', icon: '📝', platforms: ['instagram', 'twitter', 'linkedin'] },
    { type: 'carousel', label: 'Carousel', icon: '🖼️', platforms: ['instagram', 'linkedin'] },
    { type: 'story', label: 'Story', icon: '📖', platforms: ['instagram'] },
    { type: 'video', label: 'Long Video', icon: '🎥', platforms: ['youtube'] },
  ];

  const platforms: { id: Platform; label: string; icon: string }[] = [
    { id: 'instagram', label: 'Instagram', icon: '📷' },
    { id: 'youtube', label: 'YouTube', icon: '▶️' },
    { id: 'tiktok', label: 'TikTok', icon: '🎵' },
    { id: 'twitter', label: 'Twitter', icon: '🐦' },
    { id: 'linkedin', label: 'LinkedIn', icon: '💼' },
  ];

  const togglePlatform = (platform: Platform) => {
    setSelectedPlatforms(prev =>
      prev.includes(platform)
        ? prev.filter(p => p !== platform)
        : [...prev, platform]
    );
  };

  const generateAICaption = async () => {
    setAiGenerating(true);
    // Simulate AI generation
    await new Promise(resolve => setTimeout(resolve, 2000));
    setCaption(`Check out this amazing content! 🚀\n\nThis is an AI-generated caption that's optimized for engagement. It includes relevant hashtags and a clear call-to-action.\n\nWhat do you think? Let me know in the comments! 👇`);
    setHashtags('#ContentCreation #AI #SocialMedia #CreatorEconomy #ContentMarketing');
    setAiGenerating(false);
  };

  const handleSubmit = async (action: 'draft' | 'schedule' | 'publish') => {
    if (!contentType || selectedPlatforms.length === 0) {
      alert('Please select content type and at least one platform');
      return;
    }

    try {
      // Upload files first if any
      let mediaUrls: string[] = [];
      if (selectedFiles.length > 0) {
        const uploadedMedia = await uploadFiles(selectedFiles);
        mediaUrls = uploadedMedia.map(m => m.url);
      }

      // Create content
      const result = await createContent.mutateAsync({
        title: title || undefined,
        caption: caption || undefined,
        content_type: contentType,
        platforms: selectedPlatforms,
        hashtags: hashtags ? hashtags.split(' ').filter(h => h.startsWith('#')) : undefined,
        status: action === 'publish' ? 'published' : 'draft',
        media_urls: mediaUrls.length > 0 ? mediaUrls : undefined,
      });

      // Schedule if needed
      if (action === 'schedule' && scheduleDate && scheduleTime) {
        const scheduledAt = new Date(`${scheduleDate}T${scheduleTime}`).toISOString();
        await scheduleContent.mutateAsync({
          id: result.id,
          scheduledAt,
        });
      }

      // Clear files and reset uploads
      clearFiles();
      resetUploads();

      // Redirect to content calendar
      router.push('/content');
    } catch (error) {
      console.error('Failed to create content:', error);
      alert('Failed to create content. Please try again.');
    }
  };

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-4xl font-bold gradient-text">Create Content</h1>
              <p className="text-muted-foreground mt-2">
                Create and schedule content with AI assistance
              </p>
            </div>
            <Button variant="outline" onClick={() => router.push('/content')}>
              Cancel
            </Button>
          </div>

          {/* Progress Steps */}
          <div className="flex items-center gap-4 mt-6">
            {[1, 2, 3].map(s => (
              <div key={s} className="flex items-center gap-2">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center font-medium ${
                    step >= s ? 'bg-tech text-white' : 'bg-surface text-muted-foreground'
                  }`}
                >
                  {s}
                </div>
                <span className={step >= s ? 'text-foreground' : 'text-muted-foreground'}>
                  {s === 1 && 'Type & Platform'}
                  {s === 2 && 'Content Details'}
                  {s === 3 && 'Schedule & Publish'}
                </span>
                {s < 3 && <div className="w-12 h-0.5 bg-border" />}
              </div>
            ))}
          </div>
        </div>

        {/* Step 1: Content Type & Platform */}
        {step === 1 && (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Select Content Type</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  {contentTypes.map(type => (
                    <button
                      key={type.type}
                      onClick={() => setContentType(type.type)}
                      className={`p-6 rounded-lg border-2 transition-all ${
                        contentType === type.type
                          ? 'border-tech bg-tech/10'
                          : 'border-border hover:border-tech/50'
                      }`}
                    >
                      <div className="text-4xl mb-2">{type.icon}</div>
                      <div className="font-medium">{type.label}</div>
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Select Platforms</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  {platforms.map(platform => (
                    <button
                      key={platform.id}
                      onClick={() => togglePlatform(platform.id)}
                      className={`p-6 rounded-lg border-2 transition-all ${
                        selectedPlatforms.includes(platform.id)
                          ? 'border-tech bg-tech/10'
                          : 'border-border hover:border-tech/50'
                      }`}
                    >
                      <div className="text-4xl mb-2">{platform.icon}</div>
                      <div className="font-medium">{platform.label}</div>
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>

            <div className="flex justify-end">
              <Button
                size="lg"
                onClick={() => setStep(2)}
                disabled={!contentType || selectedPlatforms.length === 0}
              >
                Next: Content Details
              </Button>
            </div>
          </div>
        )}

        {/* Step 2: Content Details */}
        {step === 2 && (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Content Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Title (Optional)
                  </label>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    className="w-full px-3 py-2 bg-surface rounded-md border border-input focus:outline-none focus:ring-2 focus:ring-tech"
                    placeholder="Give your content a title..."
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium">
                      Caption
                    </label>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={generateAICaption}
                      disabled={aiGenerating}
                    >
                      {aiGenerating ? '✨ Generating...' : '✨ AI Generate'}
                    </Button>
                  </div>
                  <textarea
                    value={caption}
                    onChange={(e) => setCaption(e.target.value)}
                    className="w-full px-3 py-2 bg-surface rounded-md border border-input focus:outline-none focus:ring-2 focus:ring-tech min-h-[150px]"
                    placeholder="Write your caption here..."
                  />
                  <div className="text-xs text-muted-foreground mt-1">
                    {caption.length} characters
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    Hashtags
                  </label>
                  <input
                    type="text"
                    value={hashtags}
                    onChange={(e) => setHashtags(e.target.value)}
                    className="w-full px-3 py-2 bg-surface rounded-md border border-input focus:outline-none focus:ring-2 focus:ring-tech"
                    placeholder="#hashtag1 #hashtag2 #hashtag3"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    Media Upload
                  </label>
                  
                  {/* Drag and drop zone */}
                  <div
                    onDragEnter={handleDragEnter}
                    onDragLeave={handleDragLeave}
                    onDragOver={handleDragOver}
                    onDrop={handleDrop}
                    className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors cursor-pointer ${
                      isDragging
                        ? 'border-tech bg-tech/10'
                        : 'border-border hover:border-tech/50'
                    }`}
                    onClick={() => document.getElementById('file-input')?.click()}
                  >
                    <input
                      id="file-input"
                      type="file"
                      multiple
                      accept="image/*,video/*"
                      onChange={handleFileSelect}
                      className="hidden"
                    />
                    <div className="text-4xl mb-2">📁</div>
                    <div className="text-sm text-muted-foreground">
                      {isDragging ? 'Drop files here' : 'Click to upload or drag and drop'}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      Video, Image, or GIF (Max 100MB per file)
                    </div>
                  </div>

                  {/* Selected files */}
                  {selectedFiles.length > 0 && (
                    <div className="mt-4 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">
                          {selectedFiles.length} file{selectedFiles.length > 1 ? 's' : ''} selected
                        </span>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={(e) => {
                            e.stopPropagation();
                            clearFiles();
                          }}
                        >
                          Clear
                        </Button>
                      </div>
                      {selectedFiles.map((file, idx) => {
                        const validation = validateFile(file);
                        return (
                          <div
                            key={idx}
                            className="flex items-center justify-between p-2 bg-surface rounded border border-border"
                          >
                            <div className="flex items-center gap-2 flex-1">
                              <span className="text-xl">
                                {file.type.startsWith('video/') ? '🎥' : '🖼️'}
                              </span>
                              <div className="flex-1 min-w-0">
                                <div className="text-sm font-medium truncate">{file.name}</div>
                                <div className="text-xs text-muted-foreground">
                                  {formatFileSize(file.size)}
                                </div>
                              </div>
                            </div>
                            {!validation.valid && (
                              <Badge variant="error" className="text-xs">
                                {validation.error}
                              </Badge>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {/* Upload progress */}
                  {uploads.length > 0 && (
                    <div className="mt-4 space-y-2">
                      <div className="text-sm font-medium">Upload Progress</div>
                      {uploads.map((upload, idx) => (
                        <div key={idx} className="space-y-1">
                          <div className="flex items-center justify-between text-xs">
                            <span className="truncate flex-1">{upload.file.name}</span>
                            <span className="text-muted-foreground ml-2">
                              {upload.status === 'success' && '✅'}
                              {upload.status === 'error' && '❌'}
                              {upload.status === 'uploading' && `${upload.progress}%`}
                              {upload.status === 'pending' && '⏳'}
                            </span>
                          </div>
                          {upload.status === 'uploading' && (
                            <div className="w-full bg-surface rounded-full h-1.5">
                              <div
                                className="bg-tech h-1.5 rounded-full transition-all"
                                style={{ width: `${upload.progress}%` }}
                              />
                            </div>
                          )}
                          {upload.error && (
                            <div className="text-xs text-error">{upload.error}</div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            <div className="flex justify-between">
              <Button variant="outline" onClick={() => setStep(1)}>
                Back
              </Button>
              <Button size="lg" onClick={() => setStep(3)}>
                Next: Schedule & Publish
              </Button>
            </div>
          </div>
        )}

        {/* Step 3: Schedule & Publish */}
        {step === 3 && (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Schedule & Publish</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Date
                    </label>
                    <input
                      type="date"
                      value={scheduleDate}
                      onChange={(e) => setScheduleDate(e.target.value)}
                      className="w-full px-3 py-2 bg-surface rounded-md border border-input focus:outline-none focus:ring-2 focus:ring-tech"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Time
                    </label>
                    <input
                      type="time"
                      value={scheduleTime}
                      onChange={(e) => setScheduleTime(e.target.value)}
                      className="w-full px-3 py-2 bg-surface rounded-md border border-input focus:outline-none focus:ring-2 focus:ring-tech"
                    />
                  </div>
                </div>

                <div className="bg-surface rounded-lg p-4 border border-border">
                  <div className="text-sm font-medium mb-2">AI Recommendation</div>
                  <div className="text-sm text-muted-foreground">
                    Based on your audience activity, the best time to post is{' '}
                    <span className="text-tech font-medium">Tuesday at 2:00 PM</span>
                  </div>
                </div>

                <div className="bg-surface rounded-lg p-4 border border-border">
                  <div className="text-sm font-medium mb-3">Publishing to:</div>
                  <div className="flex flex-wrap gap-2">
                    {selectedPlatforms.map(platform => (
                      <Badge key={platform} variant="default">
                        {platforms.find(p => p.id === platform)?.icon}{' '}
                        {platforms.find(p => p.id === platform)?.label}
                      </Badge>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>

            <div className="flex justify-between">
              <Button variant="outline" onClick={() => setStep(2)}>
                Back
              </Button>
              <div className="flex gap-2">
                <Button 
                  variant="outline" 
                  onClick={() => handleSubmit('draft')}
                  disabled={createContent.isPending || isUploading}
                >
                  {isUploading ? 'Uploading...' : createContent.isPending ? 'Saving...' : 'Save as Draft'}
                </Button>
                <Button 
                  variant="outline" 
                  onClick={() => handleSubmit('schedule')}
                  disabled={createContent.isPending || isUploading || !scheduleDate || !scheduleTime}
                >
                  {isUploading ? 'Uploading...' : createContent.isPending ? 'Scheduling...' : 'Schedule'}
                </Button>
                <Button 
                  onClick={() => handleSubmit('publish')}
                  disabled={createContent.isPending || isUploading}
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
