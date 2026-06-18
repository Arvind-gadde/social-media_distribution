# @contentflow/api-client

Production-grade TypeScript API client for ContentFlow platform.

## Features

- ✅ **Automatic retry logic** - 3 retries with exponential backoff
- ✅ **Token management** - Automatic access token refresh on 401
- ✅ **Error handling** - Comprehensive error transformation
- ✅ **Request tracing** - Correlation IDs for distributed tracing
- ✅ **TypeScript** - Full type safety
- ✅ **Singleton pattern** - Single client instance across app

## Installation

```bash
npm install @contentflow/api-client
```

## Usage

### Initialize Client

```typescript
import { createApiClient } from '@contentflow/api-client';

const client = createApiClient({
  baseURL: 'https://api.contentflow.ai',
  timeout: 30000,
  retries: 3,
  onTokenExpired: () => {
    // Redirect to login
    window.location.href = '/login';
  },
  onUnauthorized: () => {
    // Show permission denied message
    console.error('Access denied');
  },
});
```

### Authentication

```typescript
import { authApi } from '@contentflow/api-client';

// Login
const { access_token, user } = await authApi.login({
  email: 'user@example.com',
  password: 'password123',
});

// Register
const { access_token, user } = await authApi.register({
  email: 'user@example.com',
  password: 'password123',
  username: 'johndoe',
});

// Logout
await authApi.logout();
```

### Agents

```typescript
import { agentsApi } from '@contentflow/api-client';

// List agent configurations
const agents = await agentsApi.list();

// Trigger agent execution
const run = await agentsApi.trigger({
  agent_type: 'trend_detection',
});

// Get agent status
const status = await agentsApi.getStatus();

// List insights
const insights = await agentsApi.listInsights({
  page: 1,
  page_size: 20,
  unread_only: true,
});

// Mark insight as read
await agentsApi.markAsRead(insightId);
```

### Trends

```typescript
import { trendsApi } from '@contentflow/api-client';

// List trends
const trends = await trendsApi.list({
  status: 'rising',
  min_score: 70,
  page: 1,
});

// Get trend details
const trend = await trendsApi.get(trendId);

// Create content from trend
const content = await trendsApi.createContent(trendId, {
  title: 'My viral video',
  content_type: 'reel',
});

// Get trend statistics
const stats = await trendsApi.getStats();
```

### Competitors

```typescript
import { competitorsApi } from '@contentflow/api-client';

// List competitors
const competitors = await competitorsApi.list({
  platform: 'instagram',
  active_only: true,
});

// Add competitor
const competitor = await competitorsApi.add({
  platform: 'instagram',
  platform_username: 'competitor_handle',
});

// Get competitor content
const content = await competitorsApi.getContent(competitorId, {
  min_viral_score: 50,
});

// Get AI analysis
const analysis = await competitorsApi.getAnalysis(competitorId);

// Remove competitor
await competitorsApi.remove(competitorId);
```

### Goals

```typescript
import { goalsApi } from '@contentflow/api-client';

// List goals
const goals = await goalsApi.list({
  status: 'active',
});

// Create goal
const goal = await goalsApi.create({
  title: 'Post 5 reels this week',
  goal_type: 'content_count',
  period: 'weekly',
  target_value: 5,
  unit: 'posts',
  starts_at: '2025-01-01T00:00:00Z',
  ends_at: '2025-01-07T23:59:59Z',
});

// Update goal
await goalsApi.update(goalId, {
  status: 'completed',
});

// Check in progress
await goalsApi.checkIn(goalId, {
  value_at_checkin: 3,
  note: 'Posted 3 reels so far',
});

// Get history
const history = await goalsApi.getHistory(goalId);

// Delete goal
await goalsApi.delete(goalId);
```

## Error Handling

All API calls throw `ContentFlowApiError` on failure:

```typescript
import { ContentFlowApiError } from '@contentflow/api-client';

try {
  await agentsApi.trigger();
} catch (error) {
  if (error instanceof ContentFlowApiError) {
    console.error('API Error:', error.message);
    console.error('Status:', error.status);
    console.error('Code:', error.code);
    console.error('Correlation ID:', error.correlationId);
  }
}
```

## TypeScript Support

Full TypeScript support with exported types:

```typescript
import type {
  Agent,
  AgentInsight,
  Trend,
  Competitor,
  Goal,
  PaginatedResponse,
} from '@contentflow/api-client';
```

## Development

```bash
# Build
npm run build

# Watch mode
npm run dev

# Type check
npm run type-check

# Clean
npm run clean
```

## License

MIT
