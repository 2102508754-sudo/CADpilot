"""Unit and Integration Tests for CADPilot Agent Core (Abhijit Saha).

Verifies:
1. Agent State Schema (CADState, TaskSpec, FeasibilityReport, CADPlan, ReflectionState)
2. Spec Extractor Node (parsing NEMA 17, custom rectangular plates, circular flanges)
3. Feasibility Pre-Flight Checker (boundary detection, collision detection, fillet feasibility)
4. CAD Sequence Planner (generating ordered tool operations matching contract)
5. Tool Executor Node (invoking CADPilotClient with mock bridge)
6. Closed-Loop Reflection and Self-Correction (automatic recovery from bridge errors)
7. Full End-to-End Agent Execution
"""

import unittest
import os
import sys

# Ensure repo root is on sys.path
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from agent.state import (
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
from agent.nodes.spec_extractor import spec_extractor_node, extract_spec_from_text
from agent.nodes.feasibility_checker import feasibility_checker_node, check_geometric_feasibility
from agent.nodes.planner import planner_node, generate_cad_plan
from agent.nodes.executor import tool_executor_node, execute_plan_steps
from agent.nodes.reflection import reflection_node, self_correct_spec
from agent.agent import CADPilotAgent
from client.test_client import CADPilotClient


class TestAgentCore(unittest.TestCase):
    """Test suite for Abhijit Saha's CADPilot Agent Core."""

    def test_01_state_schema_initialization(self):
        """Verifies initial state structure and serialization."""
        state = create_initial_cad_state("Test prompt")
        self.assertEqual(state["prompt"], "Test prompt")
        self.assertEqual(state["status"], "specifying")
        self.assertIn("spec", state)
        self.assertIn("feasibility", state)
        self.assertIn("plan", state)
        self.assertIn("observations", state)
        self.assertIn("reflection", state)

        # Test TaskSpec serialization round-trip
        spec = TaskSpec(
            part_type="mounting_plate",
            dimensions={"width": 42.3, "height": 42.3, "thickness": 4.0},
            holes=[HoleSpec(position=[0.0, 0.0], diameter=22.0)],
            fillets=FilletSpec(radius=2.0),
            export=ExportSpec(format="step", output_path="/tmp/test.step")
        )
        spec_dict = spec.to_dict()
        spec_restored = TaskSpec.from_dict(spec_dict)
        self.assertEqual(spec_restored.dimensions["width"], 42.3)
        self.assertEqual(len(spec_restored.holes), 1)
        self.assertEqual(spec_restored.holes[0].diameter, 22.0)
        self.assertIsNotNone(spec_restored.fillets)
        self.assertEqual(spec_restored.fillets.radius, 2.0)

    def test_02_spec_extractor_nema17(self):
        """Verifies parsing of standard NEMA 17 natural language prompt."""
        prompt = (
            "Create a 42.3mm NEMA 17 mount plate with 4mm thickness, 22mm center hole, "
            "and 4x M3 holes spaced 31mm apart with 2mm fillets, export to /tmp/nema17.step"
        )
        spec = extract_spec_from_text(prompt)
        self.assertEqual(spec.part_type, "mounting_plate")
        self.assertEqual(spec.shape_type, "rectangle")
        self.assertEqual(spec.dimensions["width"], 42.3)
        self.assertEqual(spec.dimensions["height"], 42.3)
        self.assertEqual(spec.dimensions["thickness"], 4.0)

        # Center hole + 4 mounting holes = 5 holes
        self.assertEqual(len(spec.holes), 5)
        center_hole = spec.holes[0]
        self.assertEqual(center_hole.position, [0.0, 0.0])
        self.assertEqual(center_hole.diameter, 22.0)

        # Check mounting hole positions (+-15.5, +-15.5)
        mount_positions = [h.position for h in spec.holes[1:]]
        self.assertIn([-15.5, -15.5], mount_positions)
        self.assertIn([15.5, 15.5], mount_positions)

        self.assertIsNotNone(spec.fillets)
        self.assertEqual(spec.fillets.radius, 2.0)
        self.assertIsNotNone(spec.export)
        self.assertEqual(spec.export.output_path, "/tmp/nema17.step")

    def test_03_spec_extractor_node_state_transition(self):
        """Verifies LangGraph node transition for spec extraction."""
        state = create_initial_cad_state("NEMA 17 motor plate 4mm thick")
        state = spec_extractor_node(state)
        self.assertEqual(state["status"], "checking")
        self.assertIn("width", state["spec"]["dimensions"])
        self.assertEqual(state["spec"]["dimensions"]["width"], 42.3)

    def test_04_feasibility_checker_valid_spec(self):
        """Verifies that a physically feasible spec passes checks."""
        spec = TaskSpec(
            part_type="mounting_plate",
            dimensions={"width": 42.3, "height": 42.3, "thickness": 4.0},
            holes=[
                HoleSpec(position=[0.0, 0.0], diameter=22.0),
                HoleSpec(position=[15.5, 15.5], diameter=3.0)
            ],
            fillets=FilletSpec(radius=2.0)
        )
        report = check_geometric_feasibility(spec)
        self.assertTrue(report.is_feasible)
        self.assertEqual(len(report.errors), 0)

    def test_05_feasibility_checker_boundary_violation(self):
        """Verifies detection of holes exceeding plate boundaries."""
        spec = TaskSpec(
            part_type="mounting_plate",
            dimensions={"width": 40.0, "height": 40.0, "thickness": 4.0},
            holes=[
                # Position 25mm on 40mm plate (half-width 20mm) exceeds boundary
                HoleSpec(position=[25.0, 0.0], diameter=10.0)
            ]
        )
        report = check_geometric_feasibility(spec)
        self.assertFalse(report.is_feasible)
        self.assertTrue(any("exceeds plate width boundary" in err for err in report.errors))
        self.assertTrue(len(report.remediation_hints) > 0)

    def test_06_feasibility_checker_hole_collision(self):
        """Verifies detection of intersecting/overlapping holes."""
        spec = TaskSpec(
            part_type="mounting_plate",
            dimensions={"width": 100.0, "height": 100.0, "thickness": 5.0},
            holes=[
                HoleSpec(position=[10.0, 0.0], diameter=12.0),  # r=6
                HoleSpec(position=[15.0, 0.0], diameter=12.0)   # r=6, dist=5 < 12 -> intersects!
            ]
        )
        report = check_geometric_feasibility(spec)
        self.assertFalse(report.is_feasible)
        self.assertTrue(any("intersects Hole" in err for err in report.errors))

    def test_07_feasibility_checker_fillet_oversize(self):
        """Verifies detection of impossible fillet radius exceeding thickness."""
        spec = TaskSpec(
            part_type="mounting_plate",
            dimensions={"width": 50.0, "height": 50.0, "thickness": 4.0},
            fillets=FilletSpec(radius=10.0)  # 10mm fillet on 4mm thick plate!
        )
        report = check_geometric_feasibility(spec)
        self.assertFalse(report.is_feasible)
        self.assertTrue(any("exceeds plate thickness" in err for err in report.errors))

    def test_08_cad_sequence_planner(self):
        """Verifies planner output adheres strictly to JSON-RPC contract."""
        spec = TaskSpec(
            part_type="mounting_plate",
            dimensions={"width": 42.3, "height": 42.3, "thickness": 4.0},
            holes=[HoleSpec(position=[0.0, 0.0], diameter=22.0)],
            fillets=FilletSpec(radius=2.0),
            export=ExportSpec(format="step", output_path="/tmp/out.step")
        )
        plan = generate_cad_plan(spec)
        tools = [s.tool for s in plan.steps]

        # Verify correct ordering
        expected_tools = [
            "reset_design",
            "create_sketch",
            "extrude_profile",
            "cut_hole",
            "apply_fillet",
            "inspect_brep",
            "export_cad"
        ]
        self.assertEqual(tools, expected_tools)

        # Check sketch params
        sketch_step = plan.steps[1]
        self.assertEqual(sketch_step.params["plane"], "xy")
        self.assertEqual(sketch_step.params["shapes"][0]["width"], 42.3)

        # Check extrude params
        extrude_step = plan.steps[2]
        self.assertEqual(extrude_step.params["distance"], 4.0)
        self.assertEqual(extrude_step.params["operation"], "new_body")

    def test_09_tool_executor_with_mock_client(self):
        """Verifies execution of planned steps against the Mock Bridge."""
        client = CADPilotClient(endpoint_url="mock")
        spec = TaskSpec(
            part_type="mounting_plate",
            dimensions={"width": 42.3, "height": 42.3, "thickness": 4.0},
            holes=[HoleSpec(position=[0.0, 0.0], diameter=22.0)],
            fillets=FilletSpec(radius=2.0),
            export=ExportSpec(format="step", output_path="/tmp/test_exec.step")
        )
        plan = generate_cad_plan(spec)

        state = create_initial_cad_state()
        state["spec"] = spec.to_dict()
        state["plan"] = plan.to_dict()

        state = tool_executor_node(state, client=client)
        self.assertEqual(state["status"], "completed")
        self.assertEqual(len(state["observations"]), len(plan.steps))
        self.assertIn("brep", state["final_output"])
        self.assertIn("export", state["final_output"])

    def test_10_closed_loop_self_correction(self):
        """Verifies closed-loop self-correction when bridge returns a geometry error."""
        client = CADPilotClient(endpoint_url="mock")

        # Deliberately configure an oversized fillet (50mm on 4mm plate)
        spec = TaskSpec(
            part_type="mounting_plate",
            dimensions={"width": 42.3, "height": 42.3, "thickness": 4.0},
            fillets=FilletSpec(radius=50.0)
        )
        plan = generate_cad_plan(spec)

        state = create_initial_cad_state()
        state["spec"] = spec.to_dict()
        state["plan"] = plan.to_dict()

        # Execute: apply_fillet should fail on mock bridge with FILLET_OVERSIZE
        state = tool_executor_node(state, client=client)
        self.assertEqual(state["status"], "reflecting")
        self.assertEqual(state["reflection"]["last_error_tool"], "apply_fillet")
        self.assertIsNotNone(state["reflection"]["last_error_hint"])

        # Call reflection node to self-correct
        state = reflection_node(state)
        self.assertEqual(state["status"], "planning")
        self.assertLessEqual(state["spec"]["fillets"]["radius"], 2.0)

        # Re-plan and re-execute to verify successful recovery
        state = planner_node(state)
        state = tool_executor_node(state, client=client)
        self.assertEqual(state["status"], "completed")

    def test_11_agent_end_to_end_nema17(self):
        """Verifies end-to-end execution of CADPilotAgent on Mock Bridge."""
        prompt = (
            "Create a 42.3mm NEMA 17 mount plate with 4mm thickness, 22mm center hole, "
            "and 4x M3 holes spaced 31mm apart with 2mm fillets, export to /tmp/nema17_full.step"
        )
        agent = CADPilotAgent(endpoint_url="mock", verbose=False)
        result_state = agent.run(prompt)

        self.assertEqual(result_state["status"], "completed")
        brep = result_state["final_output"].get("brep", {})
        self.assertEqual(brep.get("overall_bounding_box", {}).get("dimensions"), [42.3, 42.3, 4.0])
        self.assertTrue(len(brep.get("bodies", [])) > 0)
        self.assertEqual(brep["bodies"][0]["body_id"], "body_1")


if __name__ == "__main__":
    unittest.main()
