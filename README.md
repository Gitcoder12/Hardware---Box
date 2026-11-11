# Hardware-Box

An open-source workbench for inspecting hardware records, CAD meshes, PCB designs and engineering tolerances.

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![CI](https://github.com/Gitcoder12/Hardware-Box/actions/workflows/tests.yml/badge.svg)](https://github.com/Gitcoder12/Hardware-Box/actions/workflows/tests.yml)

## Workspaces

- Device registry, validation and design-readiness review
- STL / 3MF mesh inspection
- Worst-case and RSS tolerance stacks; hole / shaft fits
- Native KiCad schematic, PCB, BOM and netlist inspection
- ERC / DRC report review
- Project-bundle integrity verification

The app performs read-only analysis. Results are advisory and do not replace CAD-kernel validation, simulation, ERC/DRC or manufacturing sign-off.

## Run the app

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS / Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Install the Python toolkit

```bash
pip install -e .
hardware-box --help
```

## Run tests

```bash
pip install -e ".[dev]"
pytest tests/ -q
```

## Project layout

```text
Hardware-Box/
├── src/hardware_box/    # Python core and CLI
├── tests/               # 21 automated test modules
├── streamlit_app.py     # Streamlit Cloud entry point
├── examples/            # Sample hardware and engineering files
├── database/            # Device schemas and records
├── docs/                # Architecture and engineering notes
└── .github/workflows/   # CI and app smoke checks
```

## Deploy a public demo

On [Streamlit Community Cloud](https://share.streamlit.io/), create an app using repository `Gitcoder12/Hardware-Box`, branch `main`, and entry point `streamlit_app.py`. The public URL is generated after deployment.

## License

Apache-2.0. See [LICENSE](LICENSE).
