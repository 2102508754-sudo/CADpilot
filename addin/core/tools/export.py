"""CAD export tool: STEP, STL, F3D."""

import os
from typing import Dict, Any
from ..errors import InvalidParamsError, BridgeError, EXPORT_FAILED

try:
    import adsk.core
    import adsk.fusion
    IN_FUSION = True
except ImportError:
    IN_FUSION = False


def export_cad(params: Dict[str, Any]) -> Dict[str, Any]:
    """Exports active design to STEP, STL, or F3D file on disk.

    Params:
        format: "step" | "stl" | "f3d"
        output_path: Absolute file path to write.
    """
    if not IN_FUSION:
        raise RuntimeError("export_cad called in non-Fusion environment without mock.")

    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        raise RuntimeError("No active design available to export.")

    fmt = str(params.get("format", "step")).lower()
    output_path = params.get("output_path", "")

    if not output_path:
        raise InvalidParamsError(
            message="Missing required parameter 'output_path'.",
            hint="Provide an absolute file path such as '/tmp/part.step'.",
            tool="export_cad"
        )

    # Ensure parent directory exists
    parent_dir = os.path.dirname(os.path.abspath(output_path))
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)

    export_mgr = design.exportManager
    root_comp = design.rootComponent

    try:
        if fmt == "step":
            step_opts = export_mgr.createSTEPExportOptions(output_path)
            export_mgr.execute(step_opts)
        elif fmt == "stl":
            if root_comp.bRepBodies.count == 0:
                raise BridgeError(
                    code=EXPORT_FAILED,
                    message="Cannot export STL: No solid bodies in design.",
                    hint="Ensure 3D geometry has been extruded before exporting.",
                    tool="export_cad"
                )
            stl_opts = export_mgr.createSTLExportOptions(root_comp.bRepBodies.item(0), output_path)
            stl_opts.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
            export_mgr.execute(stl_opts)
        elif fmt == "f3d":
            f3d_opts = export_mgr.createFusionArchiveExportOptions(output_path)
            export_mgr.execute(f3d_opts)
        else:
            raise InvalidParamsError(
                message=f"Unsupported export format '{fmt}'.",
                hint="Supported formats are 'step', 'stl', and 'f3d'.",
                tool="export_cad"
            )

        file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0

        return {
            "status": "success",
            "format": fmt,
            "output_path": output_path,
            "file_size_bytes": file_size
        }

    except Exception as e:
        raise BridgeError(
            code=EXPORT_FAILED,
            message=f"Export failed for format '{fmt}': {str(e)}",
            hint="Verify write permissions for the destination directory and that geometry is valid.",
            tool="export_cad"
        )

