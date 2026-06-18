/**
 * DM Inbox Page
 * 
 * Manage messages across all platforms with AI classification
 */

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useDMList, useDMStats, useMarkDMRead, useReplyToDM } from '@/hooks/useInbox';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

type MessageCategory = 'all' | 'brand_deal' | 'collab' | 'fan' | 'question' | 'spam';

export default function InboxPage() {
  const [selectedCategory, setSelectedCategory] = useState<MessageCategory>('all');
  const [selectedMessage, setSelectedMessage] = useState<string | null>(null);
  const [replyText, setReplyText] = useState('');

  // Fetch data
  const { data, isLoading, error, refetch } = useDMList({
    ai_category: selectedCategory === 'all' ? undefined : selectedCategory,
  });
  const { data: stats } = useDMStats();
  const markRead = useMarkDMRead();
  const sendReply = useReplyToDM();

  // Handle message selection
  const handleSelectMessage = async (id: string) => {
    setSelectedMessage(id);
    const message = data?.items.find((m: any) => m.id === id);
    if (message && !message.is_read) {
      try {
        await markRead.mutateAsync(id);
      } catch (error) {
        console.error('Failed to mark as read:', error);
      }
    }
  };

  // Handle reply
  const handleSendReply = async () => {
    if (!selectedMessage || !replyText.trim()) return;
    
    try {
      await sendReply.mutateAsync({
        id: selectedMessage,
        data: { message: replyText },
      });
      setReplyText('');
    } catch (error) {
      console.error('Failed to send reply:', error);
    }
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const getPlatformIcon = (platform: string) => {
    const icons: Record<string, string> = {
      instagram: '📷',
      youtube: '▶️',
      tiktok: '🎵',
      twitter: '🐦',
    };
    return icons[platform?.toLowerCase()] || '📱';
  };

  const getCategoryColor = (category: string): 'default' | 'success' | 'warning' | 'error' => {
    const colors: Record<string, 'default' | 'success' | 'warning' | 'error'> = {
      brand_deal: 'success',
      collab: 'warning',
      fan: 'default',
      question: 'default',
      spam: 'error',
    };
    return colors[category] || 'default';
  };

  const getCategoryLabel = (category: string) => {
    const labels: Record<string, string> = {
      brand_deal: 'Brand Deal',
      collab: 'Collaboration',
      fan: 'Fan Message',
      question: 'Question',
      spam: 'Spam',
    };
    return labels[category] || category;
  };

  const getPriorityColor = (priority: number) => {
    if (priority >= 8) return 'text-error';
    if (priority >= 6) return 'text-warning';
    return 'text-muted-foreground';
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-tech mx-auto mb-4" />
              <p className="text-muted-foreground">Loading messages...</p>
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
              <h2 className="text-2xl font-bold mb-2">Failed to load messages</h2>
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

  const messages = data?.items || [];
  const selectedMsg = messages.find((m: any) => m.id === selectedMessage);

  // Mock messages data - will be replaced with real API
  const mockMessages = [
    {
      id: '1',
      platform: 'Instagram',
      sender: 'TechGear Co',
      senderUsername: '@techgearco',
      senderFollowers: 125000,
      message: 'Hi! We love your content and would like to discuss a potential partnership. Are you open to sponsored content?',
      category: 'brand_deal',
      aiSummary: 'Brand partnership inquiry from verified company',
      aiSentiment: 0.85,
      aiPriority: 9,
      receivedAt: '2 hours ago',
      isRead: false,
      avatar: '🏢',
    },
    {
      id: '2',
      platform: 'TikTok',
      sender: 'Sarah Creator',
      senderUsername: '@sarahcreates',
      senderFollowers: 45000,
      message: 'Hey! I\'m a fellow creator in the tech niche. Would you be interested in doing a collab video together?',
      category: 'collab',
      aiSummary: 'Collaboration request from creator with similar audience',
      aiSentiment: 0.78,
      aiPriority: 7,
      receivedAt: '5 hours ago',
      isRead: false,
      avatar: '👩',
    },
    {
      id: '3',
      platform: 'YouTube',
      sender: 'John Smith',
      senderUsername: '@johnsmith',
      senderFollowers: 250,
      message: 'Love your videos! What camera do you use for filming? Keep up the great work!',
      category: 'fan',
      aiSummary: 'Fan appreciation with equipment question',
      aiSentiment: 0.92,
      aiPriority: 4,
      receivedAt: '1 day ago',
      isRead: true,
      avatar: '👤',
    },
    {
      id: '4',
      platform: 'Instagram',
      sender: 'Marketing Pro',
      senderUsername: '@marketingpro',
      senderFollowers: 8900,
      message: 'Can you explain how you edit your reels? I\'m trying to improve my content quality.',
      category: 'question',
      aiSummary: 'Technical question about content creation process',
      aiSentiment: 0.65,
      aiPriority: 5,
      receivedAt: '2 days ago',
      isRead: true,
      avatar: '💼',
    },
  ];

  const filteredMessages = messages.filter(msg =>
    selectedCategory === 'all' || msg.ai_category === selectedCategory
  );

  const selectedMsgLegacy = messages.find(m => m.id === selectedMessage);

  const formatNumberLegacy = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const getPlatformIconLegacy = (platform: string) => {
    const icons: Record<string, string> = {
      Instagram: '📷',
      YouTube: '▶️',
      TikTok: '🎵',
      Twitter: '🐦',
    };
    return icons[platform] || '📱';
  };

  const getCategoryColorLegacy = (category: string): 'default' | 'success' | 'warning' | 'error' => {
    const colors: Record<string, 'default' | 'success' | 'warning' | 'error'> = {
      brand_deal: 'success',
      collab: 'warning',
      fan: 'default',
      question: 'default',
      spam: 'error',
    };
    return colors[category] || 'default';
  };

  const getCategoryLabelLegacy = (category: string) => {
    const labels: Record<string, string> = {
      brand_deal: 'Brand Deal',
      collab: 'Collaboration',
      fan: 'Fan Message',
      question: 'Question',
      spam: 'Spam',
    };
    return labels[category] || category;
  };

  const getPriorityColorLegacy = (priority: number) => {
    if (priority >= 8) return 'text-error';
    if (priority >= 6) return 'text-warning';
    return 'text-muted-foreground';
  };

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-4xl font-bold gradient-text">DM Inbox</h1>
              <p className="text-muted-foreground mt-2">
                AI-powered message management across all platforms
              </p>
            </div>
            <Link href="/inbox/collaborations">
              <Button>
                🤝 View Collaborations
              </Button>
            </Link>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">{stats?.total_unread || 0}</div>
                <div className="text-sm text-muted-foreground">Unread</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">{stats?.total_business_inquiries || 0}</div>
                <div className="text-sm text-muted-foreground">Brand Deals</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">{stats?.by_category?.collab || 0}</div>
                <div className="text-sm text-muted-foreground">Collabs</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">{stats?.by_category?.question || 0}</div>
                <div className="text-sm text-muted-foreground">Questions</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">{stats?.high_priority_count || 0}</div>
                <div className="text-sm text-muted-foreground">High Priority</div>
              </CardContent>
            </Card>
          </div>

          {/* Filters */}
          <div className="flex gap-2">
            {(['all', 'brand_deal', 'collab', 'fan', 'question', 'spam'] as MessageCategory[]).map(category => (
              <Button
                key={category}
                variant={selectedCategory === category ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSelectedCategory(category)}
              >
                {category === 'all' ? 'All Messages' : getCategoryLabel(category)}
              </Button>
            ))}
          </div>
        </div>

        {/* Messages Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Message List */}
          <div className="lg:col-span-1 space-y-2">
            {messages.length > 0 ? messages.map((message: any) => (
              <Card
                key={message.id}
                className={`cursor-pointer transition-all ${
                  selectedMessage === message.id ? 'border-tech' : ''
                } ${!message.is_read ? 'bg-tech/5' : ''}`}
                onClick={() => handleSelectMessage(message.id)}
              >
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <div className="text-3xl">
                      {message.sender_avatar_url ? (
                        <img src={message.sender_avatar_url} alt={message.sender_display_name} className="w-10 h-10 rounded-full" />
                      ) : (
                        '👤'
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <div className="font-semibold truncate">{message.sender_display_name || message.sender_username}</div>
                        {!message.is_read && (
                          <div className="w-2 h-2 rounded-full bg-tech flex-shrink-0" />
                        )}
                      </div>
                      <div className="flex items-center gap-2 mb-2">
                        {message.ai_category && (
                          <Badge variant={getCategoryColor(message.ai_category)} className="text-xs">
                            {getCategoryLabel(message.ai_category)}
                          </Badge>
                        )}
                        <span className="text-xs">{getPlatformIcon(message.platform)}</span>
                        <span className={`text-xs font-semibold ${getPriorityColor(message.ai_priority)}`}>
                          P{message.ai_priority}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground truncate">
                        {message.message_text}
                      </p>
                      <div className="text-xs text-muted-foreground mt-1">
                        {new Date(message.received_at).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )) : (
              <Card>
                <CardContent className="py-12">
                  <div className="text-center">
                    <div className="text-6xl mb-4">📭</div>
                    <h3 className="text-xl font-semibold mb-2">No messages</h3>
                    <p className="text-muted-foreground">
                      {selectedCategory === 'all'
                        ? 'Your inbox is empty'
                        : `No ${getCategoryLabel(selectedCategory)} messages`}
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Message Detail */}
          <div className="lg:col-span-2">
            {selectedMsg ? (
              <Card>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-4">
                      <div className="text-5xl">
                        {selectedMsg.sender_avatar_url ? (
                          <img
                            src={selectedMsg.sender_avatar_url}
                            alt={selectedMsg.sender_display_name || selectedMsg.sender_username}
                            className="w-14 h-14 rounded-full object-cover"
                          />
                        ) : (
                          'ðŸ‘¤'
                        )}
                      </div>
                      <div>
                        <CardTitle>{selectedMsg.sender_display_name || selectedMsg.sender_username}</CardTitle>
                        <div className="text-sm text-muted-foreground mt-1">
                          {selectedMsg.sender_username} • {formatNumber(selectedMsg.sender_followers_count || 0)} followers
                        </div>
                        <div className="flex items-center gap-2 mt-2">
                          {selectedMsg.ai_category && (
                            <Badge variant={getCategoryColor(selectedMsg.ai_category)}>
                              {getCategoryLabel(selectedMsg.ai_category)}
                            </Badge>
                          )}
                          <Badge variant="outline">
                            {getPlatformIcon(selectedMsg.platform)} {selectedMsg.platform}
                          </Badge>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* AI Analysis */}
                  {selectedMsg.ai_summary && (
                    <div className="p-4 bg-tech/10 border border-tech/20 rounded-lg">
                      <div className="font-medium text-tech mb-2">🤖 AI Analysis</div>
                      <div className="text-sm mb-3">{selectedMsg.ai_summary}</div>
                      <div className="flex items-center gap-4 text-xs">
                        <div>
                          <span className="text-muted-foreground">Priority: </span>
                          <span className={`font-semibold ${getPriorityColor(selectedMsg.ai_priority)}`}>
                            {selectedMsg.ai_priority}/10
                          </span>
                        </div>
                        {selectedMsg.ai_sentiment && (
                          <div>
                            <span className="text-muted-foreground">Sentiment: </span>
                            <span className="font-semibold text-success">
                              {(selectedMsg.ai_sentiment * 100).toFixed(0)}% Positive
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Message */}
                  <div>
                    <div className="text-sm font-medium mb-2">Message</div>
                    <div className="p-4 bg-surface rounded-lg">
                      {selectedMsg.message_text}
                    </div>
                    <div className="text-xs text-muted-foreground mt-2">
                      Received {new Date(selectedMsg.received_at).toLocaleDateString()}
                    </div>
                  </div>

                  {/* Reply */}
                  <div>
                    <div className="text-sm font-medium mb-2">
                      {selectedMsg.ai_suggested_reply ? '✨ AI Suggested Reply' : 'Reply'}
                    </div>
                    <textarea
                      className="w-full px-3 py-2 bg-surface rounded-md border border-input focus:outline-none focus:ring-2 focus:ring-tech min-h-[100px]"
                      value={replyText}
                      onChange={(e) => setReplyText(e.target.value)}
                      placeholder={selectedMsg.ai_suggested_reply || 'Type your reply...'}
                    />
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2">
                    <Button 
                      className="flex-1"
                      onClick={handleSendReply}
                      disabled={sendReply.isPending || !replyText.trim()}
                    >
                      {sendReply.isPending ? 'Sending...' : 'Send Reply'}
                    </Button>
                    {selectedMsg.ai_suggested_reply && (
                      <Button 
                        variant="outline"
                        onClick={() => setReplyText(selectedMsg.ai_suggested_reply || '')}
                      >
                        ✨ Use AI Reply
                      </Button>
                    )}
                    {selectedMsg.is_business_inquiry && (
                      <Link href="/inbox/collaborations">
                        <Button variant="outline">Create Deal</Button>
                      </Link>
                    )}
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent className="py-12">
                  <div className="text-center">
                    <div className="text-6xl mb-4">📬</div>
                    <h3 className="text-xl font-semibold mb-2">Select a message</h3>
                    <p className="text-muted-foreground">
                      Choose a message from the list to view details and reply
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
