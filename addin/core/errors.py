"""Structured error handling for CADPilot JSON-RPC Bridge.

Maps internal Fusion exceptions and geometric validation failures into
structured JSON-RPC 2.0 error payloads with actionable hints for LLM agents.
"""

from typing import Optional, Dict, Any


# Standard JSON-RPC 2.0 Error Codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# CADPilot Application Error Codes
NO_ACTIVE_DESIGN = -32000
OPERATION_TIMEOUT = -32001
GEOMETRY_ERROR = -32002
ENTITY_NOT_FOUND = -32003
EXPORT_FAILED = -32004


class BridgeError(Exception):
    """Base exception for CADPilot Bridge errors."""

    def __init__(
        self,
        code: int,
        message: str,
        hint: Optional[str] = None,
        tool: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint
        self.tool = tool
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to JSON-RPC error object."""
        error_dict: Dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        data: Dict[str, Any] = {}
        if self.hint:
            data["hint"] = self.hint
        if self.tool:
            data["tool"] = self.tool
        if self.details:
            data.update(self.details)
        if data:
            error_dict["data"] = data
        return error_dict


class GeometryError(BridgeError):
    """Raised when a geometric feature fails to generate (e.g. self-intersecting, impossible fillet)."""

    def __init__(
        self,
        message: str,
        hint: str,
        tool: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            code=GEOMETRY_ERROR,
            message=message,
            hint=hint,
            tool=tool,
            details=details,
        )


class EntityNotFoundError(BridgeError):
    """Raised when a referenced face, edge, body, or profile token cannot be found."""

    def __init__(self, entity_token: str, tool: Optional[str] = None):
        super().__init__(
            code=ENTITY_NOT_FOUND,
            message=f"Entity not found: '{entity_token}'",
            hint="Verify that the referenced entity ID matches the output of a preceding tool call (e.g. sketch or extrude).",
            tool=tool,
            details={"missing_token": entity_token},
        )


class InvalidParamsError(BridgeError):
    """Raised when parameter types or ranges are violated."""

    def __init__(self, message: str, hint: str, tool: Optional[str] = None):
        super().__init__(
            code=INVALID_PARAMS,
            message=message,
            hint=hint,
            tool=tool,
        )


def format_exception_for_agent(exc: Exception, tool_name: Optional[str] = None) -> Dict[str, Any]:
    """Wraps arbitrary Python or adsk exceptions into structured JSON-RPC error dicts."""
    if isinstance(exc, BridgeError):
        return exc.to_dict()

    err_str = str(exc)

    # Inspect adsk / geometry specific messages
    if "InternalValidationError" in err_str or "failed to execute" in err_str.lower():
        hint = (
            "The CAD engine encountered a geometric conflict or invalid topology. "
            "Ensure shapes do not self-intersect, fillet radii are smaller than wall thicknesses, "
            "and extrusions refer to valid closed planar profiles."
        )
        return BridgeError(
            code=GEOMETRY_ERROR,
            message=f"Fusion 360 geometric operation failed: {err_str}",
            hint=hint,
            tool=tool_name,
        ).to_dict()

    return BridgeError(
        code=INTERNAL_ERROR,
        message=f"Unexpected error in tool '{tool_name}': {err_str}",
        hint="Retry after calling reset_design if the model is in a broken state.",
        tool=tool_name,
    ).to_dict()

