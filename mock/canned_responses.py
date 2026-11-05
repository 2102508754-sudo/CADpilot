"""Canned responses and geometry models for the CADPilot Mock Bridge."""

from typing import Dict, Any, List


def get_default_nema17_mock() -> Dict[str, Any]:
    """Standard NEMA 17 motor mount plate dimensions and geometry specs."""
    return {
        "part_family": "mounting_plate",
        "name": "NEMA 17 Motor Mount Plate",
        "face_size_mm": [42.3, 42.3],
        "thickness_mm": 4.0,
        "pilot_diameter_mm": 22.0,
        "mount_holes": {
            "diameter_mm": 3.0,
            "spacing_mm": 31.0,
            "count": 4,
            "positions_mm": [
                [-15.5, -15.5],
                [15.5, -15.5],
                [15.5, 15.5],
                [-15.5, 15.5]
            ]
        },
        "fillet_radius_mm": 2.0,
        "bounding_box": {
            "min": [-21.15, -21.15, 0.0],
            "max": [21.15, 21.15, 4.0],
            "dimensions": [42.3, 42.3, 4.0],
            "unit": "mm"
        }
    }


def get_default_lbracket_mock() -> Dict[str, Any]:
    """Standard 90-degree L-bracket geometry specs."""
    return {
        "part_family": "l_bracket",
        "name": "90-degree L-Bracket",
        "leg1_mm": 50.0,
        "leg2_mm": 50.0,
        "width_mm": 30.0,
        "thickness_mm": 4.0,
        "bounding_box": {
            "min": [0.0, 0.0, 0.0],
            "max": [50.0, 30.0, 50.0],
            "dimensions": [50.0, 30.0, 50.0],
            "unit": "mm"
        }
    }

