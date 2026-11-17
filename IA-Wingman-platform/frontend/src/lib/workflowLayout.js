// Layout and interaction model for the Workflow page. Pure and dependency-free
// so it runs under `node --test` (tests/workflow.test.mjs).
//
// Phases stack as horizontal bands. Positions are hand-tuned for the known
// lifecycle graph, with one rule the tests enforce: a stage entered from another
// band sits on its band's top row, so connecting lines run through gutters and
// gaps and never through a card. A stage the map does not know yet still gets
// the first free cell of its band rather than disappearing.

export const GRID = {
  nodeW: 184,
  nodeH: 58,
  colGap: 24,
  rowGap: 10,
  padX: 20,
  headH: 40,
  padTop: 6,
  padBottom: 18,
  bandGap: 18,
  cols: 5,
  radius: 8,
}

export const POSITIONS = {
  // Planning — understand, scope, assess the risk, build and sign the spine.
  topic_intelligence: [0, 0], process_understanding: [0, 1],
  frameworks: [1, 0], supervisory_guidance: [1, 1],
  // The RCSA sits just before the background risk assessment, because that is
  // what it changes: what the audit starts from is the business's own view of
  // its risks, not a blank page.
  scope: [2, 0], kickoff: [2, 1], rcsa_import: [2, 2],
  bra: [3, 0], anl: [3, 1], resource_plan: [3, 2],
  work_program: [4, 0], racm_scoping: [4, 1],
  // Gathering — asking people, requesting documents, matching what arrives.
  // Every one of these is entered from Planning, so all four sit on the top row.
  interview_guide: [0, 0], drl: [1, 0], pbc_assistant: [2, 0], racm_evidence_chase: [3, 0],
  interview_companion: [0, 1],
  // Fieldwork
  fieldwork: [0, 0], racm_governance: [1, 0], racm_data_analysis: [2, 0],
  vendor_guard: [1, 1], privacy_guard: [2, 1],
  // Reporting
  findings: [0, 0], report_draft: [1, 0],
  // Quality
  quality_coverage: [0, 0], quality_review: [1, 0], quality_peer_review: [2, 0],
}

