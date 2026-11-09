"""LangGraph Node 2: Feasibility Pre-Flight Checker.

Performs rigorous geometric and physical modeling pre-flight verification
on the structured TaskSpec before sending any instructions to the CAD kernel.
Detects:
1. Non-positive or zero physical dimensions.
2. Holes protruding outside workpiece boundaries.
3. Insufficient edge margins / thin walls (< 1.0mm).
4. Hole-to-hole intersections and collisions.
5. Fillet radii exceeding physical thickness or adjacent features.
"""

import math
from typing import Dict, Any, List, Tuple
from agent.state import CADState, TaskSpec, FeasibilityReport, HoleSpec


def check_geometric_feasibility(spec: TaskSpec) -> FeasibilityReport:
    """Evaluates geometric feasibility and generates actionable remediation hints."""
    errors: List[str] = []
    warnings: List[str] = []
    hints: List[str] = []

    dims = spec.dimensions
    shape = spec.shape_type

    # 1. Dimension Validation
    thickness = dims.get("thickness", 0.0)
    if thickness <= 0.0:
        errors.append(f"Invalid plate thickness: {thickness}mm (must be > 0.0mm).")
        hints.append("Set thickness to a positive value (e.g. >= 2.0mm).")

    if shape == "circle":
        diameter = dims.get("diameter", 0.0)
        if diameter <= 0.0:
            errors.append(f"Invalid plate diameter: {diameter}mm (must be > 0.0mm).")
            hints.append("Set diameter to a positive value (e.g. >= 20.0mm).")
        outer_radius = diameter / 2.0
    else:
        width = dims.get("width", 0.0)
        height = dims.get("height", 0.0)
        if width <= 0.0:
            errors.append(f"Invalid plate width: {width}mm (must be > 0.0mm).")
            hints.append("Set width to a positive value (e.g. >= 10.0mm).")
        if height <= 0.0:
            errors.append(f"Invalid plate height: {height}mm (must be > 0.0mm).")
            hints.append("Set height to a positive value (e.g. >= 10.0mm).")
        half_w = width / 2.0
        half_h = height / 2.0

    # 2. Hole Containment & Edge Clearance
    for idx, hole in enumerate(spec.holes, 1):
        if hole.diameter <= 0.0:
            errors.append(f"Hole #{idx} diameter is non-positive: {hole.diameter}mm.")
            hints.append(f"Increase diameter of hole #{idx} to > 0.0mm.")
            continue

        hr = hole.diameter / 2.0
        hx, hy = hole.position

        if shape == "circle":
            center_dist = math.hypot(hx, hy)
            if center_dist + hr > outer_radius:
                errors.append(
                    f"Hole #{idx} (dia {hole.diameter}mm at [{hx}, {hy}]) protrudes outside circular plate boundary (radius {outer_radius}mm)."
                )
                safe_max_r = max(1.0, outer_radius - center_dist - 1.0)
                hints.append(f"Reduce hole #{idx} diameter to <= {safe_max_r*2:.1f}mm or shift center inward.")
            elif center_dist + hr > outer_radius - 1.0:
                warnings.append(f"Hole #{idx} edge margin is under 1.0mm from outer perimeter.")
        else:
            # Rectangular boundary
            if abs(hx) + hr > half_w:
                errors.append(
                    f"Hole #{idx} (dia {hole.diameter}mm at [{hx}, {hy}]) exceeds plate width boundary (+/-{half_w}mm)."
                )
                safe_max_w = max(width, (abs(hx) + hr + 2.0) * 2.0)
                hints.append(f"Increase plate width to at least {safe_max_w:.1f}mm or move hole #{idx} closer to center.")

            if abs(hy) + hr > half_h:
                errors.append(
                    f"Hole #{idx} (dia {hole.diameter}mm at [{hx}, {hy}]) exceeds plate height boundary (+/-{half_h}mm)."
                )
                safe_max_h = max(height, (abs(hy) + hr + 2.0) * 2.0)
                hints.append(f"Increase plate height to at least {safe_max_h:.1f}mm or move hole #{idx} closer to center.")

            margin_x = half_w - (abs(hx) + hr)
            margin_y = half_h - (abs(hy) + hr)
            if 0.0 <= margin_x < 1.0 or 0.0 <= margin_y < 1.0:
                warnings.append(f"Hole #{idx} has thin edge margin (< 1.0mm) to plate border.")

    # 3. Hole-to-Hole Collision Detection
    for i in range(len(spec.holes)):
        for j in range(i + 1, len(spec.holes)):
            h1 = spec.holes[i]
            h2 = spec.holes[j]
            r1 = h1.diameter / 2.0
            r2 = h2.diameter / 2.0
            dist = math.hypot(h1.position[0] - h2.position[0], h1.position[1] - h2.position[1])

            if dist < (r1 + r2):
                errors.append(
                    f"Hole collision: Hole #{i+1} (at {h1.position}, r={r1}mm) intersects Hole #{j+1} (at {h2.position}, r={r2}mm). Distance={dist:.2f}mm < {r1+r2:.2f}mm."
                )
                hints.append(f"Increase spacing between holes #{i+1} and #{j+1} to >= {(r1+r2+1.0):.1f}mm.")
            elif dist < (r1 + r2 + 1.0):
                warnings.append(
                    f"Thin wall between Hole #{i+1} and Hole #{j+1} ({dist - (r1 + r2):.2f}mm clearance)."
                )

    # 4. Fillet Viability Check
    if spec.fillets:
        fr = spec.fillets.radius
        if fr <= 0.0:
            errors.append(f"Fillet radius is non-positive: {fr}mm.")
            hints.append("Set fillet radius to > 0.0mm or omit fillet.")
        elif fr >= thickness:
            errors.append(
                f"Fillet radius {fr}mm exceeds plate thickness {thickness}mm. "
                f"Will trigger topological self-intersection in CAD kernel."
            )
            safe_fr = round(thickness * 0.5, 1)
            hints.append(f"Reduce fillet radius to <= {safe_fr}mm (strictly less than plate thickness {thickness}mm).")

        if shape == "rectangle":
            min_dim = min(dims.get("width", 50.0), dims.get("height", 50.0))
            if fr >= min_dim / 2.0:
                errors.append(f"Fillet radius {fr}mm exceeds half of minimum dimension ({min_dim/2.0}mm).")
                hints.append(f"Reduce fillet radius to <= {min_dim*0.25:.1f}mm.")

    is_feasible = (len(errors) == 0)
    return FeasibilityReport(
        is_feasible=is_feasible,
        errors=errors,
        warnings=warnings,
        remediation_hints=hints
    )


def feasibility_checker_node(state: CADState) -> CADState:
    """LangGraph node: validates geometric feasibility of the TaskSpec.

    Updates:
        state["feasibility"]: FeasibilityReport dict
        state["status"]: "planning" (if feasible) or "reflecting" (if infeasible)
    """
    spec_dict = state.get("spec", {})
    if not spec_dict:
        state["error"] = "Cannot check feasibility: No spec found in state."
        state["status"] = "failed"
        return state

    try:
        spec = TaskSpec.from_dict(spec_dict)
        report = check_geometric_feasibility(spec)
        state["feasibility"] = report.to_dict()

        if report.is_feasible:
            state["status"] = "planning"
        else:
            state["status"] = "reflecting"
            state["error"] = f"Geometric feasibility violation: {'; '.join(report.errors)}"
    except Exception as e:
        state["error"] = f"Feasibility check error: {str(e)}"
        state["status"] = "failed"

    return state
