# SAAF quality standards

Adopted for Session 11, the hardening day of 17 November 2026. This page is the single source for the nine standards and the three layers of control. Handouts, the portal and the `harden-agent-repo` skill point here.

Every agent repo and every shared service in the SAAF-Project org goes through the same nine standards. We call that the car wash. An agent is finished when all nine are in place on its default branch (for example `main` or `master`).

## The nine standards

| # | Standard | What must be in it | Defined in |
|---|---|---|---|
| 1 | `README.md` | What the agent does, its inputs and outputs. Prerequisites, with keys read from environment variables. How to install it and run one demo on synthetic data. Guardrails, model and data residency, limitations and the human review step. Licence, contact and a link to the plan. | `docs/handouts/session-6/A6-readme-hardening.md` |
| 2 | `agent.yaml` | Name, repo, island, maturity, description and a mandate block. The repo is also listed in `repos.txt` of the Living Map. | `docs/conventions/agent-yaml.md` |
| 3 | `AUDIT-CRITERIA.md` | At least three control objectives mapped to a framework, pass or fail acceptance criteria, good output and a never-do list, coverage gaps, and the date of the last review. Every criterion has a fixed number (`CO-1.1`, `M-1`, `N-1`) and a tag: `[code]` when a program can decide it exactly, `[llm]` when someone, or a model acting as judge, has to read the run. | `docs/conventions/audit-criteria-template.md` |
| 4 | `SECURITY.md` | The vulnerability disclosure policy of the repo: how to report a weakness privately, what we ask of the finder and what the finder can expect (acknowledged within 2 days, a first assessment within 10 days, an update every 14 days, public after 90 days at the latest, no legal action for a report that follows the policy). | Stichting SAAF's policy in `SAAF-Project/.github` covers every repo; `docs/conventions/security-md-template.md` for a repo of its own |
| 5 | `LICENSE` | The MIT licence text. | This page |
| 6 | Tests | At least one test that runs without keys, on synthetic data. | `CLAUDE.md` (synthetic data only) |
| 7 | Dependencies | A manifest or lockfile with pinned versions, for example `requirements.txt` with `==`, `uv.lock` or `package-lock.json`. | `docs/handouts/session-6/A6-readme-hardening.md` |
| 8 | CI | A workflow that runs on every pull request: the tests, the standards check and one guard from Session 10. | This page |
| 9 | `CODEOWNERS` | A named owner. The owner does the quarterly review. | This page |

The numbers in `AUDIT-CRITERIA.md` are what tests, checks and reviews refer to. A number stays with its criterion: a new criterion gets the next number, and a removed number is not used again.

**LLM checks.** Every criterion tagged `[llm]` has one check in `llm_checks.yaml` (in the root of the repo, or in `evals/`), under the same number. The `id` is the number of the criterion, `look_for` says what a judge reads in one run, and `pass_when` is the pass condition in one sentence. `AUDIT-CRITERIA.md` stays the source: it says what must be true, the check says how to judge it. A check without a criterion is not a check, and a tagged criterion without a check is a gap. Nobody keeps the two files in step by hand: a coding assistant or a skill writes the checks from the criteria. The file in `SAAF-Project/agent-template` explains the format, and `scripts/check_standards.py` there reports numbers that do not line up. LLM checks belong to standard 3; they are not a tenth standard.

## How each standard is checked

The check has two depths. The board in the portal looks at files on the default branch. The skill and the reviewer look at the content.

| # | Standard | Board rule (file level) | Content check |
|---|---|---|---|
| 1 | `README.md` | `README.md` in the repo root, at least 500 bytes | The skill reads it and asks whether it explains purpose, input, output and how to run. A README that is only a list of names or an empty scaffold does not pass. The reviewer confirms. |
| 2 | `agent.yaml` | `agent.yaml` or `agent.yml` in the repo root | `python scripts/build_map.py --offline` in the Living Map repo validates the fields. |
| 3 | `AUDIT-CRITERIA.md` | `AUDIT-CRITERIA.md` in the repo root | A maintainer reviews it; the portal marks the repo as reviewed. |
| 4 | `SECURITY.md` | The organisation policy in `SAAF-Project/.github`, or `SECURITY.md` in the root, `.github/` or `docs/` | The reviewer checks that the contact route works. |
| 5 | `LICENSE` | `LICENSE`, `LICENSE.md`, `LICENSE.txt` or `COPYING` in the root | The reviewer checks that it is the MIT text. |
| 6 | Tests | A test file or test folder | CI runs the tests. |
| 7 | Dependencies | A manifest or lockfile outside vendored folders | CI audits the dependencies. |
| 8 | CI | A workflow file in `.github/workflows/` | The workflow runs on pull requests and is green. |
| 9 | `CODEOWNERS` | `CODEOWNERS` in the root, `.github/` or `docs/` | The named owner exists and accepts the role. |

The board reads the default branch only. A tile turns on after a merge, not after a push to a feature branch. When GitHub gives no data for a repo the board shows "not checked", never "missing".

