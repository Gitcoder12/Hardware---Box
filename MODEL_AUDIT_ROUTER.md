# Independent Model Audit Router — Hardware-Box

**Revision date:** 2026-11-13

## Data integrity and evidence rules
- Never replace real or maintainer-provided data with invented, generated, synthetic or placeholder records.
- Trace data to its original source, licence, collection date and Git-history baseline before changing it.
- If provenance is unknown, preserve existing data and label it unknown/unverified. Do not guess.
- Synthetic datasets are allowed only in clearly labelled, isolated tests or examples.
- Do not fabricate government/official records, identities, measurements, source references, metrics, customers, partners, deployments or contributors.
- Never claim a test or benchmark passed unless run against the exact commit reviewed.

## README preservation
Recover the last maintainer-authored README from Git history and preserve it intact. Never rewrite or replace it. Append AI-generated project notes only as a dated, clearly labelled section at the very bottom.

## Independent reviewers
1. Data provenance, real-vs-synthetic and source-integrity checker.
2. Architecture and implementation reviewer.
3. Security, privacy and dependency reviewer.
4. Test, CI, build and reproducibility reviewer.
5. README history, licensing and attribution reviewer.
6. Career/research claim and public evidence reviewer.

## Audit workflow
1. Record URL, default branch, exact HEAD SHA, fork/original status and PR heads.
2. Classify changes as merged, open, closed-unmerged, reverted or unverified.
3. Inspect all runtime data, fixtures, generated artefacts, APIs and provenance.
4. Compare README with its pre-AI Git-history version.
5. Run install/build/lint/test commands on the exact commit and inspect CI for skipped or suppressed failures.
6. Review security, privacy, accessibility, error handling, edge cases and performance.
7. Verify public claims and links; company matches are prospective skill fits, not partnerships or customers.
8. Publish findings with evidence before changes are proposed.

## Finding format
Severity (**P0/P1/P2/P3**), exact path/line, reproduction, expected vs actual, evidence and commit SHA, confirmed/suspected/unverifiable status, minimum fix, regression test, and data/README impact.

## Merge gate
- [ ] No fabricated data presented as real or official.
- [ ] Real/user-provided data preserved; no silent data substitution.
- [ ] Synthetic data labelled and isolated from runtime records.
- [ ] Original README preserved; AI notes only at the bottom.
- [ ] Exact-head tests/CI checked; failures disclosed.
- [ ] No secrets, private personal details, classified or confidential content.
- [ ] Licensing, attribution and upstream provenance retained.
- [ ] Independent second review and maintainer approval recorded.

Repository: **Hardware-Box**. Do not infer capability from repository title or roadmap. Do not merge, delete, force-push, overwrite datasets or edit original README while auditing. The repository owner has final approval.
