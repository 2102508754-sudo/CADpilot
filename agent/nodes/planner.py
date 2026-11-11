"""LangGraph Node 3: CAD Sequence Planner.

Transforms a validated TaskSpec into an ordered, executable sequence of
JSON-RPC 2.0 tool operations complying with docs/JSON_RPC_CONTRACT.md.
"""

from typing import Dict, Any, List
from agent.state import CADState, TaskSpec, CADPlan, PlanStep


def generate_cad_plan(spec: TaskSpec) -> CADPlan:
    """Generates an ordered CADPlan from the validated TaskSpec."""
    steps: List[PlanStep] = []
    step_idx = 1

    # Step 1: Clean Reset
    steps.append(PlanStep(
        step_index=step_idx,
        tool="reset_design",
        params={"save_existing": False},
        description="Reset active design workspace to clean slate"
    ))
    step_idx += 1

    # Step 2: Base Sketch
    plane = spec.base_plane or "xy"
    shapes = []
    if spec.shape_type == "circle":
        shapes.append({
            "type": "circle",
            "center": spec.center,
            "diameter": spec.dimensions.get("diameter", 50.0)
        })
        desc = f"Create base circular sketch (dia {spec.dimensions.get('diameter', 50.0)}mm)"
    else:
        # Default rectangular
        w = spec.dimensions.get("width", 42.3)
        h = spec.dimensions.get("height", 42.3)
        shapes.append({
            "type": "rectangle",
            "center": spec.center,
            "width": w,
            "height": h
        })
        desc = f"Create base rectangular sketch ({w}mm x {h}mm)"

    steps.append(PlanStep(
        step_index=step_idx,
        tool="create_sketch",
        params={"plane": plane, "shapes": shapes},
        description=desc
    ))
    step_idx += 1

    # Step 3: Extrude Solid
    thickness = spec.dimensions.get("thickness", 4.0)
    steps.append(PlanStep(
        step_index=step_idx,
        tool="extrude_profile",
        params={
            "profile_id": "all",
            "distance": thickness,
            "operation": "new_body"
        },
        description=f"Extrude base profile by {thickness}mm to create solid body"
    ))
    step_idx += 1

    # Step 4: Hole Cutting Operations
    for h_idx, hole in enumerate(spec.holes, 1):
        steps.append(PlanStep(
            step_index=step_idx,
            tool="cut_hole",
            params={
                "face": hole.face or "xy",
                "position": hole.position,
                "diameter": hole.diameter,
                "depth": hole.depth
            },
            description=f"Cut {hole.description or f'hole #{h_idx}'} (dia {hole.diameter}mm at {hole.position})"
        ))
        step_idx += 1

    # Step 5: Fillets
    if spec.fillets:
        steps.append(PlanStep(
            step_index=step_idx,
            tool="apply_fillet",
            params={
                "target": spec.fillets.target or "all_vertical_edges",
                "radius": spec.fillets.radius
            },
            description=f"Apply {spec.fillets.radius}mm fillet on {spec.fillets.target}"
        ))
        step_idx += 1

    # Step 6: B-Rep Geometric Verification (inspect_brep)
    steps.append(PlanStep(
        step_index=step_idx,
        tool="inspect_brep",
        params={"target_body": "all"},
        description="Inspect final B-Rep geometry and verify topological properties"
    ))
    step_idx += 1

    # Step 7: Export CAD Artifact
    if spec.export:
        steps.append(PlanStep(
            step_index=step_idx,
            tool="export_cad",
            params={
                "format": spec.export.format,
                "output_path": spec.export.output_path
            },
            description=f"Export CAD model ({spec.export.format.upper()}) to {spec.export.output_path}"
        ))
        step_idx += 1

    return CADPlan(steps=steps)


def planner_node(state: CADState) -> CADState:
    """LangGraph node: produces the ordered CAD tool call plan.

    Updates:
        state["plan"]: CADPlan dict
        state["status"]: "executing"
    """
    spec_dict = state.get("spec", {})
    if not spec_dict:
        state["error"] = "Cannot plan: TaskSpec missing from state."
        state["status"] = "failed"
        return state

    try:
        spec = TaskSpec.from_dict(spec_dict)
        plan = generate_cad_plan(spec)
        state["plan"] = plan.to_dict()
        state["status"] = "executing"
    except Exception as e:
        state["error"] = f"Planning failed: {str(e)}"
        state["status"] = "failed"

    return state

