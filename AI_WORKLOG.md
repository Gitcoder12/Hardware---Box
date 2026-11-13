# AI Engineering Worklog

## Scope

Repository: Hardware-Box  
Branch: `deep-dive-sprint`  
Date: 2026-11-13

## Confirmed work in the current engineering PR

- Added detailed mesh error counts and safer STL parsing for truncated binary input.
- Hardened 3MF ZIP/XML parsing and malformed vertex handling.
- Added deterministic worst-case tolerance-stack and hole/shaft clearance calculations.
- Added an explicitly assumed statistical hole/shaft model using normal distributions and independent-process RSS.
- Added BOM record validation and clearer handling of malformed KiCad input.
- Added regression coverage and documented formulas, assumptions, and non-GD&T limitations in README.md.

## Nine-gate assessment

| Gate | Assessment | Evidence / next work |
|---|---|---|
| Architecture | Good modular toolkit | CAD mesh, tolerance, BOM, KiCad and app surfaces are separated |
| Correctness | Improved | Worst-case and statistical formulas have dedicated tests; expand property-based and reference-case tests |
| Tests | Passed | Python 3.10–3.13 matrix and Streamlit smoke check passed on exact PR head `7fe54fe6546c053c81c7d74ef7d6121f5470deea` |
| Error handling | Improved | Truncated STL and invalid UTF-8 inputs are normalized to clear errors |
| Security | Review needed | Keep parsing bounded; treat imported CAD/project bundles as untrusted input |
| Dependencies | Review needed | Monitor CAD/parser dependency updates and optional native tools |
| Performance | Review needed | Benchmark large STL/3MF files and constrain memory for untrusted uploads |
| Documentation | Improved | README explains worst-case, RSS, statistical assumptions and limitations |
| CI/release | Passed at verified head | Python matrix and Streamlit smoke checks completed successfully; rerun after any further code change |

## Engineering model limits

- Tolerance-stack calculations are one-dimensional algebraic models.
- RSS assumes independent contributors and is not a worst-case guarantee.
- The statistical fit model assumes independent normal hole and shaft processes with the configured sigma multiplier.
- The fit calculation is size-only; it does not certify GD&T, geometric form, datum relationships, thermal effects, or manufacturing capability.
- STL unit metadata may be unspecified; 3MF object/build transforms are not applied by the mesh analyzer.
- Mesh inspection is not a substitute for full CAD-kernel validation or manufacturing sign-off.

## Validation evidence

- Latest verified PR head at time of writing: `7fe54fe6546c053c81c7d74ef7d6121f5470deea`.
- Python 3.10, 3.11, 3.12, and 3.13 pytest jobs: passed.
- Streamlit app smoke check: passed.
- The workflow also compiled source/tests, validated example records, and checked CLI entry points.
- A malformed test function in the new KiCad tests was found by CI and corrected before the successful run.

## Next actions

1. Add reference examples with independently calculated expected outputs for tolerance and fit calculations.
2. Add bounded-input tests for very large and malformed mesh/project files.
3. Benchmark representative STL/3MF files from real CAD tools.
4. Keep the UI and docs explicit that outputs are advisory engineering analysis.

## 2026-11-13 — Portfolio audit of current main

### Audit record
- Audited main HEAD: `e3a9822d36519e8ca5cb1f239eb71b34d92758ae`.
- Recursive tree: 86 tracked files, including 25 test modules, 2 GitHub Actions workflows, package metadata, examples, documentation, and a `src/hardware_box` package.
- Recommendation: IMPROVE / strong engineering-toolkit candidate.

### Confirmed findings
- The README still labels the project "Early Development — Architecture and Planning" and describes most capabilities as future roadmap items. The current tree already contains CAD mesh inspection, KiCad parsing/auditing, BOM tooling, device/catalog registries, project bundles, supply-chain analysis, electrical checks, tolerance-stack and fit analysis, CLI, Streamlit app, examples, and extensive tests. The README materially understates the implementation.
- The main branch has a modular installable package and CLI entry point `hardware_box.cli:main`.
- CI definitions exist for a Python 3.10–3.13 test matrix and a Streamlit app health check.
- The existing worklog's successful test evidence refers to a different deep-dive branch and exact commit `7fe54fe6546c053c81c7d74ef7d6121f5470deea`; it must not be represented as a pass on current main HEAD `e3a9822...`.
- The CLI and imported CAD/EDA bundles process untrusted files. Keep archive extraction, ZIP/XML parsing, mesh size, decompression, path handling, and memory use bounded.
- The README and worklog correctly state important model limits: 1-D tolerance assumptions, RSS independence assumptions, missing GD&T certification, STL unit ambiguity, and no full CAD-kernel validation.

### Verification
- Inspected main README, pyproject, requirements, CLI, CI workflows, recursive tree, and existing AI_WORKLOG.
- No local tests were run in this audit.
- Current main commit workflow result: NOT VERIFIED in this run. Workflow files are present, but the available commit-run query returned no PR-triggered run for main.
- Independent review of the current documentation PR #2: NOT PERFORMED.

### Next actions
1. Update README implementation status and project structure without replacing the maintainer's original content.
2. Run the Python matrix and Streamlit smoke check on the exact current main/PR head before merging.
3. Add bounded archive/mesh input tests, property-based tolerance tests, and independently calculated reference cases.
4. Add resource limits and clear failure handling for malformed or oversized CAD/EDA bundles.
5. Benchmark representative files from real CAD tools; keep results separate from synthetic examples.
