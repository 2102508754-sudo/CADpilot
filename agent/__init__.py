"""CADPilot Agent Core Package.

State machine, natural language specification extractor, feasibility checker,
CAD sequence planner, and closed-loop self-correction engine.
"""

from .state import (
    CADState,
    TaskSpec,
    HoleSpec,
    FilletSpec,
    ExportSpec,
    FeasibilityReport,
    CADPlan,
    PlanStep,
    ExecutionObservation,
    ReflectionState,
    create_initial_cad_state
)


def __getattr__(name: str):
    if name == "CADPilotAgent":
        from .agent import CADPilotAgent
        return CADPilotAgent
    raise AttributeError(f"module 'agent' has no attribute '{name}'")


__all__ = [
    "CADPilotAgent",
    "CADState",
    "TaskSpec",
    "HoleSpec",
    "FilletSpec",
    "ExportSpec",
    "FeasibilityReport",
    "CADPlan",
    "PlanStep",
    "ExecutionObservation",
    "ReflectionState",
    "create_initial_cad_state"
]
