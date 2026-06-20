'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { RefreshCw } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Spinner } from '@/components/ui/spinner';

export default function DebugPage() {
  const router = useRouter();
  const [checks, setChecks] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(false);
  const [initialLoad, setInitialLoad] = useState(true);

  useEffect(() => { runChecks(); }, []);

  const runChecks = async () => {
    setLoading(true);
    const results: Record<string, any> = {};

    try {
      results.env = {
        apiUrl: process.env.NEXT_PUBLIC_API_URL || 'NOT SET',
        wsUrl: process.env.NEXT_PUBLIC_WS_URL || 'NOT SET',
        status: process.env.NEXT_PUBLIC_API_URL ? '✅' : '❌',
      };

      if (typeof window !== 'undefined') {
        const token = localStorage.getItem('access_token');
        const rawUser = localStorage.getItem('user');
        let userValid = false;
        if (rawUser) {
          try {
            JSON.parse(rawUser);
            userValid = true;
          } catch {
            userValid = false;
          }
        }
        // Presence only — never render the JWT or user PII into the DOM.
        results.localStorage = {
          hasToken: token ? '✅ Yes' : '❌ No',
          hasUser: rawUser ? (userValid ? '✅ Yes' : '⚠️ Present but invalid JSON') : '❌ No',
        };
      }

      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/health`);
        results.backendHealth = { status: response.ok ? '✅ Online' : '❌ Offline', statusCode: response.status };
      } catch (error: any) {
        results.backendHealth = { status: '❌ Cannot connect', error: error.message };
      }

      const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;

      try {
        if (token) {
          apiClient.setAccessToken(token);
          const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/me`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          // Status only — do not dump the response body (it contains PII).
          results.auth = {
            status: response.ok ? '✅ Authenticated' : '❌ Not authenticated',
            statusCode: response.status,
          };
        } else {
          results.auth = { status: '❌ No token' };
        }
      } catch (error: any) {
        results.auth = { status: '❌ Error', error: error.message };
      }

      try {
        if (token) {
          const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/goals`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          results.goalsApi = {
            status: response.ok ? '✅ Working' : '❌ Failed',
            statusCode: response.status,
          };
        } else {
          results.goalsApi = { status: '⏭️ Skipped (no token)' };
        }
      } catch (error: any) {
        results.goalsApi = { status: '❌ Error', error: error.message };
      }

      setChecks(results);
    } finally {
      // Always clear the loading flags so a thrown error can never strand the
      // page on the full-screen spinner forever.
      setLoading(false);
      setInitialLoad(false);
    }
  };

  if (initialLoad && loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Spinner size="lg" color="primary" />
      </div>
    );
  }

  const getStatusBadge = (status: string) => {
    if (status.includes('✅')) return <Badge variant="success">{status}</Badge>;
    if (status.includes('❌')) return <Badge variant="error">{status}</Badge>;
    if (status.includes('⏭️')) return <Badge variant="gray">{status}</Badge>;
    return <Badge variant="warning">{status}</Badge>;
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-10 space-y-6 animate-fade-in">
        <header className="space-y-4">
          <Button variant="secondary" onClick={() => router.push('/')}>← Back to Home</Button>
          <div className="space-y-1">
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-50">🔧 Debug Dashboard</h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">System diagnostics to help identify issues</p>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="primary" leadingIcon={<RefreshCw className="h-4 w-4" />} onClick={runChecks} disabled={loading} loading={loading}>
              {loading ? 'Running checks...' : 'Re-run Checks'}
            </Button>
            {checks.env?.status === '✅' && checks.backendHealth?.status?.includes('✅') && (
              <Badge variant="success">All Systems Operational</Badge>
            )}
          </div>
        </header>

        <div className="space-y-4">
          {[
            { n: 1, label: 'Environment Variables', key: 'env' },
            { n: 2, label: 'LocalStorage', key: 'localStorage' },
            { n: 3, label: 'Backend Health', key: 'backendHealth' },
            { n: 4, label: 'Authentication', key: 'auth' },
            { n: 5, label: 'Goals API', key: 'goalsApi' },
          ].map(({ n, label, key }) => (
            <Card key={key}>
              <CardHeader><CardTitle>{n}. {label}</CardTitle></CardHeader>
              <CardContent>
                <pre className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg overflow-auto text-xs text-gray-900 dark:text-gray-50">
                  {JSON.stringify(checks[key], null, 2)}
                </pre>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-base font-semibold text-gray-900 dark:text-gray-50 mb-3">Quick Fixes</h2>
          <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
            <p>❌ Backend offline? → Start it: <code className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 px-2 py-0.5 rounded text-xs">cd backend && python -m uvicorn app.main:app --reload --port 8000</code></p>
            <p>❌ No token? → <a href="/login" className="text-brand-600 dark:text-brand-400 hover:underline">Login here</a></p>
            <p>❌ No user? → Create test user: <code className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 px-2 py-0.5 rounded text-xs">cd backend && python create_test_user.py</code></p>
            <p>❌ API errors? → Check backend terminal for error logs</p>
          </div>
        </div>
      </div>
    </div>
  );
}
