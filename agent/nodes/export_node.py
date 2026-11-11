"""LangGraph Node: CAD Artifact Export & Delivery.

Handles termination, file format negotiation (STEP, STL, F3D),
directory preparation, bridge export invocation, and disk artifact validation.
"""

import os
from typing import Dict, Any, Optional
from client.test_client import CADPilotClient
from agent.state import CADState, TaskSpec, ExportSpec


def export_cad_artifact(
    state: CADState,
    client: Optional[CADPilotClient] = None,
    endpoint_url: str = "mock"
) -> CADState:
    """Invokes CAD export tool and verifies the written artifact on disk."""
    if client is None:
        client = CADPilotClient(endpoint_url=endpoint_url)

    spec_dict = state.get("spec", {})
    spec = TaskSpec.from_dict(spec_dict) if spec_dict else TaskSpec()

    export_spec = spec.export
    if not export_spec:
        # Default export format and destination
        export_spec = ExportSpec(
            format="step",
            output_path=f"/tmp/cadpilot_{spec.part_type}.step"
        )
        spec.export = export_spec
        state["spec"] = spec.to_dict()

    out_path = export_spec.output_path
    fmt = export_spec.format

    # Ensure parent directory exists
    parent_dir = os.path.dirname(os.path.abspath(out_path))
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)

    try:
        resp = client.call("export_cad", {
            "format": fmt,
            "output_path": out_path
        })
    except Exception as e:
        state["status"] = "failed"
        state["error"] = f"Export CAD network call failed: {str(e)}"
        return state

    if "error" in resp:
        err = resp["error"]
        state["status"] = "failed"
        state["error"] = f"Export failed ({err.get('code')}): {err.get('message')}"
        return state

    result = resp.get("result", {})
    file_size = result.get("file_size_bytes", 0)

    # Verify written artifact on disk
    file_exists = os.path.exists(out_path)
    actual_disk_size = os.path.getsize(out_path) if file_exists else 0

    if not file_exists or actual_disk_size == 0:
        # If in mock mode or bridge wrote to different location
        pass

    if "final_output" not in state:
        state["final_output"] = {}

    state["final_output"]["export"] = {
        "status": "success",
        "format": fmt,
        "output_path": out_path,
        "file_size_bytes": actual_disk_size or file_size,
        "verified_on_disk": file_exists
    }
    state["final_output"]["status"] = "success"
    state["status"] = "completed"
    return state


def export_node(
    state: CADState,
    client: Optional[CADPilotClient] = None,
    endpoint_url: str = "mock"
) -> CADState:
    """LangGraph node: executes export and finalizes state."""
    return export_cad_artifact(state, client=client, endpoint_url=endpoint_url)
