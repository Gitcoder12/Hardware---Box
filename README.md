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

## Engineering models and assumptions

Hardware-Box reports deterministic size limits separately from statistical process estimates.

### One-dimensional tolerance stacks

For a linear stack with nominal dimensions (d_i) and signed coefficients (c_i):

```text
Nominal stack = Σ(cᵢ × dᵢ)
Worst-case upper/lower deviations = sum of the corresponding absolute tolerance contributions
RSS upper/lower deviations = sqrt(Σ(contributionᵢ²))
```

For a negative stack coefficient, the plus/minus tolerance contributions are swapped. RSS is an estimate under the assumption that contributors are statistically independent; it is not a worst-case guarantee.

### Hole-and-shaft clearance

The deterministic limits are:

```text
Minimum clearance = minimum hole size − maximum shaft size
Maximum clearance = maximum hole size − minimum shaft size
```

The reported worst-case fit is clearance when the minimum clearance is non-negative, interference when the maximum clearance is negative, and transition otherwise.

### Optional statistical fit estimate

The `fit-check --statistical` mode models each size as a normal process distribution. For a configured (k)-sigma limit:

```text
Process mean = nominal + (upper tolerance − lower tolerance) / 2
Process sigma = (upper tolerance + lower tolerance) / (2k)
Clearance sigma = sqrt(hole sigma² + shaft sigma²)
P(interference) = Φ(−clearance mean / clearance sigma)
```

The default is (k=3). The model assumes independent hole and shaft processes and reports the assumed distribution and sigma multiplier with the result. It is a statistical estimate, not a guaranteed production yield or a substitute for measured process capability.

### Scope and limitations

These calculations are one-dimensional and size-only. They do not evaluate GD&T position/orientation, form, datum reference frames, cylindricity, runout, surface finish, thermal expansion, material deformation, coatings, alignment, assembly force, or a complete CAD tolerance analysis. STL units may be unspecified; 3MF object/build transforms are not applied by the mesh analyzer. Treat all output as engineering decision support and obtain appropriate CAD, simulation, metrology, and manufacturing review before releasing a design.


## License

Apache-2.0. See [LICENSE](LICENSE).

---

## Project handbook

- [Activity log](ACTIVITY_LOG.md)
- [Feature upgrade plan](FEATURE_UPGRADE_PLAN.md)
- [Company and team fit](COMPANY_FIT.md)
- [Beginner and technical README draft](README_ADDENDUM_DRAFT.md)
- [README quality checklist](README_QUALITY_CHECKLIST.md)
- [Contribution guide](CONTRIBUTING.md)
- [Agent instructions](AGENTS.md)
- [Agent skill map](SKILLS.md)
