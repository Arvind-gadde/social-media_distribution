'use client';

import { CreditCard, RefreshCw } from 'lucide-react';
import { useCurrentUser } from '@/hooks/useAuth';
import { useUsage, useCreatePortal } from '@/hooks/useBilling';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { EmptyState } from '@/components/ui/empty-state';
import { Spinner } from '@/components/ui/spinner';
import {
  Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbLink, BreadcrumbSeparator, BreadcrumbPage,
} from '@/components/ui/breadcrumb';

const plans = [
  {
    id: 'free', name: 'Free', price: 0,
    features: ['2 connected accounts', '3 basic AI agents', '30 content ideas/month', '2 competitor tracking', '30 days analytics history'],
  },
  {
    id: 'pro', name: 'Pro', price: 29, popular: true,
    features: ['6 connected accounts', 'All 14 AI agents', 'Unlimited content ideas', '10 competitor tracking', '1 year analytics history', '50 videos/month processing'],
  },
  {
    id: 'business', name: 'Business', price: 79,
    features: ['Unlimited connected accounts', 'All 14 AI agents + custom', 'Unlimited content ideas', '50 competitor tracking', '3 years analytics history', 'Unlimited video processing', '5 team members', 'API access'],
  },
];

export default function BillingSettingsPage() {
  const { data: userData, isLoading: userLoading, error: userError } = useCurrentUser();
  const { data: usage, isLoading: usageLoading } = useUsage();
  const createPortal = useCreatePortal();

  const handleManageBilling = () => {
    createPortal.mutate({ return_url: window.location.href });
  };

  const handleUpgrade = (planId: string) => {
    alert(`Upgrade to ${planId} plan — Stripe integration coming in Phase 20`);
  };

  if (userLoading || usageLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Spinner size="lg" color="primary" />
      </div>
    );
  }

  if (userError) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <EmptyState
          icon={<CreditCard />}
          iconColor="error"
          title="Failed to load billing information"
          description={userError instanceof Error ? userError.message : 'Something went wrong'}
          actions={<Button onClick={() => window.location.reload()} leadingIcon={<RefreshCw className="h-4 w-4" />}>Retry</Button>}
        />
      </div>
    );
  }

  const user = userData?.user;
  const currentTier = user?.subscription_tier || 'free';
  const subscriptionExpires = user?.subscription_expires_at;

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-10 space-y-8 animate-fade-in">
        <header>
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem><BreadcrumbLink href="/settings">Settings</BreadcrumbLink></BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem><BreadcrumbPage>Billing & Subscription</BreadcrumbPage></BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
          <div className="mt-4 space-y-1">
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">Billing & Subscription</h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">Manage your subscription and payment methods.</p>
          </div>
        </header>

        {/* Current Subscription */}
        <Card>
          <CardHeader><CardTitle>Current Subscription</CardTitle></CardHeader>
          <CardContent>
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-xl font-semibold capitalize text-gray-900 dark:text-gray-50">{currentTier} Plan</h3>
                  <Badge variant="success">Active</Badge>
                </div>
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
                  {currentTier === 'free' ? 'Free forever' : `$${plans.find(p => p.id === currentTier)?.price || 0}/month`}
                </p>
                {subscriptionExpires && (
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {currentTier === 'free'
                      ? 'Upgrade to unlock more features'
                      : `Renews on ${new Date(subscriptionExpires).toLocaleDateString()}`}
                  </p>
                )}
              </div>
              {currentTier !== 'free' && (
                <Button variant="secondary" onClick={handleManageBilling} disabled={createPortal.isPending} loading={createPortal.isPending}>
                  {createPortal.isPending ? 'Loading...' : 'Manage Billing'}
                </Button>
              )}
            </div>

            {usage && (
              <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-800">
                <h4 className="font-semibold text-sm text-gray-900 dark:text-gray-50 mb-4">Current Usage</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {[
                    { label: 'Posts This Month', current: usage.posts_this_month, limit: usage.posts_limit },
                    { label: 'Connected Platforms', current: usage.platforms_connected, limit: usage.platforms_limit },
                  ].map((item) => (
                    <div key={item.label}>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">{item.label}</p>
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className="text-xl font-semibold text-gray-900 dark:text-gray-50">{item.current}</span>
                        <span className="text-sm text-gray-500 dark:text-gray-400">/ {item.limit}</span>
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                        <div
                          className="bg-brand-600 h-1.5 rounded-full transition-all"
                          style={{ width: `${Math.min((item.current / item.limit) * 100, 100)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Available Plans */}
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-50 mb-4">Available Plans</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {plans.map(plan => (
              <Card
                key={plan.id}
                className={plan.popular ? 'border-brand-500 dark:border-brand-400 border-2' : ''}
              >
                <CardHeader>
                  {plan.popular && <Badge variant="brand" className="w-fit mb-2">Most Popular</Badge>}
                  <CardTitle>{plan.name}</CardTitle>
                  <div className="text-3xl font-bold mt-2 text-gray-900 dark:text-gray-50">
                    ${plan.price}
                    <span className="text-base font-normal text-gray-500 dark:text-gray-400">/month</span>
                  </div>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2 mb-6">
                    {plan.features.map((feature, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm">
                        <span className="text-success-600 dark:text-success-400 mt-0.5">✓</span>
                        <span className="text-gray-700 dark:text-gray-300">{feature}</span>
                      </li>
                    ))}
                  </ul>
                  <Button
                    className="w-full"
                    variant={currentTier === plan.id ? 'secondary' : 'primary'}
                    disabled={currentTier === plan.id}
                    onClick={() => handleUpgrade(plan.id)}
                  >
                    {currentTier === plan.id ? 'Current Plan' : 'Upgrade'}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {currentTier !== 'free' && (
          <>
            <Card>
              <CardHeader><CardTitle>Payment Method</CardTitle></CardHeader>
              <CardContent>
                <div className="text-center py-8">
                  <p className="text-gray-500 dark:text-gray-400 mb-4">Payment methods are managed through Stripe</p>
                  <Button variant="secondary" onClick={handleManageBilling} disabled={createPortal.isPending} loading={createPortal.isPending}>
                    {createPortal.isPending ? 'Loading...' : 'Manage Payment Methods'}
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>Billing History</CardTitle></CardHeader>
              <CardContent>
                <div className="text-center py-8">
                  <p className="text-gray-500 dark:text-gray-400 mb-4">View your invoices and billing history through Stripe</p>
                  <Button variant="secondary" onClick={handleManageBilling} disabled={createPortal.isPending} loading={createPortal.isPending}>
                    {createPortal.isPending ? 'Loading...' : 'View Billing History'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}