// The narrated tour. Order follows the lifecycle, and the text is deliberately
// concrete: a demo that says "agents help you" teaches nothing, while one that
// names which agent reads what, and who signs it off, teaches the method.
//
// Two rules hold this list together:
//
//  * No `duration` here. `tourFor` derives it from the sentence, so a beat can be
//    rewritten without anyone remembering to retime it.
//  * A beat's narration stays under ~230 characters, which is where `durationFor`
//    hits its ceiling. Past that the clock stops growing with the text and the
//    caption would be pulled off screen mid-sentence when the voice is muted.
export const TOUR_BEATS = [
  {
    id: 'lifecycle', focus: [],
    title: 'One audit, end to end',
    text: 'Every engagement moves from planning through fieldwork to reporting — each step visible, traceable and yours to steer.',
  },
  {
    id: 'assistant', focus: [],
    title: 'Your line to the agents',
    text: 'Ask in plain language. The assistant proposes the step; you accept or dismiss. It never runs one by itself.',
  },
  {
    id: 'propose', particles: true,
    focus: ['topic_intelligence', 'frameworks', 'process_understanding', 'supervisory_guidance', 'scope'],
    title: 'AI proposes',
    text: 'Topic Intelligence reads the regulation, Process Understanding drafts the walkthrough, Supervisory Guidance adds what the regulator published. All of it is a proposal.',
  },
  {
    id: 'kickoff', particles: true,
    focus: ['topic_intelligence', 'kickoff'],
    title: 'Planning, part one',
    text: 'The kick-off meeting belongs to part one, and its agenda is drafted from what those scans found.',
  },
  {
    id: 'decide',
    focus: ['scope', 'bra', 'work_program'],
    title: 'You decide',
    text: 'Nothing moves forward until you accept it. Scope items, background risks and the Work Program all wait for your sign-off.',
  },
  {
    id: 'anl',
    focus: ['scope', 'anl'],
    title: 'The letter follows the scope',
    text: 'The Audit Notification Letter is written from Scope & Objectives — only the items you accepted reach the auditee.',
  },
  {
    id: 'interviews', particles: true,
    focus: ['interview_guide', 'interview_companion'],
    title: 'Interviews, prepared and captured',
    text: 'The Interview Guide asks per persona, each question traceable to a risk. The Companion turns the answers into observations and minutes.',
  },
  {
    id: 'unlock', particles: true,
    focus: ['work_program', 'fieldwork'],
    title: 'Your sign-off unlocks fieldwork',
    text: 'Signing off the Work Program is the hard gate. Fieldwork stays locked until you do.',
  },
  {
    id: 'fieldwork', particles: true,
    focus: ['racm_scoping', 'racm_governance', 'racm_data_analysis'],
    title: 'Agents test the controls',
    text: 'Governance assessment reads the policies against the frameworks; data analysis runs the whole population rather than a sample.',
  },
  {
    id: 'guards', particles: true,
    focus: ['vendor_guard', 'privacy_guard'],
    title: 'Two guards on the edges',
    text: 'Vendor Guard scores a third party against eight EU and Dutch frameworks. Privacy Guard masks personal data by role — no model, no cost.',
  },
  {
    id: 'evidence', particles: true,
    // Isabelle first: this set reaches from Planning down to Fieldwork and does
    // not fit on one screen, so focus[0] is what the tour pans to and must be
    // the card the sentence opens with.
    focus: ['pbc_assistant', 'racm_evidence_chase', 'drl'],
    title: 'Chasing the evidence',
    text: 'PBC means Prepared By Client — what the auditee owes you. Each test says what evidence it needs, so Isabelle’s requests name the tests they settle, and evidence nobody asked for shows as a number.',
  },
  {
    id: 'report', particles: true,
    focus: ['fieldwork', 'findings', 'report_draft'],
    title: 'From evidence to report',
    text: 'Observations become 5C findings. A second agent challenges each rating before you approve the report.',
  },
  {
    id: 'quality',
    focus: ['quality_coverage', 'quality_review'],
    title: 'Quality runs alongside',
    text: 'Coverage checks that every scoped area has risks, controls and tests behind it — by reference where there is one, and it says so where it had to guess.',
  },
  {
    id: 'peer_review',
    focus: ['quality_peer_review'],
    title: 'The AI peer review',
    text: 'An independent second opinion, scored against the Global Internal Audit Standards. It rates only what the file evidences — not produced reads as not evidenced, never as a pass.',
  },
]

