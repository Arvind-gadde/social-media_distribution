'use client';

import * as React from 'react';
import * as TabsPrimitive from '@radix-ui/react-tabs';
import { cn } from '@/lib/utils';

type TabsVariant = 'underline' | 'pill' | 'button-group';

interface TabsContextValue {
  variant: TabsVariant;
}

const TabsVariantContext = React.createContext<TabsContextValue>({ variant: 'underline' });

interface TabsProps extends React.ComponentPropsWithoutRef<typeof TabsPrimitive.Root> {
  variant?: TabsVariant;
}

const Tabs = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Root>,
  TabsProps
>(({ variant = 'underline', className, ...props }, ref) => (
  <TabsVariantContext.Provider value={{ variant }}>
    <TabsPrimitive.Root
      ref={ref}
      className={cn('flex flex-col gap-4', className)}
      {...props}
    />
  </TabsVariantContext.Provider>
));
Tabs.displayName = 'Tabs';

const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => {
  const { variant } = React.useContext(TabsVariantContext);

  const listStyles: Record<TabsVariant, string> = {
    underline: 'border-b border-gray-200 dark:border-gray-800 flex gap-3',
    pill: 'inline-flex items-center gap-1 rounded-lg bg-gray-100 dark:bg-gray-900 p-1',
    'button-group':
      'inline-flex items-center rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 p-0 shadow-xs overflow-hidden',
  };

  return (
    <TabsPrimitive.List
      ref={ref}
      className={cn(listStyles[variant], className)}
      {...props}
    />
  );
});
TabsList.displayName = 'TabsList';

const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => {
  const { variant } = React.useContext(TabsVariantContext);

  const triggerStyles: Record<TabsVariant, string> = {
    underline: cn(
      'inline-flex items-center gap-2 pb-3 pt-1 px-1 text-sm font-medium',
      'border-b-2 border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200',
      'transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2',
      'disabled:pointer-events-none disabled:opacity-50',
      'data-[state=active]:border-brand-600 data-[state=active]:text-brand-700 dark:data-[state=active]:text-brand-300'
    ),
    pill: cn(
      'inline-flex items-center justify-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium',
      'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100',
      'transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500',
      'disabled:pointer-events-none disabled:opacity-50',
      'data-[state=active]:bg-white dark:data-[state=active]:bg-gray-800 data-[state=active]:text-gray-900 dark:data-[state=active]:text-gray-100 data-[state=active]:shadow-sm'
    ),
    'button-group': cn(
      'inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium',
      'text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-950 hover:bg-gray-50 dark:hover:bg-gray-900',
      'border-r border-gray-200 dark:border-gray-800 last:border-r-0',
      'transition-colors focus-visible:outline-none focus-visible:z-10 focus-visible:ring-2 focus-visible:ring-brand-500',
      'disabled:pointer-events-none disabled:opacity-50',
      'data-[state=active]:bg-gray-50 dark:data-[state=active]:bg-gray-900 data-[state=active]:text-brand-700 dark:data-[state=active]:text-brand-300'
    ),
  };

  return (
    <TabsPrimitive.Trigger
      ref={ref}
      className={cn(triggerStyles[variant], className)}
      {...props}
    />
  );
});
TabsTrigger.displayName = 'TabsTrigger';

const TabsContent = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn(
      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 rounded-md',
      className
    )}
    {...props}
  />
));
TabsContent.displayName = 'TabsContent';

export { Tabs, TabsList, TabsTrigger, TabsContent };
export type { TabsProps, TabsVariant };
