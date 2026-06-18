/**
 * Navigation Component
 * 
 * Main navigation for the dashboard with WebSocket status and command bar
 */

'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { WebSocketStatus } from './WebSocketStatus';
import { useCommandBarContext } from '@/lib/command-bar-context';
import { authApi } from '@contentflow/api-client';
import { toast } from '@/lib/toast';

const navItems = [
  { href: '/', label: 'Home', icon: '🏠' },
  { href: '/insights', label: 'Insights', icon: '💡' },
  { href: '/trends', label: 'Trends', icon: '🔥' },
  { href: '/goals', label: 'Goals', icon: '🎯' },
];

export function Navigation() {
  const pathname = usePathname();
  const router = useRouter();
  const { open } = useCommandBarContext();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [user, setUser] = useState<any>(null);
  const [mounted, setMounted] = useState(false);

  // Get user from localStorage after mount to prevent hydration issues
  useEffect(() => {
    setMounted(true);
    if (typeof window !== 'undefined') {
      const userStr = localStorage.getItem('user');
      if (userStr) {
        try {
          setUser(JSON.parse(userStr));
        } catch (e) {
          console.error('Failed to parse user from localStorage', e);
        }
      }
    }
  }, []);

  const handleLogout = async () => {
    try {
      setIsLoggingOut(true);
      await authApi.logout();
      
      // Clear local storage
      if (typeof window !== 'undefined') {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
      }
      
      toast.success('Logged out successfully');
      router.push('/login');
      router.refresh();
    } catch (error) {
      console.error('Logout error:', error);
      // Even if API fails, clear local storage and redirect
      if (typeof window !== 'undefined') {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
      }
      router.push('/login');
      router.refresh();
    } finally {
      setIsLoggingOut(false);
      setShowUserMenu(false);
    }
  };

  const userInitial = user?.name?.charAt(0).toUpperCase() || user?.email?.charAt(0).toUpperCase() || 'U';

  if (!mounted) {
    return null; // Prevent hydration mismatch
  }

  return (
    <nav className="glass border-b border-white/10 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2">
            <span className="text-2xl">⚡</span>
            <span className="font-bold text-xl gradient-text">ContentFlow</span>
          </Link>

          {/* Nav Items */}
          <div className="flex items-center gap-1">
            {navItems.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    'flex items-center gap-2 px-4 py-2 rounded-lg transition-colors',
                    isActive
                      ? 'bg-tech/20 text-tech'
                      : 'text-muted-foreground hover:bg-surface hover:text-foreground'
                  )}
                >
                  <span>{item.icon}</span>
                  <span className="font-medium">{item.label}</span>
                </Link>
              );
            })}
          </div>

          {/* Right Side */}
          <div className="flex items-center gap-4">
            {/* Command Bar Trigger */}
            <button
              type="button"
              onClick={() => {
                console.log('Search button clicked!');
                open();
              }}
              className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface/50 border border-white/10 text-sm text-muted-foreground hover:text-foreground hover:border-tech/50 transition-colors cursor-pointer"
            >
              <span>🔍</span>
              <span>Search</span>
              <kbd className="hidden lg:inline-flex h-5 select-none items-center gap-1 rounded border border-white/10 bg-background/50 px-1.5 font-mono text-xs">
                ⌘K
              </kbd>
            </button>

            {/* User Menu */}
            <div className="relative">
              <button 
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="w-8 h-8 rounded-full bg-tech flex items-center justify-center text-white font-bold hover:scale-110 transition-transform"
              >
                {userInitial}
              </button>

              {/* Dropdown Menu */}
              {showUserMenu && (
                <>
                  {/* Backdrop */}
                  <div 
                    className="fixed inset-0 z-40" 
                    onClick={() => setShowUserMenu(false)}
                  />
                  
                  {/* Menu */}
                  <div className="absolute right-0 mt-2 w-64 glass rounded-lg border border-white/10 shadow-xl z-50">
                    <div className="p-4 border-b border-white/10">
                      <p className="font-medium text-foreground truncate">{user?.name || 'User'}</p>
                      <p className="text-sm text-muted-foreground truncate">{user?.email}</p>
                      {user?.id && (
                        <p className="text-xs text-muted-foreground mt-1 font-mono truncate">
                          ID: {user.id.substring(0, 8)}...
                        </p>
                      )}
                    </div>
                    
                    <div className="p-2">
                      <button
                        onClick={() => {
                          router.push('/settings');
                          setShowUserMenu(false);
                        }}
                        className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left text-muted-foreground hover:bg-surface hover:text-foreground transition-colors"
                      >
                        <span>⚙️</span>
                        <span>Settings</span>
                      </button>
                      
                      <button
                        onClick={handleLogout}
                        disabled={isLoggingOut}
                        className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left text-error hover:bg-error/10 transition-colors disabled:opacity-50"
                      >
                        <span>🚪</span>
                        <span>{isLoggingOut ? 'Logging out...' : 'Logout'}</span>
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}
