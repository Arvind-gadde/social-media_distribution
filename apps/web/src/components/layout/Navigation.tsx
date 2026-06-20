'use client';

import * as React from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState, useEffect } from 'react';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import {
  Home,
  FileText,
  Sparkles,
  PenLine,
  Calendar,
  BarChart3,
  Lightbulb,
  TrendingUp,
  Newspaper,
  Users,
  Inbox,
  Target,
  Settings,
  Search,
  LogOut,
  ChevronDown,
  ChevronsUpDown,
  PanelLeftClose,
  PanelLeftOpen,
  Zap,
  Plus,
  User as UserIcon,
  Check,
} from 'lucide-react';

import { cn } from '@/lib/utils';
import { WebSocketStatus } from './WebSocketStatus';
import { useCommandBarContext } from '@/lib/command-bar-context';
import { authApi } from '@contentflow/api-client';
import { toast } from '@/lib/toast';
import { clearSession } from '@/lib/session';

type NavItem = {
  href: string;
  label: string;
  Icon: React.ComponentType<{ className?: string }>;
  exact?: boolean;
  badge?: React.ReactNode;
};

type NavSection = {
  label: string;
  items: NavItem[];
};

const navSections: NavSection[] = [
  {
    label: 'Content',
    items: [
      { href: '/', label: 'Home', Icon: Home, exact: true },
      { href: '/content', label: 'Content', Icon: FileText },
      { href: '/content/ideas', label: 'Ideas', Icon: Sparkles },
      { href: '/content/create', label: 'Create', Icon: PenLine, badge: <Plus className="h-3 w-3" /> },
      { href: '/schedule', label: 'Schedule', Icon: Calendar },
      { href: '/analytics', label: 'Analytics', Icon: BarChart3 },
    ],
  },
  {
    label: 'Discover',
    items: [
      { href: '/insights', label: 'AI Insights', Icon: Lightbulb },
      { href: '/trends', label: 'Trends', Icon: TrendingUp },
      { href: '/news', label: 'News', Icon: Newspaper },
      { href: '/competitors', label: 'Competitors', Icon: Users },
    ],
  },
  {
    label: 'Engage',
    items: [
      { href: '/inbox', label: 'Inbox', Icon: Inbox },
      { href: '/goals', label: 'Goals', Icon: Target },
    ],
  },
];

const SIDEBAR_KEY = 'sidebar-collapsed';
const COLLAPSED_W = '4rem';
const EXPANDED_W = '16rem';

const WORKSPACES = ['Personal'] as const;

type SessionUser = { name?: string; email?: string } | null;

interface NavigationProps {
  forceExpanded?: boolean;
  onNavigate?: () => void;
}

