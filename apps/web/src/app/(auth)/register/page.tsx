'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { authApi } from '@contentflow/api-client';
import { apiClient } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function RegisterPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPasswordRequirements, setShowPasswordRequirements] = useState(false);

  // Password strength validation
  const passwordRequirements = {
    length: password.length >= 8,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    number: /[0-9]/.test(password),
    special: /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(password),
  };

  const allRequirementsMet = Object.values(passwordRequirements).every(Boolean);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validation
    if (name.trim().length < 2) {
      setError('Name must be at least 2 characters');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (!allRequirementsMet) {
      setError('Password does not meet all requirements');
      return;
    }

    setLoading(true);

    try {
      const response = await authApi.register({
        email,
        password,
        name,
      });
      
      // Store access token
      apiClient.setAccessToken(response.access_token);
      
      // Store in localStorage for persistence
      if (typeof window !== 'undefined') {
        localStorage.setItem('access_token', response.access_token);
        localStorage.setItem('user', JSON.stringify(response.user));
      }
      
      // Redirect to home
      router.push('/');
    } catch (err: any) {
      console.error('Registration error:', err);
      setError(err.message || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="text-4xl mb-4">⚡</div>
          <CardTitle className="text-3xl gradient-text">ContentFlow AI</CardTitle>
          <p className="text-muted-foreground mt-2">
            Create your account
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleRegister} className="space-y-4">
            {error && (
              <div className="bg-error/10 border border-error text-error px-4 py-3 rounded-md text-sm">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="name" className="block text-sm font-medium mb-2">
                Full Name
              </label>
              <input
                id="name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 bg-surface rounded-md border border-input focus:outline-none focus:ring-2 focus:ring-tech"
                placeholder="John Doe"
                required
                disabled={loading}
              />
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium mb-2">
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 bg-surface rounded-md border border-input focus:outline-none focus:ring-2 focus:ring-tech"
                placeholder="you@example.com"
                required
                disabled={loading}
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium mb-2">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onFocus={() => setShowPasswordRequirements(true)}
                className="w-full px-3 py-2 bg-surface rounded-md border border-input focus:outline-none focus:ring-2 focus:ring-tech"
                placeholder="Enter your password"
                required
                disabled={loading}
              />
              
              {/* Password Requirements */}
              {showPasswordRequirements && password && (
                <div className="mt-2 p-3 bg-surface rounded-md border border-border text-xs space-y-1">
                  <p className="font-medium mb-2">Password must contain:</p>
                  <div className={`flex items-center gap-2 ${passwordRequirements.length ? 'text-success' : 'text-muted-foreground'}`}>
                    <span>{passwordRequirements.length ? '✓' : '○'}</span>
                    <span>At least 8 characters</span>
                  </div>
                  <div className={`flex items-center gap-2 ${passwordRequirements.uppercase ? 'text-success' : 'text-muted-foreground'}`}>
                    <span>{passwordRequirements.uppercase ? '✓' : '○'}</span>
                    <span>One uppercase letter (A-Z)</span>
                  </div>
                  <div className={`flex items-center gap-2 ${passwordRequirements.lowercase ? 'text-success' : 'text-muted-foreground'}`}>
                    <span>{passwordRequirements.lowercase ? '✓' : '○'}</span>
                    <span>One lowercase letter (a-z)</span>
                  </div>
                  <div className={`flex items-center gap-2 ${passwordRequirements.number ? 'text-success' : 'text-muted-foreground'}`}>
                    <span>{passwordRequirements.number ? '✓' : '○'}</span>
                    <span>One number (0-9)</span>
                  </div>
                  <div className={`flex items-center gap-2 ${passwordRequirements.special ? 'text-success' : 'text-muted-foreground'}`}>
                    <span>{passwordRequirements.special ? '✓' : '○'}</span>
                    <span>One special character (!@#$%^&*...)</span>
                  </div>
                </div>
              )}
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium mb-2">
                Confirm Password
              </label>
              <input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-3 py-2 bg-surface rounded-md border border-input focus:outline-none focus:ring-2 focus:ring-tech"
                placeholder="Confirm your password"
                required
                disabled={loading}
              />
              {confirmPassword && password !== confirmPassword && (
                <p className="text-xs text-error mt-1">Passwords do not match</p>
              )}
            </div>

            <Button
              type="submit"
              className="w-full"
              disabled={loading || !allRequirementsMet || password !== confirmPassword}
            >
              {loading ? 'Creating account...' : 'Create Account'}
            </Button>

            <div className="text-center text-sm text-muted-foreground">
              Already have an account?{' '}
              <Link href="/login" className="text-tech hover:underline">
                Sign in
              </Link>
            </div>
          </form>

          <div className="mt-6 pt-6 border-t border-border">
            <p className="text-xs text-center text-muted-foreground mb-4">
              Or continue with
            </p>
            <Button
              variant="outline"
              className="w-full"
              onClick={() => {
                // TODO: Implement Google OAuth
                alert('Google OAuth coming soon!');
              }}
            >
              <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
                <path
                  fill="currentColor"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="currentColor"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="currentColor"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                />
                <path
                  fill="currentColor"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
              Continue with Google
            </Button>
          </div>

          <p className="text-xs text-center text-muted-foreground mt-6">
            By creating an account, you agree to our{' '}
            <Link href="/terms" className="text-tech hover:underline">
              Terms of Service
            </Link>{' '}
            and{' '}
            <Link href="/privacy" className="text-tech hover:underline">
              Privacy Policy
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
