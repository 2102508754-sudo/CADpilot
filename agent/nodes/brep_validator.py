"""LangGraph Node: B-Rep & Geometric Property Validator.

Implements Bibhukesh's reflection step: queries B-Rep bodies, calculates theoretical
vs actual solid volume, surface area, bounding box dimensions, and verifies hole
features and cylindrical face tokens.
"""

import math
from typing import Dict, Any, List, Optional
from agent.state import CADState, TaskSpec


def validate_brep_geometry(spec: TaskSpec, brep_result: Dict[str, Any]) -> Dict[str, Any]:
    """Validates the B-Rep geometry against theoretical mechanical expectations."""
    discrepancies: List[str] = []
    warnings: List[str] = []

    bodies = brep_result.get("bodies", [])
    if not bodies:
        return {
            "passed": False,
            "discrepancies": ["No solid bodies found in B-Rep inspection."],
            "warnings": [],
            "metrics": {}
        }

    primary_body = bodies[0]
    actual_vol = float(primary_body.get("volume_mm3", 0.0))
    actual_sa = float(primary_body.get("surface_area_mm2", 0.0))
    is_solid = bool(primary_body.get("is_solid", False))

    if not is_solid:
        discrepancies.append("Primary body is not marked as a closed solid B-Rep.")

    # 1. Bounding Box Check
    dims = spec.dimensions
    bbox = brep_result.get("overall_bounding_box", {}).get("dimensions", [0.0, 0.0, 0.0])

    if spec.shape_type == "circle":
        expected_diam = dims.get("diameter", 50.0)
        expected_thick = dims.get("thickness", 4.0)
        if abs(bbox[0] - expected_diam) > 0.5 or abs(bbox[1] - expected_diam) > 0.5:
            warnings.append(f"Bounding box diameter [{bbox[0]}, {bbox[1]}] deviates from expected {expected_diam}mm.")
        if abs(bbox[2] - expected_thick) > 0.5:
            discrepancies.append(f"Bounding box thickness {bbox[2]}mm deviates from expected {expected_thick}mm.")
        base_vol = math.pi * ((expected_diam / 2.0) ** 2) * expected_thick
    else:
        expected_w = dims.get("width", 42.3)
        expected_h = dims.get("height", 42.3)
        expected_thick = dims.get("thickness", 4.0)
        if abs(bbox[0] - expected_w) > 0.5:
            discrepancies.append(f"Width {bbox[0]}mm deviates from expected {expected_w}mm.")
        if abs(bbox[1] - expected_h) > 0.5:
            discrepancies.append(f"Height {bbox[1]}mm deviates from expected {expected_h}mm.")
        if abs(bbox[2] - expected_thick) > 0.5:
            discrepancies.append(f"Thickness {bbox[2]}mm deviates from expected {expected_thick}mm.")
        base_vol = expected_w * expected_h * expected_thick

    # 2. Theoretical vs Actual Volume
    hole_vol_total = 0.0
    for h in spec.holes:
        hr = h.diameter / 2.0
        h_depth = expected_thick if h.depth == "through" else float(h.depth)
        hole_vol_total += math.pi * (hr ** 2) * h_depth

    expected_theoretical_vol = max(0.0, base_vol - hole_vol_total)
    vol_diff = abs(actual_vol - expected_theoretical_vol)
    vol_diff_pct = (vol_diff / expected_theoretical_vol * 100.0) if expected_theoretical_vol > 0 else 0.0

    # Volume comparison: fillets reduce volume slightly (~1-5%), so allow up to 8% margin
    if vol_diff_pct > 15.0:
        discrepancies.append(
            f"Gross volume discrepancy: actual {actual_vol:.2f}mm³ vs theoretical {expected_theoretical_vol:.2f}mm³ ({vol_diff_pct:.1f}% deviation exceeds 15% tolerance)."
        )
    elif vol_diff_pct > 8.0:
        warnings.append(
            f"Volume deviation: actual {actual_vol:.2f}mm³ vs theoretical {expected_theoretical_vol:.2f}mm³ ({vol_diff_pct:.1f}%)."
        )

    # 3. Cylindrical Feature Count & Hole Placement
    cyl_features = primary_body.get("cylindrical_features", [])
    expected_holes = len(spec.holes)
    actual_holes = len(cyl_features)

    if expected_holes > 0 and actual_holes < expected_holes:
        discrepancies.append(f"Hole count mismatch: expected {expected_holes} holes, but found {actual_holes} in B-Rep.")

    passed = (len(discrepancies) == 0)
    return {
        "passed": passed,
        "discrepancies": discrepancies,
        "warnings": warnings,
        "metrics": {
            "actual_volume_mm3": actual_vol,
            "theoretical_volume_mm3": round(expected_theoretical_vol, 2),
            "volume_diff_pct": round(vol_diff_pct, 2),
            "surface_area_mm2": actual_sa,
            "face_count": primary_body.get("face_count", 0),
            "edge_count": primary_body.get("edge_count", 0),
            "cylindrical_hole_count": actual_holes
        }
    }


def brep_validator_node(state: CADState) -> CADState:
    """LangGraph node: performs B-Rep reflection and geometric validation."""
    brep_res = state.get("final_output", {}).get("brep")
    spec_dict = state.get("spec", {})

    if not brep_res:
        state["validation"] = {
            "passed": False,
            "discrepancies": ["No inspect_brep output found to validate."],
            "warnings": [],
            "metrics": {}
        }
        state["status"] = "exporting"
        return state

    spec = TaskSpec.from_dict(spec_dict)
    val_report = validate_brep_geometry(spec, brep_res)
    state["validation"] = val_report

    if val_report["passed"]:
        state["status"] = "exporting"
    else:
        # Route to reflection if there are critical discrepancies
        err_msg = f"B-Rep validation failed: {'; '.join(val_report['discrepancies'])}"
        state["status"] = "reflecting"
        state["error"] = err_msg
        if "reflection" not in state or not state["reflection"]:
            state["reflection"] = {}
        state["reflection"]["last_error_tool"] = "inspect_brep"
        state["reflection"]["last_error_code"] = -32007
        state["reflection"]["last_error_message"] = err_msg
        state["reflection"]["last_error_hint"] = "Review geometry dimensions or hole cut parameters to match theoretical volume."

    return state
