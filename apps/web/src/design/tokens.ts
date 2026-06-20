/**
 * ContentFlow Design Tokens — Untitled UI public design system
 * Source of truth for colors, typography, radius, shadows.
 *
 * Consumed by tailwind.config.ts and globals.css.
 * Do NOT hardcode hex colors in components — reference via Tailwind classes.
 */

// ─── Color Scales ──────────────────────────────────────────────────────────

export const brand = {
  25: '#fcfaff',
  50: '#f9f5ff',
  100: '#f4ebff',
  200: '#e9d7fe',
  300: '#d6bbfb',
  400: '#b692f6',
  500: '#9e77ed',
  600: '#7f56d9',
  700: '#6941c6',
  800: '#53389e',
  900: '#42307d',
  950: '#2c1c5f',
} as const;

export const gray = {
  25: '#fcfcfd',
  50: '#f9fafb',
  100: '#f2f4f7',
  200: '#eaecf0',
  300: '#d0d5dd',
  400: '#98a2b3',
  500: '#667085',
  600: '#475467',
  700: '#344054',
  800: '#182230',
  900: '#101828',
  950: '#0c111d',
} as const;

export const error = {
  25: '#fffbfa',
  50: '#fef3f2',
  100: '#fee4e2',
  200: '#fecdca',
  300: '#fda29b',
  400: '#f97066',
  500: '#f04438',
  600: '#d92d20',
  700: '#b42318',
  800: '#912018',
  900: '#7a271a',
  950: '#55160c',
} as const;

export const warning = {
  25: '#fffcf5',
  50: '#fffaeb',
  100: '#fef0c7',
  200: '#fedf89',
  300: '#fec84b',
  400: '#fdb022',
  500: '#f79009',
  600: '#dc6803',
  700: '#b54708',
  800: '#93370d',
  900: '#7a2e0e',
  950: '#4e1d09',
} as const;

export const success = {
  25: '#f6fef9',
  50: '#ecfdf3',
  100: '#dcfae6',
  200: '#abefc6',
  300: '#75e0a7',
  400: '#47cd89',
  500: '#17b26a',
  600: '#079455',
  700: '#067647',
  800: '#085d3a',
  900: '#074d31',
  950: '#053321',
} as const;

export const blue = {
  25: '#f5faff',
  50: '#eff8ff',
  100: '#d1e9ff',
  200: '#b2ddff',
  300: '#84caff',
  400: '#53b1fd',
  500: '#2e90fa',
  600: '#1570ef',
  700: '#175cd3',
  800: '#1849a9',
  900: '#194185',
  950: '#102a56',
} as const;

export const indigo = {
  25: '#f5f8ff',
  50: '#eef4ff',
  100: '#e0eaff',
  200: '#c7d7fe',
  300: '#a4bcfd',
  400: '#8098f9',
  500: '#6172f3',
  600: '#444ce7',
  700: '#3538cd',
  800: '#2d31a6',
  900: '#2d3282',
  950: '#1f235b',
} as const;

export const purple = {
  25: '#fafaff',
  50: '#f4f3ff',
  100: '#ebe9fe',
  200: '#d9d6fe',
  300: '#bdb4fe',
  400: '#9b8afb',
  500: '#7a5af8',
  600: '#6938ef',
  700: '#5925dc',
  800: '#4a1fb8',
  900: '#3e1c96',
  950: '#27115f',
} as const;

export const pink = {
  25: '#fef6fb',
  50: '#fdf2fa',
  100: '#fce7f6',
  200: '#fcceee',
  300: '#faa7e0',
  400: '#f670c7',
  500: '#ee46bc',
  600: '#dd2590',
  700: '#c11574',
  800: '#9e165f',
  900: '#851651',
  950: '#4e0d30',
} as const;

export const orange = {
  25: '#fefaf5',
  50: '#fef6ee',
  100: '#fdead7',
  200: '#f9dbaf',
  300: '#f7b27a',
  400: '#f38744',
  500: '#ef6820',
  600: '#e04f16',
  700: '#b93815',
  800: '#932f19',
  900: '#772917',
  950: '#511c10',
} as const;

