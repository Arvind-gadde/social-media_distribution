'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Users, Plus, RefreshCw, Sparkles } from 'lucide-react';
import {
  useCollaborationsList,
  useCollaborationStats,
  useUpdateCollaborationStatus,
  useDeleteCollaboration,
} from '@/hooks/useCollaborations';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { EmptyState } from '@/components/ui/empty-state';
import { Spinner } from '@/components/ui/spinner';
import { cn } from '@/lib/utils';
import {
  Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbLink, BreadcrumbSeparator, BreadcrumbPage,
} from '@/components/ui/breadcrumb';

type CollabStatus = 'all' | 'inquiry' | 'negotiating' | 'contract_sent' | 'in_progress' | 'completed';

const statusVariant: Record<string, 'gray' | 'success' | 'warning' | 'error'> = {
  inquiry: 'gray', negotiating: 'warning', contract_sent: 'warning',
  in_progress: 'success', completed: 'success', cancelled: 'error',
};

const statusLabel: Record<string, string> = {
  inquiry: 'Inquiry', negotiating: 'Negotiating', contract_sent: 'Contract Sent',
  in_progress: 'In Progress', completed: 'Completed', cancelled: 'Cancelled',
};

const typeLabel: Record<string, string> = {
  brand_deal: 'Brand Deal', sponsorship: 'Sponsorship', collab: 'Collaboration',
  affiliate: 'Affiliate', ugc: 'UGC',
};

const deliverableIcon: Record<string, string> = { reel: '🎬', video: '🎥', story: '📖', post: '📝', carousel: '🖼️' };

