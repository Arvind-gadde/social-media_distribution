'use client';

import * as React from 'react';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import * as Dialog from '@radix-ui/react-dialog';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Bell,
  Search,
  Menu,
  ChevronDown,
  LogOut,
  Settings,
  User as UserIcon,
} from 'lucide-react';

import { Navigation } from '@/components/layout/Navigation';
import { Toaster } from '@/components/ui/toaster';
import { CommandBar, useCommandBar } from '@/components/ui/command-bar';
import { CommandBarContext, useCommandBarContext } from '@/lib/command-bar-context';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import { cn } from '@/lib/utils';
import { authApi } from '@contentflow/api-client';
import { toast } from '@/lib/toast';
import { clearSession } from '@/lib/session';

type SessionUser = { name?: string; email?: string } | null;

function readUserFromStorage(): SessionUser {
  if (typeof window === 'undefined') return null;
  const raw = localStorage.getItem('user');
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === 'object') {
      const candidate = parsed as Record<string, unknown>;
      const name = typeof candidate.name === 'string' ? candidate.name : undefined;
      const email = typeof candidate.email === 'string' ? candidate.email : undefined;
      return { name, email };
    }
  } catch {
    localStorage.removeItem('user');
  }
  return null;
}

function TopBarSearchTrigger() {
  const { open } = useCommandBarContext();
  return (
    <button
      type="button"
      onClick={open}
      className={cn(
        'group hidden md:flex items-center gap-2 h-9 w-72 max-w-full',
        'rounded-lg border border-border bg-background pl-3 pr-2',
        'text-sm text-muted-foreground hover:text-foreground',
        'hover:border-gray-300 dark:hover:border-gray-700 transition-colors'
      )}
    >
      <Search className="h-4 w-4 shrink-0" />
      <span className="flex-1 text-left">Search...</span>
      <kbd className="inline-flex items-center gap-0.5 text-[10px] font-medium border border-border bg-secondary rounded px-1.5 py-0.5">
        ⌘K
      </kbd>
    </button>
  );
}

function TopBarSearchIcon() {
  const { open } = useCommandBarContext();
  return (
    <button
      type="button"
      onClick={open}
      aria-label="Search"
      className="md:hidden inline-flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
    >
      <Search className="h-4 w-4" />
    </button>
  );
}

function NotificationsBell() {
  return (
    <button
      type="button"
      aria-label="Notifications"
      className="relative inline-flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
    >
      <Bell className="h-4 w-4" />
      <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-brand-600 ring-2 ring-background" />
    </button>
  );
}

