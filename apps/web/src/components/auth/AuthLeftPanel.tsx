'use client';

import * as React from 'react';
import { Zap, CheckCircle2 } from 'lucide-react';

import { cn } from '@/lib/utils';

const FEATURES = [
  'Publish to every major platform from one place',
  'AI-powered captions, scheduling, and trend insights',
  'Real-time analytics across 150+ countries',
  'Built for solo creators and full teams alike',
] as const;

const QUOTE = {
  body:
    "ContentFlow replaced four separate tools for us. Our team ships twice the content with half the effort — and the AI suggestions are uncannily on-brand.",
  author: 'Maya Patel',
  role: 'Head of Content, Lumen Studio',
} as const;

export function AuthLeftPanel() {
  return (
    <div
      className={cn(
        'relative hidden lg:flex lg:w-1/2 flex-col overflow-hidden',
        'bg-gradient-to-br from-brand-600 via-brand-700 to-brand-800',
        'text-white'
      )}
    >
      {/* Dot grid overlay */}
      <div
        aria-hidden
        className="absolute inset-0 opacity-[0.12] pointer-events-none"
        style={{
          backgroundImage:
            'radial-gradient(rgba(255,255,255,0.6) 1px, transparent 1px)',
          backgroundSize: '20px 20px',
        }}
      />

      {/* Floating gradient orbs */}
      <div
        aria-hidden
        className="absolute -top-24 -left-24 h-72 w-72 rounded-full bg-brand-400/30 blur-3xl animate-float pointer-events-none"
      />
      <div
        aria-hidden
        className="absolute -bottom-32 -right-16 h-96 w-96 rounded-full bg-purple-500/25 blur-3xl animate-float pointer-events-none"
        style={{ animationDelay: '1.2s' }}
      />
      <div
        aria-hidden
        className="absolute top-1/3 right-1/4 h-48 w-48 rounded-full bg-pink-400/15 blur-3xl animate-float pointer-events-none"
        style={{ animationDelay: '2.4s' }}
      />

      {/* Content */}
      <div className="relative z-10 flex h-full flex-col px-12 py-10 xl:px-16 xl:py-12">
        {/* Top: brand mark + tagline */}
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/15 backdrop-blur-md border border-white/20 shadow-sm">
            <Zap className="h-5 w-5 text-white" />
          </div>
          <div className="leading-tight">
            <p className="text-base font-semibold tracking-tight">ContentFlow</p>
            <p className="text-xs text-white/70">Publish once. Reach everywhere.</p>
          </div>
        </div>

        {/* Middle: testimonial card */}
        <div className="flex-1 flex items-center">
          <figure
            className={cn(
              'w-full rounded-2xl border border-white/15 bg-white/10 backdrop-blur-md',
              'p-7 xl:p-8 shadow-xl'
            )}
          >
            <svg
              aria-hidden
              className="h-7 w-7 text-white/40 mb-4"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path d="M7.17 6A5.17 5.17 0 0 0 2 11.17V18h6.83v-6.83H5.17A2 2 0 0 1 7.17 9V6Zm10 0A5.17 5.17 0 0 0 12 11.17V18h6.83v-6.83h-3.66A2 2 0 0 1 17.17 9V6Z" />
            </svg>
            <blockquote className="text-lg xl:text-xl font-medium leading-snug tracking-tight text-white">
              &ldquo;{QUOTE.body}&rdquo;
            </blockquote>
            <figcaption className="mt-5 flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-white/20 text-sm font-semibold">
                {QUOTE.author.charAt(0)}
              </span>
              <span className="leading-tight">
                <span className="block text-sm font-semibold text-white">
                  {QUOTE.author}
                </span>
                <span className="block text-xs text-white/70">{QUOTE.role}</span>
              </span>
            </figcaption>
          </figure>
        </div>

        {/* Bottom: feature checklist */}
        <ul className="space-y-3">
          {FEATURES.map((feature) => (
            <li key={feature} className="flex items-start gap-3">
              <CheckCircle2 className="h-5 w-5 shrink-0 text-white/90 mt-0.5" />
              <span className="text-sm text-white/90 leading-snug">{feature}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
