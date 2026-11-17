# Contributing

Thanks for helping improve the Agent Rogue-Risk Assessor. Contributions are welcome from SAAF, ISACA and NOREA community members and anyone else.

## Ground rules

1. **Open an issue first** for anything that changes scoring (weights, floors, thresholds, flag definitions). Use the *Rubric change* template.
2. **Rubric changes need**:
   - a rationale and, ideally, evidence (e.g. calibration against real agent repos);
   - a version bump in `references/rubric.md`, `SKILL.md` metadata and `scripts/scan_repo.py` (`SCANNER_VERSION`);
   - a CHANGELOG entry;
   - approval from a reviewer listed for the rubric in `.github/CODEOWNERS` who did not author the change.
3. **No softening without approval.** CI blocks changes that replace *must / required / never* with *should / may / plausible*. If intended, a maintainer adds the `approved-softening` label with a comment explaining why.
4. **Tests**: every new heuristic needs a positive and a negative test in `tests/`.
5. **Supporting skills**: additions to `references/trusted-publishers.md` need the publisher's GitHub owner, rationale and approver.

## Development

```bash
python -m pip install -r requirements-dev.txt
pytest -q
```

## Commit messages

`<area>: <summary>` — areas: `rubric`, `scanner`, `skill`, `docs`, `ci`, `tests`.
