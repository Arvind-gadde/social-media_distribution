import type { Config } from 'tailwindcss';
import {
  brand,
  gray,
  error,
  warning,
  success,
  blue,
  indigo,
  purple,
  pink,
  orange,
  teal,
  radius,
  shadow,
  typography,
} from './src/design/tokens';

const config: Config = {
  darkMode: ['class'],
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      // ── Color system ────────────────────────────────────────────────
      colors: {
        // Full Untitled UI scales (use directly: `bg-brand-600`, `text-gray-500`)
        brand,
        gray,
        error,
        warning,
        success,
        blue,
        indigo,
        purple,
        pink,
        orange,
        teal,

        // Semantic tokens — driven by CSS variables in globals.css
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        sidebar: 'hsl(var(--sidebar))',

        // Legacy compat — keep existing class names working
        surface: 'hsl(var(--card))',
        'surface-hover': 'hsl(var(--secondary))',

        // Niche accents (content categorization) — rebranded to Untitled palette
        tech: brand[600],       // violet primary
        fitness: orange[500],
        finance: success[600],
        beauty: pink[500],
        food: warning[500],
        gaming: purple[600],

        // Status flat aliases — point to Untitled scales
        info: blue[500],
      },

      // ── Typography ─────────────────────────────────────────────────
      fontFamily: typography.fontFamily,
      fontSize: typography.fontSize,

      // ── Radius ─────────────────────────────────────────────────────
      borderRadius: {
        none: radius.none,
        xxs: radius.xxs,
        xs: radius.xs,
        sm: 'calc(var(--radius) - 4px)',
        md: 'calc(var(--radius) - 2px)',
        lg: 'var(--radius)',
        xl: radius.xl,
        '2xl': radius['2xl'],
        '3xl': radius['3xl'],
        '4xl': radius['4xl'],
        full: radius.full,
      },

      // ── Shadows ────────────────────────────────────────────────────
      boxShadow: {
        xs: shadow.xs,
        sm: shadow.sm,
        md: shadow.md,
        lg: shadow.lg,
        xl: shadow.xl,
        '2xl': shadow['2xl'],
        '3xl': shadow['3xl'],
        'focus-brand': shadow['focus-ring-brand'],
        'focus-gray': shadow['focus-ring-gray'],
        'focus-error': shadow['focus-ring-error'],
        // Legacy compat aliases used by existing components
        soft: shadow.xs,
        medium: shadow.md,
        large: shadow.lg,
        'glow-primary': '0 0 24px -4px hsl(var(--primary) / 0.35)',
        'glow-success': `0 0 24px -4px ${success[500]}59`,
        'inner-sm': 'inset 0 1px 2px 0 rgb(0 0 0 / 0.06)',
      },

      // ── Animations (preserved) ─────────────────────────────────────
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
        'fade-up': {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'slide-in-left': {
          from: { opacity: '0', transform: 'translateX(-12px)' },
          to: { opacity: '1', transform: 'translateX(0)' },
        },
        'scale-in': {
          from: { opacity: '0', transform: 'scale(0.95)' },
          to: { opacity: '1', transform: 'scale(1)' },
        },
        shimmer: {
          from: { backgroundPosition: '-200% 0' },
          to: { backgroundPosition: '200% 0' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-6px)' },
        },
        pulse: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        'fade-up': 'fade-up 0.3s ease-out',
        'fade-in': 'fade-in 0.25s ease-out',
        'slide-in-left': 'slide-in-left 0.25s ease-out',
        'scale-in': 'scale-in 0.2s ease-out',
        shimmer: 'shimmer 2s ease-in-out infinite',
        float: 'float 3s ease-in-out infinite',
        pulse: 'pulse 2s cubic-bezier(0.4,0,0.6,1) infinite',
      },

      // ── Backgrounds (preserved) ────────────────────────────────────
      backgroundImage: {
        'grid-light':
          'linear-gradient(hsl(var(--border)) 1px, transparent 1px), linear-gradient(90deg, hsl(var(--border)) 1px, transparent 1px)',
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        brand: `linear-gradient(135deg, ${brand[200]} 0%, ${brand[400]} 100%)`,
        'brand-mobile': `linear-gradient(135deg, ${brand[100]} 0%, ${brand[300]} 100%)`,
        'brand-deep': `linear-gradient(135deg, ${brand[600]} 0%, ${brand[800]} 100%)`,
      },
      backgroundSize: {
        grid: '32px 32px',
      },
    },
  },
  plugins: [],
};

export default config;
