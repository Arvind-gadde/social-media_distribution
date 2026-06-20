'use client';

import { Bot, RefreshCw } from 'lucide-react';
import { useAgentsList, useUpdateAgent } from '@/hooks/useAgents';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { EmptyState } from '@/components/ui/empty-state';
import { Spinner } from '@/components/ui/spinner';
import {
  Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbLink, BreadcrumbSeparator, BreadcrumbPage,
} from '@/components/ui/breadcrumb';
import { useRouter } from 'next/navigation';
import type { AgentType } from '@contentflow/api-client';

export default function AgentsSettingsPage() {
  const router = useRouter();
  const { data, isLoading, error, refetch } = useAgentsList();
  const updateAgent = useUpdateAgent();

  const toggleAgent = async (agentType: AgentType, currentEnabled: boolean) => {
    try {
      await updateAgent.mutateAsync({ agentType, data: { is_enabled: !currentEnabled } });
    } catch (e) { console.error(e); }
  };

  const getAgentIcon = (agentType: string) => {
    const icons: Record<string, string> = {
      niche_intelligence: '🧠', trend: '📈', analytics: '📊', competitor: '🔍',
      content_research: '💡', goal_reminder: '🎯', collaboration: '🤝', news_fetcher: '📰',
      tips_tricks: '💡', scheduling: '⏰', growth: '🚀', video_editor: '🎬', manipulation: '🎯',
    };
    return icons[agentType] || '🤖';
  };

  const getFrequencyLabel = (frequency: string) => {
    const labels: Record<string, string> = {
      hourly: 'Every hour', every_6h: 'Every 6 hours', daily: 'Daily',
      weekly: 'Weekly', on_demand: 'On demand', real_time: 'Real-time',
    };
    return labels[frequency] || frequency;
  };

  const formatLastRun = (lastRunAt: string | null) => {
    if (!lastRunAt) return 'Never';
    const diffMs = Date.now() - new Date(lastRunAt).getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

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
          icon={<Bot />}
          iconColor="error"
          title="Failed to load agents"
          description={error instanceof Error ? error.message : 'Something went wrong'}
          actions={<Button onClick={() => refetch()} leadingIcon={<RefreshCw className="h-4 w-4" />}>Retry</Button>}
        />
      </div>
    );
  }

  const agents = data || [];
  const enabledAgents = agents.filter((a: any) => a.is_enabled);
  const agentsRunToday = agents.filter((a: any) => {
    if (!a.last_run_at) return false;
    return new Date(a.last_run_at).toDateString() === new Date().toDateString();
  });

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-10 space-y-8 animate-fade-in">
        <header>
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem><BreadcrumbLink href="/settings">Settings</BreadcrumbLink></BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem><BreadcrumbPage>AI Agents</BreadcrumbPage></BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
          <div className="mt-4 space-y-1">
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">AI Agents</h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">Configure your AI-powered automation agents.</p>
          </div>
        </header>

        <div className="grid grid-cols-3 gap-4">
          {[
            { label: 'Active Agents', value: `${enabledAgents.length}/${agents.length}` },
            { label: 'Agents Run Today', value: agentsRunToday.length },
            { label: 'Available to Enable', value: agents.length - enabledAgents.length },
          ].map((s) => (
            <Card key={s.label} className="p-4">
              <p className="text-2xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">{s.value}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{s.label}</p>
            </Card>
          ))}
        </div>

        <Card>
          <CardHeader><CardTitle>Your AI Agents</CardTitle></CardHeader>
          <CardContent>
            {agents.length > 0 ? (
              <div className="space-y-3">
                {agents.map((agent: any) => (
                  <div
                    key={agent.id}
                    className="flex items-start justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg"
                  >
                    <div className="flex items-start gap-4 flex-1">
                      <span className="text-3xl">{getAgentIcon(agent.agent_type)}</span>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <p className="font-semibold text-sm text-gray-900 dark:text-gray-50">{agent.agent_name || agent.agent_type}</p>
                          <Badge variant={agent.is_enabled ? 'success' : 'gray'}>
                            {agent.is_enabled ? 'Active' : 'Inactive'}
                          </Badge>
                        </div>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mb-1.5 capitalize">
                          {agent.agent_type.replace(/_/g, ' ')} agent
                        </p>
                        <p className="text-xs text-gray-400 dark:text-gray-500">
                          Runs: {getFrequencyLabel(agent.run_frequency)} · Last run: {formatLastRun(agent.last_run_at)} · Total: {agent.run_count || 0}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => toggleAgent(agent.agent_type, agent.is_enabled)}
                        disabled={updateAgent.isPending}
                      >
                        {agent.is_enabled ? 'Disable' : 'Enable'}
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => router.push(`/settings/agents/${agent.id}`)}
                      >
                        Configure
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                icon={<Bot />}
                iconColor="gray"
                title="No agents configured"
                description="Agents will be automatically created when you complete onboarding."
              />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>About AI Agents</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-3 text-sm text-gray-500 dark:text-gray-400">
              <p>
                AI Agents are autonomous assistants that work in the background to help you manage your content creation workflow. Each agent has a specific purpose and runs on a schedule you can customize.
              </p>
              <p>
                Agents use advanced AI models to analyze data, generate insights, and take actions on your behalf. You can enable or disable any agent at any time.
              </p>
              <div className="rounded-lg bg-brand-50 dark:bg-brand-950/40 border border-brand-200 dark:border-brand-800 p-4 mt-2">
                <p className="font-medium text-brand-700 dark:text-brand-300 mb-1">Pro Tip</p>
                <p className="text-brand-600 dark:text-brand-400">
                  Enable all agents for the best experience! They work together to provide comprehensive insights and automation for your content strategy.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
