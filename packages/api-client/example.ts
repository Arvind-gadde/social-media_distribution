/**
 * ContentFlow API Client - Usage Examples
 * 
 * This file demonstrates how to use the API client in your application
 */

import {
  createApiClient,
  authApi,
  agentsApi,
  trendsApi,
  competitorsApi,
  goalsApi,
  ContentFlowApiError,
} from './src/index';

// ═══════════════════════════════════════════════════════════════════════════════
// 1. INITIALIZE CLIENT
// ═══════════════════════════════════════════════════════════════════════════════

const client = createApiClient({
  baseURL: process.env.API_URL || 'http://localhost:8000',
  timeout: 30000,
  retries: 3,
  onTokenExpired: () => {
    console.log('Token expired, redirecting to login...');
    // In real app: router.push('/login')
  },
  onUnauthorized: () => {
    console.error('Access denied');
    // In real app: toast.error('Access denied')
  },
});

// ═══════════════════════════════════════════════════════════════════════════════
// 2. AUTHENTICATION
// ═══════════════════════════════════════════════════════════════════════════════

async function exampleAuth() {
  try {
    // Login
    const { access_token, user } = await authApi.login({
      email: 'user@example.com',
      password: 'password123',
    });
    console.log('Logged in:', user.email);

    // Get current user
    const currentUser = await authApi.getCurrentUser();
    console.log('Current user:', currentUser);

    // Logout
    await authApi.logout();
    console.log('Logged out');
  } catch (error) {
    if (error instanceof ContentFlowApiError) {
      console.error('Auth error:', error.message, error.status);
    }
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 3. AGENTS
// ═══════════════════════════════════════════════════════════════════════════════

async function exampleAgents() {
  try {
    // List agent configurations
    const agents = await agentsApi.list();
    console.log('Agents:', agents.length);

    // Get agent status
    const status = await agentsApi.getStatus();
    console.log('Agent status:', status);

    // Trigger agent
    const run = await agentsApi.trigger({
      agent_type: 'trend_detection',
    });
    console.log('Agent run started:', run.id);

    // List insights
    const insights = await agentsApi.listInsights({
      page: 1,
      page_size: 20,
      unread_only: true,
      agent_type: 'trend_detection',
    });
    console.log('Unread insights:', insights.total);

    // Mark insight as read
    if (insights.items.length > 0) {
      await agentsApi.markAsRead(insights.items[0].id);
      console.log('Marked insight as read');
    }
  } catch (error) {
    if (error instanceof ContentFlowApiError) {
      console.error('Agent error:', error.message);
    }
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 4. TRENDS
// ═══════════════════════════════════════════════════════════════════════════════

async function exampleTrends() {
  try {
    // List rising trends
    const trends = await trendsApi.list({
      status: 'rising',
      min_score: 70,
      page: 1,
      page_size: 10,
    });
    console.log('Rising trends:', trends.total);

    // Get trend details
    if (trends.items.length > 0) {
      const trend = await trendsApi.get(trends.items[0].id);
      console.log('Trend:', trend.title, 'Score:', trend.trend_score);

      // Create content from trend
      const content = await trendsApi.createContent(trend.id, {
        title: 'My viral video based on this trend',
        content_type: 'reel',
        target_platforms: ['instagram', 'tiktok'],
      });
      console.log('Content created:', content.content_project_id);
    }

    // Get trend statistics
    const stats = await trendsApi.getStats();
    console.log('Trend stats:', stats);
  } catch (error) {
    if (error instanceof ContentFlowApiError) {
      console.error('Trend error:', error.message);
    }
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 5. COMPETITORS
// ═══════════════════════════════════════════════════════════════════════════════

async function exampleCompetitors() {
  try {
    // Add competitor
    const competitor = await competitorsApi.add({
      platform: 'instagram',
      platform_username: 'competitor_handle',
    });
    console.log('Added competitor:', competitor.id);

    // List competitors
    const competitors = await competitorsApi.list({
      platform: 'instagram',
      active_only: true,
    });
    console.log('Active competitors:', competitors.total);

    // Get competitor content
    if (competitors.items.length > 0) {
      const content = await competitorsApi.getContent(competitors.items[0].id, {
        min_viral_score: 50,
        page: 1,
      });
      console.log('Competitor posts:', content.total);

      // Get AI analysis
      const analysis = await competitorsApi.getAnalysis(competitors.items[0].id);
      console.log('Analysis:', analysis.content_strategy_summary);
      console.log('Strengths:', analysis.strengths);
      console.log('Opportunities:', analysis.opportunities_for_you);
    }
  } catch (error) {
    if (error instanceof ContentFlowApiError) {
      console.error('Competitor error:', error.message);
    }
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 6. GOALS
// ═══════════════════════════════════════════════════════════════════════════════

async function exampleGoals() {
  try {
    // Create goal
    const goal = await goalsApi.create({
      title: 'Post 5 reels this week',
      description: 'Weekly content goal',
      goal_type: 'content_count',
      period: 'weekly',
      target_value: 5,
      unit: 'posts',
      starts_at: new Date().toISOString(),
      ends_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
      reminder_enabled: true,
    });
    console.log('Goal created:', goal.id);

    // List goals
    const goals = await goalsApi.list({
      status: 'active',
    });
    console.log('Active goals:', goals.total);

    // Check in progress
    await goalsApi.checkIn(goal.id, {
      value_at_checkin: 3,
      note: 'Posted 3 reels so far, 2 more to go!',
    });
    console.log('Progress updated');

    // Get goal with computed fields
    const updatedGoal = await goalsApi.get(goal.id);
    console.log('Progress:', updatedGoal.progress_pct + '%');
    console.log('On track:', updatedGoal.is_on_track);
    console.log('Days remaining:', updatedGoal.days_remaining);

    // Get history
    const history = await goalsApi.getHistory(goal.id);
    console.log('Check-ins:', history.total_check_ins);
  } catch (error) {
    if (error instanceof ContentFlowApiError) {
      console.error('Goal error:', error.message);
    }
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 7. ERROR HANDLING
// ═══════════════════════════════════════════════════════════════════════════════

async function exampleErrorHandling() {
  try {
    // This will fail with 401 if not authenticated
    await agentsApi.list();
  } catch (error) {
    if (error instanceof ContentFlowApiError) {
      console.error('Error details:');
      console.error('  Message:', error.message);
      console.error('  Status:', error.status);
      console.error('  Code:', error.code);
      console.error('  Correlation ID:', error.correlationId);
      console.error('  Details:', error.details);
    } else {
      console.error('Unknown error:', error);
    }
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// RUN EXAMPLES
// ═══════════════════════════════════════════════════════════════════════════════

async function main() {
  console.log('ContentFlow API Client Examples\n');

  // Uncomment to run examples
  // await exampleAuth();
  // await exampleAgents();
  // await exampleTrends();
  // await exampleCompetitors();
  // await exampleGoals();
  // await exampleErrorHandling();
}

// Run if executed directly
if (require.main === module) {
  main().catch(console.error);
}
