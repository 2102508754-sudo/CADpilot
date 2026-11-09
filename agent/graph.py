"""LangGraph State Graph definition for CADPilot.

Defines the complete state machine topology:
  [START]
     |
     v
  [spec_extractor]
     |
     v
  [feasibility_checker] --(infeasible)--> [reflector] --(retries exhausted)--> [END (failed)]
     | (feasible)                              ^
     v                                         | (bridge error)
  [planner]                                    |
     |                                         |
     v                                         |
  [tool_executor] -----------------------------+
     | (success)
     v
   [END (completed)]
"""

from typing import Dict, Any, Optional, Callable
from agent.state import CADState, create_initial_cad_state
from agent.nodes import (
    spec_extractor_node,
    feasibility_checker_node,
    planner_node,
    tool_executor_node,
    reflection_node
)
from client.test_client import CADPilotClient


def route_after_feasibility(state: CADState) -> str:
    """Routes to planner if feasible, or reflector if infeasible."""
    status = state.get("status", "")
    if status == "planning":
        return "planner"
    return "reflector"


def route_after_executor(state: CADState) -> str:
    """Routes to END if completed, or reflector if tool call failed."""
    status = state.get("status", "")
    if status == "completed":
        return "END"
    return "reflector"


def route_after_reflection(state: CADState) -> str:
    """Routes back to planner if retrying, or END if max retries exceeded."""
    status = state.get("status", "")
    if status == "planning":
        return "planner"
    return "END"


def build_langgraph_app(endpoint_url: str = "mock", client: Optional[CADPilotClient] = None):
    """Builds a compiled LangGraph app if langgraph is installed."""
    try:
        from langgraph.graph import StateGraph, START, END  # type: ignore

        graph = StateGraph(CADState)

        # Add Nodes
        graph.add_node("spec_extractor", spec_extractor_node)
        graph.add_node("feasibility_checker", feasibility_checker_node)
        graph.add_node("planner", planner_node)
        graph.add_node(
            "tool_executor",
            lambda s: tool_executor_node(s, client=client, endpoint_url=endpoint_url)
        )
        graph.add_node("reflector", reflection_node)

        # Add Edges
        graph.add_edge(START, "spec_extractor")
        graph.add_edge("spec_extractor", "feasibility_checker")

        graph.add_conditional_edges(
            "feasibility_checker",
            route_after_feasibility,
            {"planner": "planner", "reflector": "reflector"}
        )

        graph.add_edge("planner", "tool_executor")

        graph.add_conditional_edges(
            "tool_executor",
            route_after_executor,
            {"END": END, "reflector": "reflector"}
        )

        graph.add_conditional_edges(
            "reflector",
            route_after_reflection,
            {"planner": "planner", "END": END}
        )

        return graph.compile()
    except ImportError:
        return None


class StandaloneCADStateMachine:
    """Zero-dependency state machine executing the CADPilot graph logic."""

    def __init__(self, endpoint_url: str = "mock", client: Optional[CADPilotClient] = None):
        self.endpoint_url = endpoint_url
        self.client = client or CADPilotClient(endpoint_url=endpoint_url)

    def invoke(self, state: CADState) -> CADState:
        """Executes the state machine synchronously until a terminal state is reached."""
        current_node = "spec_extractor"
        max_steps = 20
        step_count = 0

        while current_node != "END" and step_count < max_steps:
            step_count += 1

            if current_node == "spec_extractor":
                state = spec_extractor_node(state)
                current_node = "feasibility_checker"

            elif current_node == "feasibility_checker":
                state = feasibility_checker_node(state)
                next_dest = route_after_feasibility(state)
                current_node = next_dest

            elif current_node == "planner":
                state = planner_node(state)
                current_node = "tool_executor"

            elif current_node == "tool_executor":
                state = tool_executor_node(state, client=self.client, endpoint_url=self.endpoint_url)
                next_dest = route_after_executor(state)
                current_node = next_dest

            elif current_node == "reflector":
                state = reflection_node(state)
                next_dest = route_after_reflection(state)
                current_node = next_dest

            else:
                break

        return state
