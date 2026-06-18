# ContentFlow — Design System Rules for Figma MCP Integration

## Project Overview

ContentFlow is an AI-powered content management platform. Monorepo structure with:
- `apps/web` — Next.js 15 App Router (primary app, dark-mode SaaS dashboard)
- `apps/mobile` — Expo / React Native
- `backend/` — Python FastAPI
- `packages/` — Shared types and API client

---

## 1. Design Tokens

### Color System

**Source of truth:** `apps/web/tailwind.config.ts` + `apps/web/src/app/globals.css`

Two-layer color system:

**Layer 1 — Static hex tokens (niche/semantic):**
```ts
// apps/web/tailwind.config.ts
background: '#0f172a'       // page background
surface:    '#1e293b'       // card/panel background
'surface-hover': '#334155'  // hover state for surfaces

// Niche accent colors
tech:     '#06b6d4'  // cyan  — primary interactive color
fitness:  '#f97316'  // orange
finance:  '#10b981'  // green
beauty:   '#ec4899'  // pink
food:     '#f59e0b'  // amber
gaming:   '#8b5cf6'  // purple

// Status
success: '#10b981'
warning: '#f59e0b'
error:   '#ef4444'
info:    '#3b82f6'
```

**Layer 2 — CSS variable tokens (Radix-style, HSL):**
```css
/* apps/web/src/app/globals.css — :root */
--background: 222.2 84% 4.9%
--foreground: 210 40% 98%
--primary: 210 40% 98%
--primary-foreground: 222.2 47.4% 11.2%
--secondary: 217.2 32.6% 17.5%
--muted: 217.2 32.6% 17.5%
--muted-foreground: 215 20.2% 65.1%
--border: 217.2 32.6% 17.5%
--radius: 0.5rem
```

Referenced in Tailwind as `hsl(var(--token))`. When designing in Figma, treat the hex values as ground truth; CSS variable values are derived.

### Typography

- **Font:** Inter (Google Fonts, loaded in `apps/web/src/app/layout.tsx`)
- **Scale:** Tailwind default type scale
- **Heading pattern:** `text-2xl font-semibold` (CardTitle), `text-sm` (muted descriptions)
- No custom font size tokens — use Tailwind scale (`text-xs` → `text-2xl`)

### Spacing / Radius

```
--radius: 0.5rem  →  rounded-lg
calc(--radius - 2px)  →  rounded-md
calc(--radius - 4px)  →  rounded-sm
```

Standard Tailwind spacing scale. No custom spacing tokens.

---

## 2. Component Library

**Location:** `apps/web/src/components/ui/`

| File | Component(s) | Pattern |
|------|-------------|---------|
| `button.tsx` | `Button` | `forwardRef` + manual variant map |
| `card.tsx` | `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent` | Compound component |
| `badge.tsx` | `Badge` | CVA variants |
| `toast.tsx` + `toaster.tsx` | `Toast`, `Toaster` | CVA + Radix Toast |
| `command-bar.tsx` | `CommandBar` | `cmdk` + global `Cmd+K` |

**Layout components:** `apps/web/src/components/layout/`
- `Navigation.tsx` — fixed left sidebar, 56px wide (`w-56`)
- `WebSocketStatus.tsx` — connection indicator

**Feature components:** `apps/web/src/components/goals/`

### Component Architecture Rules

1. All components use `React.forwardRef`
2. All accept `className` prop; merge via `cn()` from `@/lib/utils`
3. No CVA on Button (manual variant map); CVA used on Badge/Toast
4. No Radix UI imports in Button/Card — pure HTML elements
5. Radix UI used for: Dialog, Dropdown, Select, Tabs, Toast, Avatar

**Button variants:**
```ts
default:     'bg-tech text-white hover:bg-tech/90'      // cyan primary
destructive: 'bg-error text-white hover:bg-error/90'
outline:     'border border-input bg-transparent hover:bg-surface'
ghost:       'hover:bg-surface'
link:        'text-tech underline-offset-4 hover:underline'
```

**Button sizes:**
```ts
default: 'h-10 px-4 py-2'
sm:      'h-9 rounded-md px-3'
lg:      'h-11 rounded-md px-8'
icon:    'h-10 w-10'
```

