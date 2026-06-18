'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export default function DebugPage() {
  const router = useRouter();
  const [checks, setChecks] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(false);
  const [initialLoad, setInitialLoad] = useState(true);

  useEffect(() => {
    runChecks();
  }, []);

  const runChecks = async () => {
    setLoading(true);
    const results: Record<string, any> = {};

    // Check 1: Environment variables
    results.env = {
      apiUrl: process.env.NEXT_PUBLIC_API_URL || 'NOT SET',
      wsUrl: process.env.NEXT_PUBLIC_WS_URL || 'NOT SET',
      status: process.env.NEXT_PUBLIC_API_URL ? '✅' : '❌',
    };

    // Check 2: LocalStorage
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      const user = localStorage.getItem('user');
      results.localStorage = {
        hasToken: token ? '✅ Yes' : '❌ No',
        tokenPreview: token ? token.substring(0, 20) + '...' : 'None',
        hasUser: user ? '✅ Yes' : '❌ No',
        user: user ? JSON.parse(user) : null,
      };
    }

    // Check 3: Backend health
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/health`);
      results.backendHealth = {
        status: response.ok ? '✅ Online' : '❌ Offline',
        statusCode: response.status,
      };
    } catch (error: any) {
      results.backendHealth = {
        status: '❌ Cannot connect',
        error: error.message,
      };
    }

    // Check 4: Auth status
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
      if (token) {
        apiClient.setAccessToken(token);
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/me`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
        results.auth = {
          status: response.ok ? '✅ Authenticated' : '❌ Not authenticated',
          statusCode: response.status,
          data: response.ok ? await response.json() : null,
        };
      } else {
        results.auth = {
          status: '❌ No token',
        };
      }
    } catch (error: any) {
      results.auth = {
        status: '❌ Error',
        error: error.message,
      };
    }

    // Check 5: Goals API
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
      if (token) {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/goals`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
        results.goalsApi = {
          status: response.ok ? '✅ Working' : '❌ Failed',
          statusCode: response.status,
          data: response.ok ? await response.json() : await response.text(),
        };
      } else {
        results.goalsApi = {
          status: '⏭️ Skipped (no token)',
        };
      }
    } catch (error: any) {
      results.goalsApi = {
        status: '❌ Error',
        error: error.message,
      };
    }

    setChecks(results);
    setLoading(false);
    setInitialLoad(false);
  };

  // Initial loading state
  if (initialLoad && loading) {
    return (
      <div className="min-h-screen bg-background p-8">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-tech mx-auto mb-4" />
              <p className="text-muted-foreground">Running diagnostics...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const getStatusBadge = (status: string) => {
    if (status.includes('✅')) return <Badge variant="success">{status}</Badge>;
    if (status.includes('❌')) return <Badge variant="error">{status}</Badge>;
    if (status.includes('⏭️')) return <Badge variant="default">{status}</Badge>;
    return <Badge variant="warning">{status}</Badge>;
  };

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <Button variant="outline" onClick={() => router.push('/')} className="mb-4">
            ← Back to Home
          </Button>
          <h1 className="text-4xl font-bold gradient-text mb-2">🔧 Debug Dashboard</h1>
          <p className="text-muted-foreground">
            System diagnostics to help identify issues
          </p>
          <div className="flex gap-2 mt-4">
            <Button onClick={runChecks} disabled={loading}>
              {loading ? 'Running checks...' : 'Re-run Checks'}
            </Button>
            {checks.env?.status === '✅' && checks.backendHealth?.status?.includes('✅') && (
              <Badge variant="success" className="py-2 px-4">
                All Systems Operational
              </Badge>
            )}
          </div>
        </div>

        <div className="space-y-6">
          {/* Environment */}
          <Card>
            <CardHeader>
              <CardTitle>1. Environment Variables</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="bg-surface p-4 rounded-lg overflow-auto">
                {JSON.stringify(checks.env, null, 2)}
              </pre>
            </CardContent>
          </Card>

          {/* LocalStorage */}
          <Card>
            <CardHeader>
              <CardTitle>2. LocalStorage</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="bg-surface p-4 rounded-lg overflow-auto">
                {JSON.stringify(checks.localStorage, null, 2)}
              </pre>
            </CardContent>
          </Card>

          {/* Backend Health */}
          <Card>
            <CardHeader>
              <CardTitle>3. Backend Health</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="bg-surface p-4 rounded-lg overflow-auto">
                {JSON.stringify(checks.backendHealth, null, 2)}
              </pre>
            </CardContent>
          </Card>

          {/* Auth Status */}
          <Card>
            <CardHeader>
              <CardTitle>4. Authentication</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="bg-surface p-4 rounded-lg overflow-auto">
                {JSON.stringify(checks.auth, null, 2)}
              </pre>
            </CardContent>
          </Card>

          {/* Goals API */}
          <Card>
            <CardHeader>
              <CardTitle>5. Goals API</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="bg-surface p-4 rounded-lg overflow-auto text-xs">
                {JSON.stringify(checks.goalsApi, null, 2)}
              </pre>
            </CardContent>
          </Card>
        </div>

        <div className="mt-8 p-6 bg-surface rounded-lg">
          <h2 className="text-xl font-bold mb-4">Quick Fixes</h2>
          <div className="space-y-2 text-sm">
            <p>❌ Backend offline? → Start it: <code className="bg-background px-2 py-1 rounded">cd backend && python -m uvicorn app.main:app --reload --port 8000</code></p>
            <p>❌ No token? → <a href="/login" className="text-tech hover:underline">Login here</a></p>
            <p>❌ No user? → Create test user: <code className="bg-background px-2 py-1 rounded">cd backend && python create_test_user.py</code></p>
            <p>❌ API errors? → Check backend terminal for error logs</p>
          </div>
        </div>
      </div>
    </div>
  );
}
