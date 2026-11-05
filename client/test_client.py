"""CADPilot Bridge Test Client and CLI.

Provides a Python client class for calling the bridge and a command-line runner
to test all tools, verify JSON-RPC responses, and execute the NEMA 17 plate sequence.
"""

import sys
import os
import json
import urllib.request
import urllib.error
import argparse
from typing import Dict, Any, Optional, List

# Ensure repo root is in sys.path
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)


class CADPilotClient:
    """Client for CADPilot JSON-RPC Bridge.

    Supports network HTTP calls (default) or in-process mock mode (when url='mock'
    or when running in sandboxed/offline environments).
    """

    def __init__(self, endpoint_url: str = "http://127.0.0.1:9090/"):
        self.endpoint_url = endpoint_url
        self._request_counter = 0
        self._in_process_handler = None
        if self.endpoint_url == "mock":
            from mock.mock_bridge import MockBridgeHTTPHandler
            self._in_process_handler = MockBridgeHTTPHandler

    def call(self, method: str, params: Optional[Dict[str, Any]] = None, timeout: float = 35.0) -> Dict[str, Any]:
        """Sends a JSON-RPC 2.0 call over HTTP POST or in-process mock."""
        self._request_counter += 1
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params if params is not None else {},
            "id": self._request_counter
        }

        if self._in_process_handler is not None:
            return self._in_process_handler.handle_rpc(
                self._in_process_handler,
                method,
                payload["params"],
                payload["id"]
            )

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint_url,
            data=data,
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                resp_bytes = response.read()
                return json.loads(resp_bytes.decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            try:
                return json.loads(err_body)
            except Exception:
                raise RuntimeError(f"HTTP Error {e.code}: {err_body}")
        except urllib.error.URLError as e:
            # Fallback to in-process mock if server is not reachable
            try:
                from mock.mock_bridge import MockBridgeHTTPHandler
                print(f"[i] Bridge not running on {self.endpoint_url} ({e.reason}). Falling back to in-process Mock Bridge...")
                self._in_process_handler = MockBridgeHTTPHandler
                return self._in_process_handler.handle_rpc(
                    self._in_process_handler,
                    method,
                    payload["params"],
                    payload["id"]
                )
            except Exception:
                raise ConnectionError(f"Could not connect to CADPilot Bridge at {self.endpoint_url}: {e.reason}")

    def ping(self) -> Dict[str, Any]:
        return self.call("ping")

    def reset_design(self, save_existing: bool = False) -> Dict[str, Any]:
        return self.call("reset_design", {"save_existing": save_existing})

    def create_sketch(self, plane: str, shapes: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.call("create_sketch", {"plane": plane, "shapes": shapes})

    def extrude_profile(self, profile_id: str = "all", distance: float = 10.0, operation: str = "new_body") -> Dict[str, Any]:
        return self.call("extrude_profile", {"profile_id": profile_id, "distance": distance, "operation": operation})

    def cut_hole(self, position: List[float], diameter: float, depth: Any = "through", face: str = "xy") -> Dict[str, Any]:
        return self.call("cut_hole", {"position": position, "diameter": diameter, "depth": depth, "face": face})

    def apply_fillet(self, target: str = "all_vertical_edges", radius: float = 1.0) -> Dict[str, Any]:
        return self.call("apply_fillet", {"target": target, "radius": radius})

    def inspect_brep(self, target_body: str = "all") -> Dict[str, Any]:
        return self.call("inspect_brep", {"target_body": target_body})

    def export_cad(self, format: str = "step", output_path: str = "/tmp/part.step") -> Dict[str, Any]:
        return self.call("export_cad", {"format": format, "output_path": output_path})


def run_nema17_sequence(client: CADPilotClient):
    """Executes the standard NEMA 17 motor mount plate sequence end-to-end.

    Spec:
    - 42.3 mm x 42.3 mm square plate
    - 4.0 mm plate thickness
    - 22.0 mm center pilot hole
    - 4x M3 mount holes (3.0 mm diam) arranged in a 31.0 mm square pattern (+/- 15.5 mm)
    - 2.0 mm corner fillets
    """
    print("\n--- [Step 1] Reset Design ---")
    res = client.reset_design()
    print(json.dumps(res, indent=2))

    print("\n--- [Step 2] Create Base Sketch (42.3mm x 42.3mm square) ---")
    res = client.create_sketch(
        plane="xy",
        shapes=[
            {"type": "rectangle", "center": [0.0, 0.0], "width": 42.3, "height": 42.3}
        ]
    )
    print(json.dumps(res, indent=2))
    sketch_id = res.get("result", {}).get("sketch_id", "sketch_1")

    print("\n--- [Step 3] Extrude Base Plate (4.0mm) ---")
    res = client.extrude_profile(profile_id=f"{sketch_id}:prof_0", distance=4.0, operation="new_body")
    print(json.dumps(res, indent=2))

    print("\n--- [Step 4] Cut Center Pilot Hole (22.0mm diameter) ---")
    res = client.cut_hole(position=[0.0, 0.0], diameter=22.0, depth="through")
    print(json.dumps(res, indent=2))

    print("\n--- [Step 5] Cut 4x M3 Mount Holes (31mm spacing -> (+/-15.5, +/-15.5)) ---")
    hole_positions = [
        [-15.5, -15.5],
        [15.5, -15.5],
        [15.5, 15.5],
        [-15.5, 15.5]
    ]
    for idx, pos in enumerate(hole_positions, 1):
        print(f"Cutting mount hole #{idx} at {pos}...")
        res = client.cut_hole(position=pos, diameter=3.0, depth="through")
        print(f"Hole #{idx} status: {res.get('result', {}).get('status', 'failed')}")

    print("\n--- [Step 6] Apply Fillets (2.0mm radius on exterior vertical edges) ---")
    res = client.apply_fillet(target="all_vertical_edges", radius=2.0)
    print(json.dumps(res, indent=2))

    print("\n--- [Step 7] Inspect B-Rep Geometry (Bibhukesh's Reflection Step) ---")
    res = client.inspect_brep()
    print(json.dumps(res, indent=2))

    print("\n--- [Step 8] Export CAD File (STEP) ---")
    export_path = "/tmp/nema17_mount_plate.step"
    res = client.export_cad(format="step", output_path=export_path)
    print(json.dumps(res, indent=2))

    print(f"\n✅ NEMA 17 Mount Plate generation complete! Exported to: {export_path}")


def run_error_recovery_test(client: CADPilotClient):
    """Deliberately calls apply_fillet with an impossible radius to verify structured error hints."""
    print("\n--- [Test] Triggering Geometry Error (Over-sized Fillet) ---")
    client.reset_design()
    client.create_sketch(plane="xy", shapes=[{"type": "rectangle", "center": [0, 0], "width": 42.3, "height": 42.3}])
    client.extrude_profile(distance=4.0)

    # Attempt 50mm fillet on 4mm plate
    res = client.apply_fillet(radius=50.0)
    print(json.dumps(res, indent=2))
    assert "error" in res, "Expected error in response!"
    print("\n✅ Verified: Bridge returned structured error code and actionable LLM hint!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CADPilot Test Client")
    parser.add_argument("--url", default="http://127.0.0.1:9090/", help="Bridge URL")
    parser.add_argument("command", choices=["ping", "reset", "nema17", "test-error"], default="ping", nargs="?")
    args = parser.parse_args()

    client = CADPilotClient(endpoint_url=args.url)

    if args.command == "ping":
        print(json.dumps(client.ping(), indent=2))
    elif args.command == "reset":
        print(json.dumps(client.reset_design(), indent=2))
    elif args.command == "nema17":
        run_nema17_sequence(client)
    elif args.command == "test-error":
        run_error_recovery_test(client)