## Three layers of control

Proposed by Tony Barratt in his security review of 7 November 2026.

1. **Always on.** Secret scanning with push protection, Dependabot and private vulnerability reporting. These are organisation settings.
2. **Every pull request.** The standards check and at least one guard from Session 10 run in the pipeline of every repo.
3. **Every quarter.** The owner takes the agent or service through the car wash again and updates the `Last reviewed` date in `AUDIT-CRITERIA.md`. The first round is 17 November 2026.

## How the pieces link

1. **Skill.** `harden-agent-repo` (in `.claude/skills/`) runs on your own laptop, inside the agent repo. It walks through the nine standards and writes what is missing.
2. **Pull request.** The standards check and your guard run before anything merges.
3. **Merge.** A teammate with write access reviews and merges. Nobody merges their own pull request.
4. **Board.** The portal reads every repo and turns on one tile per standard on the standards board (`/standards`).
5. **Quarter.** The owner reviews again and sets the date.

## Tools that help

- **Dependencies (standard 7).** Is It Dead Yet (`https://isitdeadyet.dev/`, built by SAAF member Ellert van der Vecht) shows which packages are abandoned or carry advisories.
- **Seeing what an agent does.** Orq.ai gives SAAF members a project to trace what an agent does and to score its runs against its own audit criteria (`https://saaf-project.orq.ai/guide`). Two skills do the work: `/orq-otel-tracing` traces every model call, `/orq-criteria-to-evals` turns criteria into checks. What you see there belongs in the observability notes of your README or `AUDIT-CRITERIA.md`.

Both are external services with their own terms. Keep keys in environment variables and use synthetic data.

## Starting a new agent

Create the repo from the template `SAAF-Project/agent-template` ("Use this template" on GitHub). All nine standards are already in place, with placeholders. Its pull request workflow runs the tests and `scripts/check_standards.py`, which fails while placeholders of the template are left. An existing repo can copy that script and the workflow as its standards check.

## Improving the standards

The standards get better when the people who use them propose changes. Open a pull request with the form `standard-proposal`:

- on `SAAF-Project/agent-template`, when the change is in the template itself;
- on `SAAF-Project/SAAF-Project`, when the change is in this guide or another file in `docs/conventions/`.

To get the form, add `?template=standard-proposal.md` to the address of the page where you open the pull request (`.../compare/main...your-branch?template=standard-proposal.md`), or copy it from `SAAF-Project/.github` (`.github/PULL_REQUEST_TEMPLATE/standard-proposal.md`), which serves it to every repo in the org. Keep the first line, `<!-- standard-proposal -->`: that is how the review finds your proposal.

A maintainer adds the label `standard-proposal`. Proposals are not merged on the day they are made. The organisers review all of them afterwards and fold the best into the next version of the standards.

A proposal is judged on five points, each from 0 to 3:

| Point | Question |
|---|---|
| Evidence | Is there a real problem, shown in a repo, a finding or a review? |
| Checkability | Can the board or a reviewer check it within a minute? |
| Simplicity | Is it the smallest change that solves the problem? |
| Fit | Does it fit the nine, without repeating one of them? |
| Reach | Does it help many repos? |

A proposal that makes the standards more complicated than the problem needs scores 0, whatever the other points say, and so does a proposal without a real problem behind it. When two proposals make the same change, the credit goes to the one that came first.

### New standards

Every new standard costs every team, in every repo, every quarter. A new standard therefore takes a higher bar:

1. It does not fit inside one of the nine. If it does, it becomes part of that standard.
2. It shows the problem in at least two repos or findings.
3. It comes with a rule the board can check without a person, and with how the review agent scores it.
4. It names the standard it replaces or merges with. One in, one out keeps the set at nine.

The standards change at most once a quarter, as a new version (for example v1.1), with a grace period for existing repos. The board, the template, the `harden-agent-repo` skill and the handouts change together.

## Scope

- **Agents and services.** The standards apply to agent repos and to shared services such as the portal, the Living Map and the Session 10 guards. A shared service that is not an agent may leave out `agent.yaml` and `AUDIT-CRITERIA.md`, and says so in its README.
- **Duplicates.** When two repos hold the same agent, the builders of both pick the one that stays. What is unique in the other moves into it with a pull request, with credit to its authors. The other repo gets a README that points to the one that stays and is then archived by a maintainer. Archiving makes a repo read-only; it keeps the history and the links and can be undone. Nothing is deleted.
- **Quiet repos.** An agent that has not been pushed to for months is not archived. It is revived: someone asks the builder, takes the agent through the nine standards and puts their name in `CODEOWNERS`.
- **Empty repos and moves.** Repos without content, and content that belongs in `SAAF-Project/SAAF-Project`, are handled by the maintainers.
- **More detail.** The checklist S01-S15 of the standards audit of November 2026 breaks the README, criteria, data and test standards down further. It lives in `audit/2026-11-standards/` once that audit is merged.
