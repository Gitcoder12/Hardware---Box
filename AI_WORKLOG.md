# AI Engineering Worklog

## ✅ Work Done

### 2026-11-13 — Deep-dive sprint (deep-dive-sprint)

The following engineering work is present on this branch; some changes were developed in parallel by another connected AI model and were reviewed for consistency before being retained.

- Retained the existing pure-Python STL/3MF triangle-mesh analysis: surface area, single-shell signed volume, edge incidence, boundary/non-manifold/orientation checks, bounds and degenerate/duplicate triangle reporting.
- Added an aggregate manifold_errors summary and count.
- Hardened STL parsing so malformed binary files and non-UTF-8 ASCII candidates return a clear ValueError.
- Hardened 3MF ZIP/XML parsing and malformed vertex handling.
- Prevented duplicate coincident faces from being treated as a watertight volume.
- Added a physical lower-limit check: nominal size minus minus-tolerance must remain positive.
- Added analyze_shaft_hole_fit with worst-case clearance and an independent normal-process RSS model; exposed it through the CLI statistical fit option.
- Hardened BOM row conversion: record must contain a components list; each component must be a valid object with non-empty name, positive integer quantity and object specifications.
- Added tests for BOM edge cases, corrupt KiCad S-expressions/encoding, mesh degeneracies and non-manifold edges, statistical shaft/hole fits, missing BOM/netlist references, and corrupted XML exports.

## 🚧 Work Left

- Run the complete Hardware-Box test suite and Streamlit smoke workflow in GitHub Actions; no test execution is claimed in this worklog.
- Confirm every supported Python matrix job passes.
- Independently test statistical fit calculations against a trusted engineering reference or hand-calculated fixtures.
- Validate representative STL/3MF files from real CAD tools; current synthetic fixtures validate algorithm behavior only.
- 3MF component/build transforms are not applied; metrics summarize object mesh definitions, not final transformed assemblies.
- Mesh edge-incidence checks do not detect every vertex-manifold issue, self-intersection or CAD-kernel/B-rep defect.
- Tolerance model is one-dimensional. It does not implement full GD&T datum reference frames, position/orientation/form tolerances, material-condition modifiers, thermal distortion, roughness or process capability.
- RSS probability assumes independent normal processes. Validate distribution assumptions using measured production data before using probabilities for decisions.
- KiCad parsing/audit remains read-only structural inspection; full ERC and DRC require KiCad CLI and project-specific configuration.
- Conduct independent review of the actual PR diff; not performed by this agent.

## 📊 Current Health

- Tests: New edge-case tests added; execution status NOT RUN in this connected GitHub-only session.
- Coverage: Not measured.
- CI: Main contains separate Python test-matrix and Streamlit smoke workflows; PR run must be checked.
- Lint: No verified lint result for this branch.
- Security audit: Focused archive/file parsing hardening inspected; no full security audit executed.
- Build: NOT RUN locally.
- Independent review: NOT PERFORMED.

## 🧱 Architecture and Engineering Risks

- STL unit metadata is not reliably encoded; users must provide known units when required.
- 3MF object/build transforms and multi-object assembly placement are not applied to the reported mesh metrics.
- Volume is reported only for a single closed, consistently oriented, non-degenerate, duplicate-free shell.
- Statistical tolerance outputs are model-based estimates, not measured process capability or a GD&T conformance result.
- BOM and KiCad reference mismatches may be intentional due to DNP/BOM exclusions or hierarchy; findings require design review.

## 🔐 Security Findings

- Fixed on branch: malformed STL/3MF data is rejected with clearer input errors; duplicate faces cannot yield a misleading watertight volume result.
- Fixed on branch: malformed BOM component records are rejected with actionable validation errors.
- Fixed on branch: malformed native KiCad expressions and invalid UTF-8 are covered by regression tests.
- Remaining: broader archive-bomb/resource-limit testing, parser fuzzing and dependency review.

## 🔍 Verification

- Inspected README, package metadata, CI workflows, mesh analyzer, tolerance stack, BOM normalization, KiCad CSV/XML/native parser and audit, associated tests and CLI integration via the connected GitHub file interface.
- Checks actually executed: GitHub branch comparison and repository file retrieval only.
- pytest: NOT RUN.
- Build/package install: NOT RUN.
- Streamlit smoke test: NOT RUN.
- CI result for this branch: Not yet verified.
- Next step: open a review PR, inspect all Python matrix and Streamlit smoke results, then address failures before merge.
