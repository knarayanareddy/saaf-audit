# SAAF — Submitted Plans

Plans submitted by participants ahead of and during each hackathon. Every hackathon gets its own subfolder. The submission template may be updated between sessions — always use the version linked in the session row below.

## Sessions

| Hackathon | Folder | Date | Venue | Status | Template |
|-----------|--------|------|-------|--------|----------|
| Alignment (Session 1) | [`alignment/`](alignment/) | January 20, 2026 | Mollie, Amsterdam | Complete | — |
| Hackathon #1 (Session 2) | _(agents built on the day — no plans submitted)_ | March 10, 2026 | Mollie, Amsterdam | Complete | — |
| Hackathon #2 (Session 3) | [`hackathon-2/`](hackathon-2/) | March 24, 2026 | Schuberg Philis | Complete | [plan-template.md](../docs/plans/plan-template.md) |
| Hackathon #3 (Session 4) | [`hackathon-3/`](hackathon-3/) | April 21, 2026 | Wolters Kluwer, Alphen aan den Rijn | Complete | [plan-template.md](../docs/plans/plan-template.md) |
| Hackathon #4 (Session 5) | [`hackathon-4/`](hackathon-4/) | TBD | TBD | Open | [plan-template.md](../docs/plans/plan-template.md) |

## Structure

```
plans/
  README.md                         ← this file (permanent index across all sessions)
  overview.md                       ← central overview of all plans with critical review
  gap-analysis.md                   ← mapping of 53 audit domains to existing plans
  meta-analysis.md                  ← cross-plan analysis, hackathon assignments, lessons learned
  alignment/
    README.md                       ← index of submitted plans for Alignment Session
    firstname-lastname-slug.md      ← one file per submission
  hackathon-2/
    README.md                       ← index of submitted plans for Hackathon #2
    firstname-lastname-slug.md      ← one file per submission
  hackathon-3/
    README.md                       ← index of submitted plans for Hackathon #3
    firstname-lastname-slug.md      ← one file per submission
  hackathon-4/
    README.md                       ← index of submitted plans for Hackathon #4
    firstname-lastname-slug.md      ← one file per submission
```

## How to submit

1. Find the folder for the upcoming hackathon in the table above
2. Copy the linked template to that folder as `firstname-lastname-your-slug.md`
3. Fill in the template; mark unfinished sections as "TBD"
4. Open a pull request — the organizers add a row to the session index on merge

Full guide: [`docs/getting-started.md`](../docs/getting-started.md)
