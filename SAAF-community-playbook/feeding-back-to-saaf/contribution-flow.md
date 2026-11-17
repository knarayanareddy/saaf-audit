# Contribution Flow

How an artefact produced inside a chapter gets contributed back to
the main SAAF Project.

The flow is deliberately lightweight — a pull request and a recap
note. Heavy review processes deter contribution; light ones produce
volume.

---

## What Gets Contributed Back

The main SAAF Project repository is organised around the four
pillars (Prompts, Tools, Regulatory, Outputs) plus docs, plans, and
recap material.

Chapters are expected to contribute back artefacts in those pillars
when they are ready to be shared. The default-share principle from
the manifesto applies.

| Artefact type | Default | Where it lands |
|---|---|---|
| Plans (agent / skill / workflow) | Public; contributed back | `plans/` (in the appropriate hackathon folder, or a chapter-specific subfolder) |
| Prompts | Public; contributed back | `prompts/audit-use-cases/` or `prompts/system-instructions/` |
| Tools / scripts / MCP servers | Public; contributed back | `tools/` |
| Regulatory mappings, control libraries | Public; contributed back | `regulatory/frameworks/` |
| Output schemas, templates | Public; contributed back | `outputs/schemas/` or `outputs/examples/` |
| Lessons learned | Public; contributed back | `docs/lessons-learned/` |
| Recaps | Public to chapter members; selected lessons public to community | Chapter site + lesson contributed to `docs/lessons-learned/` |
| Real audit data | **Never** | — |
| Internal-only patterns | Withheld | — |

If you are unsure whether an artefact belongs upstream, the default
answer is yes — the contribution flow includes a review step where
the national project organisers can flag concerns.

---

## Internal Vs. Regional Contribution

The flow differs slightly between chapter types.

### Internal chapter contributions

An internal chapter contributes:

- Prompts that don't reveal organisational specifics.
- Generic versions of tools (the script, with credentials and
  organisation-specific paths abstracted).
- Control-mapping patterns (the structure, not the proprietary
  internal control library).
- Lessons learned, especially those grounded in pilot or production
  experience.
- Anonymised case studies (with appropriate sign-off internally).

What an internal chapter typically does not contribute:

- The full internal control library.
- Specific findings.
- Organisation-specific configurations.
- Trade-secret-grade prompts (rare, but possible).

The principle: contribute the *pattern*, withhold the *instance*.
Other chapters benefit from the pattern; the organisation keeps the
instance.

### Regional chapter contributions

A regional chapter contributes more directly — the chapter is
already cross-organisation, so the artefacts are already designed
for sharing. The full plan, the full prompt, the full tool, the full
mapping all go upstream.

Cross-organisation chapter work that requires inputs from multiple
member organisations is contributed back as the *synthesised pattern*,
not as the underlying real data. The Check-stage pilots happen
inside individual organisations; the contributed artefact is what was
learned across them.

---

## The Git Workflow

The main SAAF Project uses GitHub. The contribution flow is a
fork-based pull request, the same as any open-source project.

### Steps

1. **Fork the SAAF-Project repository** to your chapter's GitHub
   account or to a member's account.
2. **Clone the fork.** Work in a feature branch with the convention
   `chapter-name/contribution-description`.
3. **Add the artefact in the appropriate pillar folder.** Follow the
   conventions in that folder's README.
4. **Update any cross-reference indices.** For example, if you are
   adding a plan, update the relevant `plans/<hackathon>/README.md`
   index.
5. **Commit with a descriptive message.** Convention:
   `[chapter-name] [pillar]: [short description]`. Example:
   `[saaf-belgium] prompts: gdpr-controller-review prompt`.
6. **Push to the fork** and open a pull request against
   `SAAF-Project/SAAF-Project:main`.
7. **PR description** includes:
   - One paragraph: what the artefact is and why it's being
     contributed.
   - Which pillar(s) it touches.
   - Which session it came from.
   - Any caveats (synthetic data only, partial implementation, etc.).
   - Attribution: who built it and what name (or pseudonym) they
     want credited.

