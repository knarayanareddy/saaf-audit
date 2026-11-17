// A deliberately small Markdown subset — just enough for what the assistant and
// the agents actually produce: paragraphs, bullets, numbered lists, headings,
// tables, bold, italic and inline code.
//
// Two rules shape it:
//  1. Pure data in, pure data out. This file returns plain objects; the React
//     component turns them into nodes. Nothing is ever rendered as raw HTML, so
//     model output can never inject markup. It also makes the parser testable
//     with `node --test` (see tests/markdown.test.mjs).
//  2. An UNCLOSED marker stays literal text. Replies stream in token by token,
//     so half a `**bold**` arrives on its own for a moment — bolding it eagerly
//     would make the whole answer flicker as it is typed.

// Ordered alternation: `code` first so markers inside it stay literal, then the
// two-star form before the one-star form so **bold** never reads as *em*.
const INLINE = /`([^`\n]+)`|\*\*([^\n]+?)\*\*|\*(?!\s)([^*\n]+?)\*/g

/**
 * Split a single line into typed spans.
 * @returns {{type:'text'|'strong'|'em'|'code', text:string}[]}
 */
export function parseInline(line) {
  const text = line ?? ''
  const spans = []
  let last = 0
  INLINE.lastIndex = 0
  let m
  while ((m = INLINE.exec(text)) !== null) {
    if (m.index > last) spans.push({ type: 'text', text: text.slice(last, m.index) })
    if (m[1] !== undefined) spans.push({ type: 'code', text: m[1] })
    else if (m[2] !== undefined) spans.push({ type: 'strong', text: m[2] })
    else spans.push({ type: 'em', text: m[3] })
    last = m.index + m[0].length
  }
  if (last < text.length) spans.push({ type: 'text', text: text.slice(last) })
  return spans.length ? spans : [{ type: 'text', text }]
}

// A table is a header row, a separator row, then body rows. The separator is
// what makes it a table — and that is also what keeps a streaming reply honest:
// the header arrives on its own first, and until the separator follows it is
// still just a line with pipes in it, so it renders as one. Same rule as an
// unclosed `**`.
const TABLE_CELL_SEP = /^:?-+:?$/

const BULLET = /^[-•*]\s+(.*)$/
const NUMBERED = /^(\d{1,2})[.)]\s+(.*)$/
const HEADING = /^(#{1,6})\s+(.*)$/
const RULE = /^([-*_])\1{2,}$/

/** `| a | b |` → ['a', 'b']. Escaped pipes are not supported; nothing here emits them. */
function splitRow(line) {
  let s = line.trim()
  if (s.startsWith('|')) s = s.slice(1)
  if (s.endsWith('|')) s = s.slice(0, -1)
  return s.split('|').map((c) => c.trim())
}

function isSeparatorRow(cells) {
  return cells.length > 0 && cells.every((c) => TABLE_CELL_SEP.test(c))
}

/** `:--` left, `--:` right, `:-:` centre — the one thing the separator says. */
function alignmentsOf(cells) {
  return cells.map((c) => {
    const left = c.startsWith(':')
    const right = c.endsWith(':')
    if (left && right) return 'center'
    if (right) return 'right'
    return 'left'
  })
}

/**
 * Parse a block of text into renderable blocks.
 * @returns {({type:'h',level:number,spans:object[]}
 *          |{type:'p',spans:object[]}
 *          |{type:'ul'|'ol',items:object[][]}
 *          |{type:'table',align:string[],head:object[][],rows:object[][][]}
 *          |{type:'hr'})[]}
 */
export function parseBlocks(text) {
  const lines = (text || '').replace(/\r/g, '').split('\n')
  const blocks = []
  let list = null          // { type: 'ul' | 'ol', items: [] }

  const flushList = () => {
    if (list?.items.length) blocks.push(list)
    list = null
  }
  const pushList = (type, content) => {
    if (list?.type !== type) {
      flushList()
      list = { type, items: [] }
    }
    list.items.push(parseInline(content))
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    if (!line) {
      flushList()
      continue
    }

    // Tables need one line of lookahead, which is why this loop is indexed.
    if (line.includes('|')) {
      const head = splitRow(line)
      const sep = i + 1 < lines.length ? splitRow(lines[i + 1].trim()) : []
      if (head.length > 1 && isSeparatorRow(sep) && sep.length === head.length) {
        flushList()
        const rows = []
        let j = i + 2
        for (; j < lines.length; j++) {
          const body = lines[j].trim()
          if (!body || !body.includes('|')) break
          const cells = splitRow(body)
          // A short row is padded, never dropped, and a long one keeps its extra
          // cells: a table that silently loses a column of an agent's answer is
          // worse than one that looks ragged.
          while (cells.length < head.length) cells.push('')
          rows.push(cells.map(parseInline))
        }
        blocks.push({
          type: 'table',
          align: alignmentsOf(sep),
          head: head.map(parseInline),
          rows,
        })
        i = j - 1
        continue
      }
    }

    if (RULE.test(line)) {
      flushList()
      blocks.push({ type: 'hr' })
      continue
    }

    const heading = line.match(HEADING)
    if (heading) {
      flushList()
      blocks.push({ type: 'h', level: heading[1].length, spans: parseInline(heading[2]) })
      continue
    }

    const numbered = line.match(NUMBERED)
    if (numbered) {
      pushList('ol', numbered[2])
      continue
    }

    const bullet = line.match(BULLET)
    if (bullet) {
      pushList('ul', bullet[1])
      continue
    }

    flushList()
    // A short line ending in a colon reads as a mini-heading, which is how the
    // agents have always structured their output — keep honouring it.
    if (line.length <= 60 && line.endsWith(':')) {
      blocks.push({ type: 'h', level: 3, spans: parseInline(line.replace(/:$/, '')) })
    } else {
      blocks.push({ type: 'p', spans: parseInline(line) })
    }
  }
  flushList()
  return blocks
}
