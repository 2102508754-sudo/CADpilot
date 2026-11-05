"""Main-thread Request Dispatcher for CADPilot Bridge."""

from typing import Dict, Any, Callable
from .errors import (
    METHOD_NOT_FOUND,
    INVALID_REQUEST,
    BridgeError,
    format_exception_for_agent
)
from .tools import (
    ping,
    reset_design,
    create_sketch,
    extrude_profile,
    cut_hole,
    apply_fillet,
    export_cad,
    inspect_brep
)


class ToolDispatcher:
    """Registry and execution dispatcher for all CAD tools."""

    def __init__(self):
        self._tools: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        self.register("ping", ping)
        self.register("reset_design", reset_design)
        self.register("create_sketch", create_sketch)
        self.register("extrude_profile", extrude_profile)
        self.register("cut_hole", cut_hole)
        self.register("apply_fillet", apply_fillet)
        self.register("export_cad", export_cad)
        self.register("inspect_brep", inspect_brep)

    def register(self, method_name: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]):
        """Register a tool handler function."""
        self._tools[method_name] = handler

    def dispatch(self, request_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches a single JSON-RPC 2.0 request.

        MUST be invoked on Fusion 360's main UI thread.
        """
        req_id = request_payload.get("id")
        method = request_payload.get("method")
        params = request_payload.get("params", {})

        if not method or not isinstance(method, str):
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": INVALID_REQUEST,
                    "message": "Invalid JSON-RPC request: 'method' must be a non-empty string."
                },
                "id": req_id
            }

        if method not in self._tools:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": METHOD_NOT_FOUND,
                    "message": f"Method '{method}' not found on bridge.",
                    "data": {
                        "hint": f"Available methods: {list(self._tools.keys())}"
                    }
                },
                "id": req_id
            }

        try:
            handler = self._tools[method]
            result = handler(params)
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": req_id
            }
        except Exception as exc:
            err_dict = format_exception_for_agent(exc, tool_name=method)
            return {
                "jsonrpc": "2.0",
                "error": err_dict,
                "id": req_id
            }

