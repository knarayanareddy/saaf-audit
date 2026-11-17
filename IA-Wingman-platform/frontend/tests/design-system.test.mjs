// The visual quality bar, as a test rather than as an opinion.
//
// A design system only stays one system if its rules are checkable. These assert
// the decisions behind the enterprise pass: elevation is a hierarchy, radius is
// tightened, colour is rationed, and hover never lifts a surface off the page.
//
// Run from the frontend dir:  node --test tests/design-system.test.mjs
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

const SRC = fileURLToPath(new URL('../src/', import.meta.url))

function walk(dir) {
  return readdirSync(dir).flatMap((name) => {
    const full = join(dir, name)
    return statSync(full).isDirectory() ? walk(full) : full.endsWith('.jsx') ? [full] : []
  })
}

// The screens this pass covers, plus the shared primitives they are built from.
//
// The agent surfaces were added once severity moved onto the sev tokens: they
// were thirty files painting the same "must fix" in rose-600 here and red-500
// there, which is precisely what a quality bar written as a test is for. The
// categorical hues (violet, sky, blue) are NOT covered yet — they distinguish
// kinds in a list rather than severity, and belong on the chart tokens. The
// rule below names them explicitly so this is a stated exception, not a gap
// nobody noticed.
const IN_SCOPE = [
  'pages/DashboardPage.jsx',
  'pages/EngagementsPage.jsx',
  'pages/BoardReportPage.jsx',
  'pages/WorkflowPage.jsx',
  'pages/AgentsPage.jsx',
  'pages/AgentStudioPage.jsx',
  'pages/QualityHubPage.jsx',
  'pages/FieldworkPage.jsx',
  'pages/RacmSpinePage.jsx',
  'pages/planning/',
  'pages/reporting/',
  'components/dashboard/',
  'components/workflow/',
  'components/racm/',
  'components/review/',
  'components/ai/',
  'components/planning/',
  'components/layout/LeftSidebar.jsx',
  'components/ui/',
  'components/charts/',
]

const files = walk(SRC)
  .map((f) => ({ path: f.slice(SRC.length).replace(/\\/g, '/'), body: readFileSync(f, 'utf8') }))
  .filter((f) => IN_SCOPE.some((s) => f.path.startsWith(s)))

