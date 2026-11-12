"""LangGraph Node 4: Tool Execution Node.

Connects to CADPilotClient (targeting Mock Bridge or live Autodesk Fusion 360)
and dispatches ordered JSON-RPC 2.0 tool calls. Collects structured observations,
updates entity registries, and intercepts errors for reflection.
"""

from typing import Dict, Any, List, Optional
from client.test_client import CADPilotClient
from agent.state import CADState, PlanStep, ExecutionObservation, ReflectionState
from agent.nodes.observation_parser import ObservationParser


def execute_plan_steps(
    state: CADState,
    client: Optional[CADPilotClient] = None,
    endpoint_url: str = "mock"
) -> CADState:
    """Executes planned CAD tool steps sequentially via CADPilotClient."""
    if client is None:
        client = CADPilotClient(endpoint_url=endpoint_url)

    plan_steps_raw = state.get("plan", {}).get("steps", [])
    if not plan_steps_raw:
        state["error"] = "No planned steps available to execute."
        state["status"] = "failed"
        return state

    observations: List[Dict[str, Any]] = list(state.get("observations", []))
    reflection_state = ReflectionState.from_dict(state.get("reflection", {}))
    obs_parser = ObservationParser.from_state(state)

    for step_dict in plan_steps_raw:
        step = PlanStep.from_dict(step_dict)
        try:
            resp = client.call(step.tool, step.params)
        except Exception as e:
            # Catch network or unexpected communication exceptions
            resp = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": str(e),
                    "data": {"hint": "Check if bridge server is alive or restart bridge."}
                },
                "id": None
            }

        if "error" in resp:
            err = resp["error"]
            err_code = err.get("code", -32603)
            err_msg = err.get("message", "Unknown bridge error")
            err_hint = err.get("data", {}).get("hint", "")

            obs = ExecutionObservation(
                step_index=step.step_index,
                tool=step.tool,
                status="error",
                error_code=err_code,
                error_message=err_msg,
                error_hint=err_hint
            )
            observations.append(obs.to_dict())
            state["observations"] = observations

            # Update reflection tracking
            reflection_state.last_error_tool = step.tool
            reflection_state.last_error_code = err_code
            reflection_state.last_error_message = err_msg
            reflection_state.last_error_hint = err_hint
            reflection_state.history.append({
                "step": step.to_dict(),
                "error": err
            })
            state["reflection"] = reflection_state.to_dict()

            state["status"] = "reflecting"
            state["error"] = f"Tool '{step.tool}' failed: {err_msg}"
            return state

        # Step succeeded
        res = resp.get("result", {})
        obs = ExecutionObservation(
            step_index=step.step_index,
            tool=step.tool,
            status="success",
            result=res,
            bounding_box=res.get("bounding_box")
        )
        observations.append(obs.to_dict())

        # Update entity token registry & lineage
        obs_parser.parse_tool_result(step.tool, step.params, res)
        obs_parser.update_state(state)

        # Track key outputs
        if step.tool == "inspect_brep":
            if "final_output" not in state:
                state["final_output"] = {}
            state["final_output"]["brep"] = res
        elif step.tool == "export_cad":
            if "final_output" not in state:
                state["final_output"] = {}
            state["final_output"]["export"] = res

    state["observations"] = observations
    state["status"] = "validating"
    if "final_output" not in state:
        state["final_output"] = {}
    state["final_output"]["status"] = "in_progress"
    return state


def tool_executor_node(
    state: CADState,
    client: Optional[CADPilotClient] = None,
    endpoint_url: str = "mock"
) -> CADState:
    """LangGraph node: executes the CAD plan via CADPilotClient."""
    return execute_plan_steps(state, client=client, endpoint_url=endpoint_url)
