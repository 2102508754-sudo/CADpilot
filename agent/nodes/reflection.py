"""LangGraph Node 5: Closed-Loop Self-Correction & Reflection.

Extracts structured hints from bridge errors (e.g. FILLET_OVERSIZE, out of bounds)
or feasibility check failures, adjusts mechanical parameters, and triggers replanning.
"""

import re
from typing import Dict, Any, Optional, Tuple
from agent.state import CADState, TaskSpec, ReflectionState


def self_correct_spec(spec: TaskSpec, reflection: ReflectionState) -> Tuple[TaskSpec, bool]:
    """Applies self-correction heuristics to TaskSpec based on error hints."""
    hint = reflection.last_error_hint or ""
    tool = reflection.last_error_tool or ""
    msg = reflection.last_error_message or ""

    corrected = False

    # 1. Fillet Oversize / Geometric Limit Failure
    if tool == "apply_fillet" or "fillet" in msg.lower() or "fillet" in hint.lower():
        if spec.fillets:
            # Check if hint specifies a safe threshold e.g. "<= 1.6mm"
            thresh_match = re.search(r"<=\s*(\d+(?:\.\d+)?)\s*mm", hint)
            if thresh_match:
                new_radius = float(thresh_match.group(1))
            else:
                # Default heuristic: half the current radius
                new_radius = round(spec.fillets.radius * 0.5, 1)

            spec.fillets.radius = max(0.5, new_radius)
            corrected = True

    # 2. Hole Protrusion or Collision Failure
    elif tool == "cut_hole" or "hole" in msg.lower() or "hole" in hint.lower():
        # Check if hint recommends reducing hole diameter
        diam_match = re.search(r"diameter to <=\s*(\d+(?:\.\d+)?)\s*mm", hint)
        if diam_match:
            new_diam = float(diam_match.group(1))
            for h in spec.holes:
                if h.diameter > new_diam:
                    h.diameter = new_diam
            corrected = True
        else:
            # Check if hint recommends enlarging plate width/height
            plate_w_match = re.search(r"width to at least\s*(\d+(?:\.\d+)?)\s*mm", hint)
            if plate_w_match:
                spec.dimensions["width"] = float(plate_w_match.group(1))
                corrected = True
            plate_h_match = re.search(r"height to at least\s*(\d+(?:\.\d+)?)\s*mm", hint)
            if plate_h_match:
                spec.dimensions["height"] = float(plate_h_match.group(1))
                corrected = True

    # Fallback heuristic if no specific tool matched
    if not corrected and spec.fillets and spec.fillets.radius > 2.0:
        spec.fillets.radius = 2.0
        corrected = True

    return spec, corrected


def reflection_node(state: CADState) -> CADState:
    """LangGraph node: performs self-correction and routes back to planner."""
    reflection = ReflectionState.from_dict(state.get("reflection", {}))
    spec_dict = state.get("spec", {})

    if reflection.retry_count >= reflection.max_retries:
        state["status"] = "failed"
        state["error"] = (
            f"Self-correction aborted: Maximum retry limit ({reflection.max_retries}) reached. "
            f"Last error: {reflection.last_error_message}"
        )
        return state

    reflection.retry_count += 1

    if not spec_dict:
        state["status"] = "failed"
        state["error"] = "Cannot self-correct: No spec in state."
        return state

    try:
        spec = TaskSpec.from_dict(spec_dict)
        updated_spec, was_corrected = self_correct_spec(spec, reflection)

        state["spec"] = updated_spec.to_dict()
        state["reflection"] = reflection.to_dict()

        if was_corrected:
            # Clear previous plan/errors and transition back to planning
            state["plan"] = {"steps": []}
            state["status"] = "planning"
            state["error"] = None
        else:
            state["status"] = "failed"
            state["error"] = f"Unable to automatically resolve error: {reflection.last_error_message}"
    except Exception as e:
        state["status"] = "failed"
        state["error"] = f"Self-correction error: {str(e)}"

    return state