export function buildLayout(workflow) {
  const g = GRID
  const width = g.padX * 2 + g.cols * g.nodeW + (g.cols - 1) * g.colGap
  const phases = workflow.phases || []
  const members = new Map(phases.map((p) => [p.key, []]))
  for (const node of workflow.nodes || []) {
    const list = members.get(node.phase) || members.get(phases[0]?.key)
    if (list) list.push(node)
  }

  const bands = []
  const nodes = []
  let y = 0
  phases.forEach((phase, bandIndex) => {
    const taken = new Set()
    const cells = []
    const list = members.get(phase.key)
    for (const node of list) {
      const pos = POSITIONS[node.key]
      if (pos && pos[0] < g.cols && !taken.has(`${pos[0]},${pos[1]}`)) {
        taken.add(`${pos[0]},${pos[1]}`)
        cells.push({ node, col: pos[0], row: pos[1] })
      }
    }
    for (const node of list) {
      if (cells.some((c) => c.node === node)) continue
      let i = 0
      while (taken.has(`${i % g.cols},${Math.floor(i / g.cols)}`)) i++
      const col = i % g.cols
      const row = Math.floor(i / g.cols)
      taken.add(`${col},${row}`)
      cells.push({ node, col, row })
    }

    const rows = Math.max(1, ...cells.map((c) => c.row + 1))
    const h = g.headH + g.padTop + rows * g.nodeH + (rows - 1) * g.rowGap + g.padBottom
    const band = { ...phase, index: bandIndex, x: 0, y, w: width, h, rows, done: 0, total: cells.length }
    for (const { node, col, row } of cells) {
      if (node.status === 'complete') band.done += 1
      nodes.push({
        ...node,
        band: phase.key,
        bandIndex,
        col,
        row,
        x: g.padX + col * (g.nodeW + g.colGap),
        y: y + g.headH + g.padTop + row * (g.nodeH + g.rowGap),
        w: g.nodeW,
        h: g.nodeH,
      })
    }
    bands.push(band)
    y += h + g.bandGap
  })
  nodes.sort((a, b) => a.bandIndex - b.bandIndex || a.col - b.col || a.row - b.row)

  const byKey = Object.fromEntries(nodes.map((n) => [n.key, n]))
  const valid = (workflow.edges || []).filter((e) => byKey[e.from] && byKey[e.to])
  const gutters = new Map()
  const runs = new Map()
  const group = (map, key, e) => map.set(key, [...(map.get(key) || []), e])
  for (const e of valid) {
    const a = byKey[e.from]
    const b = byKey[e.to]
    if (b.bandIndex > a.bandIndex) {
      group(gutters, `${a.bandIndex}:${a.col}`, e)
      group(runs, b.bandIndex, e)
    }
  }
  const spread = (map, key, e, step) => {
    const list = map.get(key)
    return (list.indexOf(e) - (list.length - 1) / 2) * step
  }

  const edges = valid.map((e) => {
    const a = byKey[e.from]
    const b = byKey[e.to]
    let route
    if (a.bandIndex === b.bandIndex) route = routeWithinBand(a, b)
    else if (b.bandIndex > a.bandIndex) {
      route = routeAcrossBands(a, b, bands[b.bandIndex],
        spread(gutters, `${a.bandIndex}:${a.col}`, e, 6), spread(runs, b.bandIndex, e, 4))
    } else route = straight(a, b)
    return { ...e, id: `${e.from}->${e.to}`, ...route }
  })

  return { width, height: Math.max(0, y - g.bandGap), bands, nodes, edges, byKey }
}

function routeWithinBand(a, b) {
  if (a.col === b.col) {
    const x = a.x + a.w / 2
    const down = b.y > a.y
    const y1 = down ? a.y + a.h : a.y
    const y2 = down ? b.y : b.y + b.h
    return { path: `M ${x} ${y1} L ${x} ${y2}`, mid: { x, y: (y1 + y2) / 2 }, end: { x, y: y2 } }
  }
  const forward = b.x > a.x
  const x1 = forward ? a.x + a.w : a.x
  const x2 = forward ? b.x : b.x + b.w
  const y1 = a.y + a.h / 2
  const y2 = b.y + b.h / 2
  const dx = Math.max(14, Math.abs(x2 - x1) / 2) * (forward ? 1 : -1)
  return {
    path: `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`,
    mid: { x: (x1 + x2) / 2, y: (y1 + y2) / 2 },
    end: { x: x2, y: y2 },
  }
}

function routeAcrossBands(a, b, targetBand, offsetX, offsetY) {
  const r = GRID.radius
  const x1 = a.x + a.w
  const y1 = a.y + a.h / 2
  const gx = x1 + GRID.colGap / 2 + offsetX
  const yRun = targetBand.y - GRID.bandGap / 2 + offsetY
  const tx = b.x + b.w / 2
  const ty = b.y
  let path
  if (Math.abs(tx - gx) < 2 * r) {
    path = `M ${x1} ${y1} H ${gx} V ${yRun} H ${tx} V ${ty}`
  } else {
    const dir = tx > gx ? 1 : -1
    path = `M ${x1} ${y1} H ${gx - r} Q ${gx} ${y1} ${gx} ${y1 + r} V ${yRun - r} `
      + `Q ${gx} ${yRun} ${gx + dir * r} ${yRun} H ${tx - dir * r} Q ${tx} ${yRun} ${tx} ${yRun + r} V ${ty}`
  }
  return { path, mid: { x: (gx + tx) / 2, y: yRun }, end: { x: tx, y: ty }, gutterX: gx, runY: yRun }
}

