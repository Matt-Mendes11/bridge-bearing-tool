import importlib

import pandas as pd
import streamlit as st

import logic

importlib.reload(logic)
from logic import BearingChecker, BearingInputs, format_status, validate_bearing_data


st.set_page_config(
    page_title="Bridge Bearing Design Checker",
    layout="wide",
)

NAIDU_GREEN = "#76b82a"
SOFT_RED = "#ff4b4b"

st.markdown(
    f"""
    <style>
        :root {{
            --primary-color: {NAIDU_GREEN};
        }}
        .stButton > button {{
            border-color: {NAIDU_GREEN};
        }}
        section.main > div {{
            padding-top: 1rem;
        }}
        h2, h3 {{
            color: #1f2933;
            margin-bottom: 0.35rem;
        }}
        div[data-testid="stAlert"] {{
            margin-bottom: 0.5rem;
        }}
        div[data-testid="stExpander"] {{
            background-color: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(118, 184, 42, 0.25);
            border-radius: 12px;
        }}
        div[data-testid="stMetric"] {{
            background-color: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 10px;
            padding: 0.75rem;
        }}
        div[data-testid="stMetricLabel"] p {{
            color: #d8dde3 !important;
        }}
        div[data-testid="stMetricValue"] {{
            color: {NAIDU_GREEN} !important;
        }}
        div[data-testid="stDataFrame"] {{
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid rgba(118, 184, 42, 0.25);
        }}
    </style>
    """,
    unsafe_allow_html=True,
)


def format_value(value):
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,.2f}"
    return value


SUMMARY_VALUE_KEYS = {
    "1. Shear Strain": "Eq",
    "2. Maximum Design Strain": "Et",
    "3. Plate Thickness": "t_min (mm)",
    "4. Stability": "Vmax/A1 (N/mm^2)",
    "5. Vertical Deflection": "Delta_total (mm)",
    "6. Rotational Limit": "Delta_total (mm)",
    "7. Fixing of Bearings": "H resultant (N)",
}


KEY_METRIC_LABELS = {
    "Ae (mm^2)": "Area Ae",
    "A1 (mm^2)": "Reduced Area A1",
    "S": "Shape Factor S",
    "Eq": "Shear Strain Eq",
    "Et": "Design Strain Et",
    "t_min (mm)": "Min Plate Thickness",
    "Vmax/A1 (N/mm^2)": "Bearing Stress",
    "Delta_total (mm)": "Total Deflection",
    "H resultant (N)": "Resultant Horizontal Force",
    "Vdl/A1 (N/mm^2)": "Dead Load Pressure",
}


def comparison_symbol(left, right, passing_operator):
    if passing_operator == "<=":
        return "<=" if left <= right else ">"
    if passing_operator == "<":
        return "<" if left < right else ">="
    if passing_operator == ">":
        return ">" if left > right else "<="
    return ""


