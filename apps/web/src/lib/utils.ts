/**
 * Shared UI utilities.
 *
 * NOTE: this module lives under apps/web/src/lib/, which the repo .gitignore
 * historically swallowed via a stray Python `lib/` rule. It is reconstructed
 * from its usage across the app — keep exports stable.
 */
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/** Merge class names with Tailwind conflict resolution (clsx + tailwind-merge). */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/**
 * Niche accent colors (hex). Mirrors the design tokens in tailwind.config.ts.
 * Returns the `tech` cyan as a sensible default for unknown niches.
 */
const NICHE_COLORS: Record<string, string> = {
  tech: '#06b6d4',
  fitness: '#f97316',
  finance: '#10b981',
  beauty: '#ec4899',
  food: '#f59e0b',
  gaming: '#8b5cf6',
};

export function getNicheColor(niche?: string | null): string {
  if (!niche) return NICHE_COLORS.tech;
  return NICHE_COLORS[niche.toLowerCase()] ?? NICHE_COLORS.tech;
}

function toDate(value: string | number | Date | null | undefined): Date | null {
  if (value === null || value === undefined || value === '') return null;
  const d = value instanceof Date ? value : new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** Format a date for display, e.g. "Jun 22, 2026". Empty string on invalid/missing input. */
export function formatDate(value: string | number | Date | null | undefined): string {
  const d = toDate(value);
  if (!d) return '';
  return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

/** Format a date as relative time, e.g. "2 hours ago" / "in 3 days". */
export function formatRelativeTime(value: string | number | Date | null | undefined): string {
  const d = toDate(value);
  if (!d) return '';

  const diffMs = d.getTime() - Date.now();
  const absMs = Math.abs(diffMs);
  const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' });

  const units: Array<[Intl.RelativeTimeFormatUnit, number]> = [
    ['year', 1000 * 60 * 60 * 24 * 365],
    ['month', 1000 * 60 * 60 * 24 * 30],
    ['week', 1000 * 60 * 60 * 24 * 7],
    ['day', 1000 * 60 * 60 * 24],
    ['hour', 1000 * 60 * 60],
    ['minute', 1000 * 60],
    ['second', 1000],
  ];

  for (const [unit, ms] of units) {
    if (absMs >= ms || unit === 'second') {
      return rtf.format(Math.round(diffMs / ms), unit);
    }
  }
  return rtf.format(0, 'second');
}

/** Compact number formatting, e.g. 1500 -> "1.5K", 2_300_000 -> "2.3M". */
export function formatNumber(num: number | null | undefined): string {
  const n = typeof num === 'number' && Number.isFinite(num) ? num : 0;
  if (Math.abs(n) >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (Math.abs(n) >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}
