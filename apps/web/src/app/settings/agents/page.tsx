/**
 * AI Agents Settings Page
 * 
 * Configure and customize AI agents
 */

'use client';

import { useRouter } from 'next/navigation';
import { useAgentsList, useUpdateAgent } from '@/hooks/useAgents';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type { AgentType } from '@contentflow/api-client';

export default function AgentsSettingsPage() {
  const router = useRouter();
  const { data, isLoading, error, refetch } = useAgentsList();
  const updateAgent = useUpdateAgent();

  const toggleAgent = async (agentType: AgentType, currentEnabled: boolean) => {
    try {
      await updateAgent.mutateAsync({
        agentType,
        data: { is_enabled: !currentEnabled },
      });
    } catch (error) {
      console.error('Failed to toggle agent:', error);
    }
  };

  const getAgentIcon = (agentType: string) => {
    const icons: Record<string, string> = {
      niche_intelligence: '🧠',
      trend: '📈',
      analytics: '📊',
      competitor: '🔍',
      content_research: '💡',
      goal_reminder: '🎯',
      collaboration: '🤝',
      news_fetcher: '📰',
      tips_tricks: '💡',
      scheduling: '⏰',
      growth: '🚀',
      video_editor: '🎬',
      manipulation: '🎯',
    };
    return icons[agentType] || '🤖';
  };

  const getFrequencyLabel = (frequency: string) => {
    const labels: Record<string, string> = {
      hourly: 'Every hour',
      every_6h: 'Every 6 hours',
      daily: 'Daily',
      weekly: 'Weekly',
      on_demand: 'On demand',
      real_time: 'Real-time',
    };
    return labels[frequency] || frequency;
  };

  const formatLastRun = (lastRunAt: string | null) => {
    if (!lastRunAt) return 'Never';
    
    const date = new Date(lastRunAt);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-tech mx-auto mb-4" />
              <p className="text-muted-foreground">Loading agents...</p>
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
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="text-error text-5xl mb-4">⚠️</div>
              <h2 className="text-2xl font-bold mb-2">Failed to load agents</h2>
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

  const agents = data || [];
  const enabledAgents = agents.filter((a: any) => a.is_enabled);
  const agentsRunToday = agents.filter((a: any) => {
    if (!a.last_run_at) return false;
    const lastRun = new Date(a.last_run_at);
    const today = new Date();
    return lastRun.toDateString() === today.toDateString();
  });

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <Button variant="outline" onClick={() => router.push('/settings')} className="mb-4">
            ← Back to Settings
          </Button>
          <h1 className="text-4xl font-bold gradient-text">AI Agents</h1>
          <p className="text-muted-foreground mt-2">
            Configure your AI-powered automation agents
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold">
                {enabledAgents.length}/{agents.length}
              </div>
              <div className="text-sm text-muted-foreground">Active Agents</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold">
                {agentsRunToday.length}
              </div>
              <div className="text-sm text-muted-foreground">Agents Run Today</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold">
                {agents.length - enabledAgents.length}
              </div>
              <div className="text-sm text-muted-foreground">Available to Enable</div>
            </CardContent>
          </Card>
        </div>

        {/* Agents List */}
        <Card>
          <CardHeader>
            <CardTitle>Your AI Agents</CardTitle>
          </CardHeader>
          <CardContent>
            {agents.length > 0 ? (
              <div className="space-y-4">
                {agents.map((agent: any) => (
                  <div
                    key={agent.id}
                    className="flex items-start justify-between p-4 bg-surface rounded-lg"
                  >
                    <div className="flex items-start gap-4 flex-1">
                      <span className="text-3xl">{getAgentIcon(agent.agent_type)}</span>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <div className="font-semibold">{agent.agent_name || agent.agent_type}</div>
                          {agent.is_enabled ? (
                            <Badge variant="success">Active</Badge>
                          ) : (
                            <Badge variant="default">Inactive</Badge>
                          )}
                        </div>
                        <div className="text-sm text-muted-foreground mb-2">
                          {agent.agent_type.replace(/_/g, ' ')} agent
                        </div>
                        <div className="flex items-center gap-4 text-xs text-muted-foreground">
                          <span>Runs: {getFrequencyLabel(agent.run_frequency)}</span>
                          <span>•</span>
                          <span>Last run: {formatLastRun(agent.last_run_at)}</span>
                          <span>•</span>
                          <span>Total runs: {agent.run_count || 0}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => toggleAgent(agent.agent_type, agent.is_enabled)}
                        disabled={updateAgent.isPending}
                      >
                        {agent.is_enabled ? 'Disable' : 'Enable'}
                      </Button>
                      <Button 
                        variant="outline" 
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
              <div className="text-center py-12">
                <div className="text-6xl mb-4">🤖</div>
                <h3 className="text-xl font-semibold mb-2">No agents configured</h3>
                <p className="text-muted-foreground">
                  Agents will be automatically created when you complete onboarding
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Agent Info */}
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>About AI Agents</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4 text-sm text-muted-foreground">
              <p>
                AI Agents are autonomous assistants that work in the background to help you
                manage your content creation workflow. Each agent has a specific purpose and
                runs on a schedule you can customize.
              </p>
              <p>
                Agents use advanced AI models to analyze data, generate insights, and take
                actions on your behalf. You can enable or disable any agent at any time, and
                configure their settings to match your preferences.
              </p>
              <div className="bg-tech/10 border border-tech/20 rounded-lg p-4 mt-4">
                <div className="font-medium text-tech mb-2">💡 Pro Tip</div>
                <p className="text-tech">
                  Enable all agents for the best experience! They work together to provide
                  comprehensive insights and automation for your content strategy.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