function straight(a, b) {
  const x1 = a.x + a.w / 2
  const y1 = a.y
  const x2 = b.x + b.w / 2
  const y2 = b.y + b.h
  return { path: `M ${x1} ${y1} L ${x2} ${y2}`, mid: { x: (x1 + x2) / 2, y: (y1 + y2) / 2 }, end: { x: x2, y: y2 } }
}

// Everything a stage waits on and everything it unlocks, transitively, plus the
// companion agents that assist it directly.
export function chainOf(key, edges) {
  const gates = edges.filter((e) => e.kind !== 'assist')
  const chain = new Set([key])
  const walk = (k, forward) => {
    for (const e of gates) {
      const from = forward ? e.from : e.to
      const to = forward ? e.to : e.from
      if (from === k && !chain.has(to)) {
        chain.add(to)
        walk(to, forward)
      }
    }
  }
  walk(key, true)
  walk(key, false)
  for (const e of edges) {
    if (e.kind === 'assist' && (e.from === key || e.to === key)) chain.add(e.from === key ? e.to : e.from)
  }
  return chain
}

// Why a locked stage is locked, in words. A hard gate ("work_program:signed_off")
// is a specific human act, so it is named as such rather than as a stage.
export function waitingOn(node, byKey) {
  if (node.status !== 'locked') return []
  const reasons = []
  for (const gate of node.gates || []) {
    const [key, attr] = gate.split(':')
    const dep = byKey[key]
    if (!dep) continue
    if (attr) reasons.push(`${dep.label} sign-off`)
    else if (dep.status !== 'complete') reasons.push(dep.label)
  }
  return reasons
}

// What gets spoken is exactly what is written, so the voice and the caption can
// never drift apart.
export const narrationOf = (beat) => {
  const title = (beat.title || '').replace(/[.!?\s]+$/, '')
  return [title, beat.text].filter(Boolean).join('. ')
}

// A beat lasts as long as its sentence needs. Reading at roughly 16 characters a
// second, plus a fixed head and tail so a short line still gets room to land.
// The bounds keep a one-word beat from flashing past and a long live summary
// from stalling the tour.
export const MIN_BEAT_MS = 5600
export const MAX_BEAT_MS = 17000
export const durationFor = (text) =>
  Math.min(MAX_BEAT_MS, Math.max(MIN_BEAT_MS, 2600 + (text || '').length * 62))

export function tourFor(workflow) {
  const known = new Set((workflow.nodes || []).map((n) => n.key))
  const beats = TOUR_BEATS.map((b) => ({ ...b, focus: b.focus.filter((k) => known.has(k)) }))
  if (workflow.engagement) {
    beats.push({
      id: 'now',
      focus: known.has(workflow.next_gate) ? [workflow.next_gate] : [],
      title: 'Where this audit stands',
      text: workflow.summary || '',
    })
  }
  // Duration is derived here rather than written per beat, so the live closing
  // beat — whose text comes from the backend and differs per audit — is timed
  // by the same rule as the scripted ones.
  return beats.map((b) => ({ ...b, narration: narrationOf(b), duration: durationFor(narrationOf(b)) }))
}

// How the tour moves the view for one beat.
//
// A beat that reaches across bands — "your sign-off unlocks fieldwork", or the
// evidence chase running from the Document Request List down to Isabelle — is
// taller than any window, and centring the whole block leaves both ends off
// screen. So the view pans: focus[0] first, then the rest of the set as one
// group. Everything the sentence names is seen, in the order it is named.
//
// `spanOf` is supplied by the caller and returns the rendered pixel height of a
// group of stages, because the page measures the real DOM at whatever scale the
// map is drawn at, while the tests measure this module's own geometry. The
// decision of what to show, and in what order, lives here either way.
export function panGroups(focus, spanOf, usable) {
  const keys = focus || []
  if (keys.length < 2 || spanOf(keys) <= usable) return keys.length ? [keys] : []
  return [[keys[0]], keys.slice(1)]
}

export function beatEdges(beat, edges) {
  if (!beat) return []
  const focus = new Set(beat.focus)
  return edges.filter((e) => e.kind !== 'assist' && focus.has(e.from) && focus.has(e.to))
}