export const teal = {
  25: '#f6fefc',
  50: '#f0fdf9',
  100: '#ccfbef',
  200: '#99f6e0',
  300: '#5fe9d0',
  400: '#2ed3b7',
  500: '#15b79e',
  600: '#0e9384',
  700: '#107569',
  800: '#125d56',
  900: '#134e48',
  950: '#0a2926',
} as const;

// ─── Typography ────────────────────────────────────────────────────────────

type FontSizeTuple = [string, { lineHeight: string; letterSpacing?: string }];

export const typography: {
  fontFamily: { sans: string[] };
  fontSize: Record<string, FontSizeTuple>;
} = {
  fontFamily: {
    sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
  },
  fontSize: {
    // Body / utility
    'text-xs':  ['12px', { lineHeight: '18px' }],
    'text-sm':  ['14px', { lineHeight: '20px' }],
    'text-md':  ['16px', { lineHeight: '24px' }],
    'text-lg':  ['18px', { lineHeight: '28px' }],
    'text-xl':  ['20px', { lineHeight: '30px' }],
    // Display
    'display-xs':  ['24px', { lineHeight: '32px' }],
    'display-sm':  ['30px', { lineHeight: '38px' }],
    'display-md':  ['36px', { lineHeight: '44px', letterSpacing: '-0.02em' }],
    'display-lg':  ['48px', { lineHeight: '60px', letterSpacing: '-0.02em' }],
    'display-xl':  ['60px', { lineHeight: '72px', letterSpacing: '-0.02em' }],
    'display-2xl': ['72px', { lineHeight: '90px', letterSpacing: '-0.02em' }],
  },
};

// ─── Radius ────────────────────────────────────────────────────────────────

export const radius = {
  none: '0px',
  xxs: '2px',
  xs: '4px',
  sm: '6px',
  md: '8px',
  lg: '10px',
  xl: '12px',
  '2xl': '16px',
  '3xl': '20px',
  '4xl': '24px',
  full: '9999px',
} as const;

// ─── Shadows ───────────────────────────────────────────────────────────────

export const shadow = {
  xs:  '0 1px 2px 0 rgba(16, 24, 40, 0.05)',
  sm:  '0 1px 3px 0 rgba(16, 24, 40, 0.10), 0 1px 2px -1px rgba(16, 24, 40, 0.10)',
  md:  '0 4px 6px -1px rgba(16, 24, 40, 0.10), 0 2px 4px -2px rgba(16, 24, 40, 0.06)',
  lg:  '0 12px 16px -4px rgba(16, 24, 40, 0.08), 0 4px 6px -2px rgba(16, 24, 40, 0.03)',
  xl:  '0 20px 24px -4px rgba(16, 24, 40, 0.08), 0 8px 8px -4px rgba(16, 24, 40, 0.03)',
  '2xl': '0 24px 48px -12px rgba(16, 24, 40, 0.18)',
  '3xl': '0 32px 64px -12px rgba(16, 24, 40, 0.14)',
  'focus-ring-brand': '0 0 0 4px rgba(158, 119, 237, 0.24)',
  'focus-ring-gray':  '0 0 0 4px rgba(152, 162, 179, 0.14)',
  'focus-ring-error': '0 0 0 4px rgba(240, 68, 56, 0.24)',
} as const;

// ─── Aggregate ─────────────────────────────────────────────────────────────

export const tokens = {
  color: {
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
  },
  typography,
  radius,
  shadow,
} as const;

export type Tokens = typeof tokens;
export type ColorScale = typeof brand;
export type ColorStep = keyof ColorScale;

// ─── Helpers ───────────────────────────────────────────────────────────────

/**
 * Apply an alpha value (0–1) to a hex color. Returns an `rgba(...)` string.
 * Accepts #RGB, #RGBA, #RRGGBB, #RRGGBBAA.
 */
export function withAlpha(hex: string, alpha: number): string {
  if (typeof hex !== 'string' || !hex.startsWith('#')) {
    throw new Error(`withAlpha: invalid hex "${hex}"`);
  }
  const a = Math.max(0, Math.min(1, alpha));
  let h = hex.slice(1);
  if (h.length === 3 || h.length === 4) {
    h = h
      .split('')
      .map((ch) => ch + ch)
      .join('');
  }
  if (h.length !== 6 && h.length !== 8) {
    throw new Error(`withAlpha: invalid hex length "${hex}"`);
  }
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${a})`;
}

export default tokens;
