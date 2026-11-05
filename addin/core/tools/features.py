"""Solid modeling features: extrude, hole, fillet."""

from typing import Dict, Any, List
from ..units import mm_to_cm, cm_to_mm, bounding_box_cm_to_mm
from ..errors import InvalidParamsError, GeometryError, EntityNotFoundError

try:
    import adsk.core
    import adsk.fusion
    IN_FUSION = True
except ImportError:
    IN_FUSION = False


def extrude_profile(params: Dict[str, Any]) -> Dict[str, Any]:
    """Extrudes a sketch profile by distance_mm."""
    if not IN_FUSION:
        raise RuntimeError("extrude_profile called in non-Fusion environment without mock.")

    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    root_comp = design.rootComponent

    profile_id = params.get("profile_id", "all")
    distance_mm = float(params.get("distance", 10.0))
    operation_str = str(params.get("operation", "new_body")).lower()

    # Determine extrusion operation
    if operation_str == "join":
        op = adsk.fusion.FeatureOperations.JoinFeatureOperation
    elif operation_str == "cut":
        op = adsk.fusion.FeatureOperations.CutFeatureOperation
    else:
        op = adsk.fusion.FeatureOperations.NewBodyFeatureOperation

    # Locate profile
    target_profile = None
    if profile_id == "all" or ":" not in profile_id:
        if root_comp.sketches.count > 0:
            last_sketch = root_comp.sketches.item(root_comp.sketches.count - 1)
            if last_sketch.profiles.count > 0:
                target_profile = last_sketch.profiles.item(0)
    else:
        sk_name, p_idx_str = profile_id.split(":")
        for sk in root_comp.sketches:
            if sk.name == sk_name:
                idx = int(p_idx_str.replace("prof_", ""))
                if idx < sk.profiles.count:
                    target_profile = sk.profiles.item(idx)
                break

    if not target_profile:
        raise EntityNotFoundError(entity_token=str(profile_id), tool="extrude_profile")

    extrudes = root_comp.features.extrudeFeatures
    distance_val = adsk.core.ValueInput.createByReal(mm_to_cm(distance_mm))
    ext_input = extrudes.createInput(target_profile, op)
    ext_input.setDistanceExtent(False, distance_val)

    try:
        ext_feat = extrudes.add(ext_input)
    except Exception as e:
        raise GeometryError(
            message=f"Failed to create extrusion: {str(e)}",
            hint="Check that the profile is planar and non-self-intersecting.",
            tool="extrude_profile"
        )

    # Gather resulting body IDs and bounding box
    body_ids = [b.name for b in root_comp.bRepBodies]
    bbox = root_comp.boundingBox
    bbox_dict = bounding_box_cm_to_mm(
        [bbox.minPoint.x, bbox.minPoint.y, bbox.minPoint.z],
        [bbox.maxPoint.x, bbox.maxPoint.y, bbox.maxPoint.z]
    )

    return {
        "status": "success",
        "feature_id": ext_feat.name,
        "body_ids": body_ids,
        "bounding_box": bbox_dict
    }


