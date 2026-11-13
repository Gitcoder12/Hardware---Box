# Hardware-Box — Feature Upgrade Plan

**Snapshot:** 2026-11-13

## Objective

A toolkit that inspects engineering files such as CAD meshes and PCB records, checks their structure and reports possible design issues.

## P0 — correctness and scope

- [ ] Expand malformed CAD/PCB fixture coverage and verify all parser failure modes.
- [ ] Document file formats, tolerances, coordinate conventions and unsupported geometry explicitly.

## P1 — complete user workflow

- [ ] Add stable machine-readable reports and reproducible sample bundles.
- [ ] Validate BOM and netlist relationships with clear diagnostics and source locations.

## P2 — research and scale

- [ ] Benchmark large models and board bundles with stated hardware and file sizes.
- [ ] Add plugin interfaces for additional engineering formats while preserving read-only defaults.

## Work packages for collaborators

1. Reproduce one defect or define one measurable question.
2. Implement one bounded change with tests.
3. Document exact commands, environment, input data and expected output.
4. Record results and limitations in ACTIVITY_LOG.md.

## Acceptance gate

- [ ] Clean setup works from README.
- [ ] Tests cover normal, boundary and failure paths.
- [ ] Claims match tested implementation.
- [ ] Benchmarks disclose environment, data and methodology.
- [ ] PR links the roadmap item, tests and log entry.