export default function CollaborationsPage() {
  const router = useRouter();
  const [selectedStatus, setSelectedStatus] = useState<CollabStatus>('all');

  const { data, isLoading, error, refetch } = useCollaborationsList({
    status: selectedStatus === 'all' ? undefined : selectedStatus,
  });
  const { data: stats } = useCollaborationStats();
  const updateStatus = useUpdateCollaborationStatus();
  const deleteCollab = useDeleteCollaboration();

  const handleUpdateStatus = async (id: string, status: string) => {
    try { await updateStatus.mutateAsync({ id, status }); } catch (e) { console.error(e); }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this collaboration?')) return;
    try { await deleteCollab.mutateAsync(id); } catch (e) { console.error(e); }
  };

  const formatCurrency = (amount: number, currency: string) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency, minimumFractionDigits: 0 }).format(amount);

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
          icon={<Users />}
          iconColor="error"
          title="Failed to load collaborations"
          description={error instanceof Error ? error.message : 'Something went wrong'}
          actions={<Button onClick={() => refetch()} leadingIcon={<RefreshCw className="h-4 w-4" />}>Retry</Button>}
        />
      </div>
    );
  }

  const collaborations = data?.items || [];

  const statCards = [
    { label: 'Active Deals', value: stats?.total_active ?? 0 },
    { label: 'In Progress', value: stats?.by_status?.in_progress ?? 0 },
    { label: 'Total Revenue', value: formatCurrency(stats?.total_revenue ?? 0, 'USD') },
    { label: 'Negotiating', value: stats?.by_status?.negotiating ?? 0 },
    { label: 'Completed', value: stats?.total_completed ?? 0 },
  ];

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-10 space-y-8 animate-fade-in">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <Breadcrumb>
              <BreadcrumbList>
                <BreadcrumbItem><BreadcrumbLink href="/inbox">Inbox</BreadcrumbLink></BreadcrumbItem>
                <BreadcrumbSeparator />
                <BreadcrumbItem><BreadcrumbPage>Collaborations</BreadcrumbPage></BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb>
            <div className="mt-3 space-y-1">
              <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">Collaboration Pipeline</h1>
              <p className="text-sm text-gray-600 dark:text-gray-400">Track and manage your brand deals and partnerships.</p>
            </div>
          </div>
          <Button variant="primary" leadingIcon={<Plus className="h-4 w-4" />} onClick={() => router.push('/inbox/collaborations/new')}>
            Add Collaboration
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
          {(['all', 'inquiry', 'negotiating', 'contract_sent', 'in_progress', 'completed'] as CollabStatus[]).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setSelectedStatus(s)}
              className={cn(
                'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                selectedStatus === s
                  ? 'bg-brand-600 text-white'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
              )}
            >
              {s === 'all' ? 'All' : statusLabel[s]}
            </button>
          ))}
        </div>

        {collaborations.length > 0 ? (
          <div className="space-y-4">
            {collaborations.map((collab: any) => (
              <Card key={collab.id} className="transition-all duration-150 hover:shadow-sm">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-3 flex-wrap">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-50">{collab.brand_name || 'Unnamed Brand'}</h3>
                        <Badge variant={statusVariant[collab.status] ?? 'gray'}>{statusLabel[collab.status] ?? collab.status}</Badge>
                        <Badge variant="gray">{typeLabel[collab.type] ?? collab.type}</Badge>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-4">
                        <div>
                          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Deal Value</p>
                          <p className="text-lg font-semibold text-gray-900 dark:text-gray-50">
                            {(collab.negotiated_amount || collab.final_amount) > 0
                              ? formatCurrency(collab.negotiated_amount || collab.final_amount || 0, collab.currency || 'USD')
                              : collab.offered_amount > 0
                              ? formatCurrency(collab.offered_amount, collab.currency || 'USD')
                              : 'Barter/Trade'}
                          </p>
                        </div>

                        <div>
                          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1.5">Deliverables</p>
                          <div className="flex flex-wrap gap-1.5">
                            {collab.deliverables?.length > 0
                              ? collab.deliverables.map((d: any, i: number) => (
                                  <Badge key={i} variant="gray" size="sm">
                                    {deliverableIcon[d.type] || '📄'} {d.count}x {d.type}
                                  </Badge>
                                ))
                              : <span className="text-xs text-gray-500 dark:text-gray-400">Not specified</span>}
                          </div>
                        </div>

                        <div>
                          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Deadline</p>
                          <p className="text-lg font-semibold text-gray-900 dark:text-gray-50">
                            {collab.deadline_at ? new Date(collab.deadline_at).toLocaleDateString() : 'Not set'}
                          </p>
                        </div>
                      </div>

                      {collab.ai_score && (
                        <div className="rounded-lg bg-brand-50 dark:bg-brand-950/40 border border-brand-200 dark:border-brand-800 p-3 mb-3">
                          <div className="flex items-center gap-2 mb-1">
                            <Sparkles className="h-3.5 w-3.5 text-brand-600 dark:text-brand-400" />
                            <span className="text-sm font-medium text-brand-700 dark:text-brand-300">
                              AI Score: {(collab.ai_score * 100).toFixed(0)}%
                            </span>
                          </div>
                          {collab.ai_recommendation && (
                            <p className="text-xs text-gray-600 dark:text-gray-400">{collab.ai_recommendation}</p>
                          )}
                        </div>
                      )}

                      <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                        {collab.contact_name && <span>Contact: {collab.contact_name}</span>}
                        {collab.brand_email && <><span>·</span><span>{collab.brand_email}</span></>}
                        <span>·</span>
                        <span>Created {new Date(collab.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>

                    <div className="flex gap-2 shrink-0 flex-col sm:flex-row">
                      <Button variant="secondary" size="sm" onClick={() => router.push(`/inbox/collaborations/${collab.id}`)}>
                        View Details
                      </Button>
                      {collab.status === 'negotiating' && (
                        <Button variant="primary" size="sm" onClick={() => handleUpdateStatus(collab.id, 'contract_sent')} disabled={updateStatus.isPending}>
                          Send Contract
                        </Button>
                      )}
                      {collab.status === 'in_progress' && (
                        <Button variant="primary" size="sm" onClick={() => handleUpdateStatus(collab.id, 'completed')} disabled={updateStatus.isPending}>
                          Mark Complete
                        </Button>
                      )}
                      <Button variant="secondary" size="sm" onClick={() => handleDelete(collab.id)} disabled={deleteCollab.isPending}>
                        Delete
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <EmptyState
            icon={<Users />}
            iconColor="brand"
            title="No collaborations found"
            description={
              selectedStatus === 'all'
                ? 'Start tracking your brand deals and partnerships.'
                : `No ${statusLabel[selectedStatus]?.toLowerCase() ?? selectedStatus} collaborations.`
            }
            actions={
              <Button variant="primary" leadingIcon={<Plus className="h-4 w-4" />} onClick={() => router.push('/inbox/collaborations/new')}>
                Add Your First Collaboration
              </Button>
            }
          />
        )}
      </div>
    </div>
  );
}