// Comments explain decisions; they are not markup. Strip them before matching so
// a sentence about the old design never fails the rule it documents.
const code = (body) => body.replace(/\/\/[^\n]*/g, '').replace(/\/\*[\s\S]*?\*\//g, '')

const hits = (pattern) =>
  files.flatMap((f) => (code(f.body).match(pattern) ? [f.path] : []))

test('in-scope files exist (the scan is actually looking at something)', () => {
  assert.ok(files.length > 20, `only ${files.length} files matched — check IN_SCOPE`)
})

test('no surface floats: shadow-card and shadow-xl are gone', () => {
  assert.deepEqual(hits(/\bshadow-(card|card-hover|xl)\b/), [])
})

test('only genuinely floating things cast a shadow', () => {
  const allowed = new Set([
    'components/ui/Modal.jsx',               // dialog
    'components/ui/AIFieldHelper.jsx',       // popover
    'components/ui/Toast.jsx',               // floats over the page
    'components/ui/Tooltip.jsx',             // floats over its trigger
    'components/workflow/NodeInspector.jsx', // popover
    'components/workflow/ShowcaseTour.jsx',  // overlay caption bar
    'components/layout/LeftSidebar.jsx',     // identity menu
    'components/layout/IdentityPicker.jsx', // dropdown over the page
    'components/palette/CommandPalette.jsx',// overlay
    'components/ai/AIChatPanel.jsx',        // slide-over
  ])
  const offenders = hits(/\bshadow-elevated\b/).filter((p) => !allowed.has(p))
  assert.deepEqual(offenders, [])
})

test('severity is a token, never a hue picked per component', () => {
  // emerald/amber/red/rose carried severity and are now sev-low/med/high.
  // violet/sky/blue/indigo/purple are categorical — a separate pass.
  const offenders = hits(/\b(?:text|bg|border|ring|divide|fill|stroke)-(?:emerald|rose|amber|red|green|teal|yellow|orange)-\d{2,3}\b/)
  assert.deepEqual(offenders, [])
})

test('a token is not written twice for dark mode', () => {
  // A sev/status/brand token already resolves per theme; a dark: variant beside
  // it is the same value in two places, and the two drift.
  assert.deepEqual(hits(/dark:(?:text|bg|border|ring)-(?:sev|brand|status|fg|surface|line)-/), [])
})

test('hover never lifts a surface off the page', () => {
  assert.deepEqual(hits(/hover:-translate-y/), [])
})

test('the largest radius is reserved for dialogs and popovers', () => {
  const allowed = new Set([
    'components/ui/Modal.jsx',
    'components/workflow/NodeInspector.jsx',
    'components/workflow/ShowcaseTour.jsx',
    'components/layout/IdentityPicker.jsx',
    'components/palette/CommandPalette.jsx',
    'components/ai/AIChatPanel.jsx',
  ])
  const offenders = hits(/\brounded-2xl\b/).filter((p) => !allowed.has(p))
  assert.deepEqual(offenders, [])
})

test('colour comes from tokens, never from a raw Tailwind hue', () => {
  // Severity lives in --sev-*, categories in --chart-*, brand in --brand.
  //
  // violet / sky / blue / indigo / purple are excluded for now, and on purpose.
  // On the agent screens they are CATEGORICAL — the audit-memory panel colours
  // finding / risk / control / scope apart, Fieldwork tags a source kind — so
  // collapsing them to one neutral would erase a distinction the reader uses.
  // They belong on --chart-1..5, and picking which index each category takes is
  // a judgement per list rather than a substitution. Until that pass happens
  // this is a named exception, not an oversight; `severity is a token` above
  // already holds the line on the hues that carry meaning.
  assert.deepEqual(hits(/\b(?:bg|text|border|ring|divide|from|to)-(?:emerald|rose|amber|teal|cyan|fuchsia|lime|orange|pink|slate|gray|zinc|neutral|stone|red|green|yellow)-\d/), [])
})

test('controls are sized to a fixed height, not to a touch-sized one', () => {
  // h-11 is 44px — a phone target. Desktop productivity software sits at 30–40px.
  assert.deepEqual(hits(/\bh-1[12]\b/), [])
})

test('the type scale is used for headings instead of ad-hoc text sizes', () => {
  const scale = readFileSync(join(SRC, 'index.css'), 'utf8')
  for (const cls of ['.text-display', '.text-h1', '.text-h2', '.text-h3', '.text-caption', '.text-metric', '.text-meta']) {
    assert.ok(scale.includes(cls), `${cls} is missing from the type scale`)
  }
  // A page title is 22px; anything bigger is a regression to the template look.
  assert.match(scale, /\.text-h1\s*\{[^}]*font-size:\s*1\.375rem/)
})

test('the radius scale is tightened at the container end', () => {
  const cfg = readFileSync(fileURLToPath(new URL('../tailwind.config.js', import.meta.url)), 'utf8')
  assert.match(cfg, /xl:\s*'0\.625rem'/)      // 10px
  assert.match(cfg, /'2xl':\s*'0\.75rem'/)    // 12px
  assert.match(cfg, /card:\s*'none'/)
})

test('every theme token used by a chart or severity is actually defined', () => {
  const css = readFileSync(join(SRC, 'index.css'), 'utf8')
  const STATUS = ['scheduled', 'planning', 'fieldwork', 'reporting', 'closed']
  const tokens = [
    '--chart-1', '--chart-2', '--chart-3', '--chart-4', '--chart-5', '--chart-neutral',
    '--sev-high', '--sev-med', '--sev-low', '--line-subtle', '--surface-raised',
    ...STATUS.flatMap((s) => [`--status-${s}`, `--status-${s}-ink`]),
  ]
  for (const token of tokens) {
    const defined = css.split(token).length - 1
    assert.ok(defined >= 2, `${token} must be defined for both light and dark (found ${defined})`)
  }
})