function UserAvatarMenu({ user }: { user: SessionUser }) {
  const router = useRouter();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const initial =
    user?.name?.charAt(0).toUpperCase() ||
    user?.email?.charAt(0).toUpperCase() ||
    'U';

  const handleLogout = async () => {
    try {
      setIsLoggingOut(true);
      await authApi.logout();
    } catch {
      // ignore network error — proceed with local cleanup
    } finally {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
      }
      clearSession();
      toast.success('Logged out successfully');
      setIsLoggingOut(false);
      router.push('/login');
      router.refresh();
    }
  };

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button
          type="button"
          aria-label="Account menu"
          className="inline-flex h-9 items-center gap-2 rounded-lg pl-1 pr-2 hover:bg-secondary transition-colors"
        >
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-100 dark:bg-brand-950/60 text-brand-700 dark:text-brand-300 text-xs font-semibold">
            {initial}
          </span>
          <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={8}
          className={cn(
            'z-50 min-w-[14rem] rounded-xl border border-border bg-popover p-1.5 shadow-lg',
            'animate-scale-in'
          )}
        >
          <div className="px-2.5 py-2 border-b border-border mb-1">
            <p className="text-sm font-semibold text-foreground truncate">
              {user?.name || 'Account'}
            </p>
            {user?.email && (
              <p className="text-xs text-muted-foreground truncate">{user.email}</p>
            )}
          </div>
          <DropdownMenu.Item asChild>
            <Link
              href="/settings/profile"
              className="flex items-center gap-2 px-2.5 py-2 rounded-md text-sm text-foreground hover:bg-secondary outline-none cursor-pointer"
            >
              <UserIcon className="h-4 w-4 text-muted-foreground" />
              Profile
            </Link>
          </DropdownMenu.Item>
          <DropdownMenu.Item asChild>
            <Link
              href="/settings"
              className="flex items-center gap-2 px-2.5 py-2 rounded-md text-sm text-foreground hover:bg-secondary outline-none cursor-pointer"
            >
              <Settings className="h-4 w-4 text-muted-foreground" />
              Settings
            </Link>
          </DropdownMenu.Item>
          <DropdownMenu.Separator className="my-1 h-px bg-border" />
          <DropdownMenu.Item
            onSelect={(e) => {
              e.preventDefault();
              handleLogout();
            }}
            disabled={isLoggingOut}
            className="flex items-center gap-2 px-2.5 py-2 rounded-md text-sm text-error-600 hover:bg-error-50 dark:hover:bg-error-950/40 outline-none cursor-pointer disabled:opacity-50"
          >
            <LogOut className="h-4 w-4" />
            {isLoggingOut ? 'Signing out...' : 'Sign out'}
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const commandBar = useCommandBar();
  const { isOpen, close, defaultCommands } = commandBar;
  const [mounted, setMounted] = useState(false);
  const [user, setUser] = useState<SessionUser>(null);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    setMounted(true);
    setUser(readUserFromStorage());
  }, []);

  // Re-read user when navigating (e.g., after login)
  useEffect(() => {
    if (mounted) setUser(readUserFromStorage());
  }, [pathname, mounted]);

  // Close mobile nav on route change
  useEffect(() => {
    setMobileNavOpen(false);
  }, [pathname]);

  const isAuthPage =
    pathname?.startsWith('/login') ||
    pathname?.startsWith('/register') ||
    pathname?.startsWith('/auth');

  if (!mounted) {
    return <div className="min-h-screen bg-background" />;
  }

  if (isAuthPage) {
    return (
      <CommandBarContext.Provider value={commandBar}>
        {children}
        <Toaster />
      </CommandBarContext.Provider>
    );
  }

  return (
    <CommandBarContext.Provider value={commandBar}>
      <div className="flex h-screen bg-background">
        {/* Desktop sidebar */}
        <div className="hidden md:block">
          <Navigation />
        </div>

        {/* Mobile drawer */}
        <Dialog.Root open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
          <Dialog.Portal>
            <Dialog.Overlay className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm data-[state=open]:animate-fade-in md:hidden" />
            <Dialog.Content
              className={cn(
                'fixed left-0 top-0 z-50 h-full w-72 outline-none',
                'data-[state=open]:animate-slide-in-left md:hidden'
              )}
            >
              <Dialog.Title className="sr-only">Navigation</Dialog.Title>
              <Navigation forceExpanded onNavigate={() => setMobileNavOpen(false)} />
            </Dialog.Content>
          </Dialog.Portal>
        </Dialog.Root>

        {/* Margin is driven purely by CSS so it reacts to viewport resize and
            sidebar collapse automatically. Reading window.matchMedia inline at
            render was stale on resize (React doesn't re-render on resize),
            leaving the content clipped under the fixed sidebar or gutter-ed. */}
        <div className="flex-1 flex flex-col min-w-0 transition-[margin-left] duration-200 ease-in-out md:ml-[var(--sidebar-w,16rem)]">
          <header
            className={cn(
              'sticky top-0 z-30 flex items-center justify-between gap-3 h-16 px-4 md:px-6 shrink-0',
              'border-b border-border bg-background/95 backdrop-blur-md'
            )}
          >
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <button
                type="button"
                onClick={() => setMobileNavOpen(true)}
                aria-label="Open navigation"
                className="md:hidden inline-flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary"
              >
                <Menu className="h-5 w-5" />
              </button>
              <TopBarSearchTrigger />
            </div>

            <div className="flex items-center gap-1 md:gap-2 shrink-0">
              <TopBarSearchIcon />
              <NotificationsBell />
              <ThemeToggle compact />
              <div className="w-px h-6 bg-border mx-1 hidden sm:block" />
              <UserAvatarMenu user={user} />
            </div>
          </header>

          <main className="flex-1 overflow-y-auto focus:outline-none">{children}</main>
        </div>
      </div>

      <Toaster />
      <CommandBar isOpen={isOpen} onClose={close} commands={defaultCommands} />
    </CommandBarContext.Provider>
  );
}