The PR is reviewed by the main SAAF Project organisers or a
delegated reviewer. Most PRs land within two weeks. Discussions
happen in PR comments, not in private channels.

### What gets feedback in review

- Manifesto alignment (vendor neutrality, synthetic data only,
  proper attribution).
- Pillar placement (is this a prompt, a tool, or a workflow plan?).
- Cross-references to existing artefacts.
- Quality bar (the artefact is at a level where another chapter
  could pick it up and adapt it).

What does *not* get reviewed:

- The audit substance of the artefact. The contributor's chapter is
  the substance reviewer.
- The technical stack. Vendor-agnostic = many stacks acceptable.
- The chapter's identity. Chapters are autonomous within the
  manifesto.

---

## Attribution Rules

Every contribution carries the contributor's name (or chosen
pseudonym), the chapter, and the session of origin.

### In the artefact itself

Plans use the existing template's metadata header. Prompts include
a YAML / Markdown frontmatter block. Tools include a header comment.
The format varies by pillar; the principle is consistent: the
artefact knows where it came from.

### In the commit

The PR title and body credit the contributor. The PR is opened by
someone with a GitHub identity, but the *credit* is in the artefact
content, not in the GitHub author of the commit.

### In the recap

The chapter's recap names the contributor. The contribution goes
upstream with that name attached. The main SAAF Project does
not strip or rewrite attribution.

### Pseudonyms

Pseudonyms are permitted at all levels. A contributor who does not
want their real name on a public artefact can use a pseudonym in
the artefact, the commit, and the recap. The chapter captain knows
the real identity (so attribution can be verified for IP purposes if
needed).

What is not permitted: anonymous contribution. Every artefact has a
real human accountable for it, even if that human's identity is
shielded by a pseudonym.

---

## Frequency Of Contribution

There is no required frequency. A healthy regional chapter
contributes something most quarters. A healthy internal chapter
contributes something most halves.

Signs you are contributing too rarely:

- A whole year goes by with nothing upstream.
- The chapter consumes from the main SAAF Project repository
  but never adds to it.
- Other captains in the federation can't name what your chapter
  has contributed.

Signs you are contributing too aggressively:

- The artefacts you contribute are not yet ready for other chapters
  to use.
- Your contribution PRs accumulate review backlog because they are
  thin.
- Other captains comment that the contributions feel rushed.

The right frequency follows the work. Don't manufacture
contributions to hit a cadence; do contribute everything that's
ready when it's ready.

---

## When A Contribution Is Rejected

Rare. When it happens, the reasons are usually:

- Real client data or organisation-identifiable data slipped in.
- The artefact would only run on a single proprietary stack.
- The artefact's pillar placement is wrong.
- The artefact duplicates an existing one without adding new value.

Rejected PRs receive a comment explaining the issue. The
contributor's chapter can revise and re-submit. There is no formal
appeals process; rejection is rare enough that ad-hoc resolution
between captains works.

A pattern of repeated rejections from a single chapter is a signal
that the chapter's contribution practice has drifted. The captain
of the contributing chapter and the national project organisers
have a one-on-one to recalibrate.

---

## What The National Project Owes The Contributor

In return for the contribution:

- The contribution is preserved in the repository, with attribution.
- The contribution is announced in the next national project session
  recap or update.
- The contributing chapter is credited in any cross-chapter
  publication (annual roundup, conference talks, etc.).
- The contribution is available to the contributor's own chapter on
  the same terms as to any other member.

The national project does not promise:

- That the contribution will be used by other chapters (use is up
  to them).
- That the contribution will be maintained by the national project
  (maintenance lives with the contributor or their chapter).
- Any monetary compensation.

These terms are listed in the chapter's charter
([template](../appendix/templates/chapter-charter.md)) and
acknowledged at chapter formation.

---

## Cross-reference

For the format of lessons learned, see
[lessons-learned.md](lessons-learned.md).
For the IP and governance details, see
[governance-and-ip.md](governance-and-ip.md).
