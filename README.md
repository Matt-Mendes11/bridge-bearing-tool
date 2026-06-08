# Bridge Bearing Design Tool

## Executive Summary

The Bridge Bearing Design Tool is a Python-based digital engineering application that automates the seven mandatory design checks for elastomeric bridge bearings, based on the Freyssinet design manual and the provided assessment spreadsheet.

The purpose of this tool is to replace error-prone manual spreadsheet workflows with a validated, user-friendly interface that gives engineers immediate feedback on whether a proposed bearing configuration passes or fails. The application preserves engineering transparency by exposing the intermediate calculations behind each check, allowing senior engineers to verify the working rather than treating the tool as a black box.

## Tech Stack & Architecture

### Python

Python was selected because it is an industry-standard language for engineering mathematics, scientific computing, validation workflows, and automation. Its readability makes the design equations easy to audit, while its ecosystem supports future extension into testing, reporting, optimization, and data integration.

### Streamlit

Streamlit was selected because it enables rapid deployment of interactive engineering dashboards with minimal front-end overhead. It allows engineers to adjust design inputs in a sidebar and immediately see pass/fail results, intermediate values, and validation messages.

### Modular Design

The application is intentionally split into two main modules:

- `logic.py` contains the engineering calculations, validation layer, constants, and design check orchestration.
- `app.py` contains the Streamlit user interface, visual styling, tables, expanders, and display formatting.

This separation keeps the mathematical logic decoupled from the UI, making the calculation layer easier to test, review, and reuse. It also allows the same logic to be integrated later into other systems, such as APIs, batch design tools, or project databases.

## Getting Started

### 1. Clone the Repository

```bash
git clone <repository-url>
cd <repository-folder>
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

If `requirements.txt` is not yet present, install the core dependency manually:

```bash
pip install streamlit pandas
```

### 3. Run the Application

```bash
streamlit run app.py
```

On Windows, if the `streamlit` command is not recognized, use:

```bash
python -m streamlit run app.py
```

## Core Features

### Input Validation

The tool includes an engineering validation layer that checks inputs before any design calculations are executed. This protects against common issues such as:

- zero or negative dimensions
- zero or negative material properties
- physically impossible bearing geometry
- total bearing height being too small for the specified steel plates
- invalid rubber layer counts
- `Vmax` being less than `Vdl`
- derived effective dimensions `le = l - 10` and `be = b - 10` being non-positive

This validation layer prevents division-by-zero errors, misleading outputs, and impossible engineering configurations from reaching the calculation stage.

### Engineering Transparency

Each design check exposes the key intermediate values used in the calculation, including:

- effective area, `Ae`
- reduced loaded area, `A1`
- shape factor, `S`
- shear strain, `Eq`
- compression strain, `Ec`
- rotation strain, `E_alpha`
- total design strain, `Et`
- vertical deflection, `Delta_total`

This allows engineers to verify the working directly against the assessment brief and Freyssinet design equations.

### Unit Management

The interface accepts force inputs in kilonewtons (`kN`), which is natural for bridge engineering workflows. Internally, the calculation layer converts these values to Newtons (`N`) where required for stresses and modulus-based equations.

This keeps the UI practical for engineers while preserving dimensional consistency in the formulas.

## Verification Against Source

The tool has been verified against the provided sample bearing design data:

- bearing size: `457 x 254 x 54 mm`
- effective dimensions: `le = 447 mm`, `be = 244 mm`
- steel plates: `4 x 4.5 mm`
- rubber layers: `3`
- internal rubber thickness: `ti = 10 mm`

Key verification results:

| Check | Expected | Tool Output |
| --- | ---: | ---: |
| Shear strain, `Eq` | `0.80` | `0.80` |
| Maximum design strain, `Et` | `5.43` | `5.41` |
| Vertical deflection, `Delta_total` | `1.59 mm` | `1.59 mm` |
| Stability pressure, `Vmax/A1` | `14.98 N/mm²` | `14.98 N/mm²` |

Note: `Et` is calculated using full floating-point precision and the input value `G = 0.9 MPa`. The spreadsheet value of `5.43` appears to be affected by intermediate rounding or a slightly different hidden precision for `G`. The application preserves the stated engineering input values and rounds only for display.

## Technical Assumptions

The following assumptions are currently encoded based on the provided assessment brief and spreadsheet screenshots:

- `Eb = 2000 MPa`
- base horizontal transverse movement: `delta_bH = 17.2 mm`
- base horizontal longitudinal movement: `delta_lH = 3.45 mm`
- allowable steel stress: `sigma_s = 290 MPa`
- maximum strain factor: `k = 1.36`
- force inputs are entered in `kN`
- stress and modulus values are treated as `N/mm²`, equivalent to `MPa`
- effective dimensions are calculated as `le = l - 10` and `be = b - 10`

## Future Roadmap

With more time, the tool could be extended into a broader digital engineering platform.

### PDF Report Generation

Generate formal calculation reports for design submissions, including inputs, assumptions, pass/fail status, intermediate values, and equation references.

### Database Integration

Store bearing designs by project, bridge, span, or revision. This would allow engineers to compare historical designs, track changes, and retrieve previous calculations.

### Auto-Optimization

Add an optimization engine that suggests the smallest safe bearing size for a given set of loads, movements, rotations, and material constraints.

### Automated Test Suite

Build a formal unit test suite around `logic.py` using the provided spreadsheet values as regression tests. This would make future formula changes safer and easier to review.

## About the Developer

Developed by Matthew Mendes (BSc CS & IT), focusing on bridging the gap between structural engineering and modern software development.
