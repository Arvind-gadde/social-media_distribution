'use client';

import * as React from 'react';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Eye, EyeOff, ArrowRight, WifiOff } from 'lucide-react';

import { apiClient } from '@/lib/api';
import { markSessionActive } from '@/lib/session';
import { safeInternalUrl } from '@/lib/safe-redirect';
import { cn } from '@/lib/utils';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Alert } from '@/components/ui/alert';

import { AuthShell, OrDivider } from '../_components/AuthShell';
import { GoogleIcon } from '../_components/GoogleIcon';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isNetworkError, setIsNetworkError] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [mfaRequired, setMfaRequired] = useState(false);
  const [mfaCode, setMfaCode] = useState('');

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsNetworkError(false);
    setLoading(true);
    try {
      const response = await apiClient.post<{
        mfa_required?: boolean;
        access_token?: string;
        user?: unknown;
      }>('/api/v1/auth/login', { email, password, mfa_code: mfaCode || undefined });

      // Account has MFA enabled — prompt for the code and resubmit.
      if (response?.mfa_required) {
        setMfaRequired(true);
        setLoading(false);
        return;
      }
      apiClient.setAccessToken(response.access_token ?? null);
      if (typeof window !== 'undefined') {
        if (response.access_token) localStorage.setItem('access_token', response.access_token);
        if (response.user) localStorage.setItem('user', JSON.stringify(response.user));
      }
      markSessionActive();
      router.push('/');
    } catch (err: any) {
      // No status = no HTTP response = network/connection failure
      if (err?.status === undefined) {
        setIsNetworkError(true);
      } else {
        setError(err?.message || 'Sign in failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleGoogle = () => {
    window.location.href = safeInternalUrl('/auth/google', '/login');
  };

  return (
    <AuthShell mounted={mounted}>
      <div className="mb-8">
        <h1 className="text-display-sm font-semibold text-gray-900 dark:text-gray-50 tracking-tight">
          Welcome back
        </h1>
        <p className="mt-2 text-text-md text-gray-600 dark:text-gray-400">
          Sign in to your content studio
        </p>
      </div>

      {isNetworkError && (
        <Alert
          variant="warning"
          className="mb-5"
          icon={<WifiOff className="h-5 w-5 text-warning-600 dark:text-warning-400" />}
          title="Cannot reach the server"
          description="Check your connection or try again in a moment."
        />
      )}
      {error && !isNetworkError && (
        <Alert variant="error" className="mb-5" description={error} />
      )}

      <form onSubmit={handleLogin} className="space-y-5" noValidate>
        <Input
          id="email"
          label="Email"
          type="email"
          autoComplete="email"
          placeholder="you@example.com"
          required
          disabled={loading}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={!!error && !isNetworkError}
        />

        <div className="flex w-full flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <label
              htmlFor="password"
              className="text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              Password
            </label>
            <button
              type="button"
              tabIndex={-1}
              className="text-sm font-semibold text-brand-700 hover:text-brand-800 dark:text-brand-400 dark:hover:text-brand-300 transition-colors"
            >
              Forgot?
            </button>
          </div>
          <div className="relative">
            <Input
              id="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              placeholder="Enter your password"
              required
              disabled={loading}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              error={!!error && !isNetworkError}
              className="pr-10"
            />
            <button
              type="button"
              tabIndex={-1}
              onClick={() => setShowPassword((s) => !s)}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              className={cn(
                'absolute right-3 top-1/2 -translate-y-1/2',
                'text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300',
                'transition-colors'
              )}
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
        </div>

        {mfaRequired && (
          <Input
            id="mfa-code"
            label="Authentication code"
            inputMode="numeric"
            autoComplete="one-time-code"
            placeholder="6-digit code or backup code"
            required
            disabled={loading}
            value={mfaCode}
            onChange={(e) => setMfaCode(e.target.value)}
          />
        )}

        <Checkbox
          id="remember-me"
          label="Remember me"
          checked={rememberMe}
          onCheckedChange={(v) => setRememberMe(v === true)}
          disabled={loading}
        />

        <Button
          type="submit"
          variant="primary"
          size="lg"
          className="w-full"
          loading={loading}
          disabled={loading || !email || !password || (mfaRequired && !mfaCode)}
          trailingIcon={!loading ? <ArrowRight className="h-4 w-4" /> : undefined}
        >
          {loading ? 'Signing in...' : mfaRequired ? 'Verify code' : 'Sign in'}
        </Button>
      </form>

      <OrDivider />

      <Button
        type="button"
        variant="secondary"
        size="lg"
        className="w-full"
        onClick={handleGoogle}
        leadingIcon={<GoogleIcon className="h-5 w-5" />}
      >
        Continue with Google
      </Button>

      <p className="text-center text-sm text-gray-600 dark:text-gray-400 mt-6">
        No account?{' '}
        <Link
          href="/register"
          className="font-semibold text-brand-700 hover:text-brand-800 dark:text-brand-400 dark:hover:text-brand-300 transition-colors"
        >
          Create one free
        </Link>
      </p>

      <p className="text-center text-xs text-gray-500 dark:text-gray-500 mt-8">
        By signing in you agree to our{' '}
        <span className="underline underline-offset-2 cursor-pointer hover:text-gray-700 dark:hover:text-gray-300 transition-colors">
          Terms
        </span>{' '}
        &amp;{' '}
        <span className="underline underline-offset-2 cursor-pointer hover:text-gray-700 dark:hover:text-gray-300 transition-colors">
          Privacy
        </span>
      </p>
    </AuthShell>
  );
}