def format_summary_value(result):
    values = result.intermediate_values

    if result.name == "1. Shear Strain":
        shear_strain = values.get("Eq")
        limit = 0.7
        if isinstance(shear_strain, (float, int)):
            operator = comparison_symbol(shear_strain, limit, "<=")
            return f"{shear_strain:,.2f} {operator} {limit:,.2f}"

    if result.name == "2. Maximum Design Strain":
        design_strain = values.get("Et")
        limit = 5.0
        if isinstance(design_strain, (float, int)):
            operator = comparison_symbol(design_strain, limit, "<=")
            return f"{design_strain:,.2f} {operator} {limit:,.2f}"

    if result.name == "3. Plate Thickness":
        minimum_thickness = values.get("t_min (mm)")
        actual_thickness = values.get("actual plate thickness (mm)")
        if isinstance(minimum_thickness, (float, int)) and isinstance(
            actual_thickness, (float, int)
        ):
            operator = comparison_symbol(minimum_thickness, actual_thickness, "<=")
            return f"{minimum_thickness:,.2f} {operator} {actual_thickness:,.2f}"

    if result.name == "4. Stability":
        pressure = values.get("Vmax/A1 (N/mm^2)")
        limit = values.get("(2beGS)/(3sum_ti)")
        if isinstance(pressure, (float, int)) and isinstance(limit, (float, int)):
            operator = comparison_symbol(pressure, limit, "<")
            return f"{pressure:,.2f} {operator} {limit:,.2f}"

    if result.name == "5. Vertical Deflection":
        deflection = values.get("Delta_total (mm)")
        limit = values.get("0.15 * ti (mm)")
        if isinstance(deflection, (float, int)) and isinstance(limit, (float, int)):
            operator = comparison_symbol(deflection, limit, "<=")
            return f"{deflection:,.2f} {operator} {limit:,.2f}"

    if result.name == "6. Rotational Limit":
        deflection = values.get("Delta_total (mm)")
        rotation_limit = values.get("(be * ab + le * al) / 3 (mm)")
        if isinstance(deflection, (float, int)) and isinstance(
            rotation_limit, (float, int)
        ):
            operator = comparison_symbol(deflection, rotation_limit, ">")
            return f"{deflection:,.2f} {operator} {rotation_limit:,.2f}"

    if result.name == "7. Fixing of Bearings":
        horizontal_force = values.get("H resultant (N)")
        horizontal_limit = values.get("0.1 * (Vmax + 2*A1)")
        pressure = values.get("Vdl/A1 (N/mm^2)")
        pressure_limit = 2.0
        if (
            isinstance(horizontal_force, (float, int))
            and isinstance(horizontal_limit, (float, int))
            and isinstance(pressure, (float, int))
        ):
            force_operator = comparison_symbol(horizontal_force, horizontal_limit, "<")
            pressure_operator = comparison_symbol(pressure, pressure_limit, ">")
            return (
                f"H: {horizontal_force / 1000:,.2f}kN {force_operator} "
                f"Limit: {horizontal_limit / 1000:,.2f}kN | "
                f"Vdl/A1: {pressure:,.2f} {pressure_operator} {pressure_limit:,.2f}"
            )

    value_key = SUMMARY_VALUE_KEYS.get(result.name)
    if value_key is None:
        return ""

    value = values.get(value_key)
    if isinstance(value, (float, int)):
        return f"{value_key} = {value:,.2f}"
    return ""


def metric_value(value):
    if isinstance(value, (float, int)):
        return f"{value:,.2f}"
    return str(value)


def key_metric_rows(result):
    return [
        (label, result.intermediate_values[key])
        for key, label in KEY_METRIC_LABELS.items()
        if key in result.intermediate_values
    ]


def safe_float(value, default):
    """Return a numeric sidebar value, falling back when Streamlit supplies None."""

    return default if value is None else float(value)


def safe_int(value, default):
    """Return an integer sidebar value, falling back when Streamlit supplies None."""

    return default if value is None else int(value)


def status_cell_style(value):
    """Return table-cell CSS for a PASS or FAIL status."""

    if value == "PASS":
        return (
            f"background-color: {NAIDU_GREEN}; color: white; font-weight: 700; "
            "text-align: center;"
        )
    if value == "FAIL":
        return (
            f"background-color: {SOFT_RED}; color: white; font-weight: 700; "
            "text-align: center;"
        )
    return ""


def summary_cell_style(column):
    """Apply modern spacing and status coloring to the summary table."""

    if column.name == "Status":
        return [status_cell_style(value) for value in column]
    if column.name == "Value vs Limit":
        return ["padding-left: 16px; padding-right: 16px;" for _ in column]
    return ["" for _ in column]


