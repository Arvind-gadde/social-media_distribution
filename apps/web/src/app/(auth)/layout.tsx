/**
 * Auth Layout
 * 
 * Layout for authentication pages (login, register)
 * No navigation bar, just the content
 */

'use client';

import type { ReactNode } from 'react';

export default function AuthLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
