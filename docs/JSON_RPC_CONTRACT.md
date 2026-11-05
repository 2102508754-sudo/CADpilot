# CADPilot: JSON-RPC 2.0 Contract Specification

**Version:** 1.0.0  
**Transport:** HTTP POST `http://127.0.0.1:9090/`  
**Content-Type:** `application/json`  
**Shared Between:** Bridge Owner (You), Agent Loop (Abhijit), Evaluator (Bibhukesh)

---

## 1. Overview & Conventions

1. **Protocol:** Strict [JSON-RPC 2.0](https://www.jsonrpc.org/specification). Every request must include `"jsonrpc": "2.0"`, `"method"`, `"params"`, and `"id"`.
2. **Units:** All linear dimensions are in **millimeters (mm)**. All angular dimensions are in **degrees (°)**.
3. **Coordinates:** `[x, y, z]` world coordinate frame (Fusion default: Z is up or Y is up depending on user settings, default plane is `xy`).
4. **Error Transparency:** Errors never return raw stack traces. They provide a standardized error code, a human-readable message, and a machine-interpretable `hint` explaining how an LLM agent should modify its call.

---

## 2. Standard Schema

### Request Format
```json
{
  "jsonrpc": "2.0",
  "method": "<method_name>",
  "params": { ... },
  "id": 1
}
```

### Success Response Format
```json
{
  "jsonrpc": "2.0",
  "result": {
    "status": "success",
    ...
  },
  "id": 1
}
```

### Structured Error Response Format
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32002,
    "message": "Fillet radius 10.0mm exceeds maximum allowable geometry limit.",
    "data": {
      "hint": "Reduce fillet radius to smaller than adjacent wall thickness (e.g. <= 2.0mm).",
      "tool": "apply_fillet",
      "details": { ... }
    }
  },
  "id": 1
}
```

---

## 3. Error Code Catalog

| Code | Label | Meaning & Agent Recovery |
|---|---|---|
| `-32700` | `PARSE_ERROR` | Invalid JSON received. Format payload properly. |
| `-32600` | `INVALID_REQUEST` | Missing `jsonrpc`, `method`, or invalid schema. |
| `-32601` | `METHOD_NOT_FOUND` | Method does not exist on bridge. Check method name. |
| `-32602` | `INVALID_PARAMS` | Missing required param or invalid type. Check doc. |
| `-32603` | `INTERNAL_ERROR` | Fusion internal crash or unexpected failure. |
| `-32000` | `NO_ACTIVE_DESIGN` | No active Fusion document. Call `reset_design`. |
| `-32001` | `OPERATION_TIMEOUT` | Fusion thread did not reply in time. |
| `-32002` | `GEOMETRY_ERROR` | Geometric failure (self-intersection, impossible fillet, non-manifold). See `hint`. |
| `-32003` | `ENTITY_NOT_FOUND` | Specified profile/edge/face ID does not exist. Check previous tool output. |
| `-32004` | `EXPORT_FAILED` | File export path could not be written. |

---

## 4. Method Catalog

### 4.1 System Methods

#### `ping`
Check if the bridge server and Fusion 360 main thread are alive and responsive.
* **Params:** none (`{}`)
* **Result:**
  ```json
  {
    "status": "ok",
    "fusion_version": "2.0.x",
    "bridge_mode": "fusion" // or "mock"
  }
  ```

#### `reset_design`
Clears the active design document or creates a fresh untitled document. Essential for clean agent retries.
* **Params:**
  * `save_existing` (boolean, optional, default `false`)
* **Result:**
  ```json
  {
    "status": "success",
    "message": "Design reset cleanly. Document is ready."
  }
  ```

---

### 4.2 Geometry & Feature Methods

#### `create_sketch`
Creates a sketch on a primary plane (`xy`, `xz`, `yz`) or an existing planar face. Creates 2D shapes (rectangles, circles, lines).
* **Params:**
  * `plane`: `"xy"` | `"xz"` | `"yz"` | `"<face_token>"`
  * `shapes`: Array of shape objects:
    * **Centered Rectangle:**
      `{"type": "rectangle", "center": [x, y], "width": float, "height": float}`
    * **Corner Rectangle:**
      `{"type": "rectangle", "corner1": [x1, y1], "corner2": [x2, y2]}`
    * **Circle:**
      `{"type": "circle", "center": [x, y], "diameter": float}`
* **Result:**
  ```json
  {
    "status": "success",
    "sketch_id": "sketch_1",
    "profiles": [
      {
        "profile_id": "sketch_1:prof_0",
        "area_mm2": 1789.29,
        "centroid_mm": [0.0, 0.0]
      }
    ],
    "bounding_box": {
      "min": [-21.15, -21.15, 0.0],
      "max": [21.15, 21.15, 0.0],
      "dimensions": [42.3, 42.3, 0.0]
    }
  }
  ```

#### `extrude_profile`
Extrudes a sketch profile to create a solid body or cut into an existing body.
* **Params:**
  * `profile_id`: (string) e.g. `"sketch_1:prof_0"` or `"all"`
  * `distance`: (float, mm) positive or negative extrusion distance
  * `operation`: (string, optional, default `"new_body"`) `"new_body"` | `"join"` | `"cut"`
* **Result:**
  ```json
  {
    "status": "success",
    "feature_id": "extrude_1",
    "body_ids": ["body_1"],
    "bounding_box": {
      "min": [-21.15, -21.15, 0.0],
      "max": [21.15, 21.15, 4.0],
      "dimensions": [42.3, 42.3, 4.0]
    }
  }
  ```

#### `cut_hole`
Creates a round hole or pattern of holes through or to a depth on a target face.
* **Params:**
  * `face`: (string) target planar face token (e.g. `"body_1:face_top"` or `"xy"`)
  * `position`: (array of 2 floats) `[x, y]` on face plane in mm
  * `diameter`: (float, mm) hole diameter
  * `depth`: (float or string, optional, default `"through"`) depth in mm, or `"through"`
* **Result:**
  ```json
  {
    "status": "success",
    "feature_id": "hole_1",
    "hole_count": 1,
    "bounding_box": {
      "min": [-21.15, -21.15, 0.0],
      "max": [21.15, 21.15, 4.0],
      "dimensions": [42.3, 42.3, 4.0]
    }
  }
  ```

#### `apply_fillet`
Applies a round fillet to specified edges or all exterior vertical edges.
* **Params:**
  * `target`: `"all_vertical_edges"` | `"body_1:edge_0"` | array of edge tokens
  * `radius`: (float, mm) fillet radius
* **Result:**
  ```json
  {
    "status": "success",
    "feature_id": "fillet_1",
    "radius_mm": 2.0,
    "edges_filleted": 4
  }
  ```
* **Failure Example:** If radius >= wall thickness, returns `-32002` with suggestion to reduce radius.

---

### 4.3 Inspection & Export Methods

#### `inspect_brep`
Extracts geometric and topological B-Rep features for verification by Bibhukesh's evaluation pipeline.
* **Params:**
  * `target_body`: (string, optional, default `"all"`)
* **Result:**
  ```json
  {
    "status": "success",
    "body_count": 1,
    "bodies": [
      {
        "body_id": "body_1",
        "volume_mm3": 6842.1,
        "surface_area_mm2": 4120.5,
        "face_count": 10,
        "edge_count": 24,
        "vertex_count": 16,
        "bounding_box": {
          "min": [-21.15, -21.15, 0.0],
          "max": [21.15, 21.15, 4.0],
          "dimensions": [42.3, 42.3, 4.0]
        }
      }
    ]
  }
  ```

#### `export_cad`
Exports the current 3D design to STEP, STL, or F3D file on disk.
* **Params:**
  * `format`: `"step"` | `"stl"` | `"f3d"`
  * `output_path`: (string) absolute file path
* **Result:**
  ```json
  {
    "status": "success",
    "format": "step",
    "output_path": "/path/to/exported_part.step",
    "file_size_bytes": 14200
  }
  ```

