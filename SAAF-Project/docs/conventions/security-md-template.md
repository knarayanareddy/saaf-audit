# SECURITY.md template: the vulnerability disclosure policy

`SECURITY.md` is the vulnerability disclosure policy of an agent repo. It tells someone who finds a weakness where to report it, what we ask of them and what they can expect from us. It follows coordinated vulnerability disclosure: the finder reports privately, the owner fixes it, and both publish together. It is standard 4 of the nine in `docs/conventions/quality-standards.md`.

Copy the block below into `SECURITY.md` next to the `README.md` of your agent repo and fill in the placeholders.

Before you commit it, switch on private vulnerability reporting for the repo: Settings, then Code security, then "Private vulnerability reporting". Without that the first reporting route does not exist.

```markdown
# Security policy

This is the vulnerability disclosure policy of this repository. We follow coordinated vulnerability disclosure: you report a weakness to us privately, we fix it, and we publish it together.

## Reporting a weakness

Please do not open a public issue for a security problem.

- Preferred: use GitHub private vulnerability reporting on this repository (Security tab, "Report a vulnerability").
- Or mail [contact address, for example info@saafproject.com].

Tell us what you found, where it is (file, endpoint or commit), how to reproduce it and what impact you expect.

## What we ask of you

- Report as soon as you can, and only to us, until it is fixed or 90 days have passed.
- Do no more than is needed to show the weakness. Do not read, change or delete data that is not yours.
- Work on a local copy, with synthetic data. No attacks on live systems, no denial of service, no social engineering.
- Do not use keys you find. Report them, and do not put live keys, secret values or personal data in the report.

## What you can expect from us

| Step | When |
|---|---|
| We confirm that we received your report | within 2 days |
| A first assessment | within 10 days |
| An update on progress | every 14 days until it is closed |
| Public disclosure, together with you | once it is fixed, and after 90 days at the latest |

- We treat your report in confidence and do not share your personal details without your consent.
- We name you as the finder in the fix or the advisory, if you want that.
- If you follow this policy, we will not take legal action against you for your report.
- There is no financial reward.

## Scope

In scope: the code and configuration in this repository, on the default branch (for example `main` or `master`).

Out of scope: third-party services this agent calls, findings that need real audit evidence or personal data to reproduce, and anything that requires an attack on a live system.

## Owner

[Name or team, as in CODEOWNERS]. This policy is reviewed every quarter, together with `AUDIT-CRITERIA.md`.
```

## Notes

- The response times follow common open-source practice. A team may promise faster times, never slower ones.
- One contact route is enough. Private vulnerability reporting is preferred because the report, the fix and the advisory stay in one place.
- The promise not to take legal action is made by the owner of the repo. If your organisation has its own disclosure policy, link to it and keep the two in line.
- A repo that depends on a shared service links to that service's `SECURITY.md` instead of repeating it.
