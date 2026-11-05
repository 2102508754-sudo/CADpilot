"""B-Rep Inspection tool for CADPilot Bridge.

Exposes geometric and topological data (bounding boxes, volumes, face counts,
hole geometries) for Bibhukesh's reflection and verification pipeline.
"""

from typing import Dict, Any, List
from ..units import cm_to_mm, bounding_box_cm_to_mm

try:
    import adsk.core
    import adsk.fusion
    IN_FUSION = True
except ImportError:
    IN_FUSION = False


def inspect_brep(params: Dict[str, Any]) -> Dict[str, Any]:
    """Inspects the current B-Rep geometry and topology of the active design.

    Params:
        target_body: Optional body name/token. Defaults to "all".
    """
    if not IN_FUSION:
        raise RuntimeError("inspect_brep called in non-Fusion environment without mock.")

    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        return {
            "status": "success",
            "body_count": 0,
            "bodies": [],
            "message": "No active design or empty workspace."
        }

    root_comp = design.rootComponent
    bodies_data: List[Dict[str, Any]] = []

    target_body = params.get("target_body", "all")

    for body in root_comp.bRepBodies:
        if target_body != "all" and body.name != target_body:
            continue

        # Physical properties
        props = body.physicalProperties
        vol_cm3 = props.volume
        area_cm2 = props.area
        vol_mm3 = vol_cm3 * 1000.0   # 1 cm^3 = 1000 mm^3
        area_mm2 = area_cm2 * 100.0  # 1 cm^2 = 100 mm^2

        # Bounding box
        bbox = body.boundingBox
        bbox_dict = bounding_box_cm_to_mm(
            [bbox.minPoint.x, bbox.minPoint.y, bbox.minPoint.z],
            [bbox.maxPoint.x, bbox.maxPoint.y, bbox.maxPoint.z]
        )

        # Detect cylindrical holes/features
        cylindrical_features = []
        for face in body.faces:
            geom = face.geometry
            if geom.surfaceType == adsk.core.SurfaceTypes.CylinderSurfaceType:
                cyl = adsk.core.Cylinder.cast(geom)
                if cyl:
                    radius_mm = cm_to_mm(cyl.radius)
                    origin = cyl.origin
                    axis = cyl.axis
                    cylindrical_features.append({
                        "face_token": face.tempId if hasattr(face, "tempId") else str(face.entityToken),
                        "radius_mm": round(radius_mm, 2),
                        "diameter_mm": round(radius_mm * 2.0, 2),
                        "origin_mm": [round(cm_to_mm(origin.x), 2), round(cm_to_mm(origin.y), 2), round(cm_to_mm(origin.z), 2)],
                        "axis": [round(axis.x, 3), round(axis.y, 3), round(axis.z, 3)]
                    })

        bodies_data.append({
            "body_id": body.name,
            "is_solid": body.isSolid,
            "volume_mm3": round(vol_mm3, 2),
            "surface_area_mm2": round(area_mm2, 2),
            "face_count": body.faces.count,
            "edge_count": body.edges.count,
            "vertex_count": body.vertices.count,
            "bounding_box": bbox_dict,
            "cylindrical_features": cylindrical_features
        })

    # Overall assembly bounding box
    overall_bbox = root_comp.boundingBox
    overall_bbox_dict = bounding_box_cm_to_mm(
        [overall_bbox.minPoint.x, overall_bbox.minPoint.y, overall_bbox.minPoint.z],
        [overall_bbox.maxPoint.x, overall_bbox.maxPoint.y, overall_bbox.maxPoint.z]
    )

    return {
        "status": "success",
        "body_count": len(bodies_data),
        "bodies": bodies_data,
        "overall_bounding_box": overall_bbox_dict
    }