**Card base:** `.glass rounded-lg p-6` (glassmorphism + 0.5rem radius + 24px padding)

---

## 3. Frameworks & Libraries

### Web App (`apps/web`)

| Category | Library | Version |
|----------|---------|---------|
| Framework | Next.js App Router | 15.1.0 |
| UI | React | 19.0.0 |
| Styling | Tailwind CSS | ^3.4.0 |
| Primitives | Radix UI | various |
| Class util | clsx + tailwind-merge | — |
| Variant mgmt | class-variance-authority | — |
| Icons | lucide-react | ^0.460.0 |
| Animation | framer-motion | ^10.18.0 |
| Forms | react-hook-form + zod | — |
| Charts | recharts | ^2.10.3 |
| Command | cmdk | ^0.2.0 |
| State | zustand | ^4.4.7 |
| Data fetching | @tanstack/react-query | ^5.17.0 |
| Auth | next-auth | ^5.0.0-beta.4 |

### Mobile App (`apps/mobile`)

Expo ~54.0.0, React Native 0.81.5, Expo Router ~6.0.24. No Tailwind — use StyleSheet or NativeWind if styling is added.

### Build System

- Monorepo: pnpm workspaces + Turborepo
- Web bundler: Next.js (Webpack/Turbopack)
- Mobile bundler: Metro (Expo)

---

## 4. Styling Approach

### Method: Tailwind CSS utility-first. No CSS Modules. No styled-components.

**Class merging pattern (always use `cn()`):**
```ts
import { cn } from '@/lib/utils';
// cn() = twMerge(clsx(...)) — resolves Tailwind conflicts
```

**CSS Layers in `globals.css`:**
```
@layer base       — CSS variables, reset, scrollbar
@layer components — .glass, .neon-glow, .card-hover, .gradient-text
@layer utilities  — .scrollbar-hide, .animate-on-scroll
```

**Key component classes:**
```css
.glass        = bg-surface/50 backdrop-blur-lg border border-white/10
.neon-glow    = box-shadow: 0 0 20px rgba(6, 182, 212, 0.3)
.card-hover   = transition-all duration-200 hover:scale-[1.02] hover:shadow-lg
.gradient-text = bg-gradient-to-r from-tech to-fitness bg-clip-text text-transparent
```

### Responsive Design

- Mobile-first Tailwind breakpoints (`sm:`, `md:`, `lg:`)
- Navigation: fixed sidebar on desktop (`w-56`), drawer on mobile
- Main content offset: `ml-56` on desktop
- Grid layouts: `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` pattern

### Dark Mode

Always dark. `darkMode: ['class']` in Tailwind config, but `:root` vars already set for dark. No light mode tokens defined. **Do not add light mode variants.**

### Animations

```ts
// Custom Tailwind keyframes
animate-fade-in   // opacity 0→1, 0.3s ease-out
animate-slide-in  // translateY(10px)+opacity 0 → 0+1, 0.3s ease-out
animate-accordion-down/up  // Radix accordion content height
```

Framer Motion available for advanced animations (page transitions, complex gestures).

---

## 5. Icon System

**Library:** `lucide-react` ^0.460.0

**Import pattern:**
```tsx
import { Home, Settings, BarChart2 } from 'lucide-react';
<Home className="h-4 w-4" />
```

**Standard sizes:**
- Nav icons: `text-base` (emoji) or `h-5 w-5` (lucide)
- Button icons: `h-4 w-4`
- Icon-only buttons: `h-4 w-4` inside `size="icon"` button

**Note:** Navigation currently uses emoji icons (🏠, 📝, ✨). New components should prefer lucide-react for consistency. Emoji icons are legacy/temporary.

**No custom SVG icon system.** No icon sprite sheets.

---

## 6. Asset Management

**Images:** Next.js `<Image>` component. Remote patterns configured in `next.config.js`.

**Public assets:** `apps/web/public/` (currently empty — no static assets committed yet)

**No CDN configuration** in place. Assets served from Next.js directly.

**Mobile assets:** Expo asset system (`app.json` + `assets/` dir in `apps/mobile`).

---

## 7. Project Structure

