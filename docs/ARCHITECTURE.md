# CADPilot Bridge: Architecture & Technical Foundations

## 1. The Main-Thread Concurrency Model

### The Problem
Autodesk Fusion 360's internal modeling engine (ASM / ShapeManager) is strictly single-threaded. Calling `adsk.fusion.*` APIs from any thread other than Fusion's main UI thread triggers:
`RuntimeError: 2 : InternalValidationError : ...` or an outright crash.

However, an AI agent operates outside Fusion and communicates via network requests. If the network server runs on the main thread, Fusion will lock up and block incoming socket connections while modeling or running modal dialogs.

### The Solution: Background Server + `CustomEvent` Handshake
```
 +------------------+                +-------------------------+
 |   LangGraph AI   |                |     Autodesk Fusion     |
 |   Agent Client   |                |                         |
 +--------+---------+                +------------+------------+
          |                                       |
          | HTTP POST (JSON-RPC)                  |
          v                                       |
   +--------------+                               |
   | Daemon HTTP  |                               |
   | Server Thread|                               |
   +------+-------+                               |
          |                                       |
          | 1. Enqueue request + Event            |
          | 2. app.fireCustomEvent(name, req_id)  |
          +-------------------------------------> | (Fires event into
          |                                       |  Fusion event queue)
          | 3. threading.Event.wait(timeout=30s)  |
          |    (Blocks only worker thread)        v
          |                               +---------------+
          |                               | CustomEvent   |
          |                               | Handler       |
          |                               | (MAIN THREAD) |
          |                               +-------+-------+
          |                                       |
          |                                       | 4. Execute tool
          |                                       |    (create_sketch,
          |                                       |     extrude, etc.)
          |                                       v
          | 5. Store result / error               |
          |    + threading.Event.set()            |
          | <-------------------------------------+
          v
   +--------------+
   | Daemon HTTP  |
   | Server Thread|
   +------+-------+
          |
          | 6. Return HTTP 200 (JSON-RPC response)
          v
 +--------+---------+
 |   LangGraph AI   |
 |   Agent Client   |
 +------------------+
```

### Why this works:
1. **Zero main thread lag:** The HTTP listener runs on standard Python `threading`.
2. **Safe modeling:** Fusion triggers the `CustomEventHandler.notify()` callback within its main application event loop when it is safe to interact with the active document.
3. **Deterministic timeouts:** If Fusion takes longer than a specified timeout (default 30s), the HTTP thread times out safely and returns an error without hanging the agent.

---

## 2. Unit System Isolation

Autodesk Fusion's underlying database stores all spatial coordinates in **centimetres (cm)** and angles in **radians**.
Engineers, CAD files, and LLM training data uniformly use **millimeters (mm)** and **degrees**.

Mixing units across various endpoints is one of the most common causes of silent CAD scaling bugs (e.g. 10x too large or 10x too small).

### Policy
- **Centralized Conversion:** Only `addin/core/units.py` is allowed to perform conversions.
- **Conversion Rule:**
  - mm to cm: `val / 10.0`
  - cm to mm: `val * 10.0`
  - deg to rad: `math.radians(val)`
  - rad to deg: `math.degrees(val)`
- **External Contract:** 100% of input parameters and 100% of returned bounding boxes/centroids are in **millimeters**.

---

## 3. Viva Preparation & Architectural Defense

### Q1: Why is the main-thread event pattern needed?
> **Answer:** Fusion 360's core geometry engine (Autodesk ShapeManager) and object model are thread-hostile. Direct API calls from worker threads violate internal state assertions, leading to hard segfaults or silent database corruption. By decoupling network reception onto a daemon thread and dispatching execution into Fusion's main event queue via `adsk.core.Application.fireCustomEvent`, we preserve complete thread safety while maintaining an asynchronous, non-blocking HTTP bridge.

### Q2: Why does the agent get structured observations instead of one-shot scripts?
> **Answer:** One-shot script execution (e.g. asking an LLM to generate a 100-line Python script that runs inside Fusion) fails abruptly on any minor geometric incompatibility, leaving the agent with no intermediate state or recovery mechanism. With a step-by-step tool bridge:
> 1. The agent observes intermediate geometry (bounding boxes, profile IDs, face tokens) after each step.
> 2. Failures are localized to a single operation (e.g. fillet radius too large).
> 3. The agent can adjust parameters dynamically based on actual geometric state rather than hallucinated coordinates.

### Q3: How do errors become useful feedback for retries?
> **Answer:** Raw Fusion errors (`RuntimeError: 2 : InternalValidationError`) contain zero actionable geometric reasoning for an LLM. Our bridge catches native exceptions and translates them into structured JSON-RPC errors with a dedicated `data.hint` property (e.g., *"Fillet radius 5mm exceeds adjacent wall thickness 2mm. Recommended radius: <= 1.0mm"*). LangGraph feeds this hint directly back into the LLM prompt, enabling closed-loop geometric self-correction.

