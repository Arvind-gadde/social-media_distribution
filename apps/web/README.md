# ContentFlow Web Dashboard

Next.js 15 dashboard for ContentFlow AI platform.

## Features

- ✅ Next.js 15 with App Router
- ✅ TypeScript with strict mode
- ✅ Tailwind CSS v4
- ✅ React Query v5 for data fetching
- ✅ Zustand for state management
- ✅ Production-grade error handling
- ✅ Comprehensive testing with Vitest
- ✅ API client integration

## Getting Started

### Prerequisites

- Node.js 18+
- npm 9+
- Backend API running on http://localhost:8000

### Installation

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.example .env.local

# Update .env.local with your values
```

### Development

```bash
# Start development server
npm run dev

# Open http://localhost:3000
```

### Testing

```bash
# Run tests
npm run test

# Run tests with UI
npm run test:ui

# Run tests with coverage
npm run test:coverage

# Type check
npm run type-check
```

### Building

```bash
# Build for production
npm run build

# Start production server
npm start
```

## Project Structure

```
src/
├── app/                    # Next.js App Router pages
│   ├── layout.tsx         # Root layout
│   ├── page.tsx           # Home page
│   ├── providers.tsx      # React Query provider
│   └── globals.css        # Global styles
├── components/            # React components
│   ├── ui/               # shadcn/ui components
│   ├── agents/           # Agent components
│   ├── trends/           # Trend components
│   ├── competitors/      # Competitor components
│   └── goals/            # Goal components
├── hooks/                # Custom React hooks
│   ├── useAgents.ts      # Agent hooks
│   ├── useTrends.ts      # Trend hooks
│   ├── useCompetitors.ts # Competitor hooks
│   └── useGoals.ts       # Goal hooks
├── lib/                  # Utility libraries
│   ├── api.ts            # API client setup
│   ├── query-client.ts   # React Query config
│   └── utils.ts          # Utility functions
└── __tests__/            # Test files
```

## API Integration

The app uses `@contentflow/api-client` package for all API calls:

```typescript
import { agentsApi, trendsApi } from '@contentflow/api-client';

// List agents
const agents = await agentsApi.list();

// List trends
const trends = await trendsApi.list({ status: 'rising' });
```

## React Query Hooks

Custom hooks for data fetching:

```typescript
import { useAgentInsights, useTrends, useGoals } from '@/hooks';

// In component
const { data, isLoading, error } = useAgentInsights({
  unread_only: true,
});
```

## Styling

Uses Tailwind CSS with custom theme:

```typescript
// Dark mode colors
background: '#0f172a'  // Deep slate
surface: '#1e293b'

// Niche colors
fitness: '#f97316'     // Orange
tech: '#06b6d4'        // Cyan
finance: '#10b981'     // Green
```

## Environment Variables

```bash
# Required
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret-key

# Optional
NEXT_PUBLIC_POSTHOG_KEY=
NEXT_PUBLIC_SENTRY_DSN=
```

## Scripts

| Script | Description |
|--------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm start` | Start production server |
| `npm run lint` | Run ESLint |
| `npm run type-check` | Run TypeScript compiler |
| `npm run test` | Run tests |
| `npm run test:ui` | Run tests with UI |
| `npm run test:coverage` | Run tests with coverage |

## Features Implemented

### Phase 16.2.1 - Foundation ✅
- [x] Next.js app structure
- [x] TypeScript configuration
- [x] Tailwind CSS setup
- [x] API client integration
- [x] React Query setup
- [x] Custom hooks (agents, trends, competitors, goals)
- [x] Home page with agent insights
- [x] Utility functions
- [x] Test setup

### Phase 16.2.2 - Core Features (Next)
- [ ] Agent insights feed page
- [ ] Trends dashboard
- [ ] Competitor tracking
- [ ] Goals & progress
- [ ] Agent management

### Phase 16.2.3 - Advanced Features (Next)
- [ ] WebSocket integration
- [ ] Real-time updates
- [ ] Command bar (Cmd+K)
- [ ] Toast notifications

## Contributing

1. Create feature branch
2. Make changes
3. Run tests: `npm run test`
4. Type check: `npm run type-check`
5. Submit PR

## License

MIT
