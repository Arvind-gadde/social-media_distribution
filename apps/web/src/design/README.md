# ContentFlow Design Tokens

Tier 0 of the 28-route redesign. Source of truth for all visual primitives.

Built on the **Untitled UI** public design system (brand violet, modern gray, full accent palette).

## Files

| Path | Purpose |
|------|---------|
| `src/design/tokens.ts` | Flat hex maps, type scales, radius, shadows. Single source of truth. |
| `tailwind.config.ts` | Pulls tokens into Tailwind utilities. |
| `src/app/globals.css` | Semantic CSS variables for light/dark themes. |

## Token Layers

There are two layers — keep them straight.

**Layer 1: Raw scales (from `tokens.ts`)**
Exposed as Tailwind classes: `bg-brand-600`, `text-gray-500`, `border-error-300`,
`bg-success-50`, etc. Each scale is 25 / 50 / 100 / 200 / 300 / 400 / 500 / 600 / 700 / 800 / 900 / 950.

Scales: `brand`, `gray`, `error`, `warning`, `success`, `blue`, `indigo`, `purple`, `pink`, `orange`, `teal`.

**Layer 2: Semantic tokens (from `globals.css`)**
Exposed as Tailwind classes: `bg-background`, `text-foreground`, `bg-primary`, `border-border`,
`bg-card`, `bg-muted`, `text-muted-foreground`, `bg-destructive`, `ring-ring`.

These resolve via `hsl(var(--token))` and swap automatically when `.dark` is added to `<html>`.

## When to use which

| Use case | Use |
|----------|-----|
| Page surface, card, body text | Semantic (`bg-background`, `bg-card`, `text-foreground`) |
| Primary CTA, links, brand accents | Semantic (`bg-primary`, `text-primary`) |
| Status pills, badges, alerts | Raw scale (`bg-success-50 text-success-700`) |
| Charts, data viz, content tags | Raw scale (`text-purple-600`, `bg-orange-500`) |

Reach for semantic first; fall back to raw scales when no semantic alias fits.

## Typography

Inter font (already wired). Scale exposed via `text-display-2xl`, `text-display-xl`, `text-display-lg`,
`text-display-md`, `text-display-sm`, `text-display-xs`, `text-text-xl`, `text-text-lg`, `text-text-md`,
`text-text-sm`, `text-text-xs`. Display sizes include `-2%` letter-spacing built in.

Default Tailwind sizes (`text-xs` through `text-9xl`) still work for ad-hoc cases.

## Radius

`rounded-xxs` (2px) · `rounded-xs` (4px) · `rounded-sm` (6px) · `rounded-md` (8px) ·
`rounded-lg` (var, default 8px) · `rounded-xl` (12px) · `rounded-2xl` (16px) ·
`rounded-3xl` (20px) · `rounded-4xl` (24px) · `rounded-full`.

## Shadows

`shadow-xs` · `shadow-sm` · `shadow-md` · `shadow-lg` · `shadow-xl` · `shadow-2xl` · `shadow-3xl`.

Focus rings: `shadow-focus-brand`, `shadow-focus-gray`, `shadow-focus-error`,
or utility classes `.focus-ring-brand`, `.focus-ring-gray`, `.focus-ring-error`.

## Dark mode

Toggle by adding/removing `.dark` on `<html>`. All semantic tokens swap automatically.
Raw scales (`bg-brand-600`, etc.) do not — pick a scale step that reads well in both modes,
or use the semantic alias.

## Helpers

```ts
import { withAlpha, tokens } from '@/design/tokens';

withAlpha(tokens.color.brand[600], 0.12); // -> "rgba(127, 86, 217, 0.12)"
```

Use this for inline styles, chart strokes, or anywhere Tailwind alpha modifiers can't reach.

## Niche colors (legacy)

`tech`, `fitness`, `finance`, `beauty`, `food`, `gaming` are still mapped — they now point
into the Untitled palette (e.g. `tech` = `brand-600`, `gaming` = `purple-600`). Prefer the
Untitled scale names in new code.
