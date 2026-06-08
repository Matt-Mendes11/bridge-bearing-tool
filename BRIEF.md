# Naidu Consulting Technical Assessment: Bridge Bearing Design Tool

## Project Goal
Convert a structural engineering Excel spreadsheet into a working software tool. 
The tool must calculate 7 design checks for Elastomeric bridge bearings based on the Freyssinet design manual.

## Input Parameters
- **l, b, T**: Bearing plan dimensions and total height (mm)
- **Plate thickness**: Reinforcing steel plate thickness (mm)
- **No. of plates / layers**: Number of steel plates and rubber layers
- **te, ti**: Edge and internal rubber layer thicknesses (mm)
- **G**: Shear modulus of rubber (N/mm²)
- **Vmax, Vdl, Vll**: Maximum, dead load, and live load vertical forces (kN)
- **Hs, Ht**: Horizontal shear forces (longitudinal and transverse) (kN)
- **Long. / Trans. movement**: Applied bearing movements (mm)
- **αb, αl**: Applied rotation angles (radians)

## The 7 Design Checks & Pass Conditions
1. **Shear Strain**: Check intermediate values (δb, δl, δr, S, Eq). Pass condition: Eq ≤ 1.0
2. **Maximum Design Strain**: Check intermediate values (A1, Ec, Eα, k, Et). Pass condition: Et ≤ 7.0
3. **Plate Thickness**: Check (t1, t2, σs, tmin). Pass condition: tmin ≤ actual plate thickness
4. **Stability**: Check V/A1, (2·be·G·S')/(3Σti), be/4. Both Stress and Geometry limits must be satisfied.
5. **Vertical Deflection**: Check (Eb, δ, ΔTotal, 0.15·ti). Pass condition: ΔTotal ≤ 0.15·ti
6. **Rotational Limit**: Check (Δ, (be·αb + le·αl)/3). Pass condition: Δ ≤ (be·αb + le·αl)/3
7. **Fixing of Bearings**: Check (H, 0.1(V + 2A1), V/A1). Both sub-checks must be satisfied.

## Verification Sample (Answer Key)
Input these values to verify the tool:
- Bearing size: 457 x 254 x 54 mm
- Plate thk / plates / layers: 4.5 mm / 4 plates / 3 layers
- G: 0.9 N/mm²
- Vmax / Vdl / Vll: 1420 / 384 / 1036 kN
- Hs / Ht: 50 / 10 kN
- Movements (long. / trans.): 10.6 / 4.19 mm
- αb / αl: 0.0001 / 0 radians

**Expected Results for Sample:**
- Check 1: FAILS (Eq = 0.80) -> *Note: Investigate why 0.8 fails if condition is <= 1.0*
- Check 2: FAILS (Et = 5.43)
- Check 3: OK
- Check 4: OK
- Check 5: FAILS (ΔTotal = 1.59 mm)
- Check 6: OK
- Check 7: OK
- **Overall Result: BEARING FAILS**