```
contentflow/
├── apps/
│   ├── web/                          # Primary Next.js 15 app
│   │   ├── src/
│   │   │   ├── app/                  # App Router pages & layouts
│   │   │   │   ├── layout.tsx        # Root layout (Inter font, providers)
│   │   │   │   ├── globals.css       # Global styles + CSS variables
│   │   │   │   ├── (auth)/           # Auth route group
│   │   │   │   └── [feature]/        # Feature pages
│   │   │   ├── components/
│   │   │   │   ├── ui/               # Primitive UI components
│   │   │   │   ├── layout/           # Shell components (nav, status)
│   │   │   │   └── [feature]/        # Feature-specific components
│   │   │   ├── lib/                  # Utilities
│   │   │   │   ├── utils.ts          # cn(), formatters, getNicheColor()
│   │   │   │   ├── api.ts            # API client config
│   │   │   │   ├── toast.ts          # Toast helper
│   │   │   │   └── command-bar-context.tsx
│   │   │   └── hooks/                # Custom React hooks
│   │   ├── tailwind.config.ts        # Design tokens
│   │   ├── next.config.js
│   │   └── tsconfig.json             # Path alias: @/* → ./src/*
│   └── mobile/                       # Expo app
│       ├── app/
│       │   ├── (auth)/               # Auth screens
│       │   └── (tabs)/               # Tab navigation screens
│       └── lib/
├── packages/
│   ├── api-client/                   # Shared API client (@contentflow/api-client)
│   ├── types/                        # Shared TypeScript types
│   └── typescript-config/
├── backend/                          # Python FastAPI
└── pnpm-workspace.yaml
```

**Path alias:** `@/` resolves to `apps/web/src/` in the web app.

**Shared package import:** `import { authApi } from '@contentflow/api-client'`

---

## 8. Figma MCP Integration Rules

### When generating code from Figma designs:

1. **Use Tailwind utilities only.** No inline styles, no CSS modules, no styled-components.
2. **Map Figma colors to existing tokens first:**
   - Dark bg panels → `bg-surface` or `bg-background`
      - Cyan/primary actions → `bg-tech` or `text-tech`
         - Glass panels → apply `.glass` class
            - Status indicators → `bg-success`, `bg-warning`, `bg-error`, `bg-info`
            3. **Place new UI primitives** in `apps/web/src/components/ui/`
            4. **Place feature components** in `apps/web/src/components/[feature]/`
            5. **Always wrap className merging** with `cn()` from `@/lib/utils`
            6. **Use `lucide-react`** for icons — never embed raw SVG unless icon doesn't exist in lucide
            7. **Use `React.forwardRef`** on all new components
            8. **Dark mode is the only mode** — do not generate light mode variants

            ### Component generation template:
            ```tsx
            'use client'; // only if using hooks/browser APIs

            import * as React from 'react';
            import { cn } from '@/lib/utils';

            interface MyComponentProps extends React.HTMLAttributes<HTMLDivElement> {
              variant?: 'default' | 'secondary';
              }

              const MyComponent = React.forwardRef<HTMLDivElement, MyComponentProps>(
                ({ className, variant = 'default', ...props }, ref) => {
                    return (
                          <div
                                  ref={ref}
                                          className={cn(
                                                    'glass rounded-lg p-6', // base
                                                              variant === 'secondary' && 'bg-surface/30',
                                                                        className
                                                                                )}
                                                                                        {...props}
                                                                                              />
                                                                                                  );
                                                                                                    }
                                                                                                    );
                                                                                                    MyComponent.displayName = 'MyComponent';

                                                                                                    export { MyComponent };
                                                                                                    ```

                                                                                                    ### Niche color usage:
                                                                                                    ```tsx
                                                                                                    import { getNicheColor } from '@/lib/utils';
                                                                                                    // Returns hex: fitness→#f97316, tech→#06b6d4, finance→#10b981, etc.

                                                                                                    // Or use Tailwind directly:
                                                                                                    <span className="text-tech">Tech</span>
                                                                                                    <span className="text-fitness">Fitness</span>
                                                                                                    ```

                                                                                                    ### Layout shell pattern:
                                                                                                    - Fixed left nav: `w-56`, `glass border-r border-white/10`, `z-50`
                                                                                                    - Page content wrapper: `ml-56 p-6` (desktop), `p-4` (mobile)
                                                                                                    - Page grid: `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6`
                                                                                                    