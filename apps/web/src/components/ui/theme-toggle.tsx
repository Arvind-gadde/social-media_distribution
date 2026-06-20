'use client';

import { useTheme } from 'next-themes';
import { Sun, Moon, Monitor } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useState, useEffect } from 'react';

interface ThemeToggleProps {
  className?: string;
  compact?: boolean;
}

export function ThemeToggle({ className, compact = false }: ThemeToggleProps) {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div
        className={cn(
          'h-9 rounded-lg bg-secondary animate-pulse',
          compact ? 'w-9' : 'w-28',
          className
        )}
      />
    );
  }

  if (compact) {
    const next = theme === 'dark' ? 'light' : theme === 'light' ? 'system' : 'dark';
    const Icon = theme === 'dark' ? Moon : theme === 'light' ? Sun : Monitor;

    return (
      <button
        onClick={() => setTheme(next)}
        className={cn(
          'flex h-9 w-9 items-center justify-center rounded-lg',
          'text-muted-foreground hover:text-foreground hover:bg-secondary',
          'transition-all duration-200',
          className
        )}
        aria-label={`Switch to ${next} mode`}
        title={`Current: ${theme} mode`}
      >
        <Icon className="h-4 w-4" />
      </button>
    );
  }

  return (
    <div
      className={cn(
        'flex items-center gap-0.5 p-1 rounded-lg bg-secondary border border-border',
        className
      )}
      role="group"
      aria-label="Theme selection"
    >
      {(
        [
          { value: 'light', Icon: Sun, label: 'Light' },
          { value: 'system', Icon: Monitor, label: 'System' },
          { value: 'dark', Icon: Moon, label: 'Dark' },
        ] as const
      ).map(({ value, Icon, label }) => (
        <button
          key={value}
          onClick={() => setTheme(value)}
          className={cn(
            'flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-all duration-150',
            theme === value
              ? 'bg-background text-foreground shadow-soft'
              : 'text-muted-foreground hover:text-foreground'
          )}
          aria-label={`${label} mode`}
          aria-pressed={theme === value}
        >
          <Icon className="h-3.5 w-3.5" />
          {label}
        </button>
      ))}
    </div>
  );
}
