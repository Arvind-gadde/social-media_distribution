/**
 * Toast notifications — a tiny framework-agnostic store plus a `useToast` hook.
 *
 * `toast.success('...')` etc. can be called from anywhere (hooks, event
 * handlers, non-React modules); the `<Toaster/>` component subscribes via
 * `useToast()` and renders the active toasts.
 */
'use client';

import { useSyncExternalStore } from 'react';

export type ToastVariant = 'default' | 'success' | 'error' | 'warning' | 'info';

export interface ToastAction {
  label: string;
  onClick: () => void;
}

export interface ToastItem {
  id: string;
  variant: ToastVariant;
  title?: string;
  description?: string;
  action?: ToastAction;
}

export interface ToastOptions {
  description?: string;
  action?: ToastAction;
  /** ms before auto-dismiss; <= 0 keeps it until dismissed. Default 5000. */
  duration?: number;
}

const DEFAULT_DURATION = 5000;
const EMPTY: ToastItem[] = [];

let toasts: ToastItem[] = EMPTY;
let counter = 0;
const listeners = new Set<() => void>();

function emit(): void {
  for (const listener of listeners) listener();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot(): ToastItem[] {
  return toasts;
}

export function dismiss(id: string): void {
  const next = toasts.filter((t) => t.id !== id);
  if (next.length !== toasts.length) {
    toasts = next;
    emit();
  }
}

function push(variant: ToastVariant, message: string, opts?: ToastOptions): string {
  const id = `toast_${++counter}`;
  const item: ToastItem = {
    id,
    variant,
    title: message,
    description: opts?.description,
    action: opts?.action,
  };
  toasts = [...toasts, item];
  emit();

  const duration = opts?.duration ?? DEFAULT_DURATION;
  if (duration > 0 && typeof window !== 'undefined') {
    window.setTimeout(() => dismiss(id), duration);
  }
  return id;
}

export const toast = {
  success: (message: string, opts?: ToastOptions) => push('success', message, opts),
  error: (message: string, opts?: ToastOptions) => push('error', message, opts),
  info: (message: string, opts?: ToastOptions) => push('info', message, opts),
  warning: (message: string, opts?: ToastOptions) => push('warning', message, opts),
  message: (message: string, opts?: ToastOptions) => push('default', message, opts),
};

/** Subscribe to the active toasts. Used by the <Toaster/> component. */
export function useToast(): { toasts: ToastItem[]; dismiss: (id: string) => void } {
  const list = useSyncExternalStore(subscribe, getSnapshot, () => EMPTY);
  return { toasts: list, dismiss };
}
