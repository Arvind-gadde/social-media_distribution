/**
 * Billing & Subscription Settings Page
 * 
 * Manage subscription and payment methods
 */

'use client';

import { useRouter } from 'next/navigation';
import { useCurrentUser } from '@/hooks/useAuth';
import { useUsage, useCreatePortal } from '@/hooks/useBilling';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export default function BillingSettingsPage() {
  const router = useRouter();
  const { data: userData, isLoading: userLoading, error: userError } = useCurrentUser();
  const { data: usage, isLoading: usageLoading } = useUsage();
  const createPortal = useCreatePortal();

  const handleManageBilling = () => {
    createPortal.mutate({
      return_url: window.location.href,
    });
  };

  const handleUpgrade = (planId: string) => {
    // TODO: Implement Stripe checkout flow in Phase 20
    alert(`Upgrade to ${planId} plan - Stripe integration coming in Phase 20`);
  };

  const plans = [
    {
      id: 'free',
      name: 'Free',
      price: 0,
      features: [
        '2 connected accounts',
        '3 basic AI agents',
        '30 content ideas/month',
        '2 competitor tracking',
        '30 days analytics history',
      ],
    },
    {
      id: 'pro',
      name: 'Pro',
      price: 29,
      popular: true,
      features: [
        '6 connected accounts',
        'All 14 AI agents',
        'Unlimited content ideas',
        '10 competitor tracking',
        '1 year analytics history',
        '50 videos/month processing',
      ],
    },
    {
      id: 'business',
      name: 'Business',
      price: 79,
      features: [
        'Unlimited connected accounts',
        'All 14 AI agents + custom',
        'Unlimited content ideas',
        '50 competitor tracking',
        '3 years analytics history',
        'Unlimited video processing',
        '5 team members',
        'API access',
      ],
    },
  ];

  // Loading state
  if (userLoading || usageLoading) {
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-tech mx-auto mb-4" />
              <p className="text-muted-foreground">Loading billing information...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (userError) {
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="text-error text-5xl mb-4">⚠️</div>
              <h2 className="text-2xl font-bold mb-2">Failed to load billing information</h2>
              <p className="text-muted-foreground mb-4">
                {userError instanceof Error ? userError.message : 'Something went wrong'}
              </p>
              <Button onClick={() => window.location.reload()}>Retry</Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const user = userData?.user;
  const currentTier = user?.subscription_tier || 'free';
  const subscriptionExpires = user?.subscription_expires_at;

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <Button variant="outline" onClick={() => router.push('/settings')} className="mb-4">
            ← Back to Settings
          </Button>
          <h1 className="text-4xl font-bold gradient-text">Billing & Subscription</h1>
          <p className="text-muted-foreground mt-2">
            Manage your subscription and payment methods
          </p>
        </div>

        {/* Current Subscription */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Current Subscription</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-2xl font-bold capitalize">{currentTier} Plan</h3>
                  <Badge variant="success">Active</Badge>
                </div>
                <div className="text-muted-foreground mb-4">
                  {currentTier === 'free' ? 'Free forever' : `$${plans.find(p => p.id === currentTier)?.price || 0}/month`}
                </div>
                {subscriptionExpires && (
                  <div className="text-sm text-muted-foreground">
                    {currentTier === 'free' 
                      ? 'Upgrade to unlock more features'
                      : `Renews on ${new Date(subscriptionExpires).toLocaleDateString()}`}
                  </div>
                )}
              </div>
              <div className="flex gap-2">
                {currentTier !== 'free' && (
                  <Button 
                    variant="outline"
                    onClick={handleManageBilling}
                    disabled={createPortal.isPending}
                  >
                    {createPortal.isPending ? 'Loading...' : 'Manage Billing'}
                  </Button>
                )}
              </div>
            </div>

            {/* Usage Stats */}
            {usage && (
              <div className="mt-6 pt-6 border-t">
                <h4 className="font-semibold mb-4">Current Usage</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-muted-foreground mb-1">Posts This Month</div>
                    <div className="flex items-center gap-2">
                      <div className="text-2xl font-bold">{usage.posts_this_month}</div>
                      <div className="text-sm text-muted-foreground">/ {usage.posts_limit}</div>
                    </div>
                    <div className="w-full bg-surface rounded-full h-2 mt-2">
                      <div 
                        className="bg-tech h-2 rounded-full transition-all"
                        style={{ width: `${Math.min((usage.posts_this_month / usage.posts_limit) * 100, 100)}%` }}
                      />
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground mb-1">Connected Platforms</div>
                    <div className="flex items-center gap-2">
                      <div className="text-2xl font-bold">{usage.platforms_connected}</div>
                      <div className="text-sm text-muted-foreground">/ {usage.platforms_limit}</div>
                    </div>
                    <div className="w-full bg-surface rounded-full h-2 mt-2">
                      <div 
                        className="bg-tech h-2 rounded-full transition-all"
                        style={{ width: `${Math.min((usage.platforms_connected / usage.platforms_limit) * 100, 100)}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Available Plans */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold mb-4">Available Plans</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {plans.map(plan => (
              <Card
                key={plan.id}
                className={plan.popular ? 'border-tech border-2' : ''}
              >
                <CardHeader>
                  {plan.popular && (
                    <Badge variant="default" className="w-fit mb-2">
                      Most Popular
                    </Badge>
                  )}
                  <CardTitle>{plan.name}</CardTitle>
                  <div className="text-3xl font-bold mt-2">
                    ${plan.price}
                    <span className="text-base font-normal text-muted-foreground">/month</span>
                  </div>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2 mb-6">
                    {plan.features.map((feature, index) => (
                      <li key={index} className="flex items-start gap-2 text-sm">
                        <span className="text-success">✓</span>
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                  <Button
                    className="w-full"
                    variant={currentTier === plan.id ? 'outline' : 'default'}
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

        {/* Payment Method - Coming in Phase 20 */}
        {currentTier !== 'free' && (
          <Card className="mb-8">
            <CardHeader>
              <CardTitle>Payment Method</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8">
                <div className="text-4xl mb-4">💳</div>
                <p className="text-muted-foreground mb-4">
                  Payment methods are managed through Stripe
                </p>
                <Button 
                  variant="outline"
                  onClick={handleManageBilling}
                  disabled={createPortal.isPending}
                >
                  {createPortal.isPending ? 'Loading...' : 'Manage Payment Methods'}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Billing History - Coming in Phase 20 */}
        {currentTier !== 'free' && (
          <Card>
            <CardHeader>
              <CardTitle>Billing History</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8">
                <div className="text-4xl mb-4">📄</div>
                <p className="text-muted-foreground mb-4">
                  View your invoices and billing history through Stripe
                </p>
                <Button 
                  variant="outline"
                  onClick={handleManageBilling}
                  disabled={createPortal.isPending}
                >
                  {createPortal.isPending ? 'Loading...' : 'View Billing History'}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
