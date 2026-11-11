# Hardware-Box

An open-source workbench for inspecting hardware records, CAD meshes, PCB data and engineering tolerances.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/app-Streamlit-ff4b4b.svg)](https://streamlit.io/)

## Workspaces

- Device registry and design-readiness review
- STL / 3MF mesh analysis
- Worst-case and RSS tolerance stacks; hole/shaft fit
- Native KiCad inspection, BOM and netlist cross-checks
- ERC / DRC report review
- Project-bundle SHA-256 verification

The app is read-only for engineering files. It does not replace simulation, CAD-kernel validation, ERC/DRC or manufacturing sign-off.

## Run the app

```bash
python -m venv .venv
# Activate the environment, then:
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Restore the full Python toolkit

The v1.2.0 source, CLI, examples, documentation and tests are included in the repository. Rebuild the verified source tree:

```bash
python restore_core.py
pip install -e "core-source[dev]"
cd core-source
pytest -q
hardware-box --help
```

The restore script verifies the release archive's SHA-256 before extraction. GitHub Actions repeats the restore, test and wheel-build checks on every push and pull request.

## Public demo

Deploy through [Streamlit Community Cloud](https://share.streamlit.io/): select `Gitcoder12/Hardware-Box`, branch `main`, and entry point `streamlit_app.py`. Streamlit will assign the app URL after you authorize and deploy it.

## License

Apache-2.0. See [LICENSE](LICENSE).
