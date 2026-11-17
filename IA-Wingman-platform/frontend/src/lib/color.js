// Tiny color helpers for white-label brand theming (no dependency).

export function hexToRgb(hex) {
  const h = hex.replace('#', '')
  const n = h.length === 3 ? h.split('').map((c) => c + c).join('') : h
  return [parseInt(n.slice(0, 2), 16), parseInt(n.slice(2, 4), 16), parseInt(n.slice(4, 6), 16)]
}

// Mix an rgb color toward a target [r,g,b] by amount 0..1.
export function mix(rgb, target, amount) {
  return rgb.map((c, i) => Math.round(c + (target[i] - c) * amount))
}

export const channels = (rgb) => rgb.join(' ')

const WHITE = [255, 255, 255]
const BLACK = [0, 0, 0]
const DARK_CANVAS = [14, 21, 18]

// Compose a CSS colour from a theme token, optionally with alpha:
//   tokenColor('--brand')        -> 'rgb(var(--brand))'
//   tokenColor('--brand', 0.12)  -> 'rgb(var(--brand) / 0.12)'
// Tokens instead of hex values means a colour keeps working in both themes and
// still follows the organisation's brand colour.
export const tokenColor = (token, alpha) =>
  alpha == null ? `rgb(var(${token}))` : `rgb(var(${token}) / ${alpha})`

// One ordered ramp for every categorical chart, derived from the brand colour.
// --chart-1 has the most contrast against the page, --chart-5 the least, in BOTH
// themes: light mixes toward white, dark mixes toward the dark canvas. Using a
// single ramp instead of a palette of unrelated hues is what keeps the dashboard
// calm — length and position carry the meaning, colour only carries order.
const RAMP_LIGHT = [
  (b) => mix(b, BLACK, 0.3),
  (b) => b,
  (b) => mix(b, WHITE, 0.26),
  (b) => mix(b, WHITE, 0.48),
  (b) => mix(b, WHITE, 0.68),
]
const RAMP_DARK = [
  (b) => mix(b, WHITE, 0.34),
  (b) => b,
  (b) => mix(b, DARK_CANVAS, 0.24),
  (b) => mix(b, DARK_CANVAS, 0.44),
  (b) => mix(b, DARK_CANVAS, 0.6),
]

function rampTokens(base, steps) {
  return Object.fromEntries(steps.map((fn, i) => [`--chart-${i + 1}`, channels(fn(base))]))
}

// Risk severity is the one place where hue itself means something, so it stays
// fixed rather than following the brand. Three levels, no more.
const SEVERITY = {
  light: { '--sev-high': '190 43 60', '--sev-med': '158 102 12', '--sev-low': '26 122 86' },
  dark: { '--sev-high': '240 138 148', '--sev-med': '227 176 92', '--sev-low': '106 197 156' },
}

// Audit status is the one categorical dimension that keeps a spectrum: a soft,
// desaturated tone per phase, plus a deeper ink of the same hue for text on it.
// Deliberately NOT derived from the brand colour — "in fieldwork" means the same
// thing at every organisation, so the hues stay fixed while the brand changes.
const STATUS = {
  light: {
    '--status-scheduled': '168 174 169', '--status-scheduled-ink': '92 101 96',
    '--status-planning': '224 184 119', '--status-planning-ink': '133 98 26',
    '--status-fieldwork': '143 179 217', '--status-fieldwork-ink': '56 92 133',
    '--status-reporting': '182 168 216', '--status-reporting-ink': '96 80 145',
    '--status-closed': '140 191 163', '--status-closed-ink': '47 109 78',
  },
  dark: {
    '--status-scheduled': '138 147 141', '--status-scheduled-ink': '186 195 189',
    '--status-planning': '217 184 124', '--status-planning-ink': '224 192 138',
    '--status-fieldwork': '150 186 224', '--status-fieldwork-ink': '164 197 231',
    '--status-reporting': '190 177 224', '--status-reporting-ink': '199 187 230',
    '--status-closed': '150 199 172', '--status-closed-ink': '162 207 182',
  },
}

// Derive the full brand token set (light + dark) from a single brand hex.
export function brandTokens(hex) {
  const base = hexToRgb(hex)
  return {
    light: {
      '--brand': channels(base),
      '--brand-hover': channels(mix(base, BLACK, 0.16)),
      '--brand-fg': channels(WHITE),
      '--brand-subtle': channels(mix(base, WHITE, 0.9)),
      '--brand-faint': channels(mix(base, WHITE, 0.95)),
      '--sidebar': channels(mix(base, BLACK, 0.42)),
      '--sidebar-2': channels(mix(base, BLACK, 0.56)),
      ...rampTokens(base, RAMP_LIGHT),
      '--chart-neutral': '148 158 153',
      ...SEVERITY.light,
      ...STATUS.light,
    },
    dark: {
      '--brand': channels(mix(base, WHITE, 0.34)),
      '--brand-hover': channels(mix(base, WHITE, 0.48)),
      '--brand-fg': channels(mix(base, BLACK, 0.85)),
      '--brand-subtle': channels(mix(base, DARK_CANVAS, 0.8)),
      '--brand-faint': channels(mix(base, DARK_CANVAS, 0.88)),
      '--sidebar': channels(mix(base, BLACK, 0.58)),
      '--sidebar-2': channels(mix(base, BLACK, 0.7)),
      ...rampTokens(mix(base, WHITE, 0.34), RAMP_DARK),
      '--chart-neutral': '104 116 110',
      ...SEVERITY.dark,
      ...STATUS.dark,
    },
  }
}
