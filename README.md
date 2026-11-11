# Hardware-Box

A practical, open-source workbench for inspecting hardware records and engineering files.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/app-Streamlit-ff4b4b.svg)](https://streamlit.io/)

## Workspaces

- **Device records** — validate structured JSON device records.
- **Tolerance & fit** — calculate worst-case and RSS stacks; classify hole/shaft fits.
- **STL inspection** — inspect triangle count, bounds and degenerate facets.
- **KiCad BOM** — review component rows, duplicate references and missing values.
- **Project integrity** — scan ZIP paths and calculate an archive SHA-256 digest.

The app is read-only. Uploaded files are processed in memory and are not saved by the application. Engineering estimates are advisory and do not replace CAD validation, simulation, ERC/DRC or manufacturing sign-off.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS / Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Deploy a public demo

1. Open [Streamlit Community Cloud](https://share.streamlit.io/).
2. Select **New app** and connect `Gitcoder12/Hardware-Box`.
3. Choose branch `main` and file `streamlit_app.py`.
4. Deploy. Streamlit will assign the public `*.streamlit.app` URL.

## License

Apache-2.0. See [LICENSE](LICENSE).
