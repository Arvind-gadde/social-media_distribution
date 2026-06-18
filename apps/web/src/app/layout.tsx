/**
 * Root Layout
 * 
 * Main layout component that wraps the entire application
 */

'use client';

import { Inter } from 'next/font/google';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Providers } from './providers';
import { Navigation } from '@/components/layout/Navigation';
import { Toaster } from '@/components/ui/toaster';
import { CommandBar, useCommandBar } from '@/components/ui/command-bar';
import { CommandBarContext } from '@/lib/command-bar-context';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

function LayoutContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const commandBar = useCommandBar();
  const { isOpen, close, defaultCommands } = commandBar;
  const [mounted, setMounted] = useState(false);
  
  // Prevent hydration mismatch
  useEffect(() => {
    setMounted(true);
  }, []);
  
  // Don't show navigation on auth pages
  const isAuthPage = pathname?.startsWith('/login') || pathname?.startsWith('/register');

  if (!mounted) {
    return <>{children}</>;
  }

  return (
    <CommandBarContext.Provider value={commandBar}>
      {!isAuthPage && <Navigation />}
      {children}
      <Toaster />
      {!isAuthPage && <CommandBar isOpen={isOpen} onClose={close} commands={defaultCommands} />}
    </CommandBarContext.Provider>
  );
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className={inter.className} suppressHydrationWarning>
        <Providers>
          <LayoutContent>{children}</LayoutContent>
        </Providers>
      </body>
    </html>
  );
}
