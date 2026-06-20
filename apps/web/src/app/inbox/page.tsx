'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Inbox, RefreshCw, Sparkles, Users } from 'lucide-react';
import { useDMList, useDMStats, useMarkDMRead, useReplyToDM } from '@/hooks/useInbox';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { EmptyState } from '@/components/ui/empty-state';
import { Spinner } from '@/components/ui/spinner';
import { cn } from '@/lib/utils';

type MessageCategory = 'all' | 'brand_deal' | 'collab' | 'fan' | 'question' | 'spam';

const categoryVariant: Record<string, 'gray' | 'success' | 'warning' | 'error' | 'blue'> = {
  brand_deal: 'success', collab: 'warning', fan: 'gray', question: 'blue', spam: 'error',
};

const categoryLabel: Record<string, string> = {
  brand_deal: 'Brand Deal', collab: 'Collaboration', fan: 'Fan Message', question: 'Question', spam: 'Spam',
};

const textareaCls = 'w-full rounded-lg border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-50 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500/24 min-h-[100px] resize-none';

export default function InboxPage() {
  const [selectedCategory, setSelectedCategory] = useState<MessageCategory>('all');
  const [selectedMessage, setSelectedMessage] = useState<string | null>(null);
  const [replyText, setReplyText] = useState('');

  const { data, isLoading, error, refetch } = useDMList({
    ai_category: selectedCategory === 'all' ? undefined : selectedCategory,
  });
  const { data: stats } = useDMStats();
  const markRead = useMarkDMRead();
  const sendReply = useReplyToDM();

  const handleSelectMessage = async (id: string) => {
    setSelectedMessage(id);
    const message = data?.items.find((m: any) => m.id === id);
    if (message && !message.is_read) {
      try { await markRead.mutateAsync(id); } catch (e) { console.error(e); }
    }
  };

  const handleSendReply = async () => {
    if (!selectedMessage || !replyText.trim()) return;
    try {
      await sendReply.mutateAsync({ id: selectedMessage, data: { message: replyText } });
      setReplyText('');
    } catch (e) { console.error(e); }
  };

  const formatNumber = (num: number) => {
    if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
    return num.toString();
  };

  const getPlatformIcon = (platform: string) => {
    const icons: Record<string, string> = { Instagram: '📷', YouTube: '▶️', TikTok: '🎵', Twitter: '🐦', instagram: '📷', youtube: '▶️', tiktok: '🎵', twitter: '🐦' };
    return icons[platform] || '📱';
  };

  const getPriorityColor = (priority: number) =>
    priority >= 8 ? 'text-error-600 dark:text-error-400' : priority >= 6 ? 'text-warning-600 dark:text-warning-400' : 'text-gray-500 dark:text-gray-400';

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
          icon={<Inbox />}
          iconColor="error"
          title="Failed to load messages"
          description={error instanceof Error ? error.message : 'Something went wrong'}
          actions={<Button onClick={() => refetch()} leadingIcon={<RefreshCw className="h-4 w-4" />}>Retry</Button>}
        />
      </div>
    );
  }

  const messages = data?.items || [];
  const selectedMsg = messages.find((m: any) => m.id === selectedMessage);

  const statCards = [
    { label: 'Unread', value: stats?.total_unread ?? 0 },
    { label: 'Brand Deals', value: stats?.total_business_inquiries ?? 0 },
    { label: 'Collabs', value: stats?.by_category?.collab ?? 0 },
    { label: 'Questions', value: stats?.by_category?.question ?? 0 },
    { label: 'High Priority', value: stats?.high_priority_count ?? 0 },
  ];

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-10 space-y-8 animate-fade-in">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="space-y-1">
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">DM Inbox</h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">AI-powered message management across all platforms.</p>
          </div>
          <Button asChild variant="secondary" leadingIcon={<Users className="h-4 w-4" />}>
            <Link href="/inbox/collaborations">View Collaborations</Link>
          </Button>
        </header>

        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
          {statCards.map((s) => (
            <Card key={s.label} className="p-4">
              <p className="text-2xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">{s.value}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{s.label}</p>
            </Card>
          ))}
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-1 rounded-lg border border-gray-200 dark:border-gray-800 p-1 w-fit">
          {(['all', 'brand_deal', 'collab', 'fan', 'question', 'spam'] as MessageCategory[]).map((cat) => (
            <button
              key={cat}
              type="button"
              onClick={() => setSelectedCategory(cat)}
              className={cn(
                'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                selectedCategory === cat
                  ? 'bg-brand-600 text-white'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
              )}
            >
              {cat === 'all' ? 'All' : categoryLabel[cat]}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Message list */}
          <div className="lg:col-span-1 space-y-2">
            {messages.length > 0 ? messages.map((message: any) => (
              <Card
                key={message.id}
                className={cn(
                  'cursor-pointer transition-all duration-150',
                  selectedMessage === message.id && 'border-brand-500 dark:border-brand-400',
                  !message.is_read && 'bg-brand-50/50 dark:bg-brand-950/20'
                )}
                onClick={() => handleSelectMessage(message.id)}
              >
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <div className="h-10 w-10 shrink-0 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-xl overflow-hidden">
                      {message.sender_avatar_url
                        ? <img src={message.sender_avatar_url} alt="" className="w-full h-full object-cover" />
                        : '👤'}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="font-semibold text-sm text-gray-900 dark:text-gray-50 truncate">
                          {message.sender_display_name || message.sender_username}
                        </p>
                        {!message.is_read && <div className="h-2 w-2 shrink-0 rounded-full bg-brand-600" />}
                      </div>
                      <div className="flex items-center gap-2 mb-1.5">
                        {message.ai_category && (
                          <Badge variant={categoryVariant[message.ai_category] ?? 'gray'} size="sm">
                            {categoryLabel[message.ai_category] ?? message.ai_category}
                          </Badge>
                        )}
                        <span className="text-xs">{getPlatformIcon(message.platform)}</span>
                        <span className={cn('text-xs font-semibold', getPriorityColor(message.ai_priority))}>
                          P{message.ai_priority}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{message.message_text}</p>
                      <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                        {new Date(message.received_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )) : (
              <EmptyState
                icon={<Inbox />}
                iconColor="brand"
                title="No messages"
                description={selectedCategory === 'all' ? 'Your inbox is empty.' : `No ${categoryLabel[selectedCategory] ?? selectedCategory} messages.`}
              />
            )}
          </div>

          {/* Message detail */}
          <div className="lg:col-span-2">
            {selectedMsg ? (
              <Card>
                <CardHeader>
                  <div className="flex items-start gap-4">
                    <div className="h-14 w-14 shrink-0 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-2xl overflow-hidden">
                      {selectedMsg.sender_avatar_url
                        ? <img src={selectedMsg.sender_avatar_url} alt="" className="w-full h-full object-cover" />
                        : '👤'}
                    </div>
                    <div>
                      <CardTitle>{selectedMsg.sender_display_name || selectedMsg.sender_username}</CardTitle>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                        {selectedMsg.sender_username} · {formatNumber(selectedMsg.sender_followers_count || 0)} followers
                      </p>
                      <div className="flex items-center gap-2 mt-2">
                        {selectedMsg.ai_category && (
                          <Badge variant={categoryVariant[selectedMsg.ai_category] ?? 'gray'}>
                            {categoryLabel[selectedMsg.ai_category] ?? selectedMsg.ai_category}
                          </Badge>
                        )}
                        <Badge variant="gray">{getPlatformIcon(selectedMsg.platform)} {selectedMsg.platform}</Badge>
                      </div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-5">
                  {selectedMsg.ai_summary && (
                    <div className="rounded-lg bg-brand-50 dark:bg-brand-950/40 border border-brand-200 dark:border-brand-800 p-4">
                      <p className="font-medium text-brand-700 dark:text-brand-300 mb-2 flex items-center gap-1.5">
                        <Sparkles className="h-4 w-4" /> AI Analysis
                      </p>
                      <p className="text-sm text-gray-700 dark:text-gray-300 mb-3">{selectedMsg.ai_summary}</p>
                      <div className="flex items-center gap-4 text-xs">
                        <span>
                          Priority: <span className={cn('font-semibold', getPriorityColor(selectedMsg.ai_priority))}>{selectedMsg.ai_priority}/10</span>
                        </span>
                        {selectedMsg.ai_sentiment && (
                          <span>
                            Sentiment: <span className="font-semibold text-success-600 dark:text-success-400">{(selectedMsg.ai_sentiment * 100).toFixed(0)}% Positive</span>
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  <div>
                    <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Message</p>
                    <div className="rounded-lg bg-gray-100 dark:bg-gray-800 px-4 py-3 text-sm text-gray-900 dark:text-gray-50">
                      {selectedMsg.message_text}
                    </div>
                    <p className="text-xs text-gray-400 dark:text-gray-500 mt-1.5">
                      Received {new Date(selectedMsg.received_at).toLocaleDateString()}
                    </p>
                  </div>

                  <div>
                    <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      {selectedMsg.ai_suggested_reply ? '✨ AI Suggested Reply' : 'Reply'}
                    </p>
                    <textarea
                      className={textareaCls}
                      value={replyText}
                      onChange={(e) => setReplyText(e.target.value)}
                      placeholder={selectedMsg.ai_suggested_reply || 'Type your reply...'}
                    />
                  </div>

                  <div className="flex gap-2">
                    <Button
                      variant="primary"
                      className="flex-1"
                      onClick={handleSendReply}
                      disabled={sendReply.isPending || !replyText.trim()}
                      loading={sendReply.isPending}
                    >
                      {sendReply.isPending ? 'Sending...' : 'Send Reply'}
                    </Button>
                    {selectedMsg.ai_suggested_reply && (
                      <Button variant="secondary" leadingIcon={<Sparkles className="h-4 w-4" />} onClick={() => setReplyText(selectedMsg.ai_suggested_reply || '')}>
                        Use AI Reply
                      </Button>
                    )}
                    {selectedMsg.is_business_inquiry && (
                      <Button asChild variant="secondary"><Link href="/inbox/collaborations">Create Deal</Link></Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ) : (
              <div className="flex h-full items-center justify-center">
                <EmptyState
                  icon={<Inbox />}
                  iconColor="gray"
                  title="Select a message"
                  description="Choose a message from the list to view details and reply."
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
