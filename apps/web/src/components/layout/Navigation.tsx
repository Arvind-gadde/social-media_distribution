'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { WebSocketStatus } from './WebSocketStatus';
import { useCommandBarContext } from '@/lib/command-bar-context';
import { authApi } from '@contentflow/api-client';
import { toast } from '@/lib/toast';

const navSections = [
  {
    label: 'CONTENT',
    items: [
      { href: '/', label: 'Home', icon: '🏠', exact: true },
      { href: '/content', label: 'Content', icon: '📝' },
      { href: '/content/ideas', label: 'Ideas', icon: '✨' },
      { href: '/content/create', label: 'Create', icon: '➕' },
      { href: '/schedule', label: 'Schedule', icon: '📅' },
      { href: '/analytics', label: 'Analytics', icon: '📊' },
    ],
  },
  {
    label: 'DISCOVER',
    items: [
      { href: '/insights', label: 'AI Insights', icon: '💡' },
      { href: '/trends', label: 'Trends', icon: '🔥' },
      { href: '/news', label: 'News', icon: '📰' },
      { href: '/competitors', label: 'Competitors', icon: '⚔️' },
    ],
  },
  {
    label: 'ENGAGE',
    items: [
      { href: '/inbox', label: 'Inbox', icon: '📬' },
      { href: '/goals', label: 'Goals', icon: '🎯' },
    ],
  },
];

export function Navigation() {
  const pathname = usePathname();
  const router = useRouter();
  const { open } = useCommandBarContext();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [user, setUser] = useState<any>(null);
  const [mounted, setMounted] = useState(false);

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
      if (typeof window !== 'undefined') {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
      }
      toast.success('Logged out successfully');
      router.push('/login');
      router.refresh();
    } catch (error) {
      console.error('Logout error:', error);
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

  const isActive = (href: string, exact?: boolean) => {
    if (exact) return pathname === href;
    if (href === '/') return pathname === '/';
    return pathname === href || pathname?.startsWith(href + '/');
  };

  const userInitial = user?.name?.charAt(0).toUpperCase() || user?.email?.charAt(0).toUpperCase() || 'U';

  if (!mounted) return null;

  return (
    <aside className="fixed left-0 top-0 h-screen w-56 glass border-r border-white/10 flex flex-col z-50 overflow-y-auto">
      {/* Logo */}
      <div className="flex items-center gap-2 px-4 py-4 border-b border-white/10">
        <span className="text-xl">⚡</span>
        <span className="font-bold text-lg gradient-text">ContentFlow</span>
      </div>

      {/* Search */}
      <div className="px-3 py-2">
        <button
          type="button"
          onClick={open}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-surface/50 border border-white/10 text-sm text-muted-foreground hover:text-foreground hover:border-tech/50 transition-colors"
        >
          <span>🔍</span>
          <span className="flex-1 text-left">Search</span>
          <kbd className="text-xs border border-white/10 bg-background/50 rounded px-1">⌘K</kbd>
        </button>
      </div>

      {/* Nav Sections */}
      <nav className="flex-1 px-3 py-2 space-y-4">
        {navSections.map((section) => (
          <div key={section.label}>
            <p className="px-2 py-1 text-xs font-semibold text-muted-foreground/60 tracking-wider">
              {section.label}
            </p>
            <div className="space-y-0.5 mt-1">
              {section.items.map((item) => {
                const active = isActive(item.href, item.exact);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      'flex items-center gap-3 px-3 py-2 rounded-lg transition-colors text-sm',
                      active
                        ? 'bg-tech/20 text-tech font-medium'
                        : 'text-muted-foreground hover:bg-surface hover:text-foreground'
                    )}
                  >
                    <span className="text-base">{item.icon}</span>
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Bottom: WebSocket status + user */}
      <div className="border-t border-white/10 p-3 space-y-2">
        <div className="px-2">
          <WebSocketStatus />
        </div>

        <Link
          href="/settings"
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:bg-surface hover:text-foreground transition-colors"
        >
          <span>⚙️</span>
          <span>Settings</span>
        </Link>

        {/* User */}
        <div className="relative">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:bg-surface hover:text-foreground transition-colors"
          >
            <span className="w-7 h-7 rounded-full bg-tech flex items-center justify-center text-white font-bold text-xs shrink-0">
              {userInitial}
            </span>
            <span className="flex-1 text-left truncate">{user?.name || user?.email || 'Account'}</span>
          </button>

          {showUserMenu && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setShowUserMenu(false)} />
              <div className="absolute bottom-full left-0 mb-1 w-56 glass rounded-lg border border-white/10 shadow-xl z-50">
                <div className="p-3 border-b border-white/10">
                  <p className="font-medium text-foreground text-sm truncate">{user?.name || 'User'}</p>
                  <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
                  {user?.id && (
                    <p className="text-xs text-muted-foreground mt-1 font-mono truncate">
                      ID: {user.id.substring(0, 8)}...
                    </p>
                  )}
                </div>
                <div className="p-2">
                  <button
                    onClick={handleLogout}
                    disabled={isLoggingOut}
                    className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left text-error hover:bg-error/10 transition-colors disabled:opacity-50 text-sm"
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
    </aside>
  );
}
