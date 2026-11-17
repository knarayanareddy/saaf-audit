// Dependency-free tests for the Markdown subset the assistant's replies use.
// Run from the frontend dir:  node --test tests/markdown.test.mjs
import test from 'node:test'
import assert from 'node:assert/strict'
import { parseBlocks, parseInline } from '../src/lib/markdown.js'

const kinds = (spans) => spans.map((s) => s.type).join('+')
const texts = (spans) => spans.map((s) => s.text).join('')

test('bold is recognised and the asterisks disappear', () => {
  const spans = parseInline('The **work program** must be signed off')
  assert.equal(kinds(spans), 'text+strong+text')
  assert.equal(spans[1].text, 'work program')
  assert.equal(texts(spans), 'The work program must be signed off')
})

test('an unclosed ** stays literal (a reply is still streaming)', () => {
  const spans = parseInline('The **work prog')
  assert.equal(kinds(spans), 'text')
  assert.equal(spans[0].text, 'The **work prog')
})

test('two bold runs on one line are both closed correctly', () => {
  const spans = parseInline('**one** and **two**')
  assert.deepEqual(spans.filter((s) => s.type === 'strong').map((s) => s.text), ['one', 'two'])
})

test('single asterisks are italic, but only when they hug a word', () => {
  assert.equal(kinds(parseInline('*scope* creep')), 'em+text')
  assert.equal(kinds(parseInline('2 * 3 items')), 'text')          // multiplication, not emphasis
})

test('inline code wins over emphasis inside it', () => {
  const spans = parseInline('use `a ** b` here')
  assert.equal(kinds(spans), 'text+code+text')
  assert.equal(spans[1].text, 'a ** b')
})

test('bullets become one list, numbered lines another', () => {
  const blocks = parseBlocks('- first\n- second\n\n1. one\n2. two')
  assert.deepEqual(blocks.map((b) => b.type), ['ul', 'ol'])
  assert.equal(blocks[0].items.length, 2)
  assert.equal(texts(blocks[1].items[1]), 'two')
})

test('markdown headings and colon mini-headings both become headings', () => {
  const blocks = parseBlocks('## Findings\nNext steps:')
  assert.deepEqual(blocks.map((b) => b.type), ['h', 'h'])
  assert.equal(texts(blocks[0].spans), 'Findings')
  assert.equal(texts(blocks[1].spans), 'Next steps')
})

test('a horizontal rule is its own block, not a bullet', () => {
  assert.deepEqual(parseBlocks('a\n---\nb').map((b) => b.type), ['p', 'hr', 'p'])
})

test('bullets keep their inline formatting', () => {
  const blocks = parseBlocks('- **Scope**: three processes')
  assert.equal(blocks[0].type, 'ul')
  assert.equal(kinds(blocks[0].items[0]), 'strong+text')
})

test('empty and whitespace input produce no blocks', () => {
  assert.deepEqual(parseBlocks(''), [])
  assert.deepEqual(parseBlocks('   \n\n'), [])
  assert.deepEqual(parseBlocks(null), [])
})

test('no asterisk or hash survives into the rendered text', () => {
  const reply = '## Summary\nThe **RACM** is ready.\n\n- *check* the `origin` field\n- 1 item left'
  const flat = parseBlocks(reply)
    .flatMap((b) => (b.items ? b.items.flat() : b.spans || []))
    .map((s) => s.text)
    .join(' ')
  assert.ok(!flat.includes('*'), `stray asterisk in: ${flat}`)
  assert.ok(!flat.includes('#'), `stray hash in: ${flat}`)
})

// ── Tables ───────────────────────────────────────────────────────────────────
// The assistant answers a "which option?" question with a table, and the panel
// used to print the pipes: `| Option | What it does |` as three paragraphs.
const TABLE = '| Option | Calls |\n|---|---:|\n| Accept | 12 |\n| Dismiss | 3 |'

test('a header, a separator and rows become one table block', () => {
  const blocks = parseBlocks(TABLE)
  assert.equal(blocks.length, 1)
  assert.equal(blocks[0].type, 'table')
  assert.deepEqual(blocks[0].head.map((c) => c[0].text), ['Option', 'Calls'])
  assert.equal(blocks[0].rows.length, 2)
  assert.deepEqual(blocks[0].rows[1].map((c) => c[0].text), ['Dismiss', '3'])
})

test('the separator says how each column is aligned', () => {
  assert.deepEqual(parseBlocks(TABLE)[0].align, ['left', 'right'])
  assert.deepEqual(parseBlocks('|a|b|c|\n|:-|:-:|-:|\n|1|2|3|')[0].align,
                   ['left', 'center', 'right'])
})

test('pipes stay literal until the separator arrives — a reply is still streaming', () => {
  // The header lands a beat before the separator does. Turning it into a
  // one-row table and then re-laying it out is the flicker the unclosed-** rule
  // exists to prevent.
  assert.deepEqual(parseBlocks('| Option | Calls |').map((b) => b.type), ['p'])
  assert.deepEqual(parseBlocks('| Option | Calls |\n|---|---:|').map((b) => b.type), ['table'])
})

test('a line with pipes and no separator under it is a paragraph, not a table', () => {
  const blocks = parseBlocks('use a | b | c to split the columns')
  assert.deepEqual(blocks.map((b) => b.type), ['p'])
})

test('cells keep their inline formatting', () => {
  const blocks = parseBlocks('| What | Where |\n|---|---|\n| **Scope** | `routers/phase3.py` |')
  assert.deepEqual(blocks[0].rows[0][0], [{ type: 'strong', text: 'Scope' }])
  assert.deepEqual(blocks[0].rows[0][1], [{ type: 'code', text: 'routers/phase3.py' }])
})

test('a short row is padded and a long one keeps its cells — nothing is dropped', () => {
  const blocks = parseBlocks('| a | b | c |\n|---|---|---|\n| 1 |\n| 1 | 2 | 3 | 4 |')
  assert.deepEqual(blocks[0].rows[0].map((c) => c[0].text), ['1', '', ''])
  assert.equal(blocks[0].rows[1].length, 4)
})

test('text after a table is its own block again', () => {
  const blocks = parseBlocks(TABLE + '\nPick one and I will do it.')
  assert.deepEqual(blocks.map((b) => b.type), ['table', 'p'])
})

test('no pipe survives into the rendered text of a table', () => {
  const flat = parseBlocks(TABLE)
    .flatMap((b) => [...b.head, ...b.rows.flat()])
    .flat()
    .map((s) => s.text)
    .join(' ')
  assert.ok(!flat.includes('|'), flat)
  assert.ok(!flat.includes('---'), flat)
})
