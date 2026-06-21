# ContentFlow — Android (Capacitor wrap)

Goal: ship an Android app reusing 100% of the Next.js web app, no separate codebase.
Because the web app is **Next.js App Router (SSR)** — not a static export — the pragmatic wrap is a
**Capacitor WebView shell that points at the deployed site** (`server.url`). The app is a native
container; the UI is the live web app. This is the fastest path and keeps one codebase.

> Requires Android Studio + Android SDK (not available in the dev container — run these on a machine
> with the SDK installed) and a deployed HTTPS URL (see [DEPLOY.md](DEPLOY.md)).

## One-time setup (in `apps/web`)
```bash
cd apps/web
pnpm add @capacitor/core @capacitor/cli @capacitor/android
npx cap init ContentFlow com.contentflow.app --web-dir=public
```

Create `apps/web/capacitor.config.ts`:
```ts
import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.contentflow.app',
  appName: 'ContentFlow',
  // SSR app: load the deployed site rather than bundling static assets.
  server: {
    url: 'https://your-domain.com',
    cleartext: false,
  },
};
export default config;
```

## Build the APK
```bash
cd apps/web
npx cap add android
npx cap sync android
npx cap open android         # opens Android Studio -> Build > Generate Signed Bundle/APK
# or headless:
cd android && ./gradlew assembleRelease
```

## Publish
- Google Play: **$25 one-time** developer fee. Upload the signed AAB/APK.
- iOS deferred (Apple $99/yr) per plan.

## Notes / future
- For deeper native features (push, camera) add the matching Capacitor plugins and a small
  client-side bridge; the WebView shell already gives you the full app today.
- If we later want offline/static screens, evaluate `next export` for the marketing/auth shell only;
  the authenticated app stays server-backed.
