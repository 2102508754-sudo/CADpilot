"""CADPilot LangGraph Nodes.

Contains the core nodes of the CADPilot state machine:
1. spec_extractor_node (Node 1)
2. feasibility_checker_node (Node 2)
3. planner_node (Node 3)
4. tool_executor_node (Node 4)
5. observation_parser (ObservationParser)
6. brep_validator_node (B-Rep & Geometric Property Validator)
7. export_node (CAD Artifact Export & Delivery)
8. reflection_node (Node 5)
"""

from .spec_extractor import spec_extractor_node, extract_spec_from_text
from .feasibility_checker import feasibility_checker_node, check_geometric_feasibility
from .planner import planner_node, generate_cad_plan
from .executor import tool_executor_node, execute_plan_steps
from .observation_parser import ObservationParser
from .brep_validator import brep_validator_node, validate_brep_geometry
from .export_node import export_node, export_cad_artifact
from .reflection import reflection_node, self_correct_spec

__all__ = [
    "spec_extractor_node",
    "extract_spec_from_text",
    "feasibility_checker_node",
    "check_geometric_feasibility",
    "planner_node",
    "generate_cad_plan",
    "tool_executor_node",
    "execute_plan_steps",
    "ObservationParser",
    "brep_validator_node",
    "validate_brep_geometry",
    "export_node",
    "export_cad_artifact",
    "reflection_node",
    "self_correct_spec"
]
