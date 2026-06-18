/**
 * Collaboration Pipeline Page
 * 
 * Track and manage brand deals and partnerships
 */

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { 
  useCollaborationsList, 
  useCollaborationStats, 
  useUpdateCollaborationStatus,
  useDeleteCollaboration 
} from '@/hooks/useCollaborations';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

type CollabStatus = 'all' | 'inquiry' | 'negotiating' | 'contract_sent' | 'in_progress' | 'completed';

export default function CollaborationsPage() {
  const router = useRouter();
  const [selectedStatus, setSelectedStatus] = useState<CollabStatus>('all');

  // Fetch data
  const { data, isLoading, error, refetch } = useCollaborationsList({
    status: selectedStatus === 'all' ? undefined : selectedStatus,
  });
  const { data: stats } = useCollaborationStats();
  const updateStatus = useUpdateCollaborationStatus();
  const deleteCollab = useDeleteCollaboration();

  // Handle status update
  const handleUpdateStatus = async (id: string, status: string) => {
    try {
      await updateStatus.mutateAsync({ id, status });
    } catch (error) {
      console.error('Failed to update status:', error);
    }
  };

  // Handle delete
  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this collaboration?')) return;
    
    try {
      await deleteCollab.mutateAsync(id);
    } catch (error) {
      console.error('Failed to delete:', error);
    }
  };

  const formatCurrency = (amount: number, currency: string) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 0,
    }).format(amount);
  };

  const getDeliverableIcon = (type: string) => {
    const icons: Record<string, string> = {
      reel: '🎬',
      video: '🎥',
      story: '📖',
      post: '📝',
      carousel: '🖼️',
    };
    return icons[type] || '📄';
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-tech mx-auto mb-4" />
              <p className="text-muted-foreground">Loading collaborations...</p>
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
              <h2 className="text-2xl font-bold mb-2">Failed to load collaborations</h2>
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

  const collaborations = data?.items || [];

  const getStatusColor = (status: string): 'default' | 'success' | 'warning' | 'error' => {
    const colors: Record<string, 'default' | 'success' | 'warning' | 'error'> = {
      inquiry: 'default',
      negotiating: 'warning',
      contract_sent: 'warning',
      in_progress: 'success',
      completed: 'success',
      cancelled: 'error',
    };
    return colors[status] || 'default';
  };

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      inquiry: 'Inquiry',
      negotiating: 'Negotiating',
      contract_sent: 'Contract Sent',
      in_progress: 'In Progress',
      completed: 'Completed',
      cancelled: 'Cancelled',
    };
    return labels[status] || status;
  };

  const getTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      brand_deal: 'Brand Deal',
      sponsorship: 'Sponsorship',
      collab: 'Collaboration',
      affiliate: 'Affiliate',
      ugc: 'UGC',
    };
    return labels[type] || type;
  };

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <Button variant="outline" onClick={() => router.push('/inbox')} className="mb-4">
                ← Back to Inbox
              </Button>
              <h1 className="text-4xl font-bold gradient-text">Collaboration Pipeline</h1>
              <p className="text-muted-foreground mt-2">
                Track and manage your brand deals and partnerships
              </p>
            </div>
            <Button>
              <span className="mr-2">+</span>
              Add Collaboration
            </Button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">{stats?.total_active || 0}</div>
                <div className="text-sm text-muted-foreground">Active Deals</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">{stats?.by_status?.in_progress || 0}</div>
                <div className="text-sm text-muted-foreground">In Progress</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">
                  {formatCurrency(stats?.total_revenue || 0, 'USD')}
                </div>
                <div className="text-sm text-muted-foreground">Total Revenue</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">{stats?.by_status?.negotiating || 0}</div>
                <div className="text-sm text-muted-foreground">Negotiating</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">{stats?.total_completed || 0}</div>
                <div className="text-sm text-muted-foreground">Completed</div>
              </CardContent>
            </Card>
          </div>

          {/* Filters */}
          <div className="flex gap-2">
            {(['all', 'inquiry', 'negotiating', 'contract_sent', 'in_progress', 'completed'] as CollabStatus[]).map(status => (
              <Button
                key={status}
                variant={selectedStatus === status ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSelectedStatus(status)}
              >
                {status === 'all' ? 'All' : getStatusLabel(status)}
              </Button>
            ))}
          </div>
        </div>

        {/* Collaborations List */}
        {collaborations.length > 0 ? (
          <div className="space-y-4">
            {collaborations.map((collab: any) => (
              <Card key={collab.id} className="card-hover">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-xl font-semibold">{collab.brand_name || 'Unnamed Brand'}</h3>
                        <Badge variant={getStatusColor(collab.status)}>
                          {getStatusLabel(collab.status)}
                        </Badge>
                        <Badge variant="outline">{getTypeLabel(collab.type)}</Badge>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-4">
                        {/* Amount */}
                        <div>
                          <div className="text-sm text-muted-foreground mb-1">Deal Value</div>
                          {(collab.negotiated_amount || collab.final_amount) > 0 ? (
                            <div>
                              <div className="text-lg font-semibold">
                                {formatCurrency(
                                  collab.negotiated_amount || collab.final_amount || 0,
                                  collab.currency || 'USD'
                                )}
                              </div>
                              {collab.negotiated_amount !== collab.offered_amount && collab.offered_amount > 0 && (
                                <div className="text-xs text-muted-foreground line-through">
                                  {formatCurrency(collab.offered_amount, collab.currency || 'USD')}
                                </div>
                              )}
                            </div>
                          ) : (
                            <div className="text-lg font-semibold text-muted-foreground">
                              {collab.offered_amount > 0 
                                ? formatCurrency(collab.offered_amount, collab.currency || 'USD')
                                : 'Barter/Trade'}
                            </div>
                          )}
                        </div>

                        {/* Deliverables */}
                        <div>
                          <div className="text-sm text-muted-foreground mb-1">Deliverables</div>
                          <div className="flex flex-wrap gap-2">
                            {collab.deliverables && collab.deliverables.length > 0 ? (
                              collab.deliverables.map((d: any, i: number) => (
                                <Badge key={i} variant="outline">
                                  {getDeliverableIcon(d.type)} {d.count}x {d.type}
                                </Badge>
                              ))
                            ) : (
                              <span className="text-sm text-muted-foreground">Not specified</span>
                            )}
                          </div>
                        </div>

                        {/* Deadline */}
                        <div>
                          <div className="text-sm text-muted-foreground mb-1">Deadline</div>
                          <div className="text-lg font-semibold">
                            {collab.deadline_at 
                              ? new Date(collab.deadline_at).toLocaleDateString()
                              : 'Not set'}
                          </div>
                        </div>
                      </div>

                      {/* AI Analysis */}
                      {collab.ai_score && (
                        <div className="p-3 bg-tech/10 border border-tech/20 rounded-lg mb-4">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-sm font-medium text-tech">🤖 AI Score:</span>
                            <span className="text-sm font-semibold text-tech">
                              {(collab.ai_score * 100).toFixed(0)}%
                            </span>
                          </div>
                          {collab.ai_recommendation && (
                            <p className="text-sm text-muted-foreground">{collab.ai_recommendation}</p>
                          )}
                        </div>
                      )}

                      {/* Contact */}
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        {collab.contact_name && <span>Contact: {collab.contact_name}</span>}
                        {collab.brand_email && (
                          <>
                            <span>•</span>
                            <span>{collab.brand_email}</span>
                          </>
                        )}
                        <span>•</span>
                        <span>Created {new Date(collab.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-2">
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => router.push(`/inbox/collaborations/${collab.id}`)}
                      >
                        View Details
                      </Button>
                      {collab.status === 'negotiating' && (
                        <Button 
                          size="sm"
                          onClick={() => handleUpdateStatus(collab.id, 'contract_sent')}
                          disabled={updateStatus.isPending}
                        >
                          Send Contract
                        </Button>
                      )}
                      {collab.status === 'in_progress' && (
                        <Button 
                          size="sm"
                          onClick={() => handleUpdateStatus(collab.id, 'completed')}
                          disabled={updateStatus.isPending}
                        >
                          Mark Complete
                        </Button>
                      )}
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => handleDelete(collab.id)}
                        disabled={deleteCollab.isPending}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="py-12">
              <div className="text-center">
                <div className="text-6xl mb-4">🤝</div>
                <h3 className="text-xl font-semibold mb-2">No collaborations found</h3>
                <p className="text-muted-foreground mb-6">
                  {selectedStatus === 'all'
                    ? 'Start tracking your brand deals and partnerships'
                    : `No ${getStatusLabel(selectedStatus).toLowerCase()} collaborations`}
                </p>
                <Button onClick={() => router.push('/inbox/collaborations/new')}>
                  Add Your First Collaboration
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
