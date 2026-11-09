"""CADPilot Agent Core: Main Runner & CLI.

Provides the high-level CADPilotAgent class and command-line interface
to run the closed-loop CAD generation state machine.
"""

import sys
import os
import json
import argparse
from typing import Dict, Any, Optional

# Ensure repo root is on sys.path
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from agent.state import CADState, create_initial_cad_state
from agent.graph import build_langgraph_app, StandaloneCADStateMachine
from client.test_client import CADPilotClient


class CADPilotAgent:
    """Autonomous CAD Generation Agent for Fusion 360 Bridge."""

    def __init__(self, endpoint_url: str = "mock", client: Optional[CADPilotClient] = None, verbose: bool = True):
        self.endpoint_url = endpoint_url
        self.client = client or CADPilotClient(endpoint_url=endpoint_url)
        self.verbose = verbose

        # Try to use LangGraph app if installed, otherwise fallback to Standalone runner
        self.app = build_langgraph_app(endpoint_url=endpoint_url, client=self.client)
        if self.app is None:
            self.app = StandaloneCADStateMachine(endpoint_url=endpoint_url, client=self.client)

    def log(self, message: str):
        if self.verbose:
            print(message)

    def run(self, prompt: str) -> CADState:
        """Runs the CADPilot state machine on the user prompt."""
        self.log("\n========================================================")
        self.log(f"🤖 CADPilot Agent: Processing Request")
        self.log(f"📝 Prompt: \"{prompt}\"")
        self.log(f"🔗 Target Bridge: {self.endpoint_url}")
        self.log("========================================================\n")

        initial_state = create_initial_cad_state(prompt)

        # Execute state machine
        if hasattr(self.app, "invoke"):
            result_state = self.app.invoke(initial_state)
        else:
            raise RuntimeError("Agent runner application is invalid.")

        self._print_summary(result_state)
        return result_state

    def _print_summary(self, state: CADState):
        status = state.get("status", "unknown")
        if status == "completed":
            self.log("\n🎉 CAD Generation SUCCESSFUL!")
            spec = state.get("spec", {})
            self.log(f"📐 Part Type: {spec.get('part_type')} ({spec.get('shape_type')})")
            self.log(f"📏 Dimensions: {spec.get('dimensions')}")
            self.log(f"⭕ Holes Generated: {len(spec.get('holes', []))}")
            if spec.get("fillets"):
                self.log(f"✨ Fillets: {spec['fillets'].get('radius')}mm on {spec['fillets'].get('target')}")

            final_out = state.get("final_output", {})
            brep = final_out.get("brep", {})
            if brep:
                overall_bbox = brep.get("overall_bounding_box", {})
                self.log(f"📦 Bounding Box: {overall_bbox.get('dimensions')} mm")
                bodies = brep.get("bodies", [])
                if bodies:
                    self.log(f"🧊 Volume: {bodies[0].get('volume_mm3')} mm³")
                    self.log(f"🧱 Face Count: {bodies[0].get('face_count')}")

            export = final_out.get("export", {})
            if export:
                self.log(f"💾 Exported File: {export.get('output_path')} ({export.get('file_size_bytes')} bytes)")
        else:
            self.log(f"\n❌ CAD Generation FAILED with status: {status}")
            self.log(f"⚠️ Error: {state.get('error')}")


def main():
    parser = argparse.ArgumentParser(description="CADPilot Agent Core CLI")
    parser.add_argument(
        "prompt",
        nargs="?",
        default="Create a 42.3mm NEMA 17 mount plate with 4mm thickness, 22mm center hole, and 4x M3 holes spaced 31mm apart with 2mm fillets, export to /tmp/nema17_plate.step",
        help="Natural language mechanical CAD request"
    )
    parser.add_argument("--url", default="mock", help="Bridge URL (e.g. 'mock' or 'http://127.0.0.1:9090/')")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose logging")
    args = parser.parse_args()

    agent = CADPilotAgent(endpoint_url=args.url, verbose=not args.quiet)
    agent.run(args.prompt)


if __name__ == "__main__":
    main()
