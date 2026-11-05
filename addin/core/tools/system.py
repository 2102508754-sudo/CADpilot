"""System level tools: ping and reset_design."""

from typing import Dict, Any, Optional
import traceback

try:
    import adsk.core
    import adsk.fusion
    IN_FUSION = True
except ImportError:
    IN_FUSION = False


def ping(params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Check bridge health and version."""
    fusion_version = "mock-mode"
    if IN_FUSION:
        app = adsk.core.Application.get()
        fusion_version = app.version if app else "unknown"

    return {
        "status": "ok",
        "fusion_version": fusion_version,
        "bridge_mode": "fusion" if IN_FUSION else "mock",
        "message": "CADPilot Bridge is alive and operational."
    }


def reset_design(params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Reset active document or open a clean untitled document for retry isolation."""
    if not IN_FUSION:
        return {
            "status": "success",
            "message": "Design reset cleanly (mock mode)."
        }

    app = adsk.core.Application.get()
    if not app:
        raise RuntimeError("Autodesk Fusion Application is unavailable.")

    # Save existing if requested, otherwise close without saving
    save_existing = False
    if params and isinstance(params, dict):
        save_existing = params.get("save_existing", False)

    doc = app.activeDocument
    if doc:
        # If user does not want to save existing, we close it or clear features
        try:
            # We open a fresh untitled document first to prevent app closing
            app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
            if not save_existing:
                doc.close(False)
        except Exception:
            # Fallback: remove all bodies/sketches in the current design component
            design = adsk.fusion.Design.cast(app.activeProduct)
            if design:
                root_comp = design.rootComponent
                for feat in reversed(list(root_comp.features)):
                    feat.deleteMe()
                for sk in reversed(list(root_comp.sketches)):
                    sk.deleteMe()

    return {
        "status": "success",
        "message": "Design reset cleanly. Workspace ready for new geometry generation."
    }

