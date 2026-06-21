/**
 * Home Page - Dashboard Overview (Untitled UI)
 */

'use client';

import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowUpRight,
  ArrowDownRight,
  Lightbulb,
  Plus,
  Settings,
  Target,
  PenLine,
  Calendar,
} from 'lucide-react';
import type { Goal } from '@contentflow/api-client';

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { EmptyState, FeaturedIcon } from '@/components/ui/empty-state';
import { SkeletonCard } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

import { useGoalsList } from '@/hooks/useGoals';
import { useCurrentUser } from '@/hooks/useAuth';

// ─── Helpers ────────────────────────────────────────────────────────────────

function getFirstName(
  user: { display_name?: string | null; name?: string | null; email?: string } | null | undefined
): string {
  if (!user) return 'there';
  const candidate =
    (user.display_name && user.display_name.trim()) ||
    (user.name && user.name.trim()) ||
    (user.email && user.email.split('@')[0]) ||
    '';
  if (!candidate) return 'there';
  return candidate.split(/\s+/)[0];
}

type TileColor = 'brand' | 'info' | 'warning' | 'success';

interface KpiCardProps {
  label: string;
  value: number | string;
  deltaLabel: string;
  deltaDirection: 'up' | 'down' | 'flat';
}

function KpiCard({ label, value, deltaLabel, deltaDirection }: KpiCardProps) {
  const isUp = deltaDirection === 'up';
  const isDown = deltaDirection === 'down';

  return (
    <Card className="p-6 flex flex-col gap-4">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{label}</p>
      </div>
      <div className="flex items-end justify-between gap-3">
        <span className="text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">
          {value}
        </span>
        <span
          className={cn(
            'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
            isUp && 'bg-success-50 text-success-700 dark:bg-success-900/30 dark:text-success-300',
            isDown && 'bg-error-50 text-error-700 dark:bg-error-900/30 dark:text-error-300',
            !isUp &&
              !isDown &&
              'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
          )}
        >
          {isUp && <ArrowUpRight className="h-3 w-3" aria-hidden="true" />}
          {isDown && <ArrowDownRight className="h-3 w-3" aria-hidden="true" />}
          {deltaLabel}
        </span>
      </div>
      {/* Sparkline placeholder */}
      <div className="mt-1 h-4 rounded-md bg-brand-100 dark:bg-brand-900/40" aria-hidden="true" />
    </Card>
  );
}

// ─── Page ───────────────────────────────────────────────────────────────────

