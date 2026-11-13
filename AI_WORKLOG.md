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
