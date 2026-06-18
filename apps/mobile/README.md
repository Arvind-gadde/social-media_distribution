# @contentflow/mobile

Expo Router shell for ContentFlow on iOS / Android.

## Stack
- Expo SDK 52, React Native 0.76 (new architecture)
- expo-router (typed routes)
- @tanstack/react-query for server state
- zustand for session
- expo-secure-store for token vault
- expo-local-authentication for biometric unlock

## Develop
```sh
pnpm --filter @contentflow/mobile dev
```

Set `EXPO_PUBLIC_API_URL` to the backend base URL (default `http://localhost:8000`).

## Layout
- `app/_layout.tsx` — root stack + query client
- `app/(auth)/login.tsx` — credential or biometric sign-in
- `app/(tabs)/*` — Dashboard, Feed, Schedule, Settings
- `lib/api.ts` — typed `fetch` wrapper with secure-store token attach
- `lib/auth.ts` — zustand session store + biometric unlock

## What's NOT here yet
- Push notifications (expo-notifications)
- Offline draft queue
- Schedule timeline (server data only)
- Studio editor (web-only for now)