def make_inputs() -> BearingInputs:
    with st.sidebar:
        st.header("Bearing Inputs")

        with st.expander("Geometry", expanded=True):
            bearing_length = st.number_input(
                "Bearing length, l (mm)", min_value=0.0, value=457.0, step=1.0
            )
            bearing_width = st.number_input(
                "Bearing width, b (mm)", min_value=0.0, value=254.0, step=1.0
            )
            total_bearing_height = st.number_input(
                "Total bearing height, T (mm)", min_value=0.0, value=54.0, step=1.0
            )
            st.caption("Effective dimensions are calculated as le = l - 10 and be = b - 10.")

        with st.expander("Rubber and Steel", expanded=True):
            steel_plate_thickness = st.number_input(
                "Plate thickness (mm)", min_value=0.0, value=4.5, step=0.1
            )
            steel_plate_count = st.number_input(
                "Number of steel plates", min_value=1, value=4, step=1
            )
            rubber_layer_count = st.number_input(
                "Number of rubber layers", min_value=1, value=3, step=1
            )
            edge_rubber_thickness = st.number_input(
                "Edge rubber thickness, te (mm)", min_value=0.0, value=10.0, step=0.1
            )
            internal_rubber_thickness = st.number_input(
                "Internal rubber layer thickness, ti (mm)",
                min_value=0.0,
                value=10.0,
                step=0.1,
            )
            shear_modulus = st.number_input(
                "Shear modulus, G (N/mm^2)", min_value=0.0, value=0.9, step=0.1
            )
            bulk_modulus = st.number_input(
                "Bulk/compression modulus, Eb (N/mm^2)",
                min_value=0.0,
                value=2000.0,
                step=100.0,
            )

        with st.expander("Loads", expanded=True):
            maximum_vertical_load = st.number_input(
                "Maximum vertical load, Vmax (kN)",
                min_value=0.0,
                value=1420.0,
                step=1.0,
            )
            dead_load_vertical_force = st.number_input(
                "Dead load vertical force, Vdl (kN)",
                min_value=0.0,
                value=384.0,
                step=1.0,
            )
            live_load_vertical_force = st.number_input(
                "Live load vertical force, Vll (kN)",
                min_value=0.0,
                value=1036.0,
                step=1.0,
            )
            longitudinal_shear_force = st.number_input(
                "Longitudinal shear force, Hs (kN)",
                min_value=0.0,
                value=50.0,
                step=1.0,
            )
            transverse_shear_force = st.number_input(
                "Transverse shear force, Ht (kN)",
                min_value=0.0,
                value=10.0,
                step=1.0,
            )

        with st.expander("Movements and Rotations", expanded=True):
            transverse_movement = st.number_input(
                "Transverse movement, delta_b (mm)",
                min_value=0.0,
                value=10.6,
                step=0.1,
            )
            horizontal_transverse_movement = st.number_input(
                "Horizontal transverse movement, delta_bH (mm)",
                min_value=0.0,
                value=17.2,
                step=0.1,
            )
            longitudinal_movement = st.number_input(
                "Longitudinal movement, delta_l (mm)",
                min_value=0.0,
                value=4.19,
                step=0.1,
            )
            horizontal_longitudinal_movement = st.number_input(
                "Horizontal longitudinal movement, delta_lH (mm)",
                min_value=0.0,
                value=3.45,
                step=0.1,
            )
            rotation_alpha_b = st.number_input(
                "Rotation ab (radians)",
                min_value=0.0,
                value=0.0001,
                step=0.0001,
                format="%.6f",
            )
            rotation_alpha_l = st.number_input(
                "Rotation al (radians)",
                min_value=0.0,
                value=0.0,
                step=0.0001,
                format="%.6f",
            )

        with st.expander("Design Constants"):
            allowable_steel_stress = st.number_input(
                "Allowable steel stress, sigma_s (N/mm^2)",
                min_value=0.0,
                value=290.0,
                step=1.0,
            )
            maximum_strain_factor = st.number_input(
                "Maximum strain factor, k", min_value=0.0, value=1.36, step=0.01
            )

    return BearingInputs(
        bearing_length=safe_float(bearing_length, 457.0),
        bearing_width=safe_float(bearing_width, 254.0),
        total_bearing_height=safe_float(total_bearing_height, 54.0),
        steel_plate_thickness=safe_float(steel_plate_thickness, 4.5),
        steel_plate_count=safe_int(steel_plate_count, 4),
        rubber_layer_count=safe_int(rubber_layer_count, 3),
        edge_rubber_thickness=safe_float(edge_rubber_thickness, 10.0),
        internal_rubber_thickness=safe_float(internal_rubber_thickness, 10.0),
        shear_modulus=safe_float(shear_modulus, 0.9),
        bulk_modulus=safe_float(bulk_modulus, 2000.0),
        maximum_vertical_load=safe_float(maximum_vertical_load, 1420.0),
        dead_load_vertical_force=safe_float(dead_load_vertical_force, 384.0),
        live_load_vertical_force=safe_float(live_load_vertical_force, 1036.0),
        longitudinal_shear_force=safe_float(longitudinal_shear_force, 50.0),
        transverse_shear_force=safe_float(transverse_shear_force, 10.0),
        longitudinal_movement=safe_float(longitudinal_movement, 4.19),
        transverse_movement=safe_float(transverse_movement, 10.6),
        horizontal_longitudinal_movement=safe_float(
            horizontal_longitudinal_movement, 3.45
        ),
        horizontal_transverse_movement=safe_float(
            horizontal_transverse_movement, 17.2
        ),
        rotation_alpha_b=safe_float(rotation_alpha_b, 0.0001),
        rotation_alpha_l=safe_float(rotation_alpha_l, 0.0),
        allowable_steel_stress=safe_float(allowable_steel_stress, 290.0),
        maximum_strain_factor=safe_float(maximum_strain_factor, 1.36),
    )


