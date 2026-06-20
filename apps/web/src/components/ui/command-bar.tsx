/**
 * Command Bar Component (Cmd+K)
 * 
 * Global search and quick actions
 */

'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';

export interface CommandItem {
  id: string;
  label: string;
  description?: string;
  icon?: string;
  keywords?: string[];
  action: () => void;
  category?: string;
}

interface CommandBarProps {
  isOpen: boolean;
  onClose: () => void;
  commands: CommandItem[];
}

export function CommandBar({ isOpen, onClose, commands }: CommandBarProps) {
  const [search, setSearch] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);

  // Filter commands based on search
  const filteredCommands = useMemo(() => {
    if (!search) return commands;

    const searchLower = search.toLowerCase();
    return commands.filter((cmd) => {
      const labelMatch = cmd.label.toLowerCase().includes(searchLower);
      const descMatch = cmd.description?.toLowerCase().includes(searchLower);
      const keywordMatch = cmd.keywords?.some((k) => k.toLowerCase().includes(searchLower));
      return labelMatch || descMatch || keywordMatch;
    });
  }, [commands, search]);

  // Group commands by category
  const groupedCommands = useMemo(() => {
    const groups: Record<string, CommandItem[]> = {};
    filteredCommands.forEach((cmd) => {
      const category = cmd.category || 'Other';
      if (!groups[category]) {
        groups[category] = [];
      }
      groups[category].push(cmd);
    });
    return groups;
  }, [filteredCommands]);

  // Reset selection when search changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [search]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, filteredCommands.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const selected = filteredCommands[selectedIndex];
        if (selected) {
          selected.action();
          onClose();
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    },
    [filteredCommands, selectedIndex, onClose]
  );

  // Close on backdrop click
  const handleBackdropClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === e.currentTarget) {
        onClose();
      }
    },
    [onClose]
  );

  // Reset state when closed
  useEffect(() => {
    if (!isOpen) {
      setSearch('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  let currentIndex = 0;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-start justify-center pt-[20vh] px-4"
      onClick={handleBackdropClick}
    >
      <div className="w-full max-w-2xl bg-popover rounded-xl shadow-2xl border border-border overflow-hidden">
        {/* Search Input */}
        <div className="flex items-center border-b border-border px-4">
          <span className="text-muted-foreground text-xl mr-3">🔍</span>
          <input
            type="text"
            className="flex-1 bg-transparent py-4 text-lg outline-none placeholder:text-muted-foreground"
            placeholder="Search pages, actions..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={handleKeyDown}
            autoFocus
          />
          <kbd className="hidden sm:inline-flex h-5 select-none items-center gap-1 rounded border border-border bg-background px-1.5 font-mono text-xs text-muted-foreground">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-[400px] overflow-y-auto p-2">
          {filteredCommands.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">
              <div className="text-4xl mb-2">🔍</div>
              <p>No commands found</p>
              <p className="text-sm mt-1">Try a different search term</p>
            </div>
          ) : (
            Object.entries(groupedCommands).map(([category, items]) => (
              <div key={category} className="mb-4 last:mb-0">
                <div className="px-2 py-1 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  {category}
                </div>
                <div className="space-y-1">
                  {items.map((cmd) => {
                    const itemIndex = currentIndex++;
                    const isSelected = itemIndex === selectedIndex;

                    return (
                      <button
                        key={cmd.id}
                        className={cn(
                          'w-full flex items-center gap-3 px-3 py-2 rounded-md text-left transition-colors',
                          isSelected
                            ? 'bg-primary/15 text-primary'
                            : 'hover:bg-secondary text-foreground'
                        )}
                        onClick={() => {
                          cmd.action();
                          onClose();
                        }}
                        onMouseEnter={() => setSelectedIndex(itemIndex)}
                      >
                        {cmd.icon && <span className="text-xl">{cmd.icon}</span>}
                        <div className="flex-1 min-w-0">
                          <div className="font-medium truncate">{cmd.label}</div>
                          {cmd.description && (
                            <div className="text-sm text-muted-foreground truncate">
                              {cmd.description}
                            </div>
                          )}
                        </div>
                        {isSelected && (
                          <kbd className="hidden sm:inline-flex h-5 select-none items-center gap-1 rounded border border-border bg-background px-1.5 font-mono text-xs text-muted-foreground">
                            ↵
                          </kbd>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-border px-4 py-2 flex items-center justify-between text-xs text-muted-foreground">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 rounded border border-border bg-background">↑</kbd>
              <kbd className="px-1.5 py-0.5 rounded border border-border bg-background">↓</kbd>
              Navigate
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 rounded border border-border bg-background">↵</kbd>
              Select
            </span>
          </div>
          <span>{filteredCommands.length} results</span>
        </div>
      </div>
    </div>
  );
}

/**
 * Hook for command bar
 */
export function useCommandBar() {
  const [isOpen, setIsOpen] = useState(false);
  const router = useRouter();

  // Global keyboard shortcut (Cmd+K / Ctrl+K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Default commands
  const defaultCommands: CommandItem[] = useMemo(
    () => [
      // Navigation
      { id: 'nav-home',        label: 'Home',         description: 'Go to dashboard',            icon: '🏠', category: 'Navigate', keywords: ['home', 'dashboard'],                   action: () => router.push('/') },
      { id: 'nav-content',     label: 'Content',      description: 'Manage your content',         icon: '📄', category: 'Navigate', keywords: ['content', 'posts', 'articles'],        action: () => router.push('/content') },
      { id: 'nav-ideas',       label: 'Ideas',        description: 'Browse content ideas',        icon: '✨', category: 'Navigate', keywords: ['ideas', 'inspiration', 'brainstorm'],  action: () => router.push('/content/ideas') },
      { id: 'nav-create',      label: 'Create',       description: 'Create new content',          icon: '✏️', category: 'Navigate', keywords: ['create', 'write', 'new', 'post'],      action: () => router.push('/content/create') },
      { id: 'nav-schedule',    label: 'Schedule',     description: 'View content calendar',       icon: '📅', category: 'Navigate', keywords: ['schedule', 'calendar', 'plan'],        action: () => router.push('/schedule') },
      { id: 'nav-analytics',   label: 'Analytics',    description: 'View performance metrics',    icon: '📊', category: 'Navigate', keywords: ['analytics', 'stats', 'metrics'],       action: () => router.push('/analytics') },
      { id: 'nav-insights',    label: 'AI Insights',  description: 'View agent insights',         icon: '💡', category: 'Navigate', keywords: ['insights', 'ai', 'agent'],             action: () => router.push('/insights') },
      { id: 'nav-trends',      label: 'Trends',       description: 'Browse trending content',     icon: '📈', category: 'Navigate', keywords: ['trends', 'trending', 'viral'],         action: () => router.push('/trends') },
      { id: 'nav-news',        label: 'News',         description: 'Latest industry news',        icon: '📰', category: 'Navigate', keywords: ['news', 'articles', 'updates'],         action: () => router.push('/news') },
      { id: 'nav-competitors', label: 'Competitors',  description: 'Track competitor activity',   icon: '🔍', category: 'Navigate', keywords: ['competitors', 'rivals', 'compare'],    action: () => router.push('/competitors') },
      { id: 'nav-inbox',       label: 'Inbox',        description: 'View messages & replies',     icon: '📬', category: 'Navigate', keywords: ['inbox', 'messages', 'dm', 'replies'],  action: () => router.push('/inbox') },
      { id: 'nav-goals',       label: 'Goals',        description: 'Track your goals',            icon: '🎯', category: 'Navigate', keywords: ['goals', 'progress', 'targets'],        action: () => router.push('/goals') },
      { id: 'nav-settings',    label: 'Settings',     description: 'Manage account settings',     icon: '⚙️', category: 'Navigate', keywords: ['settings', 'account', 'profile'],      action: () => router.push('/settings') },
      // Actions
      { id: 'act-create',      label: 'New Content',  description: 'Start creating content now',  icon: '✏️', category: 'Actions',  keywords: ['new', 'create', 'write'],              action: () => router.push('/content/create') },
      { id: 'act-goal',        label: 'New Goal',     description: 'Set a new content goal',      icon: '🎯', category: 'Actions',  keywords: ['goal', 'new', 'target'],               action: () => router.push('/goals') },
      { id: 'act-refresh',     label: 'Refresh',      description: 'Reload current page',         icon: '🔄', category: 'Actions',  keywords: ['refresh', 'reload'],                   action: () => window.location.reload() },
    ],
    [router]
  );

  return {
    isOpen,
    open: () => setIsOpen(true),
    close: () => setIsOpen(false),
    toggle: () => setIsOpen((prev) => !prev),
    defaultCommands,
  };
}
