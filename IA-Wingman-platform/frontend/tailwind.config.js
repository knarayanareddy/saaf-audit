/** @type {import('tailwindcss').Config} */
const withAlpha = (v) => `rgb(var(${v}) / <alpha-value>)`

export default {
  darkMode: ['selector', '[data-theme="dark"]'],
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        heading: ['var(--font-display)', 'sans-serif'],
        body: ['var(--font-body)', 'sans-serif'],
      },
      colors: {
        // Semantic, theme-aware tokens (channel-based → opacity modifiers work)
        canvas: withAlpha('--canvas'),
        surface: {
          DEFAULT: withAlpha('--surface'),
          2: withAlpha('--surface-2'),
          3: withAlpha('--surface-3'),
          // What genuinely sits ABOVE the page: modals, popovers, the palette.
          raised: withAlpha('--surface-raised'),
        },
        fg: {
          DEFAULT: withAlpha('--fg'),
          muted: withAlpha('--fg-muted'),
          subtle: withAlpha('--fg-subtle'),
        },
        line: {
          DEFAULT: withAlpha('--line'),
          strong: withAlpha('--line-strong'),
          // Separators INSIDE a section — lighter than a container's own border.
          subtle: withAlpha('--line-subtle'),
        },
        sidebar: {
          DEFAULT: withAlpha('--sidebar'),
          2: withAlpha('--sidebar-2'),
        },
        brand: {
          DEFAULT: withAlpha('--brand'),
          hover: withAlpha('--brand-hover'),
          fg: withAlpha('--brand-fg'),
          subtle: withAlpha('--brand-subtle'),
          faint: withAlpha('--brand-faint'),
          // Fixed accents (rarely theme-critical)
          light: '#A8D5A2',
          mid: '#2F7A5B',
          periwinkle: '#9B8EC4',
        },
        // Ordered ramp for categorical charts, derived from the brand colour.
        chart: {
          1: withAlpha('--chart-1'),
          2: withAlpha('--chart-2'),
          3: withAlpha('--chart-3'),
          4: withAlpha('--chart-4'),
          5: withAlpha('--chart-5'),
          neutral: withAlpha('--chart-neutral'),
        },
        // Risk severity — one token set instead of scattered rose/amber/emerald,
        // so a single class reads correctly in light AND dark.
        sev: {
          high: withAlpha('--sev-high'),
          med: withAlpha('--sev-med'),
          low: withAlpha('--sev-low'),
        },
      },
      // Elevation is a hierarchy, not decoration. A surface that simply sits ON
      // the page is separated by a 1px border, never by a shadow; only things
      // that genuinely float (modals, popovers, the palette) cast one.
      boxShadow: {
        card: 'none',
        'card-hover': 'none',
        sm: '0 1px 1px rgb(var(--shadow-rgb) / 0.03)',
        DEFAULT: '0 1px 2px rgb(var(--shadow-rgb) / 0.05)',
        md: '0 2px 6px rgb(var(--shadow-rgb) / 0.06)',
        lg: '0 4px 12px rgb(var(--shadow-rgb) / 0.08)',
        xl: '0 6px 20px rgb(var(--shadow-rgb) / 0.10), 0 1px 2px rgb(var(--shadow-rgb) / 0.06)',
        elevated: '0 6px 20px rgb(var(--shadow-rgb) / 0.10), 0 1px 2px rgb(var(--shadow-rgb) / 0.06)',
        ring: '0 0 0 2px rgb(var(--brand) / 0.35)',
      },
      // Tightened one step across the board: 14px/18px read as a consumer app.
      // Redefining the scale re-shapes every existing call site at once.
      borderRadius: {
        md: '0.375rem',    // 6px  — buttons, inputs, filters, tabs, chips
        lg: '0.5rem',      // 8px  — cards, list rows, menu items
        xl: '0.625rem',    // 10px — panels, larger surfaces
        '2xl': '0.75rem',  // 12px — modals, command palette
      },
      keyframes: {
        'fade-in': { from: { opacity: '0' }, to: { opacity: '1' } },
        'fade-in-up': {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'scale-in': {
          from: { opacity: '0', transform: 'scale(0.97)' },
          to: { opacity: '1', transform: 'scale(1)' },
        },
      },
      transitionTimingFunction: {
        // One curve app-wide: quick out of the gate, settles without bouncing.
        DEFAULT: 'cubic-bezier(0.2, 0, 0, 1)',
        crisp: 'cubic-bezier(0.2, 0, 0, 1)',
      },
      transitionDuration: {
        DEFAULT: '160ms',
      },
      animation: {
        'fade-in': 'fade-in 0.25s ease both',
        'fade-in-up': 'fade-in-up 0.35s cubic-bezier(0.16,1,0.3,1) both',
        'scale-in': 'scale-in 0.18s cubic-bezier(0.16,1,0.3,1) both',
      },
    },
  },
  plugins: [],
}
