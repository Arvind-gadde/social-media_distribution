/**
 * Toaster Component
 * 
 * Renders all active toasts with animations
 */

'use client';

import { useToast } from '@/lib/toast';
import { Toast } from './toast';
import { Button } from './button';

export function Toaster() {
  const { toasts, dismiss } = useToast();

  return (
    <div className="fixed top-0 right-0 z-[100] flex max-h-screen w-full flex-col-reverse p-4 sm:top-auto sm:right-0 sm:bottom-0 sm:flex-col md:max-w-[420px]">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className="animate-in slide-in-from-top-full sm:slide-in-from-bottom-full mb-2"
        >
          <Toast
            variant={toast.variant}
            title={toast.title}
            description={toast.description}
            action={
              toast.action ? (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    toast.action?.onClick();
                    dismiss(toast.id);
                  }}
                >
                  {toast.action.label}
                </Button>
              ) : undefined
            }
            onClose={() => dismiss(toast.id)}
          />
        </div>
      ))}
    </div>
  );
}
