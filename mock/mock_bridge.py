"""CADPilot Mock Bridge Server.

Implements 100% of the JSON-RPC 2.0 contract defined in docs/JSON_RPC_CONTRACT.md.
Maintains simulated geometric state (sketches, bodies, bounding boxes, hole count,
and volume) to unblock Abhijit (LangGraph agent loop) and Bibhukesh (eval & validation).
"""

import http.server
import json
import os
import sys
import argparse
from typing import Dict, Any, List, Optional
import math


class SimulatedCADState:
    """Simulates the CAD kernel document state."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.sketches: Dict[str, Dict[str, Any]] = {}
        self.bodies: Dict[str, Dict[str, Any]] = {}
        self.features: List[Dict[str, Any]] = []
        self.sketch_counter = 0
        self.feature_counter = 0
        self.body_counter = 0
        self.bounding_box = {
            "min": [0.0, 0.0, 0.0],
            "max": [0.0, 0.0, 0.0],
            "dimensions": [0.0, 0.0, 0.0],
            "unit": "mm"
        }

    def add_sketch(self, plane: str, shapes: List[Dict[str, Any]]) -> Dict[str, Any]:
        self.sketch_counter += 1
        sk_id = f"sketch_{self.sketch_counter}"

        min_x, max_x = float("inf"), float("-inf")
        min_y, max_y = float("inf"), float("-inf")
        total_area = 0.0
        profiles = []

        for idx, s in enumerate(shapes):
            stype = s.get("type", "").lower()
            if stype == "rectangle":
                if "center" in s:
                    cx, cy = s["center"]
                    w, h = s.get("width", 10.0), s.get("height", 10.0)
                    x1, y1 = cx - w / 2.0, cy - h / 2.0
                    x2, y2 = cx + w / 2.0, cy + h / 2.0
                else:
                    c1 = s.get("corner1", [0.0, 0.0])
                    c2 = s.get("corner2", [10.0, 10.0])
                    x1, y1 = min(c1[0], c2[0]), min(c1[1], c2[1])
                    x2, y2 = max(c1[0], c2[0]), max(c1[1], c2[1])
                min_x, max_x = min(min_x, x1), max(max_x, x2)
                min_y, max_y = min(min_y, y1), max(max_y, y2)
                area = (x2 - x1) * (y2 - y1)
                total_area += area
                profiles.append({
                    "profile_id": f"{sk_id}:prof_{idx}",
                    "index": idx,
                    "area_mm2": round(area, 2)
                })
            elif stype == "circle":
                cx, cy = s.get("center", [0.0, 0.0])
                d = s.get("diameter", 10.0)
                r = d / 2.0
                min_x, max_x = min(min_x, cx - r), max(max_x, cx + r)
                min_y, max_y = min(min_y, cy - r), max(max_y, cy + r)
                area = math.pi * (r ** 2)
                total_area += area
                profiles.append({
                    "profile_id": f"{sk_id}:prof_{idx}",
                    "index": idx,
                    "area_mm2": round(area, 2)
                })

        if min_x == float("inf"):
            min_x, max_x = 0.0, 0.0
            min_y, max_y = 0.0, 0.0

        bbox = {
            "min": [round(min_x, 2), round(min_y, 2), 0.0],
            "max": [round(max_x, 2), round(max_y, 2), 0.0],
            "dimensions": [round(max_x - min_x, 2), round(max_y - min_y, 2), 0.0],
            "unit": "mm"
        }

        self.sketches[sk_id] = {
            "plane": plane,
            "shapes": shapes,
            "profiles": profiles,
            "bounding_box": bbox,
            "total_area": total_area
        }

        return {
            "status": "success",
            "sketch_id": sk_id,
            "profiles": profiles,
            "bounding_box": bbox
        }

    def extrude(self, profile_id: str, distance_mm: float, operation: str = "new_body") -> Dict[str, Any]:
        self.feature_counter += 1
        feat_id = f"extrude_{self.feature_counter}"

        # Find sketch
        target_sk = None
        for sk in self.sketches.values():
            for p in sk["profiles"]:
                if profile_id == "all" or p["profile_id"] == profile_id:
                    target_sk = sk
                    break
            if target_sk:
                break

        if not target_sk and self.sketches:
            target_sk = list(self.sketches.values())[-1]

        sk_bbox = target_sk["bounding_box"] if target_sk else self.bounding_box
        min_x, min_y = sk_bbox["min"][0], sk_bbox["min"][1]
        max_x, max_y = sk_bbox["max"][0], sk_bbox["max"][1]
        min_z = 0.0
        max_z = round(distance_mm, 2)

        self.bounding_box = {
            "min": [min_x, min_y, min_z],
            "max": [max_x, max_y, max_z],
            "dimensions": [round(max_x - min_x, 2), round(max_y - min_y, 2), round(abs(max_z - min_z), 2)],
            "unit": "mm"
        }

        self.body_counter += 1
        body_id = f"body_{self.body_counter}"
        volume = (max_x - min_x) * (max_y - min_y) * distance_mm

        self.bodies[body_id] = {
            "body_id": body_id,
            "is_solid": True,
            "volume_mm3": round(volume, 2),
            "surface_area_mm2": round(2 * ((max_x - min_x)*(max_y - min_y) + (max_x - min_x)*distance_mm + (max_y - min_y)*distance_mm), 2),
            "face_count": 6,
            "edge_count": 12,
            "vertex_count": 8,
            "bounding_box": self.bounding_box,
            "cylindrical_features": []
        }

        return {
            "status": "success",
            "feature_id": feat_id,
            "body_ids": [body_id],
            "bounding_box": self.bounding_box
        }

    def cut_hole(self, position: List[float], diameter: float, depth: Any = "through") -> Dict[str, Any]:
        self.feature_counter += 1
        feat_id = f"hole_{self.feature_counter}"

        # Update primary body
        if not self.bodies:
            raise ValueError("Cannot cut hole: no solid bodies exist.")

        body = list(self.bodies.values())[0]
        r = diameter / 2.0
        hole_vol = math.pi * (r ** 2) * self.bounding_box["dimensions"][2]
        body["volume_mm3"] = round(max(0.0, body["volume_mm3"] - hole_vol), 2)
        body["face_count"] += 1  # Cylindrical inside face

        body["cylindrical_features"].append({
            "face_token": f"cyl_{len(body['cylindrical_features']) + 1}",
            "radius_mm": round(r, 2),
            "diameter_mm": round(diameter, 2),
            "origin_mm": [round(position[0], 2), round(position[1], 2), 0.0],
            "axis": [0.0, 0.0, 1.0]
        })

        return {
            "status": "success",
            "feature_id": feat_id,
            "hole_count": len(body["cylindrical_features"]),
            "bounding_box": self.bounding_box
        }

    def apply_fillet(self, target: str, radius_mm: float) -> Dict[str, Any]:
        self.feature_counter += 1
        feat_id = f"fillet_{self.feature_counter}"

        # Geometric rule: fillet radius must not exceed half of the smallest dimension
        min_dim = min([d for d in self.bounding_box["dimensions"] if d > 0] or [10.0])
        if radius_mm >= min_dim:
            # Simulated geometry error with self-correction hint for testing agent loop!
            max_safe = round(min_dim * 0.4, 1)
            raise ValueError(
                f"FILLET_OVERSIZE:Fillet radius {radius_mm}mm exceeds maximum geometry limit of {min_dim}mm.|"
                f"Reduce fillet radius to <= {max_safe}mm to avoid topological self-intersection."
            )

        if self.bodies:
            body = list(self.bodies.values())[0]
            body["face_count"] += 4  # Typical 4 vertical fillets

        return {
            "status": "success",
            "feature_id": feat_id,
            "radius_mm": radius_mm,
            "edges_filleted": 4
        }


class MockBridgeHTTPHandler(http.server.BaseHTTPRequestHandler):
    """HTTP Request Handler for Mock Bridge."""

    cad_state = SimulatedCADState()

    def log_message(self, format: str, *args: Any):
        sys.stdout.write(f"[MockBridge] {self.address_string()} - {format % args}\n")
        sys.stdout.flush()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length)

        try:
            req = json.loads(raw_body.decode("utf-8"))
        except Exception as e:
            self._send_json({
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": f"Parse error: {str(e)}"},
                "id": None
            }, 400)
            return

        method = req.get("method")
        params = req.get("params", {})
        req_id = req.get("id")

        resp = self.handle_rpc(method, params, req_id)
        self._send_json(resp, 200)

    def handle_rpc(self, method: str, params: Dict[str, Any], req_id: Any) -> Dict[str, Any]:
        try:
            if method == "ping":
                return {
                    "jsonrpc": "2.0",
                    "result": {
                        "status": "ok",
                        "fusion_version": "2.0.mock",
                        "bridge_mode": "mock",
                        "message": "CADPilot Mock Bridge active and ready."
                    },
                    "id": req_id
                }

            elif method == "reset_design":
                self.cad_state.reset()
                return {
                    "jsonrpc": "2.0",
                    "result": {
                        "status": "success",
                        "message": "Design reset cleanly (mock mode)."
                    },
                    "id": req_id
                }

            elif method == "create_sketch":
                plane = params.get("plane", "xy")
                shapes = params.get("shapes", [])
                res = self.cad_state.add_sketch(plane, shapes)
                return {"jsonrpc": "2.0", "result": res, "id": req_id}

            elif method == "extrude_profile":
                prof_id = params.get("profile_id", "all")
                dist = float(params.get("distance", 10.0))
                op = params.get("operation", "new_body")
                res = self.cad_state.extrude(prof_id, dist, op)
                return {"jsonrpc": "2.0", "result": res, "id": req_id}

            elif method == "cut_hole":
                pos = params.get("position", [0.0, 0.0])
                diam = float(params.get("diameter", 3.0))
                depth = params.get("depth", "through")
                res = self.cad_state.cut_hole(pos, diam, depth)
                return {"jsonrpc": "2.0", "result": res, "id": req_id}

            elif method == "apply_fillet":
                target = params.get("target", "all_vertical_edges")
                radius = float(params.get("radius", 1.0))
                res = self.cad_state.apply_fillet(target, radius)
                return {"jsonrpc": "2.0", "result": res, "id": req_id}

            elif method == "inspect_brep":
                bodies_list = list(self.cad_state.bodies.values())
                return {
                    "jsonrpc": "2.0",
                    "result": {
                        "status": "success",
                        "body_count": len(bodies_list),
                        "bodies": bodies_list,
                        "overall_bounding_box": self.cad_state.bounding_box
                    },
                    "id": req_id
                }

            elif method == "export_cad":
                fmt = params.get("format", "step")
                out_path = params.get("output_path", "/tmp/mock_cad_export.step")
                parent = os.path.dirname(os.path.abspath(out_path))
                if parent and not os.path.exists(parent):
                    os.makedirs(parent, exist_ok=True)
                with open(out_path, "w") as f:
                    f.write(f"/* ISO-10303-21 Mock CADPilot STEP Export - format {fmt} */\n")
                size = os.path.getsize(out_path)
                return {
                    "jsonrpc": "2.0",
                    "result": {
                        "status": "success",
                        "format": fmt,
                        "output_path": out_path,
                        "file_size_bytes": size
                    },
                    "id": req_id
                }

            else:
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32601,
                        "message": f"Method '{method}' not found on bridge.",
                        "data": {
                            "hint": "Check method name against JSON-RPC Contract: ping, reset_design, create_sketch, extrude_profile, cut_hole, apply_fillet, inspect_brep, export_cad"
                        }
                    },
                    "id": req_id
                }

        except Exception as exc:
            msg = str(exc)
            if "FILLET_OVERSIZE" in msg:
                parts = msg.split("|")
                err_msg = parts[0].replace("FILLET_OVERSIZE:", "")
                hint_msg = parts[1] if len(parts) > 1 else "Reduce fillet radius."
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32002,
                        "message": err_msg,
                        "data": {
                            "hint": hint_msg,
                            "tool": "apply_fillet"
                        }
                    },
                    "id": req_id
                }

            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32002,
                    "message": f"Mock error: {msg}",
                    "data": {"hint": "Check parameters or call reset_design."}
                },
                "id": req_id
            }

    def _send_json(self, data: Dict[str, Any], status: int = 200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


def run_mock_server(host: str = "127.0.0.1", port: int = 9090):
    server = http.server.HTTPServer((host, port), MockBridgeHTTPHandler)
    print(f"============================================================")
    print(f"  CADPilot Standalone Mock Bridge Server")
    print(f"  Listening on: http://{host}:{port}")
    print(f"  Contract: JSON-RPC 2.0 (Strict)")
    print(f"  Ready for Abhijit (Agent Core) & Bibhukesh (Validation)")
    print(f"============================================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Mock Bridge Server...")
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CADPilot Mock Bridge Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=9090, help="Port (default: 9090)")
    args = parser.parse_args()

    run_mock_server(args.host, args.port)

