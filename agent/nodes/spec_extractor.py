"""LangGraph Node 1: Spec Extractor.

Translates natural language user prompts and mechanical specifications into
a structured, validated TaskSpec. Supports both high-precision rule-based
extraction for standard CAD parts (NEMA 17/23, mounting plates, circular flanges,
linear arrays, PCD bolt circles, symmetric bolt patterns) and LLM-assisted extraction.
"""

import re
import math
from typing import Dict, Any, List, Optional, Callable
from agent.state import CADState, TaskSpec, HoleSpec, FilletSpec, ExportSpec


def extract_spec_from_text(prompt: str) -> TaskSpec:
    """Extracts a structured TaskSpec from natural language prompt."""
    prompt_lower = prompt.lower()
    spec = TaskSpec(raw_prompt=prompt)

    # 1. Base Part Type & Shape Detection
    if "nema 17" in prompt_lower:
        spec.part_type = "mounting_plate"
        spec.shape_type = "rectangle"
        width = 42.3
        height = 42.3
        thick_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mm)?\s*thick(?:ness)?", prompt_lower)
        thickness = float(thick_match.group(1)) if thick_match else 4.0
        spec.dimensions = {"width": width, "height": height, "thickness": thickness}

        center_hole_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:center|pilot)", prompt_lower)
        center_diam = float(center_hole_match.group(1)) if center_hole_match else 22.0
        spec.holes.append(HoleSpec(
            position=[0.0, 0.0],
            diameter=center_diam,
            depth="through",
            face="xy",
            description="center pilot hole"
        ))

        mount_spacing_match = re.search(r"spaced\s*(\d+(?:\.\d+)?)\s*(?:mm)?\s*apart", prompt_lower)
        spacing = float(mount_spacing_match.group(1)) if mount_spacing_match else 31.0
        half_s = spacing / 2.0

        hole_diam_match = re.search(r"m(\d+(?:\.\d+)?)", prompt_lower)
        hole_diam = float(hole_diam_match.group(1)) if hole_diam_match else 3.0

        for i, (hx, hy) in enumerate([(-half_s, -half_s), (half_s, -half_s), (half_s, half_s), (-half_s, half_s)], 1):
            spec.holes.append(HoleSpec(
                position=[round(hx, 2), round(hy, 2)],
                diameter=hole_diam,
                depth="through",
                face="xy",
                description=f"mounting hole #{i}"
            ))

        fillet_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mm)?\s*fillet", prompt_lower)
        if fillet_match:
            spec.fillets = FilletSpec(radius=float(fillet_match.group(1)), target="all_vertical_edges", description="corner fillets")
        else:
            spec.fillets = FilletSpec(radius=2.0, target="all_vertical_edges", description="corner fillets")

    elif "nema 23" in prompt_lower:
        spec.part_type = "mounting_plate"
        spec.shape_type = "rectangle"
        spec.dimensions = {"width": 57.1, "height": 57.1, "thickness": 5.0}
        spec.holes.append(HoleSpec(position=[0.0, 0.0], diameter=38.1, depth="through", face="xy", description="center pilot hole"))
        half_s = 47.1 / 2.0
        for i, (hx, hy) in enumerate([(-half_s, -half_s), (half_s, -half_s), (half_s, half_s), (-half_s, half_s)], 1):
            spec.holes.append(HoleSpec(position=[round(hx, 2), round(hy, 2)], diameter=5.0, depth="through", face="xy", description=f"mounting hole #{i}"))
        spec.fillets = FilletSpec(radius=3.0, target="all_vertical_edges", description="corner fillets")

    else:
        spec.part_type = "mounting_plate"
        spec.shape_type = "rectangle"

        # Check for circular plate
        if "circle" in prompt_lower or "circular" in prompt_lower or "flange" in prompt_lower or "round plate" in prompt_lower:
            spec.shape_type = "circle"
            diam_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:circular\s*flange|circular\s*plate|round\s*flange|round\s*plate|circle|disc|disk)", prompt_lower) or \
                         re.search(r"(?:flange|plate|disc|disk)\s*(?:of|=|:)?\s*(\d+(?:\.\d+)?)\s*(?:mm)?", prompt_lower) or \
                         re.search(r"(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:outer\s*diameter|od|diameter|dia)", prompt_lower)
            diam = float(diam_match.group(1)) if diam_match else 50.0
            thick_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mm)?\s*thick(?:ness)?", prompt_lower)
            thickness = float(thick_match.group(1)) if thick_match else 5.0
            spec.dimensions = {"diameter": diam, "thickness": thickness}
        else:
            # Parse rectangular dimensions
            dim_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:x|by|\*)\s*(\d+(?:\.\d+)?)\s*(?:mm)?(?:\s*(?:x|by|\*)\s*(\d+(?:\.\d+)?)\s*(?:mm)?)?", prompt_lower)
            if dim_match:
                w = float(dim_match.group(1))
                h = float(dim_match.group(2))
                t = float(dim_match.group(3)) if dim_match.group(3) else 5.0
                spec.dimensions = {"width": w, "height": h, "thickness": t}
            else:
                w_match = re.search(r"width\s*(?:of|=|:)?\s*(\d+(?:\.\d+)?)", prompt_lower)
                h_match = re.search(r"height\s*(?:of|=|:)?\s*(\d+(?:\.\d+)?)", prompt_lower)
                t_match = re.search(r"thickness\s*(?:of|=|:)?\s*(\d+(?:\.\d+)?)", prompt_lower)
                w = float(w_match.group(1)) if w_match else 50.0
                h = float(h_match.group(1)) if h_match else 50.0
                t = float(t_match.group(1)) if t_match else 4.0
                spec.dimensions = {"width": w, "height": h, "thickness": t}

        # Parse Hole Depth (default through)
        depth_val: Any = "through"
        depth_match = re.search(r"depth\s*(?:of|=|:)?\s*(\d+(?:\.\d+)?)\s*(?:mm)?", prompt_lower)
        if depth_match and "through" not in prompt_lower:
            depth_val = float(depth_match.group(1))

        # Parse Center Hole
        center_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:center|pilot|bore|concentric)\s*hole", prompt_lower) or \
                       re.search(r"center\s*(?:pilot|bore)?\s*hole\s*(?:of|with|diameter|=|:)?\s*(\d+(?:\.\d+)?)", prompt_lower)
        if center_match:
            cd = float(center_match.group(1))
            spec.holes.append(HoleSpec(position=[0.0, 0.0], diameter=cd, depth=depth_val, face="xy", description="center hole"))

        # Parse Linear Array Pattern (e.g. "2x3 grid of 4mm holes with 30mm pitch X and 20mm pitch Y", "linear array of 3x2 holes spaced 10mm in X and 15mm in Y")
        linear_match = re.search(r"(\d+)\s*(?:x|by)\s*(\d+)\s*(?:grid|linear\s*array|array)", prompt_lower) or \
                       re.search(r"(?:linear\s*array|grid|array)\s*(?:of)?\s*(\d+)\s*(?:x|by)\s*(\d+)", prompt_lower)
        if linear_match:
            rows = int(linear_match.group(1))
            cols = int(linear_match.group(2))

            px_match = re.search(r"(?:pitch\s*x|pitch-x|in\s*x)\s*(?:of|=|:)?\s*(\d+(?:\.\d+)?)", prompt_lower) or \
                       re.search(r"(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:pitch\s*x|in\s*x)", prompt_lower) or \
                       re.search(r"(?:spaced|pitch)\s*(\d+(?:\.\d+)?)", prompt_lower)
            py_match = re.search(r"(?:pitch\s*y|pitch-y|in\s*y)\s*(?:of|=|:)?\s*(\d+(?:\.\d+)?)", prompt_lower) or \
                       re.search(r"(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:pitch\s*y|in\s*y)", prompt_lower)

            pitch_x = float(px_match.group(1)) if px_match else 20.0
            pitch_y = float(py_match.group(1)) if py_match else pitch_x

            start_x = -((cols - 1) * pitch_x) / 2.0
            start_y = -((rows - 1) * pitch_y) / 2.0

            hole_d_match = re.search(r"(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:mm)?\s*holes?", prompt_lower) or \
                           re.search(r"(?:diameter|dia|m)\s*(\d+(?:\.\d+)?)", prompt_lower)
            hole_d = float(hole_d_match.group(1)) if hole_d_match else 3.0

            for r_idx in range(rows):
                for c_idx in range(cols):
                    pos_x = round(start_x + c_idx * pitch_x, 2)
                    pos_y = round(start_y + r_idx * pitch_y, 2)
                    spec.holes.append(HoleSpec(
                        position=[pos_x, pos_y],
                        diameter=hole_d,
                        depth=depth_val,
                        face="xy",
                        description=f"array hole [{r_idx},{c_idx}]"
                    ))

        # Parse PCD (Pitch Circle Diameter / Bolt Circle)
        elif "pcd" in prompt_lower or "bolt circle" in prompt_lower or "pitch circle" in prompt_lower:
            count_match = re.search(r"(\d+)\s*(?:x\s*)?(?:(\d+(?:\.\d+)?)\s*(?:mm)?\s*)?holes?.*?(?:pcd|bolt\s*circle|pitch\s*circle)", prompt_lower) or \
                          re.search(r"(?:pcd|bolt\s*circle|pitch\s*circle).*?(\d+)\s*holes?", prompt_lower)
            count = int(count_match.group(1)) if count_match else 4

            hole_d = 3.0
            if count_match and count_match.lastindex and count_match.lastindex >= 2 and count_match.group(2):
                hole_d = float(count_match.group(2))
            else:
                hd_search = re.search(r"(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:holes?|diameter|dia)", prompt_lower)
                if hd_search:
                    hole_d = float(hd_search.group(1))

            pcd_d_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:bolt\s*circle\s*pcd|bolt\s*circle|pcd|pitch\s*circle)", prompt_lower) or \
                          re.search(r"(?:pcd|bolt\s*circle|pitch\s*circle)\s*(?:of|=|:)?\s*(\d+(?:\.\d+)?)", prompt_lower)
            pcd_diam = float(pcd_d_match.group(1)) if pcd_d_match else 50.0
            pcd_r = pcd_diam / 2.0

            for i in range(count):
                angle = (2.0 * math.pi / count) * i
                hx = round(pcd_r * math.cos(angle), 2)
                hy = round(pcd_r * math.sin(angle), 2)
                spec.holes.append(HoleSpec(
                    position=[hx, hy],
                    diameter=hole_d,
                    depth=depth_val,
                    face="xy",
                    description=f"pcd hole #{i+1}"
                ))

        # Parse Symmetric / Corner Hole Pattern (e.g. 4x M3 or 4 holes spaced X mm apart)
        else:
            spacing_match = re.search(r"(\d+)\s*(?:x|holes)?.*?spaced\s*(\d+(?:\.\d+)?)\s*(?:mm)?\s*apart", prompt_lower) or \
                            re.search(r"spaced\s*(\d+(?:\.\d+)?)\s*(?:mm)?\s*apart", prompt_lower) or \
                            re.search(r"bolt\s*pattern\s*(\d+(?:\.\d+)?)\s*(?:x|by)\s*(\d+(?:\.\d+)?)", prompt_lower)
            if spacing_match:
                if spacing_match.lastindex >= 2 and spacing_match.group(2):
                    sp_x = float(spacing_match.group(1))
                    sp_y = float(spacing_match.group(2))
                else:
                    sp_x = float(spacing_match.group(2)) if spacing_match.lastindex >= 2 else float(spacing_match.group(1))
                    sp_y = sp_x

                half_sx = sp_x / 2.0
                half_sy = sp_y / 2.0
                hole_d_match = re.search(r"(?:m|diameter|dia)\s*(\d+(?:\.\d+)?)", prompt_lower)
                hole_d = float(hole_d_match.group(1)) if hole_d_match else 3.0
                for i, (hx, hy) in enumerate([(-half_sx, -half_sy), (half_sx, -half_sy), (half_sx, half_sy), (-half_sx, half_sy)], 1):
                    spec.holes.append(HoleSpec(
                        position=[round(hx, 2), round(hy, 2)],
                        diameter=hole_d,
                        depth=depth_val,
                        face="xy",
                        description=f"mounting hole #{i}"
                    ))

        # Parse Fillet
        fillet_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mm)?\s*fillet", prompt_lower) or \
                       re.search(r"fillet\s*(?:of|radius|=|:)?\s*(\d+(?:\.\d+)?)", prompt_lower)
        if fillet_match:
            r = float(fillet_match.group(1))
            spec.fillets = FilletSpec(radius=r, target="all_vertical_edges", description="exterior fillets")

    # Parse Export Target
    export_match = re.search(r"export(?:\s*to|\s*as)?\s*([/\w\.-]+\.(?:step|stl|f3d))", prompt_lower)
    if export_match:
        out_path = export_match.group(1)
        fmt = "step"
        if out_path.endswith(".stl"):
            fmt = "stl"
        elif out_path.endswith(".f3d"):
            fmt = "f3d"
        spec.export = ExportSpec(format=fmt, output_path=out_path)
    elif "step" in prompt_lower or "export" in prompt_lower:
        spec.export = ExportSpec(format="step", output_path="/tmp/cadpilot_output.step")

    return spec


def spec_extractor_node(state: CADState, llm_callable: Optional[Callable[[str], str]] = None) -> CADState:
    """LangGraph node: transforms prompt into structured TaskSpec.

    Updates:
        state["spec"]: TaskSpec dict
        state["status"]: "checking"
    """
    prompt = state.get("prompt", "")
    if not prompt:
        state["error"] = "Prompt cannot be empty"
        state["status"] = "failed"
        return state

    try:
        spec = extract_spec_from_text(prompt)
        state["spec"] = spec.to_dict()
        state["status"] = "checking"
    except Exception as e:
        state["error"] = f"Spec extraction failed: {str(e)}"
        state["status"] = "failed"

    return state
