"""Agent Observation Parser & Entity Token Registry.

Parses intermediate JSON-RPC responses from the Fusion Bridge (or Mock Bridge)
and extracts structured sketches, profiles, bodies, cylindrical features, and
maintains token lineage across consecutive modeling operations.
"""

from typing import Dict, Any, List, Optional
from agent.state import (
    CADState,
    EntityRegistry,
    SketchEntity,
    ProfileEntity,
    BodyEntity,
    CylindricalFeatureEntity,
    FeatureRecord
)


class ObservationParser:
    """Parses tool call observations into the centralized EntityRegistry."""

    def __init__(self, registry: Optional[EntityRegistry] = None):
        self.registry = registry or EntityRegistry()

    @classmethod
    def from_state(cls, state: CADState) -> "ObservationParser":
        raw = state.get("entities", {})
        return cls(registry=EntityRegistry.from_dict(raw))

    @property
    def sketches(self) -> Dict[str, Dict[str, Any]]:
        return self.registry.sketches

    @property
    def bodies(self) -> Dict[str, Dict[str, Any]]:
        return self.registry.bodies

    @property
    def features(self) -> List[Dict[str, Any]]:
        return self.registry.features

    @property
    def feature_records(self) -> List[Dict[str, Any]]:
        return self.registry.features

    @property
    def token_lineage(self) -> Dict[str, List[str]]:
        return self.registry.token_lineage

    @property
    def active_sketch_id(self) -> Optional[str]:
        return self.registry.active_sketch_id

    @property
    def active_profile_id(self) -> Optional[str]:
        return self.registry.active_profile_id

    @property
    def active_body_id(self) -> Optional[str]:
        return self.registry.active_body_id

    @property
    def cylindrical_features(self) -> Dict[str, CylindricalFeatureEntity]:
        cyls: Dict[str, CylindricalFeatureEntity] = {}
        for b in self.registry.bodies.values():
            for c in b.get("cylindrical_features", []):
                face_tok = c.get("face_token", "")
                if face_tok:
                    cyls[face_tok] = CylindricalFeatureEntity(
                        face_token=face_tok,
                        radius_mm=float(c.get("radius_mm", 0.0)),
                        diameter_mm=float(c.get("diameter_mm", 0.0)),
                        origin_mm=list(c.get("origin_mm", [0.0, 0.0, 0.0])),
                        axis=list(c.get("axis", [0.0, 0.0, 1.0]))
                    )
        return cyls

    def update_state(self, state: CADState):
        state["entities"] = self.registry.to_dict()

    def parse_tool_result(self, tool: str, params: Dict[str, Any], result: Dict[str, Any]):
        """Parses the result of a tool call and updates entities & token lineage."""
        if not result or result.get("status") in ("error", "failed"):
            return

        if tool == "reset_design":
            self.registry = EntityRegistry()

        elif tool == "create_sketch":
            self._parse_sketch(params, result)

        elif tool == "extrude_profile":
            self._parse_extrude(params, result)

        elif tool == "cut_hole":
            self._parse_cut_hole(params, result)

        elif tool == "apply_fillet":
            self._parse_fillet(params, result)

        elif tool == "inspect_brep":
            self._parse_inspect_brep(result)

    def _parse_sketch(self, params: Dict[str, Any], result: Dict[str, Any]):
        sketch_id = result.get("sketch_id", "sketch_1")
        plane = params.get("plane", "xy")
        bbox = result.get("bounding_box", {})

        profiles: List[ProfileEntity] = []
        raw_profiles = result.get("profiles", [])
        if raw_profiles and isinstance(raw_profiles[0], dict):
            for p in raw_profiles:
                prof_id = p.get("profile_id", f"{sketch_id}:prof_{p.get('index', 0)}")
                prof_entity = ProfileEntity(
                    profile_id=prof_id,
                    index=int(p.get("index", 0)),
                    area_mm2=float(p.get("area_mm2", 0.0)),
                    centroid_mm=list(p.get("centroid_mm", [0.0, 0.0]))
                )
                profiles.append(prof_entity)
        elif "profile_ids" in result:
            for idx, pid in enumerate(result.get("profile_ids", [])):
                prof_entity = ProfileEntity(
                    profile_id=pid,
                    index=idx,
                    area_mm2=0.0,
                    centroid_mm=[0.0, 0.0]
                )
                profiles.append(prof_entity)

        sketch_entity = SketchEntity(
            sketch_id=sketch_id,
            plane=plane,
            profiles=profiles,
            bounding_box=bbox,
            total_area=sum(p.area_mm2 for p in profiles)
        )
        self.registry.sketches[sketch_id] = sketch_entity.to_dict()
        self.registry.active_sketch_id = sketch_id

        if profiles:
            self.registry.active_profile_id = profiles[0].profile_id

        # Record feature and token lineage
        feat_rec = FeatureRecord(
            feature_id=sketch_id,
            tool="create_sketch",
            params=params,
            input_tokens=[plane],
            output_tokens=[p.profile_id for p in profiles]
        )
        self.registry.features.append(feat_rec.to_dict())
        self.registry.token_lineage[sketch_id] = [p.profile_id for p in profiles]

    def _parse_extrude(self, params: Dict[str, Any], result: Dict[str, Any]):
        feat_id = result.get("feature_id", "extrude_1")
        body_ids = result.get("body_ids", ["body_1"])
        bbox = result.get("bounding_box", {})
        prof_id = params.get("profile_id", self.registry.active_profile_id or "all")

        for b_id in body_ids:
            if b_id not in self.registry.bodies:
                body_entity = BodyEntity(
                    body_id=b_id,
                    is_solid=True,
                    bounding_box=bbox
                )
                self.registry.bodies[b_id] = body_entity.to_dict()
            else:
                self.registry.bodies[b_id]["bounding_box"] = bbox

        if body_ids:
            self.registry.active_body_id = body_ids[0]

        feat_rec = FeatureRecord(
            feature_id=feat_id,
            tool="extrude_profile",
            params=params,
            input_tokens=[prof_id],
            output_tokens=body_ids
        )
        self.registry.features.append(feat_rec.to_dict())
        self.registry.token_lineage[prof_id] = [feat_id] + body_ids
        for b_id in body_ids:
            if b_id not in self.registry.token_lineage:
                self.registry.token_lineage[b_id] = []
            if prof_id not in self.registry.token_lineage[b_id]:
                self.registry.token_lineage[b_id].append(prof_id)

    def _parse_cut_hole(self, params: Dict[str, Any], result: Dict[str, Any]):
        feat_id = result.get("feature_id", "hole_1")
        face_token = result.get("face_token")
        bbox = result.get("bounding_box", {})
        active_b_id = self.registry.active_body_id

        if active_b_id and active_b_id in self.registry.bodies:
            body_dict = self.registry.bodies[active_b_id]
            body_dict["bounding_box"] = bbox
            body_dict["face_count"] = body_dict.get("face_count", 6) + 1
            if face_token:
                diam = float(params.get("diameter", result.get("radius_mm", 0.0) * 2.0))
                radius = float(result.get("radius_mm", diam / 2.0))
                cyl_dict = {
                    "face_token": face_token,
                    "radius_mm": radius,
                    "diameter_mm": diam,
                    "origin_mm": list(params.get("position", [0.0, 0.0])) + [0.0],
                    "axis": [0.0, 0.0, 1.0]
                }
                if "cylindrical_features" not in body_dict:
                    body_dict["cylindrical_features"] = []
                body_dict["cylindrical_features"].append(cyl_dict)

        face_target = params.get("face", "xy")
        out_tokens = [face_token] if face_token else [feat_id]
        feat_rec = FeatureRecord(
            feature_id=feat_id,
            tool="cut_hole",
            params=params,
            input_tokens=[face_target],
            output_tokens=out_tokens
        )
        self.registry.features.append(feat_rec.to_dict())
        if active_b_id:
            if active_b_id not in self.registry.token_lineage:
                self.registry.token_lineage[active_b_id] = []
            self.registry.token_lineage[active_b_id].append(face_token or feat_id)

    def _parse_fillet(self, params: Dict[str, Any], result: Dict[str, Any]):
        feat_id = result.get("feature_id", "fillet_1")
        target = params.get("target", "all_vertical_edges")
        edges_filleted = result.get("edges_filleted", 4)
        active_b_id = self.registry.active_body_id

        if active_b_id and active_b_id in self.registry.bodies:
            body_dict = self.registry.bodies[active_b_id]
            body_dict["face_count"] = body_dict.get("face_count", 6) + edges_filleted

        feat_rec = FeatureRecord(
            feature_id=feat_id,
            tool="apply_fillet",
            params=params,
            input_tokens=[str(target)],
            output_tokens=[feat_id]
        )
        self.registry.features.append(feat_rec.to_dict())
        if active_b_id:
            if active_b_id not in self.registry.token_lineage:
                self.registry.token_lineage[active_b_id] = []
            self.registry.token_lineage[active_b_id].append(feat_id)

    def _parse_inspect_brep(self, result: Dict[str, Any]):
        for b_data in result.get("bodies", []):
            b_id = b_data.get("body_id", "body_1")
            cyl_list: List[CylindricalFeatureEntity] = []
            for c in b_data.get("cylindrical_features", []):
                cyl_entity = CylindricalFeatureEntity(
                    face_token=c.get("face_token", ""),
                    radius_mm=float(c.get("radius_mm", 0.0)),
                    diameter_mm=float(c.get("diameter_mm", 0.0)),
                    origin_mm=list(c.get("origin_mm", [0.0, 0.0, 0.0])),
                    axis=list(c.get("axis", [0.0, 0.0, 1.0]))
                )
                cyl_list.append(cyl_entity)

            body_entity = BodyEntity(
                body_id=b_id,
                is_solid=bool(b_data.get("is_solid", True)),
                volume_mm3=float(b_data.get("volume_mm3", 0.0)),
                surface_area_mm2=float(b_data.get("surface_area_mm2", 0.0)),
                face_count=int(b_data.get("face_count", 6)),
                edge_count=int(b_data.get("edge_count", 12)),
                vertex_count=int(b_data.get("vertex_count", 8)),
                bounding_box=dict(b_data.get("bounding_box", {})),
                cylindrical_features=cyl_list
            )
            self.registry.bodies[b_id] = body_entity.to_dict()

            # Record token lineage for cylindrical faces
            self.registry.token_lineage[b_id] = [c.face_token for c in cyl_list]

        if result.get("bodies"):
            self.registry.active_body_id = result["bodies"][0].get("body_id", "body_1")
