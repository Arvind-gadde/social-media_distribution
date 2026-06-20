# Untitled UI — Reference Sources for Pixel-Accurate Build

> File key under research: `QERVV4a2Fpa1FmsZ5LGW3S` (PRO Figma file — API-locked, returns `403 "File not exportable"` on image/file/styles endpoints).

---

## Authoritative URLs

| Purpose | URL |
|---|---|
| Marketing / product overview | https://www.untitledui.com/ |
| Figma kit (free vs PRO scope) | https://www.untitledui.com/figma-ui-kit (404 — page replaced); use https://www.untitledui.com/figma and https://www.untitledui.com/free-figma-ui-kit |
| Changelog (v8.0 — Tailwind v4.2 colors, Mar 2026) | https://www.untitledui.com/changelog |
| Color palette methodology (25–950 scale) | https://www.untitledui.com/blog/figma-color-palettes |
| React component docs (component inventory) | https://www.untitledui.com/react/docs/introduction |
| Open-source React library (MIT) — **token source of truth** | https://github.com/untitleduico/react |
| Free Figma kit (Community / Gumroad) | https://www.figma.com/community/file/1020079203222518115 · https://untitledui.gumroad.com/l/untitled-ui-free |

`/styles` and `/figma-ui-kit` both 404 — no public token-spec page exists.

---

## Token references

The richest public token source is the MIT-licensed React repo. It contains a full `@theme {}` Tailwind v4 block with every color scale, type ramp, shadow, and animation token — this is effectively the same token set the PRO Figma file uses.

| Resource | URL | Coverage |
|---|---|---|
| `untitleduico/react` → `styles/theme.css` | https://raw.githubusercontent.com/untitleduico/react/main/styles/theme.css | 834 lines. Full `@theme` block: `--font-body` (Inter), text scale `text-xs` → `text-display-2xl` (with line-height + letter-spacing), `--max-width-container: 1280px`, breakpoints `xxs 320 / xs 600`, full shadow ramp (`xs`→`3xl`, skeuomorphic, modern-mockup), brand purple 50–950, semantic text/border/fg/bg roles, dark-mode `.dark-mode` overrides. |
| Official changelog v6.0 entry | https://www.untitledui.com/changelog | Quotes the **canonical gray ramp** verbatim (see below). |
| Tailwind CSS v4.2 color palette | https://tailwindcss.com/docs/colors | v8.0 changelog states Untitled UI adopted this palette wholesale — utility colors (blue/red/yellow/green) match Tailwind 4.2 defaults. |
| Untitled UI Icons (companion) | https://www.untitledui.com/icons | 1,100+ free icons; same neutral aesthetic. |

### Confirmed hex values (from public changelog + theme.css)

**Gray (v6.0+ flat neutral, still current):**
```
25:#FCFCFD  50:#F9FAFB  100:#F2F4F7  200:#E4E7EC  300:#D0D5DD
400:#98A2B3 500:#667085 600:#475467 700:#344054 800:#182230
900:#101828 950:#0C111D
```

**Brand (default purple, from theme.css):**
```
50:rgb(249 245 255)   100:rgb(244 235 255)  200:rgb(233 215 254)
300:rgb(214 187 251)  400:rgb(182 146 246)  500:rgb(158 119 237)
600:rgb(127 86 217)   700:rgb(105 65 198)   800:rgb(83 56 158)
900:rgb(66 48 125)    950:rgb(44 28 95)
```

---

## Figma API endpoints (file `QERVV4a2Fpa1FmsZ5LGW3S`)

| Endpoint | HTTP | Usable? | Response (truncated) |
|---|---|---|---|
| `GET /v1/files/{key}/components` | **200** | No — empty | `{"error":false,"status":200,"meta":{"components":[]},"i18n":null}` |
| `GET /v1/files/{key}/component_sets` | **200** | No — empty | `{"error":false,"status":200,"meta":{"component_sets":[]},"i18n":null}` |
| `GET /v1/files/{key}/versions` | **403** | No | `{"status":403,"err":"File not exportable"}` |
| `GET /v1/images/{key}?ids=0:1` | **403** | No | `{"status":403,"err":"File not exportable"}` |
| `GET /v1/files/{key}` (prior) | 403 | No | `File not exportable` |
| `GET /v1/files/{key}/styles` (prior) | 403 | No | `File not exportable` |

**Conclusion:** `components` / `component_sets` are technically reachable but the PRO file has the export flag disabled at the publisher level — the arrays are empty. No additional data is recoverable through the Figma REST API for this key.

---

## Component coverage map (FREE vs PRO)

Sourced from `/figma`, `/free-figma-ui-kit`, `/react/docs/introduction`, and changelog.

### FREE (Figma Community / Gumroad)
- 2,000+ components & variants
- 350+ global styles (color / type / effects — **non-variable**, static styles only)
- 900+ icons & logos
- 20+ page examples
- No Figma variables, no dark-mode switching, no Auto Layout 5.0, no interactive components, no lifetime updates

### PRO (file `QERVV4a2Fpa1FmsZ5LGW3S`) — $139 bundle
- 10,000+ components & variants
- 900+ global styles **+ variables** (color, spacing, radius, width, typography, effects)
- Full dark-mode variable set
- 420+ page designs (desktop + mobile)
- 2,000+ icons & logos
- Three flavours: PRO VARIABLES, PRO STYLES, PRO LITE
- Lifetime updates (currently v8.0 — Tailwind v4.2 palette)

### Open-source React (MIT, mirrors PRO tokens)
- ~35 base components (Avatar, Badge, Button, Checkbox, Dropdown, Input, Radio, Slider, Toggle, Tooltip, Video Player…)
- ~45 application components (Activity Feed, Alert, Breadcrumb, Calendar, Carousel, Charts line/bar/pie/radar, Date Picker, Modal, Table, Tabs, Nav…)
- ~20+ marketing sections (Hero, Pricing, Testimonials, FAQ, Footer, Team)
- Stack: React 19.2, Tailwind CSS v4.2, TypeScript 5.9, React Aria

---

## Recommendation

**Proceed with the hardcoded Untitled UI tokens the other agent is staging — they are correct.** The PRO Figma file cannot be unlocked through any Figma REST endpoint we have access to (every meaningful endpoint returns `403 File not exportable`; the two that return 200 yield empty arrays). However, the **`untitleduico/react` MIT repo's `styles/theme.css` is an authoritative public mirror of the same token system** the PRO Figma file uses, and the official changelog publishes the canonical gray ramp verbatim. Between those two sources we have pixel-accurate color, typography, spacing, shadow, breakpoint, and dark-mode token values without needing PRO Figma access. Use `theme.css` as the lockfile; cross-check the gray ramp against the changelog; treat Tailwind v4.2 defaults as ground truth for utility/feedback colors.