export default function HomePage() {
  const router = useRouter();

  // Auth enforced by middleware.ts — unauthenticated users redirect at edge.
  const { data: userData } = useCurrentUser();
  const {
    data: goalsData,
    isLoading: goalsLoading,
  } = useGoalsList({ status: 'active', page_size: 3 });

  const goals: Goal[] = goalsData?.items ?? [];

  const firstName = getFirstName(userData?.user);

  const quickActions: Array<{
    label: string;
    icon: React.ReactNode;
    color: TileColor;
    href: string;
  }> = [
    { label: 'Create content', icon: <PenLine />, color: 'brand', href: '/content/create' },
    { label: 'Schedule', icon: <Calendar />, color: 'warning', href: '/schedule' },
    { label: 'Generate ideas', icon: <Lightbulb />, color: 'info', href: '/content/ideas' },
    { label: 'Settings', icon: <Settings />, color: 'success', href: '/settings' },
  ];

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-10 space-y-8 animate-fade-in">
        {/* Page header */}
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="space-y-1.5">
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">
              Welcome back, {firstName}
            </h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Here&apos;s what&apos;s happening with your content today.
            </p>
          </div>
          <div className="flex-shrink-0">
            <Button asChild size="md" leadingIcon={<Plus className="h-4 w-4" />}>
              <Link href="/content/create">Create</Link>
            </Button>
          </div>
        </header>

        {/* KPI row */}
        <section
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6"
          aria-label="Key metrics"
        >
          <KpiCard
            label="Active goals"
            value={goals.length}
            deltaLabel="Active"
            deltaDirection="up"
          />
          <KpiCard
            label="Scheduled posts"
            value={0}
            deltaLabel="Plan"
            deltaDirection="flat"
          />
          <KpiCard
            label="Published"
            value={0}
            deltaLabel="This week"
            deltaDirection="flat"
          />
          <KpiCard
            label="Connected accounts"
            value={0}
            deltaLabel="Connect"
            deltaDirection="flat"
          />
        </section>

        {/* Two-column grid */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent goals */}
          <Card className="flex flex-col">
            <CardHeader className="flex-row items-start justify-between space-y-0 gap-3">
              <div className="space-y-1">
                <CardTitle>Recent goals</CardTitle>
                <CardDescription>Your active targets and progress.</CardDescription>
              </div>
              <Button asChild variant="link-color" size="sm" className="shrink-0">
                <Link href="/goals">View all</Link>
              </Button>
            </CardHeader>
            <CardContent className="flex-1">
              {goalsLoading ? (
                <div className="space-y-3">
                  <SkeletonCard showAvatar={false} lines={1} />
                  <SkeletonCard showAvatar={false} lines={1} />
                </div>
              ) : goals.length > 0 ? (
                <ul className="space-y-4">
                  {goals.slice(0, 3).map((goal) => {
                    const pct = Math.max(0, Math.min(100, Math.round(goal.progress_pct ?? 0)));
                    return (
                      <li key={goal.id} className="space-y-2">
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                            {goal.title}
                          </p>
                          <span className="text-xs font-medium text-gray-600 dark:text-gray-400 shrink-0">
                            {pct}%
                          </span>
                        </div>
                        <div
                          className="h-2 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800"
                          role="progressbar"
                          aria-valuenow={pct}
                          aria-valuemin={0}
                          aria-valuemax={100}
                          aria-label={`${goal.title} progress`}
                        >
                          <div
                            className="h-full rounded-full bg-brand-600 transition-all"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <EmptyState
                  icon={<Target />}
                  iconColor="brand"
                  title="No active goals"
                  description="Set a target to start tracking your progress."
                  actions={
                    <Button onClick={() => router.push('/goals')} size="sm">
                      Create your first goal
                    </Button>
                  }
                />
              )}
            </CardContent>
          </Card>

          {/* Getting started */}
          <Card className="flex flex-col">
            <CardHeader className="flex-row items-start justify-between space-y-0 gap-3">
              <div className="space-y-1">
                <CardTitle>Getting started</CardTitle>
                <CardDescription>Set up your workspace to start publishing.</CardDescription>
              </div>
            </CardHeader>
            <CardContent className="flex-1">
              <ul className="space-y-3 text-sm text-gray-700 dark:text-gray-300">
                <li className="flex items-center justify-between gap-3">
                  <span>Connect a social account</span>
                  <Button asChild variant="link-color" size="sm">
                    <Link href="/settings/accounts">Connect</Link>
                  </Button>
                </li>
                <li className="flex items-center justify-between gap-3">
                  <span>Create your first post</span>
                  <Button asChild variant="link-color" size="sm">
                    <Link href="/content/create">Create</Link>
                  </Button>
                </li>
                <li className="flex items-center justify-between gap-3">
                  <span>Generate ideas with AI</span>
                  <Button asChild variant="link-color" size="sm">
                    <Link href="/content/ideas">Ideas</Link>
                  </Button>
                </li>
              </ul>
            </CardContent>
          </Card>
        </section>

        {/* Quick actions */}
        <section>
          <Card>
            <CardHeader>
              <CardTitle>Quick actions</CardTitle>
              <CardDescription>Jump straight into the most common tasks.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {quickActions.map((action) => (
                  <button
                    key={action.href}
                    type="button"
                    onClick={() => router.push(action.href)}
                    className={cn(
                      'group flex flex-col items-center justify-center gap-3 rounded-xl border border-gray-200 bg-white p-4 text-center',
                      'transition-all duration-150 hover:border-brand-300 hover:bg-brand-50/40 hover:shadow-sm',
                      'focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/24',
                      'dark:border-gray-800 dark:bg-gray-900 dark:hover:border-brand-700 dark:hover:bg-brand-900/20'
                    )}
                  >
                    <FeaturedIcon
                      size="md"
                      color={action.color}
                      icon={action.icon}
                      className="transition-transform duration-150 group-hover:-translate-y-0.5"
                    />
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      {action.label}
                    </span>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        </section>
      </div>
    </div>
  );
}