inputs = make_inputs()

validation_errors = validate_bearing_data(inputs)
if validation_errors:
    st.error("Input validation failed. Please fix the following issues:")
    for error in validation_errors:
        st.error(error)
    st.stop()

try:
    checker = BearingChecker(inputs)
    results = checker.run_all_checks()
except ValueError as exc:
    st.error(f"Input validation failed: {exc}")
    st.stop()

overall_passed = all(result.passed for result in results)

with st.container():
    st.subheader("Bridge Bearing Design")
    if overall_passed:
        st.success("BEARING PASSES")
    else:
        st.error("BEARING FAILS")

st.subheader("✓ Check Summary")
summary_rows = [
    {
        "Design Check": result.name,
        "Status": result.status,
        "Value vs Limit": format_summary_value(result),
    }
    for result in results
]
summary_df = pd.DataFrame(summary_rows)
styled_summary = summary_df.style.apply(
    summary_cell_style,
)
st.dataframe(
    styled_summary,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Design Check": st.column_config.TextColumn(width="large"),
        "Status": st.column_config.TextColumn(width="small"),
        "Value vs Limit": st.column_config.TextColumn(width="large"),
    },
)

st.subheader("Intermediate Values")
for result in results:
    icon = "OK" if result.passed else "FAIL"
    with st.expander(f"{icon} - {result.name}", expanded=not result.passed):
        st.markdown(f"**Status:** {format_status(result.passed)}")
        st.write(f"**Pass condition:** {result.pass_condition}")
        metrics = key_metric_rows(result)
        if metrics:
            st.caption("Main engineering values")
            metric_columns = st.columns(3)
            for index, (label, value) in enumerate(metrics):
                metric_columns[index % len(metric_columns)].metric(
                    label, metric_value(value)
                )

st.subheader("Engineering Assumptions")
st.markdown(
    f"""
- Units are in mm and kN at input; force values are converted to N inside the calculation logic.
- Stress and modulus values are treated as N/mm^2, equivalent to MPa.
- Eb (Bulk Modulus) is assumed to be {inputs.bulk_modulus:g} MPa unless changed in the sidebar.
- G (Shear Modulus) is assumed to be {inputs.shear_modulus:g} MPa unless changed in the sidebar.
- Allowable steel stress, sigma_s, is assumed to be {inputs.allowable_steel_stress:g} MPa unless changed in the sidebar.
- Maximum strain factor, k, is assumed to be {inputs.maximum_strain_factor:g} unless changed in the sidebar.
"""
)
