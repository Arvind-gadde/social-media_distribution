'use client';

import * as React from 'react';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Eye, EyeOff, ArrowRight, Check, X, WifiOff } from 'lucide-react';

import { authApi } from '@contentflow/api-client';
import { apiClient } from '@/lib/api';
import { markSessionActive } from '@/lib/session';
import { safeInternalUrl } from '@/lib/safe-redirect';
import { cn } from '@/lib/utils';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Alert } from '@/components/ui/alert';

import { AuthShell, OrDivider } from '../_components/AuthShell';
import { GoogleIcon } from '../_components/GoogleIcon';

const PWD_RULES = [
  { key: 'length',  label: 'At least 8 characters', test: (p: string) => p.length >= 8 },
  { key: 'upper',   label: 'Uppercase letter (A–Z)', test: (p: string) => /[A-Z]/.test(p) },
  { key: 'lower',   label: 'Lowercase letter (a–z)', test: (p: string) => /[a-z]/.test(p) },
  { key: 'number',  label: 'Number (0–9)',           test: (p: string) => /[0-9]/.test(p) },
  { key: 'special', label: 'Special character',      test: (p: string) => /[^A-Za-z0-9]/.test(p) },
] as const;

export default function RegisterPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [showRules, setShowRules] = useState(false);
  const [error, setError] = useState('');
  const [isNetworkError, setIsNetworkError] = useState(false);
  const [loading, setLoading] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const rules = PWD_RULES.map((r) => ({ ...r, met: r.test(password) }));
  const allMet = rules.every((r) => r.met);
  const pwdMatch = password === confirmPassword;
  const canSubmit =
    name.trim().length >= 2 && email.length > 0 && allMet && pwdMatch && !loading;

  const pwdStrength = rules.filter((r) => r.met).length;
  const strengthLabel =
    pwdStrength <= 1
      ? 'Weak'
      : pwdStrength <= 3
      ? 'Fair'
      : pwdStrength === 4
      ? 'Good'
      : 'Strong';
  const strengthColor =
    pwdStrength <= 1
      ? 'bg-error-500'
      : pwdStrength <= 3
      ? 'bg-warning-500'
      : pwdStrength === 4
      ? 'bg-blue-500'
      : 'bg-success-500';

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsNetworkError(false);

    if (name.trim().length < 2) {
      setError('Name must be at least 2 characters.');
      return;
    }
    if (!pwdMatch) {
      setError('Passwords do not match.');
      return;
    }
    if (!allMet) {
      setError('Password does not meet all requirements.');
      return;
    }

    setLoading(true);
    try {
      const response = await authApi.register({
        email,
        password,
        name: name.trim(),
      });
      apiClient.setAccessToken(response.access_token);
      if (typeof window !== 'undefined') {
        localStorage.setItem('access_token', response.access_token);
        localStorage.setItem('user', JSON.stringify(response.user));
      }
      markSessionActive();
      router.push('/');
    } catch (err: any) {
      if (err?.status === undefined) {
        setIsNetworkError(true);
      } else {
        setError(err?.message || 'Registration failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleGoogle = () => {
    window.location.href = safeInternalUrl('/auth/google', '/register');
  };

  return (
    <AuthShell mounted={mounted}>
      <div className="mb-7">
        <h1 className="text-display-sm font-semibold text-gray-900 dark:text-gray-50 tracking-tight">
          Create account
        </h1>
        <p className="mt-2 text-text-md text-gray-600 dark:text-gray-400">
          Join 12,000+ creators on ContentFlow
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

      <form onSubmit={handleRegister} className="space-y-5" noValidate>
        <Input
          id="name"
          label="Full name"
          type="text"
          autoComplete="name"
          placeholder="Alex Johnson"
          required
          disabled={loading}
          value={name}
          onChange={(e) => setName(e.target.value)}
          error={!!error && name.trim().length < 2}
        />

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
        />

        {/* Password */}
        <div className="flex w-full flex-col gap-1.5">
          <label
            htmlFor="password"
            className="text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Password
          </label>
          <div className="relative">
            <Input
              id="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              placeholder="Create a strong password"
              required
              disabled={loading}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onFocus={() => setShowRules(true)}
              className="pr-10"
            />
            <button
              type="button"
              tabIndex={-1}
              onClick={() => setShowPassword((s) => !s)}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 transition-colors"
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>

          {password && (
            <div className="space-y-2 pt-1">
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1.5 rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
                  <div
                    className={cn(
                      'h-full rounded-full transition-all duration-300',
                      strengthColor
                    )}
                    style={{ width: `${(pwdStrength / 5) * 100}%` }}
                  />
                </div>
                <span className="text-xs font-medium text-gray-600 dark:text-gray-400 w-12 text-right">
                  {strengthLabel}
                </span>
              </div>

              {showRules && (
                <div className="grid grid-cols-1 gap-1 p-3 rounded-lg bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800">
                  {rules.map(({ key, label, met }) => (
                    <div
                      key={key}
                      className={cn(
                        'flex items-center gap-2 text-xs transition-colors',
                        met
                          ? 'text-success-700 dark:text-success-400'
                          : 'text-gray-500 dark:text-gray-500'
                      )}
                    >
                      {met ? (
                        <Check className="h-3.5 w-3.5 text-success-600 dark:text-success-400 shrink-0" />
                      ) : (
                        <X className="h-3.5 w-3.5 text-gray-300 dark:text-gray-600 shrink-0" />
                      )}
                      {label}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Confirm password */}
        <div className="flex w-full flex-col gap-1.5">
          <label
            htmlFor="confirm"
            className="text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Confirm password
          </label>
          <div className="relative">
            <Input
              id="confirm"
              type={showConfirm ? 'text' : 'password'}
              autoComplete="new-password"
              placeholder="Repeat your password"
              required
              disabled={loading}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              error={!!confirmPassword && !pwdMatch}
              className="pr-16"
            />
            <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
              {confirmPassword && (
                <span aria-hidden="true">
                  {pwdMatch ? (
                    <Check className="h-4 w-4 text-success-600 dark:text-success-400" />
                  ) : (
                    <X className="h-4 w-4 text-error-500 dark:text-error-400" />
                  )}
                </span>
              )}
              <button
                type="button"
                tabIndex={-1}
                onClick={() => setShowConfirm((s) => !s)}
                aria-label={showConfirm ? 'Hide password' : 'Show password'}
                className="text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 transition-colors"
              >
                {showConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>
          {confirmPassword && !pwdMatch && (
            <p className="text-xs text-error-600 dark:text-error-400 flex items-center gap-1">
              <X className="h-3 w-3" /> Passwords do not match
            </p>
          )}
          {confirmPassword && pwdMatch && (
            <p className="text-xs text-success-700 dark:text-success-400 flex items-center gap-1">
              <Check className="h-3 w-3" /> Passwords match
            </p>
          )}
        </div>

        <Button
          type="submit"
          variant="primary"
          size="lg"
          className="w-full"
          loading={loading}
          disabled={!canSubmit}
          trailingIcon={!loading ? <ArrowRight className="h-4 w-4" /> : undefined}
        >
          {loading ? 'Creating account...' : 'Create account'}
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
        Already have an account?{' '}
        <Link
          href="/login"
          className="font-semibold text-brand-700 hover:text-brand-800 dark:text-brand-400 dark:hover:text-brand-300 transition-colors"
        >
          Sign in
        </Link>
      </p>

      <p className="text-center text-xs text-gray-500 dark:text-gray-500 mt-6">
        By creating an account you agree to our{' '}
        <span className="underline underline-offset-2 cursor-pointer hover:text-gray-700 dark:hover:text-gray-300 transition-colors">
          Terms
        </span>{' '}
        &amp;{' '}
        <span className="underline underline-offset-2 cursor-pointer hover:text-gray-700 dark:hover:text-gray-300 transition-colors">
          Privacy Policy
        </span>
      </p>
    </AuthShell>
  );
}
