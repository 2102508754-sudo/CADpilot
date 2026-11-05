"""Centralized unit conversion utilities for CADPilot Bridge.

Fusion 360's internal database standard:
- Linear distance: Centimetres (cm)
- Angular measure: Radians (rad)

CADPilot JSON-RPC Agent standard:
- Linear distance: Millimetres (mm)
- Angular measure: Degrees (deg)

All conversions between agent payloads and Fusion internal geometry MUST occur
through this module.
"""

from typing import List, Tuple, Dict, Any
import math


MM_PER_CM = 10.0
CM_PER_MM = 0.1


def mm_to_cm(val_mm: float) -> float:
    """Convert millimeters (API / Agent) to centimeters (Fusion 360 internal)."""
    return float(val_mm) * CM_PER_MM


def cm_to_mm(val_cm: float) -> float:
    """Convert centimeters (Fusion 360 internal) to millimeters (API / Agent)."""
    return float(val_cm) * MM_PER_CM


def deg_to_rad(deg: float) -> float:
    """Convert degrees to radians."""
    return math.radians(float(deg))


def rad_to_deg(rad: float) -> float:
    """Convert radians to degrees."""
    return math.degrees(float(rad))


def point_mm_to_cm(pt_mm: List[float]) -> List[float]:
    """Convert 2D or 3D coordinate list from mm to cm."""
    return [mm_to_cm(c) for c in pt_mm]


def point_cm_to_mm(pt_cm: List[float]) -> List[float]:
    """Convert 2D or 3D coordinate list from cm to mm."""
    return [round(cm_to_mm(c), 4) for c in pt_cm]


def bounding_box_cm_to_mm(min_pt: List[float], max_pt: List[float]) -> Dict[str, Any]:
    """Convert a bounding box from cm to standard mm bounding box dict."""
    min_mm = point_cm_to_mm(min_pt)
    max_mm = point_cm_to_mm(max_pt)
    dims_mm = [round(max_mm[i] - min_mm[i], 4) for i in range(len(min_pt))]
    return {
        "min": min_mm,
        "max": max_mm,
        "dimensions": dims_mm,
        "unit": "mm"
    }

