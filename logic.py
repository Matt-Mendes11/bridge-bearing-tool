from dataclasses import dataclass
from math import sqrt
from typing import ClassVar


def format_status(passed: bool) -> str:
    """Return a Streamlit-friendly colored status string."""

    return ":green[PASS]" if passed else ":red[FAIL]"


@dataclass(frozen=True)
class BearingInputs:
    """Input values for the elastomeric bearing design checks."""

    bearing_length: float
    bearing_width: float
    total_bearing_height: float
    steel_plate_thickness: float
    steel_plate_count: int
    rubber_layer_count: int
    edge_rubber_thickness: float
    internal_rubber_thickness: float
    shear_modulus: float
    bulk_modulus: float
    maximum_vertical_load: float
    dead_load_vertical_force: float
    live_load_vertical_force: float
    longitudinal_shear_force: float
    transverse_shear_force: float
    longitudinal_movement: float
    transverse_movement: float
    horizontal_longitudinal_movement: float
    horizontal_transverse_movement: float
    rotation_alpha_b: float
    rotation_alpha_l: float
    allowable_steel_stress: float = 290.0
    maximum_strain_factor: float = 1.36

    @property
    def effective_length(self) -> float:
        """Calculate effective length le as l - 10, matching the Excel sheet."""

        return self.bearing_length - 10

    @property
    def effective_width(self) -> float:
        """Calculate effective width be as b - 10, matching the Excel sheet."""

        return self.bearing_width - 10


@dataclass(frozen=True)
class CheckDefinition:
    """Defines one design check and the BearingChecker method that runs it."""

    key: str
    name: str
    method_name: str


@dataclass(frozen=True)
class CheckResult:
    """Result for one design check."""

    name: str
    passed: bool
    status: str
    pass_condition: str
    intermediate_values: dict[str, float | str]


def validate_bearing_data(inputs: BearingInputs) -> list[str]:
    """Run engineering sanity checks before any design calculations are performed."""

    errors: list[str] = []
    required_positive_values = {
        "Bearing length, l": inputs.bearing_length,
        "Bearing width, b": inputs.bearing_width,
        "Total bearing height, T": inputs.total_bearing_height,
        "Internal rubber thickness, ti": inputs.internal_rubber_thickness,
        "Edge rubber thickness, te": inputs.edge_rubber_thickness,
        "Steel plate thickness, t_thk": inputs.steel_plate_thickness,
        "Shear modulus, G": inputs.shear_modulus,
        "Bulk modulus, Eb": inputs.bulk_modulus,
        "Maximum vertical load, Vmax": inputs.maximum_vertical_load,
    }

    for label, value in required_positive_values.items():
        if value is None:
            errors.append(f"{label} is required.")
        elif value <= 0:
            errors.append(f"{label} must be greater than zero.")

    if inputs.rubber_layer_count < 1:
        errors.append("Layer Error: The number of rubber layers must be at least 1.")

    if inputs.steel_plate_count < 1:
        errors.append("Layer Error: The number of steel plates must be at least 1.")

    total_steel_plate_height = inputs.steel_plate_count * inputs.steel_plate_thickness
    if inputs.total_bearing_height <= total_steel_plate_height:
        errors.append(
            "Physical Error: Total height is too small to contain the specified steel plates."
        )

    if inputs.maximum_vertical_load < inputs.dead_load_vertical_force:
        errors.append("Data Error: Vmax cannot be less than Vdl.")

    if inputs.effective_length <= 0:
        errors.append(
            "Dimension Error: Effective length le = l - 10 must be positive; "
            "bearing length must be greater than 10 mm."
        )
    if inputs.effective_width <= 0:
        errors.append(
            "Dimension Error: Effective width be = b - 10 must be positive; "
            "bearing width must be greater than 10 mm."
        )

    if (
        inputs.longitudinal_movement < 0
        or inputs.transverse_movement < 0
        or inputs.horizontal_longitudinal_movement < 0
        or inputs.horizontal_transverse_movement < 0
    ):
        errors.append("Movement Error: Movement values must not be negative.")

    if inputs.dead_load_vertical_force < 0 or inputs.live_load_vertical_force < 0:
        errors.append("Load Error: Vertical load components must not be negative.")

    if inputs.longitudinal_shear_force < 0 or inputs.transverse_shear_force < 0:
        errors.append("Load Error: Shear force components must not be negative.")

    if inputs.allowable_steel_stress <= 0:
        errors.append("Allowable steel stress, sigma_s, must be greater than zero.")

    if inputs.maximum_strain_factor <= 0:
        errors.append("Maximum strain factor, k, must be greater than zero.")

    if not errors:
        effective_area_factor = (
            1
            - (
                inputs.transverse_movement
                + inputs.horizontal_transverse_movement
            )
            / inputs.effective_width
            - (
                inputs.longitudinal_movement
                + inputs.horizontal_longitudinal_movement
            )
            / inputs.effective_length
        )
        if effective_area_factor <= 0:
            errors.append(
                "Geometry Error: Effective loaded area A1 must be positive; "
                "reduce movements or increase effective bearing dimensions."
            )

    return errors


