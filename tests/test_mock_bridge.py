"""Unit tests verifying CADPilot Bridge JSON-RPC 2.0 contract directly (no network socket required)."""

import unittest
import os
from mock.mock_bridge import MockBridgeHTTPHandler, SimulatedCADState
from addin.core.units import mm_to_cm, cm_to_mm, point_mm_to_cm, point_cm_to_mm, bounding_box_cm_to_mm
from addin.core.errors import (
    BridgeError,
    GeometryError,
    EntityNotFoundError,
    InvalidParamsError,
    format_exception_for_agent,
    GEOMETRY_ERROR
)
from addin.core.dispatcher import ToolDispatcher


class TestCADPilotBridgeDirectContract(unittest.TestCase):
    """Direct contract and logic test without socket network dependency."""

    def setUp(self):
        self.handler = MockBridgeHTTPHandler
        self.handler.cad_state = SimulatedCADState()

    def rpc(self, method, params=None, req_id=1):
        return self.handler.handle_rpc(self.handler, method, params or {}, req_id)

    def test_01_ping(self):
        resp = self.rpc("ping")
        self.assertEqual(resp.get("jsonrpc"), "2.0")
        self.assertIn("result", resp)
        self.assertEqual(resp["result"].get("status"), "ok")
        self.assertEqual(resp["result"].get("bridge_mode"), "mock")

    def test_02_create_sketch(self):
        resp = self.rpc("create_sketch", {
            "plane": "xy",
            "shapes": [
                {"type": "rectangle", "center": [0, 0], "width": 42.3, "height": 42.3}
            ]
        })
        self.assertEqual(resp.get("jsonrpc"), "2.0")
        res = resp.get("result", {})
        self.assertEqual(res.get("status"), "success")
        self.assertTrue(len(res.get("profiles", [])) > 0)
        bbox = res.get("bounding_box", {})
        self.assertEqual(bbox.get("dimensions"), [42.3, 42.3, 0.0])

    def test_03_extrude_profile(self):
        self.rpc("create_sketch", {
            "plane": "xy",
            "shapes": [{"type": "rectangle", "center": [0, 0], "width": 42.3, "height": 42.3}]
        })
        resp = self.rpc("extrude_profile", {"distance": 4.0})
        self.assertEqual(resp.get("jsonrpc"), "2.0")
        res = resp.get("result", {})
        self.assertEqual(res.get("status"), "success")
        self.assertEqual(res.get("bounding_box", {}).get("dimensions"), [42.3, 42.3, 4.0])

    def test_04_cut_hole(self):
        self.rpc("create_sketch", {
            "plane": "xy",
            "shapes": [{"type": "rectangle", "center": [0, 0], "width": 42.3, "height": 42.3}]
        })
        self.rpc("extrude_profile", {"distance": 4.0})
        resp = self.rpc("cut_hole", {"position": [0.0, 0.0], "diameter": 22.0})
        self.assertEqual(resp.get("jsonrpc"), "2.0")
        res = resp.get("result", {})
        self.assertEqual(res.get("status"), "success")
        self.assertEqual(res.get("hole_count"), 1)

    def test_05_apply_fillet_success(self):
        self.rpc("create_sketch", {
            "plane": "xy",
            "shapes": [{"type": "rectangle", "center": [0, 0], "width": 42.3, "height": 42.3}]
        })
        self.rpc("extrude_profile", {"distance": 4.0})
        resp = self.rpc("apply_fillet", {"radius": 1.5})
        self.assertEqual(resp.get("jsonrpc"), "2.0")
        self.assertEqual(resp.get("result", {}).get("status"), "success")

    def test_06_apply_fillet_oversize_error_hint(self):
        self.rpc("create_sketch", {
            "plane": "xy",
            "shapes": [{"type": "rectangle", "center": [0, 0], "width": 42.3, "height": 42.3}]
        })
        self.rpc("extrude_profile", {"distance": 4.0})
        # 50mm fillet on 4mm plate thickness should trigger structured error with hint
        resp = self.rpc("apply_fillet", {"radius": 50.0})
        self.assertIn("error", resp)
        err = resp["error"]
        self.assertEqual(err.get("code"), -32002)
        self.assertIn("hint", err.get("data", {}))
        self.assertIn("Reduce fillet radius", err["data"]["hint"])

    def test_07_inspect_brep(self):
        self.rpc("create_sketch", {
            "plane": "xy",
            "shapes": [{"type": "rectangle", "center": [0, 0], "width": 42.3, "height": 42.3}]
        })
        self.rpc("extrude_profile", {"distance": 4.0})
        self.rpc("cut_hole", {"position": [0.0, 0.0], "diameter": 22.0})
        resp = self.rpc("inspect_brep")
        self.assertEqual(resp.get("jsonrpc"), "2.0")
        res = resp.get("result", {})
        self.assertEqual(res.get("body_count"), 1)
        body = res["bodies"][0]
        self.assertEqual(len(body.get("cylindrical_features", [])), 1)

    def test_08_export_cad(self):
        self.rpc("create_sketch", {
            "plane": "xy",
            "shapes": [{"type": "rectangle", "center": [0, 0], "width": 42.3, "height": 42.3}]
        })
        self.rpc("extrude_profile", {"distance": 4.0})
        out_file = "/tmp/test_cadpilot_export.step"
        resp = self.rpc("export_cad", {"format": "step", "output_path": out_file})
        self.assertEqual(resp.get("jsonrpc"), "2.0")
        self.assertTrue(os.path.exists(out_file))

    def test_09_units_conversion(self):
        self.assertEqual(mm_to_cm(10.0), 1.0)
        self.assertEqual(cm_to_mm(1.0), 10.0)
        self.assertEqual(point_mm_to_cm([10.0, 20.0, 30.0]), [1.0, 2.0, 3.0])
        self.assertEqual(point_cm_to_mm([1.0, 2.0, 3.0]), [10.0, 20.0, 30.0])
        bbox = bounding_box_cm_to_mm([0.0, 0.0, 0.0], [4.23, 4.23, 0.4])
        self.assertEqual(bbox["dimensions"], [42.3, 42.3, 4.0])

    def test_10_structured_error_hints(self):
        exc = GeometryError(
            message="Impossible fillet",
            hint="Decrease radius to 1.0mm",
            tool="apply_fillet"
        )
        formatted = format_exception_for_agent(exc, tool_name="apply_fillet")
        self.assertEqual(formatted["code"], GEOMETRY_ERROR)
        self.assertEqual(formatted["data"]["hint"], "Decrease radius to 1.0mm")
        self.assertEqual(formatted["data"]["tool"], "apply_fillet")


if __name__ == "__main__":
    unittest.main()