def cut_hole(params: Dict[str, Any]) -> Dict[str, Any]:
    """Cuts a hole through a body at position [x, y] in mm with diameter and depth."""
    if not IN_FUSION:
        raise RuntimeError("cut_hole called in non-Fusion environment without mock.")

    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    root_comp = design.rootComponent

    pos = params.get("position", [0.0, 0.0])
    diam_mm = float(params.get("diameter", 3.0))
    depth_val = params.get("depth", "through")

    if root_comp.bRepBodies.count == 0:
        raise GeometryError(
            message="Cannot cut hole: no solid bodies exist in the design.",
            hint="Create a base solid first by calling create_sketch and extrude_profile.",
            tool="cut_hole"
        )

    # Cut hole by creating a sketch on top planar face or XY plane and doing cut extrusion
    top_face = None
    max_z = -1e9
    for b in root_comp.bRepBodies:
        for f in b.faces:
            if f.geometry.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType:
                pt = f.centroid
                if pt.z > max_z:
                    max_z = pt.z
                    top_face = f

    sketch_target = top_face if top_face else root_comp.xYConstructionPlane
    sk = root_comp.sketches.add(sketch_target)
    center_pt = adsk.core.Point3D.create(mm_to_cm(pos[0]), mm_to_cm(pos[1]), 0.0)
    sk.sketchCurves.sketchCircles.addByCenterRadius(center_pt, mm_to_cm(diam_mm / 2.0))

    if sk.profiles.count == 0:
        raise GeometryError(
            message="Hole circle sketch produced no enclosed profile.",
            hint="Check hole position coordinates relative to target face boundaries.",
            tool="cut_hole"
        )

    hole_prof = sk.profiles.item(0)
    extrudes = root_comp.features.extrudeFeatures

    ext_input = extrudes.createInput(hole_prof, adsk.fusion.FeatureOperations.CutFeatureOperation)
    if depth_val == "through":
        ext_input.setAllExtent(adsk.fusion.ExtentDirections.SymmetricExtentDirection)
    else:
        d_val = adsk.core.ValueInput.createByReal(-abs(mm_to_cm(float(depth_val))))
        ext_input.setDistanceExtent(False, d_val)

    try:
        hole_feat = extrudes.add(ext_input)
    except Exception as e:
        raise GeometryError(
            message=f"Hole cut failed: {str(e)}",
            hint="Ensure hole position lies completely within body boundaries and does not intersect edge boundaries.",
            tool="cut_hole"
        )

    bbox = root_comp.boundingBox
    bbox_dict = bounding_box_cm_to_mm(
        [bbox.minPoint.x, bbox.minPoint.y, bbox.minPoint.z],
        [bbox.maxPoint.x, bbox.maxPoint.y, bbox.maxPoint.z]
    )

    return {
        "status": "success",
        "feature_id": hole_feat.name,
        "hole_count": 1,
        "bounding_box": bbox_dict
    }


def apply_fillet(params: Dict[str, Any]) -> Dict[str, Any]:
    """Applies a fillet of radius_mm to target edges."""
    if not IN_FUSION:
        raise RuntimeError("apply_fillet called in non-Fusion environment without mock.")

    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    root_comp = design.rootComponent

    radius_mm = float(params.get("radius", 1.0))
    if radius_mm <= 0:
        raise InvalidParamsError(
            message=f"Fillet radius must be strictly positive, got {radius_mm}mm.",
            hint="Specify a positive fillet radius (e.g., 1.5mm).",
            tool="apply_fillet"
        )

    target = params.get("target", "all_vertical_edges")
    edge_collection = adsk.core.ObjectCollection.create()

    # Collect target edges
    for b in root_comp.bRepBodies:
        for edge in b.edges:
            if target == "all_vertical_edges":
                # Check if edge is approximately vertical (Z direction)
                start_pt = edge.startVertex.geometry
                end_pt = edge.endVertex.geometry
                dx = abs(start_pt.x - end_pt.x)
                dy = abs(start_pt.y - end_pt.y)
                dz = abs(start_pt.z - end_pt.z)
                if dx < 1e-4 and dy < 1e-4 and dz > 1e-4:
                    edge_collection.add(edge)
            else:
                edge_collection.add(edge)

    if edge_collection.count == 0:
        raise EntityNotFoundError(entity_token=str(target), tool="apply_fillet")

    fillets = root_comp.features.filletFeatures
    fillet_input = fillets.createInput()
    radius_val = adsk.core.ValueInput.createByReal(mm_to_cm(radius_mm))
    fillet_input.addConstantRadiusEdgeSet(edge_collection, radius_val, True)

    try:
        fillet_feat = fillets.add(fillet_input)
    except Exception as e:
        raise GeometryError(
            message=f"Fillet creation failed for radius {radius_mm}mm: {str(e)}",
            hint=f"Radius {radius_mm}mm is likely too large for the adjacent geometry or corner topology. Try a smaller radius (e.g. {round(radius_mm * 0.4, 1)}mm).",
            tool="apply_fillet"
        )

    return {
        "status": "success",
        "feature_id": fillet_feat.name,
        "radius_mm": radius_mm,
        "edges_filleted": edge_collection.count
    }