class BearingChecker:
    """Runs the seven elastomeric bridge bearing design checks."""

    # Constants copied from the Excel assessment sheet.
    EXCEL_DEFAULT_MAXIMUM_STRAIN_FACTOR = 1.36  # k in the maximum strain check.
    EXCEL_DEFAULT_ALLOWABLE_STEEL_STRESS = 290.0  # sigma_s for plates without holes.
    EXCEL_DEFAULT_HORIZONTAL_TRANSVERSE_MOVEMENT = 17.2  # delta_bH in mm.
    EXCEL_DEFAULT_HORIZONTAL_LONGITUDINAL_MOVEMENT = 3.45  # delta_lH in mm.

    # Formula constants from the Freyssinet/manual checks shown in the brief.
    NEWTONS_PER_KILONEWTON = 1000.0
    SHEAR_STRAIN_LIMIT = 0.7
    COMPRESSION_STRAIN_FACTOR = 1.5
    MAXIMUM_DESIGN_STRAIN_LIMIT = 5.0
    PLATE_THICKNESS_FACTOR = 1.3
    STABILITY_STRESS_NUMERATOR_FACTOR = 2.0
    STABILITY_STRESS_DENOMINATOR_FACTOR = 3.0
    STABILITY_GEOMETRY_DIVISOR = 4.0
    VERTICAL_DEFLECTION_STIFFNESS_FACTOR = 5.0
    VERTICAL_DEFLECTION_LIMIT_FACTOR = 0.15
    ROTATIONAL_LIMIT_DIVISOR = 3.0
    FIXING_FORCE_FACTOR = 0.1
    MINIMUM_FIXING_PRESSURE = 2.0

    CHECK_DEFINITIONS: ClassVar[dict[str, CheckDefinition]] = {
        "shear_strain": CheckDefinition(
            key="shear_strain",
            name="1. Shear Strain",
            method_name="check_shear_strain",
        ),
        "maximum_design_strain": CheckDefinition(
            key="maximum_design_strain",
            name="2. Maximum Design Strain",
            method_name="check_max_design_strain",
        ),
        "plate_thickness": CheckDefinition(
            key="plate_thickness",
            name="3. Plate Thickness",
            method_name="check_plate_thickness",
        ),
        "stability": CheckDefinition(
            key="stability",
            name="4. Stability",
            method_name="check_stability",
        ),
        "vertical_deflection": CheckDefinition(
            key="vertical_deflection",
            name="5. Vertical Deflection",
            method_name="check_vertical_deflection",
        ),
        "rotational_limit": CheckDefinition(
            key="rotational_limit",
            name="6. Rotational Limit",
            method_name="check_rotational_limit",
        ),
        "fixing_of_bearings": CheckDefinition(
            key="fixing_of_bearings",
            name="7. Fixing of Bearings",
            method_name="check_fixing_of_bearings",
        ),
    }

    def __init__(self, inputs: BearingInputs):
        """Store bearing inputs and validate them before running checks."""

        self.inputs = inputs
        self._validate_inputs()

    def _validate_inputs(self) -> None:
        """Validate all dimensions, material properties, loads, and movements."""

        errors = validate_bearing_data(self.inputs)
        if errors:
            raise ValueError("; ".join(errors))

    @property
    def effective_area(self) -> float:
        """Calculate the effective plan area Ae = le * be."""

        return self.calculate_area(
            self.inputs.effective_length,
            self.inputs.effective_width,
        )

    @property
    def total_internal_rubber_thickness(self) -> float:
        """Calculate sum_ti as the number of rubber layers times ti."""

        return self.inputs.rubber_layer_count * self.inputs.internal_rubber_thickness

    @property
    def total_rubber_thickness(self) -> float:
        """Calculate tq as T minus the total thickness of reinforcing plates."""

        return self.inputs.total_bearing_height - (
            self.inputs.steel_plate_count * self.inputs.steel_plate_thickness
        )

    @property
    def total_longitudinal_movement(self) -> float:
        """Calculate total_dl from imposed longitudinal movement plus delta_lH."""

        return (
            self.inputs.longitudinal_movement
            + self.inputs.horizontal_longitudinal_movement
        )

    @property
    def total_transverse_movement(self) -> float:
        """Calculate total_db from imposed transverse movement plus delta_bH."""

        return self.inputs.transverse_movement + self.inputs.horizontal_transverse_movement

    @property
    def effective_shear_thickness(self) -> float:
        """Return tq, the effective shear thickness used in the Excel sheet."""

        return self.total_rubber_thickness

    @property
    def shape_factor(self) -> float:
        """Calculate the shape factor S based on Freyssinet Section 4.1."""

        return self.calculate_shape_factor(
            effective_area=self.effective_area,
            internal_rubber_thickness=self.inputs.internal_rubber_thickness,
            effective_length=self.inputs.effective_length,
            effective_width=self.inputs.effective_width,
        )

    @property
    def loaded_shape_factor(self) -> float:
        """Calculate the reduced shape factor S' using loaded area A1."""

        return self.calculate_shape_factor(
            effective_area=self.loaded_area_after_movement,
            internal_rubber_thickness=self.inputs.internal_rubber_thickness,
            effective_length=self.inputs.effective_length,
            effective_width=self.inputs.effective_width,
        )

    @property
    def loaded_area_after_movement(self) -> float:
        """Calculate reduced loaded area A1 after longitudinal and transverse movement."""

        return self.effective_area * (
            1
            - (self.total_transverse_movement / self.inputs.effective_width)
            - (self.total_longitudinal_movement / self.inputs.effective_length)
        )

    @property
    def maximum_vertical_load_newtons(self) -> float:
        """Convert maximum vertical load Vmax from kN to N."""

        return self.inputs.maximum_vertical_load * self.NEWTONS_PER_KILONEWTON

    @staticmethod
    def calculate_area(length: float, width: float) -> float:
        """Calculate a rectangular bearing area from length and width."""

        return length * width

    @staticmethod
    def calculate_resultant_movement(
        transverse_movement: float,
        longitudinal_movement: float,
    ) -> float:
        """Calculate resultant movement delta_r from transverse and longitudinal components."""

        return sqrt(transverse_movement**2 + longitudinal_movement**2)

    @staticmethod
    def calculate_shape_factor(
        effective_area: float,
        internal_rubber_thickness: float,
        effective_length: float,
        effective_width: float,
    ) -> float:
        """Calculate shape factor S using Ae / (2 * ti * (le + be))."""

        return effective_area / (
            2
            * internal_rubber_thickness
            * (effective_length + effective_width)
        )

    @staticmethod
    def build_result(
        name: str,
        passed: bool,
        pass_condition: str,
        intermediate_values: dict[str, float | str],
    ) -> CheckResult:
        """Create a CheckResult with a consistent PASS or FAIL status."""

        return CheckResult(
            name=name,
            passed=passed,
            status="PASS" if passed else "FAIL",
            pass_condition=pass_condition,
            intermediate_values=intermediate_values,
        )

    # Freyssinet limits shear deformation so service movements do not overstress
    # the elastomer in shear. The resultant plan movement is divided by the
    # effective shear thickness and compared to the allowable shear strain.
    def check_shear_strain(self) -> CheckResult:
        """Check shear strain Eq = delta_r / tq against the 0.7 limit."""

        resultant_movement = self.calculate_resultant_movement(
            transverse_movement=self.total_transverse_movement,
            longitudinal_movement=self.total_longitudinal_movement,
        )
        shear_strain = resultant_movement / self.effective_shear_thickness
        passed = shear_strain <= self.SHEAR_STRAIN_LIMIT
        return self.build_result(
            name="1. Shear Strain",
            passed=passed,
            pass_condition="Eq <= 0.7",
            intermediate_values={
                "delta_l (mm)": self.inputs.longitudinal_movement,
                "delta_b (mm)": self.inputs.transverse_movement,
                "delta_lH (mm)": self.inputs.horizontal_longitudinal_movement,
                "delta_bH (mm)": self.inputs.horizontal_transverse_movement,
                "total_dl (mm)": self.total_longitudinal_movement,
                "total_db (mm)": self.total_transverse_movement,
                "delta_r (mm)": resultant_movement,
                "tq effective shear thickness (mm)": self.effective_shear_thickness,
                "Ae (mm^2)": self.effective_area,
                "A1 (mm^2)": self.loaded_area_after_movement,
                "S": self.shape_factor,
                "Eq": shear_strain,
            },
        )

    # Freyssinet combines compression strain, shear strain, and rotation strain
    # to check the total design strain in the elastomer. The manual applies the
    # maximum strain factor k to this combined demand.
    def check_max_design_strain(
        self, shear_strain: float | None = None
    ) -> CheckResult:
        """Check maximum total design strain Et against the Freyssinet limit of 5.0."""

        if shear_strain is None:
            shear_strain = float(self.check_shear_strain().intermediate_values["Eq"])

        compression_strain = (
            self.COMPRESSION_STRAIN_FACTOR * self.maximum_vertical_load_newtons
        ) / (
            self.inputs.shear_modulus
            * self.loaded_area_after_movement
            * self.shape_factor
        )
        rotation_strain = (
            (self.inputs.effective_width**2 * self.inputs.rotation_alpha_b)
            + (self.inputs.effective_length**2 * self.inputs.rotation_alpha_l)
        ) / (
            2
            * self.inputs.internal_rubber_thickness
            * self.total_internal_rubber_thickness
        )
        total_design_strain = self.inputs.maximum_strain_factor * (
            compression_strain + shear_strain + rotation_strain
        )
        passed = total_design_strain <= self.MAXIMUM_DESIGN_STRAIN_LIMIT
        return self.build_result(
            name="2. Maximum Design Strain",
            passed=passed,
            pass_condition="Et <= 5.0",
            intermediate_values={
                "Ae (mm^2)": self.effective_area,
                "A1 (mm^2)": self.loaded_area_after_movement,
                "S": self.shape_factor,
                "sum_ti (mm)": self.total_internal_rubber_thickness,
                "Ec": compression_strain,
                "Eq": shear_strain,
                "E_alpha": rotation_strain,
                "k": self.inputs.maximum_strain_factor,
                "Et": total_design_strain,
            },
        )

    # Freyssinet sizes the reinforcing steel plate so bending stress from the
    # compressed rubber layers stays within the allowable steel stress.
    def check_plate_thickness(self) -> CheckResult:
        """Check minimum reinforcing plate thickness against the actual plate thickness."""

        lower_rubber_layer_thickness = self.inputs.internal_rubber_thickness
        upper_rubber_layer_thickness = self.inputs.internal_rubber_thickness
        minimum_plate_thickness = (
            self.PLATE_THICKNESS_FACTOR
            * (lower_rubber_layer_thickness + upper_rubber_layer_thickness)
            * self.maximum_vertical_load_newtons
        ) / (
            self.loaded_area_after_movement * self.inputs.allowable_steel_stress
        )
        passed = minimum_plate_thickness <= self.inputs.steel_plate_thickness
        return self.build_result(
            name="3. Plate Thickness",
            passed=passed,
            pass_condition="t_min <= actual plate thickness",
            intermediate_values={
                "t1 (mm)": lower_rubber_layer_thickness,
                "t2 (mm)": upper_rubber_layer_thickness,
                "Vmax (N)": self.maximum_vertical_load_newtons,
                "A1 (mm^2)": self.loaded_area_after_movement,
                "sigma_s (N/mm^2)": self.inputs.allowable_steel_stress,
                "t_min (mm)": minimum_plate_thickness,
                "actual plate thickness (mm)": self.inputs.steel_plate_thickness,
            },
        )

    # Freyssinet stability checks guard against bearing buckling by limiting
    # compressive stress relative to shape factor and by keeping the rubber stack
    # slenderness within the effective bearing width.
    def check_stability(self) -> CheckResult:
        """Check bearing stability using pressure and rubber-stack geometry limits."""

        compressive_stress = (
            self.maximum_vertical_load_newtons / self.loaded_area_after_movement
        )
        stress_limit = (
            self.STABILITY_STRESS_NUMERATOR_FACTOR
            * self.inputs.effective_width
            * self.inputs.shear_modulus
            * self.shape_factor
        ) / (
            self.STABILITY_STRESS_DENOMINATOR_FACTOR
            * self.total_internal_rubber_thickness
        )
        geometry_limit = (
            self.inputs.effective_width / self.STABILITY_GEOMETRY_DIVISOR
        )
        stress_ok = compressive_stress < stress_limit
        geometry_ok = self.total_internal_rubber_thickness < geometry_limit
        passed = stress_ok and geometry_ok
        return self.build_result(
            name="4. Stability",
            passed=passed,
            pass_condition="Vmax/A1 < (2beGS)/(3sum_ti) and sum_ti < be/4",
            intermediate_values={
                "Vmax/A1 (N/mm^2)": compressive_stress,
                "(2beGS)/(3sum_ti)": stress_limit,
                "stress limit satisfied": "Yes" if stress_ok else "No",
                "sum_ti (mm)": self.total_internal_rubber_thickness,
                "be/4 (mm)": geometry_limit,
                "geometry limit satisfied": "Yes" if geometry_ok else "No",
            },
        )

    # Freyssinet vertical deflection combines shape-factor-dependent compression
    # with bulk compression. The total deflection over all rubber layers is
    # limited to a fraction of the layer thickness.
    def check_vertical_deflection(self) -> CheckResult:
        """Check total vertical deflection Delta_total against 0.15 * ti."""

        deflection_per_layer = (
            self.maximum_vertical_load_newtons * self.inputs.internal_rubber_thickness
        ) / (
            self.VERTICAL_DEFLECTION_STIFFNESS_FACTOR
            * self.effective_area
            * self.inputs.shear_modulus
            * self.shape_factor**2
        ) + (
            self.maximum_vertical_load_newtons * self.inputs.internal_rubber_thickness
        ) / (self.effective_area * self.inputs.bulk_modulus)
        total_vertical_deflection = (
            deflection_per_layer * self.inputs.rubber_layer_count
        )
        deflection_limit = (
            self.VERTICAL_DEFLECTION_LIMIT_FACTOR
            * self.inputs.internal_rubber_thickness
        )
        passed = total_vertical_deflection <= deflection_limit
        return self.build_result(
            name="5. Vertical Deflection",
            passed=passed,
            pass_condition="Delta_total <= 0.15 * ti",
            intermediate_values={
                "Eb (N/mm^2)": self.inputs.bulk_modulus,
                "S": self.shape_factor,
                "delta per layer (mm)": deflection_per_layer,
                "num_layers": self.inputs.rubber_layer_count,
                "Delta_total (mm)": total_vertical_deflection,
                "0.15 * ti (mm)": deflection_limit,
            },
        )

    # Freyssinet requires enough vertical compression to accommodate imposed
    # rotations without lift-off. The calculated compression deflection must
    # exceed the rotation demand across the effective plan dimensions.
    def check_rotational_limit(
        self, total_vertical_deflection: float | None = None
    ) -> CheckResult:
        """Check that vertical deflection is greater than the rotational demand."""

        if total_vertical_deflection is None:
            total_vertical_deflection = float(
                self.check_vertical_deflection().intermediate_values[
                    "Delta_total (mm)"
                ]
            )

        rotation_limit = (
            (self.inputs.effective_width * self.inputs.rotation_alpha_b)
            + (self.inputs.effective_length * self.inputs.rotation_alpha_l)
        ) / self.ROTATIONAL_LIMIT_DIVISOR
        passed = total_vertical_deflection > rotation_limit
        return self.build_result(
            name="6. Rotational Limit",
            passed=passed,
            pass_condition="Delta_total > (be * ab + le * al) / 3",
            intermediate_values={
                "Delta_total (mm)": total_vertical_deflection,
                "(be * ab + le * al) / 3 (mm)": rotation_limit,
            },
        )

    # Freyssinet fixing checks use the horizontal force generated by shear
    # deformation, then verify permanent-load pressure is high enough.
    def check_fixing_of_bearings(self) -> CheckResult:
        """Check fixing requirements under all loading and permanent loading."""

        resultant_movement = self.calculate_resultant_movement(
            transverse_movement=self.total_transverse_movement,
            longitudinal_movement=self.total_longitudinal_movement,
        )
        gross_bearing_area = self.calculate_area(
            self.inputs.bearing_length,
            self.inputs.bearing_width,
        )
        resultant_horizontal_force_newtons = (
            gross_bearing_area
            * self.inputs.shear_modulus
            * resultant_movement
            / self.effective_shear_thickness
        )
        horizontal_force_limit = self.FIXING_FORCE_FACTOR * (
            self.maximum_vertical_load_newtons + (2 * self.loaded_area_after_movement)
        )
        bearing_pressure = (
            self.inputs.dead_load_vertical_force
            * self.NEWTONS_PER_KILONEWTON
            / self.loaded_area_after_movement
        )
        force_ok = resultant_horizontal_force_newtons < horizontal_force_limit
        pressure_ok = bearing_pressure > self.MINIMUM_FIXING_PRESSURE
        passed = force_ok and pressure_ok
        return self.build_result(
            name="7. Fixing of Bearings",
            passed=passed,
            pass_condition="H < 0.1 * (Vmax + 2*A1) and Vdl/A1 > 2",
            intermediate_values={
                "gross bearing area (mm^2)": gross_bearing_area,
                "delta_r (mm)": resultant_movement,
                "tq effective shear thickness (mm)": self.effective_shear_thickness,
                "H resultant (N)": resultant_horizontal_force_newtons,
                "0.1 * (Vmax + 2*A1)": horizontal_force_limit,
                "force sub-check satisfied": "Yes" if force_ok else "No",
                "Vdl/A1 (N/mm^2)": bearing_pressure,
                "pressure sub-check satisfied": "Yes" if pressure_ok else "No",
            },
        )

    def run_all_checks(self) -> list[CheckResult]:
        """Run the seven design checks in the structured order used by the UI."""

        completed_checks: dict[str, CheckResult] = {}

        for check_key, definition in self.CHECK_DEFINITIONS.items():
            if check_key == "maximum_design_strain":
                result = self.check_max_design_strain(
                    shear_strain=float(
                        completed_checks["shear_strain"].intermediate_values["Eq"]
                    )
                )
            elif check_key == "rotational_limit":
                result = self.check_rotational_limit(
                    total_vertical_deflection=float(
                        completed_checks["vertical_deflection"].intermediate_values[
                            "Delta_total (mm)"
                        ]
                    )
                )
            else:
                check_method = getattr(self, definition.method_name)
                result = check_method()

            completed_checks[check_key] = result

        return list(completed_checks.values())

    def overall_passed(self) -> bool:
        """Return True only when every Freyssinet design check passes."""

        return all(result.passed for result in self.run_all_checks())
