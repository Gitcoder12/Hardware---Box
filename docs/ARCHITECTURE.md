# Architecture

Hardware-Box is organized as a local-first Python package and a Streamlit interface.

```text
Hardware-Box/
├── src/hardware_box/       # Core library and command-line interface
├── tests/                  # Automated unit and integration tests
├── hardware_box_streamlit.py
├── streamlit_app.py        # Streamlit Community Cloud entry point
├── database/               # Device schema and sample records
├── examples/               # Synthetic engineering and KiCad fixtures
├── docs/                   # Architecture and engineering notes
└── .github/workflows/      # CI and Streamlit startup checks
```

The core package handles device records, component cataloguing, compatibility and electrical screening, tolerance analysis, mesh metadata, KiCad exports/native file structure, and integrity-checked project bundles.

The Streamlit app is a separate presentation layer. It is read-only for supplied engineering files and provides advisory checks; it does not replace CAD kernels, simulation, ERC/DRC, safety review or manufacturing sign-off.
