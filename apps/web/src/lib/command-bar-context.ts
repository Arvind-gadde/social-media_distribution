/**
 * Command-bar context.
 *
 * The state itself is produced by `useCommandBar()` in components/ui/command-bar.tsx;
 * AppShell provides that value here so any component (Navigation, 404, top bar)
 * can open/close the command palette via `useCommandBarContext()`.
 */
'use client';

import { createContext, useContext } from 'react';
import type { CommandItem } from '@/components/ui/command-bar';

export interface CommandBarValue {
  isOpen: boolean;
  open: () => void;
  close: () => void;
  toggle: () => void;
  defaultCommands: CommandItem[];
}

export const CommandBarContext = createContext<CommandBarValue | null>(null);

// Safe no-op fallback so consumers rendered outside the provider (e.g. the
// not-found page) never crash on destructure.
const NOOP: CommandBarValue = {
  isOpen: false,
  open: () => {},
  close: () => {},
  toggle: () => {},
  defaultCommands: [],
};

export function useCommandBarContext(): CommandBarValue {
  return useContext(CommandBarContext) ?? NOOP;
}
