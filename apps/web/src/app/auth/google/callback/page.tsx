'use client';

import { Suspense, useEffect, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { apiClient } from '@/lib/api';

interface CallbackResponse {
  user?: { id: string; email: string; name: string | null };
  access_token?: string;
}

function CallbackShell({ message }: { message: string }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="text-center">
        <div className="text-2xl font-semibold mb-2 text-gray-900 dark:text-gray-50">ContentFlow</div>
        <p className="text-gray-500 dark:text-gray-400">{message}</p>
      </div>
    </div>
  );
}

function GoogleCallbackInner() {
  const router = useRouter();
  const params = useSearchParams();
  const ranRef = useRef(false);
  const [message, setMessage] = useState('Signing you in…');

  useEffect(() => {
    if (ranRef.current) return;
    ranRef.current = true;

    const code = params.get('code');
    const state = params.get('state');
    const oauthError = params.get('error');

    if (oauthError) {
      router.replace(`/login?error=${encodeURIComponent(oauthError)}`);
      return;
    }
    if (!code || !state) {
      router.replace('/login?error=missing_oauth_params');
      return;
    }

    const url =
      `/api/v1/auth/google/callback` +
      `?code=${encodeURIComponent(code)}` +
      `&state=${encodeURIComponent(state)}`;

    apiClient
      .get<CallbackResponse>(url)
      .then((res) => {
        if (res?.access_token) {
          apiClient.setAccessToken(res.access_token);
          if (typeof window !== 'undefined') {
            localStorage.setItem('access_token', res.access_token);
            if (res.user) localStorage.setItem('user', JSON.stringify(res.user));
          }
        }
        router.replace('/');
      })
      .catch((err: unknown) => {
        const msg =
          err && typeof err === 'object' && 'message' in err
            ? String((err as { message: unknown }).message)
            : 'oauth_failed';
        setMessage('Login failed.');
        router.replace(`/login?error=${encodeURIComponent(msg)}`);
      });
  }, [params, router]);

  return <CallbackShell message={message} />;
}

// useSearchParams() must be wrapped in a Suspense boundary so Next can render
// the surrounding shell statically; otherwise the production build errors /
// forces the whole route into client-side rendering.
export default function GoogleCallbackPage() {
  return (
    <Suspense fallback={<CallbackShell message="Signing you in…" />}>
      <GoogleCallbackInner />
    </Suspense>
  );
}
