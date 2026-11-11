# Validation and engineering boundaries

## Automated checks

Run the complete suite from the repository root:

```bash
pip install -e ".[dev]"
pytest tests/ -q
```

GitHub Actions runs the same suite on supported Python versions. It also compiles the package and tests the Streamlit application health endpoint.

## Engineering limits

- A successful JSON validation confirms record shape and declared metadata only.
- Interface matching compares declared metadata; it does not prove electrical, mechanical, timing, firmware or protocol compatibility.
- Electrical budget checks are arithmetic screening, not transient, thermal, EMC or electrical-safety analysis.
- Tolerance calculations use a one-dimensional stack. RSS assumes statistical independence and must not be treated as a production capability claim.
- Mesh checks infer topology from triangle-edge incidence; they are not a CAD-kernel repair or manufacturing certification.
- KiCad parsers inspect source structures and exported reports. The optional CLI integration runs the installed KiCad checks, but a clean report only reflects enabled checks and declared exclusions.
- Asset manifests and bundles detect missing, modified and untracked files; they do not establish provenance or ownership.