export function Navigation({ forceExpanded = false, onNavigate }: NavigationProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { open } = useCommandBarContext();

  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [user, setUser] = useState<SessionUser>(null);
  const [mounted, setMounted] = useState(false);
  const [currentWorkspace, setCurrentWorkspace] = useState<string>('Personal');

  useEffect(() => {
    setMounted(true);
    if (typeof window === 'undefined') return;

    const collapsed = localStorage.getItem(SIDEBAR_KEY) === 'true';
    setIsCollapsed(collapsed);
    if (!forceExpanded) {
      document.documentElement.style.setProperty('--sidebar-w', collapsed ? COLLAPSED_W : EXPANDED_W);
    }

    const raw = localStorage.getItem('user');
    if (raw) {
      try {
        const parsed = JSON.parse(raw);
        if (parsed && typeof parsed === 'object') {
          const candidate = parsed as Record<string, unknown>;
          const name = typeof candidate.name === 'string' ? candidate.name : undefined;
          const email = typeof candidate.email === 'string' ? candidate.email : undefined;
          setUser({ name, email });
        }
      } catch {
        localStorage.removeItem('user');
      }
    }
  }, [forceExpanded]);

  const collapsed = forceExpanded ? false : isCollapsed;

  const toggleCollapse = () => {
    if (forceExpanded) return;
    const next = !isCollapsed;
    setIsCollapsed(next);
    localStorage.setItem(SIDEBAR_KEY, String(next));
    document.documentElement.style.setProperty('--sidebar-w', next ? COLLAPSED_W : EXPANDED_W);
  };

  const allItems = navSections.flatMap((s) => s.items);

  const isActive = (href: string, exact?: boolean): boolean => {
    if (exact) return pathname === href;
    if (href === '/') return pathname === '/';
    if (pathname === href) return true;
    if (!pathname?.startsWith(href + '/')) return false;
    const moreSpecific = allItems.find(
      (item) =>
        item.href !== href &&
        item.href.startsWith(href) &&
        (pathname === item.href || pathname?.startsWith(item.href + '/'))
    );
    return !moreSpecific;
  };

  const handleLogout = async () => {
    try {
      setIsLoggingOut(true);
      await authApi.logout();
    } catch {
      // ignore
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

  const handleNavClick = () => {
    onNavigate?.();
  };

  const userInitial =
    user?.name?.charAt(0).toUpperCase() ||
    user?.email?.charAt(0).toUpperCase() ||
    'U';

  if (!mounted) return null;

  /* ── Nav item classes ─────────────────────────────── */
  const itemClasses = (active: boolean) =>
    cn(
      'group relative flex items-center rounded-lg text-sm font-medium transition-colors duration-150 select-none',
      collapsed ? 'h-9 w-9 mx-auto justify-center' : 'h-9 gap-3 px-3',
      active
        ? 'bg-brand-50 dark:bg-brand-950/40 text-brand-700 dark:text-brand-300'
        : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-100'
    );

  const positionClass = forceExpanded
    ? 'relative h-full w-72'
    : cn(
        'fixed left-0 top-0 h-screen z-40',
        collapsed ? 'w-16' : 'w-64'
      );

  return (
    <aside
      className={cn(
        'flex flex-col bg-background border-r border-border overflow-hidden',
        'transition-[width] duration-200 ease-in-out',
        positionClass
      )}
    >
      {/* ── Logo + Workspace switcher ───────────────────────── */}
      <div
        className={cn(
          'flex items-center h-14 shrink-0 border-b border-border',
          collapsed ? 'justify-center px-2' : 'px-3 gap-2'
        )}
      >
        {collapsed ? (
          <button
            onClick={toggleCollapse}
            className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 hover:bg-brand-700 shadow-xs transition-colors"
            title="Expand sidebar"
            aria-label="Expand sidebar"
          >
            <Zap className="h-4 w-4 text-white" />
          </button>
        ) : (
          <>
            <DropdownMenu.Root>
              <DropdownMenu.Trigger asChild>
                <button
                  type="button"
                  className={cn(
                    'flex-1 min-w-0 flex items-center gap-2 h-10 px-2 rounded-lg',
                    'hover:bg-secondary transition-colors'
                  )}
                >
                  <span className="flex h-7 w-7 items-center justify-center rounded-md bg-brand-600 shrink-0">
                    <Zap className="h-3.5 w-3.5 text-white" />
                  </span>
                  <span className="flex-1 min-w-0 text-left">
                    <span className="block text-sm font-semibold text-foreground truncate leading-none">
                      ContentFlow
                    </span>
                    <span className="block text-[11px] text-muted-foreground truncate mt-0.5">
                      {currentWorkspace}
                    </span>
                  </span>
                  <ChevronsUpDown className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                </button>
              </DropdownMenu.Trigger>
              <DropdownMenu.Portal>
                <DropdownMenu.Content
                  align="start"
                  sideOffset={6}
                  className="z-50 min-w-[14rem] rounded-xl border border-border bg-popover p-1.5 shadow-lg animate-scale-in"
                >
                  <div className="px-2 py-1.5 text-[11px] font-semibold tracking-wider uppercase text-muted-foreground">
                    Workspaces
                  </div>
                  {WORKSPACES.map((ws) => (
                    <DropdownMenu.Item
                      key={ws}
                      onSelect={() => setCurrentWorkspace(ws)}
                      className="flex items-center justify-between gap-2 px-2.5 py-2 rounded-md text-sm text-foreground hover:bg-secondary outline-none cursor-pointer"
                    >
                      <span className="truncate">{ws}</span>
                      {currentWorkspace === ws && (
                        <Check className="h-3.5 w-3.5 text-brand-600" />
                      )}
                    </DropdownMenu.Item>
                  ))}
                  <DropdownMenu.Separator className="my-1 h-px bg-border" />
                  <DropdownMenu.Item
                    className="flex items-center gap-2 px-2.5 py-2 rounded-md text-sm text-muted-foreground hover:bg-secondary hover:text-foreground outline-none cursor-pointer"
                    onSelect={() => {
                      /* placeholder — wire backend */
                    }}
                  >
                    <Plus className="h-3.5 w-3.5" />
                    Switch workspace…
                  </DropdownMenu.Item>
                </DropdownMenu.Content>
              </DropdownMenu.Portal>
            </DropdownMenu.Root>

            {!forceExpanded && (
              <button
                onClick={toggleCollapse}
                className="shrink-0 flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                title="Collapse sidebar"
                aria-label="Collapse sidebar"
              >
                <PanelLeftClose className="h-4 w-4" />
              </button>
            )}
          </>
        )}
      </div>

      {/* ── Search ───────────────────────────────────────────── */}
      <div className={cn('shrink-0', collapsed ? 'px-2 pt-3 pb-1' : 'px-3 pt-3 pb-1')}>
        {collapsed ? (
          <button
            onClick={open}
            title="Search (⌘K)"
            aria-label="Open search"
            className="w-9 h-9 mx-auto flex items-center justify-center rounded-lg text-muted-foreground hover:text-foreground hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          >
            <Search className="h-4 w-4" />
          </button>
        ) : (
          <button
            type="button"
            onClick={open}
            className={cn(
              'group w-full flex items-center gap-2 h-9 px-3 rounded-lg',
              'border border-border bg-background',
              'text-sm text-muted-foreground hover:text-foreground',
              'hover:border-gray-300 dark:hover:border-gray-700 transition-colors'
            )}
          >
            <Search className="h-4 w-4 shrink-0" />
            <span className="flex-1 text-left">Search</span>
            <kbd className="inline-flex items-center text-[10px] font-medium border border-border bg-secondary rounded px-1.5 py-0.5">
              ⌘K
            </kbd>
          </button>
        )}
      </div>

      {/* ── Nav sections ─────────────────────────────────────── */}
      <nav className="flex-1 overflow-y-auto scrollbar-hide px-2 py-3 space-y-5">
        {navSections.map((section) => (
          <div key={section.label}>
            {!collapsed && (
              <p className="px-3 pb-1.5 text-[11px] font-semibold text-muted-foreground tracking-wider uppercase">
                {section.label}
              </p>
            )}
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const { href, label, Icon, exact, badge } = item;
                const active = isActive(href, exact);
                return (
                  <Link
                    key={href}
                    href={href}
                    onClick={handleNavClick}
                    title={collapsed ? label : undefined}
                    aria-current={active ? 'page' : undefined}
                    className={itemClasses(active)}
                  >
                    {active && !collapsed && (
                      <span
                        aria-hidden
                        className="absolute left-0 top-1.5 bottom-1.5 w-0.5 rounded-r bg-brand-600"
                      />
                    )}
                    <Icon
                      className={cn(
                        'h-5 w-5 shrink-0',
                        active
                          ? 'text-brand-600 dark:text-brand-400'
                          : 'text-gray-400 dark:text-gray-500 group-hover:text-gray-600 dark:group-hover:text-gray-300'
                      )}
                    />
                    {!collapsed && (
                      <>
                        <span className="flex-1 truncate">{label}</span>
                        {badge && (
                          <span className="ml-auto flex h-5 w-5 items-center justify-center rounded-full bg-brand-600 text-white">
                            {badge}
                          </span>
                        )}
                      </>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* ── Footer: status + user menu ─────────────────────── */}
      <div
        className={cn(
          'border-t border-border shrink-0',
          collapsed ? 'p-2 space-y-1' : 'p-3 space-y-1'
        )}
      >
        {!collapsed && (
          <div className="px-3 py-1">
            <WebSocketStatus />
          </div>
        )}

        <Link
          href="/settings"
          onClick={handleNavClick}
          title={collapsed ? 'Settings' : undefined}
          className={itemClasses(isActive('/settings'))}
        >
          <Settings
            className={cn(
              'h-5 w-5 shrink-0',
              isActive('/settings')
                ? 'text-brand-600 dark:text-brand-400'
                : 'text-gray-400 dark:text-gray-500'
            )}
          />
          {!collapsed && <span>Settings</span>}
        </Link>

        {/* User menu */}
        <DropdownMenu.Root>
          <DropdownMenu.Trigger asChild>
            <button
              title={collapsed ? user?.name || 'Account' : undefined}
              className={cn(
                'w-full flex items-center rounded-lg text-sm font-medium transition-colors duration-150',
                'hover:bg-gray-50 dark:hover:bg-gray-800',
                collapsed ? 'h-10 w-10 mx-auto justify-center' : 'gap-2.5 px-2 py-2'
              )}
            >
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100 dark:bg-brand-950/60 text-brand-700 dark:text-brand-300 text-xs font-semibold shrink-0">
                {userInitial}
              </span>
              {!collapsed && (
                <>
                  <span className="flex-1 text-left min-w-0">
                    <span className="block truncate text-sm font-semibold text-foreground leading-tight">
                      {user?.name || 'Account'}
                    </span>
                    {user?.email && (
                      <span className="block truncate text-xs text-muted-foreground leading-tight">
                        {user.email}
                      </span>
                    )}
                  </span>
                  <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                </>
              )}
            </button>
          </DropdownMenu.Trigger>
          <DropdownMenu.Portal>
            <DropdownMenu.Content
              side={collapsed ? 'right' : 'top'}
              align={collapsed ? 'end' : 'start'}
              sideOffset={8}
              className="z-50 min-w-[14rem] rounded-xl border border-border bg-popover p-1.5 shadow-lg animate-scale-in"
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
                  onClick={handleNavClick}
                  className="flex items-center gap-2 px-2.5 py-2 rounded-md text-sm text-foreground hover:bg-secondary outline-none cursor-pointer"
                >
                  <UserIcon className="h-4 w-4 text-muted-foreground" />
                  Profile
                </Link>
              </DropdownMenu.Item>
              <DropdownMenu.Item asChild>
                <Link
                  href="/settings"
                  onClick={handleNavClick}
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

        {collapsed && !forceExpanded && (
          <button
            onClick={toggleCollapse}
            className="w-9 h-9 mx-auto flex items-center justify-center rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
            title="Expand sidebar"
            aria-label="Expand sidebar"
          >
            <PanelLeftOpen className="h-4 w-4" />
          </button>
        )}
      </div>
    </aside>
  );
}
