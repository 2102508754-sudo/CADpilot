"""Sketch creation tool for CADPilot Bridge."""

from typing import Dict, Any, List
from ..units import mm_to_cm, cm_to_mm, bounding_box_cm_to_mm
from ..errors import InvalidParamsError, GeometryError

try:
    import adsk.core
    import adsk.fusion
    IN_FUSION = True
except ImportError:
    IN_FUSION = False


def create_sketch(params: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a 2D sketch on a plane and draws geometry (rectangles, circles).

    Params:
        plane: "xy" | "xz" | "yz" | "<face_token>"
        shapes: List of shape dicts:
            - {"type": "rectangle", "center": [x, y], "width": w, "height": h}
            - {"type": "rectangle", "corner1": [x1, y1], "corner2": [x2, y2]}
            - {"type": "circle", "center": [x, y], "diameter": d}
    """
    if not IN_FUSION:
        # Mock behavior handled in mock/mock_bridge.py
        raise RuntimeError("create_sketch called in non-Fusion environment without mock.")

    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        raise RuntimeError("No active Fusion design document.")

    root_comp = design.rootComponent
    plane_param = str(params.get("plane", "xy")).lower()

    # Determine sketch plane
    if plane_param == "xy":
        target_plane = root_comp.xYConstructionPlane
    elif plane_param == "xz":
        target_plane = root_comp.xZConstructionPlane
    elif plane_param == "yz":
        target_plane = root_comp.yZConstructionPlane
    else:
        # Search faces for matching token/name
        target_plane = None
        for b in root_comp.bRepBodies:
            for f in b.faces:
                if f.tempId == plane_param or f.entityToken == plane_param:
                    target_plane = f
                    break
        if not target_plane:
            target_plane = root_comp.xYConstructionPlane

    sketches = root_comp.sketches
    sketch = sketches.add(target_plane)
    sketch_lines = sketch.sketchCurves.sketchLines
    sketch_circles = sketch.sketchCurves.sketchCircles

    shapes = params.get("shapes", [])
    if not shapes:
        raise InvalidParamsError(
            message="No shapes specified in 'create_sketch' params.",
            hint="Provide a list of shapes, e.g. [{'type': 'rectangle', 'center': [0, 0], 'width': 42.3, 'height': 42.3}].",
            tool="create_sketch"
        )

    for shape in shapes:
        stype = shape.get("type", "").lower()
        if stype == "rectangle":
            if "center" in shape and "width" in shape and "height" in shape:
                cx, cy = shape["center"]
                w, h = shape["width"], shape["height"]
                x1 = mm_to_cm(cx - w / 2.0)
                y1 = mm_to_cm(cy - h / 2.0)
                x2 = mm_to_cm(cx + w / 2.0)
                y2 = mm_to_cm(cy + h / 2.0)
            elif "corner1" in shape and "corner2" in shape:
                x1 = mm_to_cm(shape["corner1"][0])
                y1 = mm_to_cm(shape["corner1"][1])
                x2 = mm_to_cm(shape["corner2"][0])
                y2 = mm_to_cm(shape["corner2"][1])
            else:
                raise InvalidParamsError(
                    message="Invalid rectangle definition.",
                    hint="Specify either {'center': [x,y], 'width': w, 'height': h} or {'corner1': [x1,y1], 'corner2': [x2,y2]}.",
                    tool="create_sketch"
                )

            pt1 = adsk.core.Point3D.create(x1, y1, 0.0)
            pt2 = adsk.core.Point3D.create(x2, y2, 0.0)
            sketch_lines.addTwoPointRectangle(pt1, pt2)

        elif stype == "circle":
            center = shape.get("center", [0.0, 0.0])
            diam_mm = shape.get("diameter", 10.0)
            radius_cm = mm_to_cm(diam_mm / 2.0)
            center_pt = adsk.core.Point3D.create(mm_to_cm(center[0]), mm_to_cm(center[1]), 0.0)
            sketch_circles.addByCenterRadius(center_pt, radius_cm)
        else:
            raise InvalidParamsError(
                message=f"Unsupported shape type '{stype}' in create_sketch.",
                hint="Supported shape types are 'rectangle' and 'circle'.",
                tool="create_sketch"
            )

    # Collect generated profiles and bounding box
    profiles_out: List[Dict[str, Any]] = []
    sketch_id = sketch.name

    for idx, prof in enumerate(sketch.profiles):
        area_cm2 = prof.areaProperties().area
        area_mm2 = area_cm2 * 100.0  # cm^2 to mm^2
        prof_token = f"{sketch_id}:prof_{idx}"
        profiles_out.append({
            "profile_id": prof_token,
            "index": idx,
            "area_mm2": round(area_mm2, 2)
        })

    bbox = sketch.boundingBox
    bbox_dict = bounding_box_cm_to_mm(
        [bbox.minPoint.x, bbox.minPoint.y, bbox.minPoint.z],
        [bbox.maxPoint.x, bbox.maxPoint.y, bbox.maxPoint.z]
    )

    return {
        "status": "success",
        "sketch_id": sketch_id,
        "profiles": profiles_out,
        "bounding_box": bbox_dict
    }

