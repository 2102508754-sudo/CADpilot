# CADPilot: Fusion 360 Bridge

The **Fusion Bridge** is the execution engine for CADPilot. It connects an AI agent (e.g. LangGraph loop) to Autodesk Fusion 360 via a lightweight, zero-dependency JSON-RPC 2.0 interface.

---

## 📅 Roadmap & Milestones (Nov 3 – Nov 27)

| Status | Phase | Dates | Milestone / Focus |
|---|---|---|---|
| ✅ | **Phase 0** | Nov 3–5 | Environment setup, Add-In skeleton, stdlib HTTP transport |
| ✅ | **Phase 1** | Nov 4–8 | Main-thread `CustomEvent` dispatch, JSON-RPC contract, mock bridge |
| 🟡 | **Phase 2** | Nov 8–15 | Tools (`sketch`, `extrude`, `cut_hole`, `fillet`, `export`, `inspect_brep`) — code written, mock-tested; live Fusion testing pending |
| 🟡 | **Phase 3** | Nov 13–17 | Structured errors + reflection done in code; live `adsk` testing + timeout guards pending |
| ⬜ | **Phase 4** | Nov 15–20 | LangGraph integration (with Abhijit), NEMA 17 test prompt |
| ⬜ | **Phase 5** | Nov 18–24 | Part families (Mounting plate, L-bracket, Standoff) |
| ⬜ | **Phase 6** | Nov 20–25 | 30-prompt evaluation & one-shot baseline (with Bibhukesh) |
| ⬜ | **Phase 7** | Nov 25–27 | Code freeze, report, viva prep |

---

## 🗓️ Distributed Day-Wise Schedule (Nov 3 – Nov 27)

> [!CAUTION]
> **Status as of Nov 11:** Jaidev (Bridge) and Abhijit (Agent Core) are **ahead of schedule** — all code for Phases 0–2 is written and tested on mock. However, **Bibhukesh has ZERO code in the repo**. All his Phase 0–2 items (benchmark prompts, Streamlit UI, validation engine) are outstanding. Nov 12–13 are designated as catch-up days. If Bibhukesh does not deliver by Nov 14, Phases 5–6 evaluation is at risk.

### 👥 Team Ownership Breakdown
* **Jaidev Basandrai (Fusion Bridge):** Fusion Add-in, stdlib HTTP JSON-RPC server, main-thread synchronization (`CustomEvent`), unit isolation (`units.py`), structured error wrapping (`errors.py`), mock bridge server, live Fusion tool implementations, CAD export.
* **Abhijit Saha (Agent Core):** LangGraph state machine, Natural Language Spec Extractor, Feasibility Checker, CAD Sequence Planner, tool execution dispatch, closed-loop self-correction reasoning.
* **Bibhukesh Medhi (Validation, Reflection & UI):** B-Rep validation metrics (`inspect_brep`), geometric checking algorithms (bounding box, volume, hole count, edge clearance), 30-prompt evaluation suite, one-shot LLM baseline comparison, Streamlit front-end.

---

### Phase 0 & Phase 1: Foundations & Mock Bridge (Nov 3 – Nov 8)

> [!NOTE]
> **Audit (Nov 11):** Jaidev & Abhijit completed all Phase 0–1 tasks. Bibhukesh's items are unverified (no code in repo). Abhijit's agent core was merged as a single PR covering all 5 nodes; Phase 0–1 agent tasks are marked done accordingly.

| Date | Lead | Jaidev Basandrai (Bridge) | Abhijit Saha (Agent Core) | Bibhukesh Medhi (Validation & UI) | Milestone |
|---|---|---|---|---|---|
| **Nov 3** | All | - [x] Verify Fusion environment, create Add-in skeleton, test palette logging, select stdlib HTTP transport. | - [x] Set up LangGraph environment, define initial Agent State schema (`CADState`, `TaskSpec`). | - [ ] Survey mechanical spec formats, define B-Rep verification criteria and tolerance thresholds. | - [ ] Add-in skeleton boots cleanly |
| **Nov 4** | All | - [x] Design daemon HTTP server thread and `CustomEvent` main-thread synchronization model. | - [x] Draft prompt templates for Natural Language Spec Extractor (dimensions, hole patterns, fillets). | - [ ] Specify `inspect_brep` schema with Jaidev (volume, bounding boxes, cylindrical hole features). | - [ ] Architecture agreement |
| **Nov 5** | All | - [x] Define shared JSON-RPC 2.0 contract (`docs/JSON_RPC_CONTRACT.md`); implement `ping` and `reset_design`. | - [x] Implement LangGraph Node 1: Spec Extractor (parsing natural language into structured geometric constraints). | - [ ] Build ground-truth validation criteria (volume tolerance %, hole center coordinates). | - [ ] Contract published |
| **Nov 6** | Jaidev + Abhijit | - [x] Implement centralized `units.py` (cm $\leftrightarrow$ mm) and `errors.py` structured error hierarchy. | - [x] Implement LangGraph Node 2: Feasibility Pre-Flight Checker (detecting geometric contradictions). | - [ ] Draft first 10 prompts of the benchmark dataset (flat mounting plates: NEMA 17, Raspberry Pi, etc.). | - [ ] Feasibility checks active |
| **Nov 7** | Jaidev + Abhijit | - [x] Build stateful `mock_bridge.py` (simulating sketches, bodies, holes, fillets, and bounding boxes). | - [x] Implement LangGraph Node 3: CAD Sequence Planner (generating ordered tool calls). | - [ ] Build standalone verification rule engine for bounding box and hole count assertions. | - [ ] Mock engine functional |
| **Nov 8** | Jaidev + Abhijit | - [x] Release & validate Mock Bridge and test client CLI (`client/test_client.py`). Deliver to team. | - [x] Wire LangGraph Tool Execution Node to call `CADPilotClient` pointing to Mock Bridge. | - [ ] Connect validation harness to Mock Bridge's `inspect_brep` output; verify metric calculations. | - [ ] 🎯 **Mock Bridge Released** |

---

### Phase 2: Native Tool Implementation & Initial Agent Loop (Nov 9 – Nov 14)

> [!IMPORTANT]
> **Audit (Nov 11):** Jaidev's native tool CODE for ALL 6 tools was written in the initial commit but has **NOT been tested against a live Fusion 360 instance** — only against the mock bridge. Abhijit's agent nodes are all complete and tested on mock. Bibhukesh has NO code in the repo. Nov 9–11 Jaidev items marked [x] for "code written"; they need live Fusion testing in Phase 4. Abhijit's Nov 9–11 items are done (agent loop fully functional on mock).

| Date | Lead | Jaidev Basandrai (Bridge) | Abhijit Saha (Agent Core) | Bibhukesh Medhi (Validation & UI) | Milestone |
|---|---|---|---|---|---|
| **Nov 9** | Jaidev + Abhijit | - [x] Implement native `create_sketch` in Fusion (rectangles, circles, plane selection) and verify profile output. | - [x] Implement agent observation parser (storing sketch IDs and profile tokens into LangGraph state). | - [ ] Build Streamlit UI wireframe (prompt input, step-by-step progress monitor, 3D placeholder). | - [ ] `create_sketch` tested |
| **Nov 10** | Jaidev + Abhijit | - [x] Implement native `extrude_profile` (distance, new_body vs cut vs join) and bounding box updates. | - [x] Wire basic end-to-end loop (Prompt $\rightarrow$ Spec $\rightarrow$ Plan $\rightarrow$ Sketch $\rightarrow$ Extrude) on Mock Bridge. | - [ ] Draft benchmark prompts 11–20 (90-degree L-brackets with gussets & fillets). | - [ ] Base solid generation works |
| **Nov 11** | Jaidev + Abhijit | - [x] Implement native `cut_hole` (planar face selection, circular cut extrusions, through/blind depths). | - [x] Add multi-hole pattern planner (linear arrays, pitch-circle diameters, symmetric bolt patterns). | - [ ] Implement `inspect_brep` cylindrical feature analyzer (extracting hole radii, origins, and axes). | - [ ] Hole patterns functional |
| **Nov 12** | **Bibhukesh** | - [x] ~~Implement native `apply_fillet`~~ (already written). **TEST on live Fusion if available.** | - [x] ~~Update state schema~~ (already done in merged PR). **Help Bibhukesh onboard.** | - [ ] **🔴 CATCH-UP DAY 1:** Draft first 15 benchmark prompts + build Streamlit UI wireframe. | - [ ] Bibhukesh catches up |
| **Nov 13** | **Bibhukesh** | - [x] ~~Implement native `export_cad`~~ (already written). **Write integration tests for fillet + export flows.** | - [x] ~~Add Export Node~~ (already done). **Write agent integration test for full NEMA 17 on mock.** | - [ ] **🔴 CATCH-UP DAY 2:** Complete prompts 16–30 + implement validation rule engine (volume, hole count checks). | - [ ] Benchmark prompts ready |
| **Nov 14** | **Jaidev** | - [x] ~~Implement native `inspect_brep`~~ (already written). **Verify all 6 tools pass standalone Python client tests.** | - [x] Execute full Happy Path loop on Mock Bridge for NEMA 17 plate sequence end-to-end. | - [ ] Connect validation harness to Mock Bridge `inspect_brep` output; verify metric calculations. | - [ ] 🎯 **Full Tool Suite Scaffolded** |

---

### Phase 3: Error Handling & Closed-Loop Self-Correction (Nov 15 – Nov 17)

> [!NOTE]
> **Audit (Nov 11):** Jaidev's `errors.py` with full structured error hierarchy + hints is already implemented. Abhijit's `reflection.py` node is already implemented and tested (self-correction works on mock). Remaining: test against REAL `adsk` exceptions in live Fusion, harden `reset_design`, and build Bibhukesh's error-injection test suite.

| Date | Lead | Jaidev Basandrai (Bridge) | Abhijit Saha (Agent Core) | Bibhukesh Medhi (Validation & UI) | Milestone |
|---|---|---|---|---|---|
| **Nov 15** | **Jaidev** | - [x] ~~Wrap `adsk` exceptions into structured errors~~ (already in `errors.py`). **Test against real `adsk` exceptions in live Fusion.** | - [x] ~~Implement Reflection Node~~ (already in `reflection.py`). **Tune self-correction heuristics on mock failures.** | - [ ] Implement retry counter tracking ($\le 3$ attempts) and error taxonomy categorization in evaluation harness. | - [ ] Structured hints active |
| **Nov 16** | **Jaidev** | - [ ] Harden `reset_design` for clean post-failure recovery; implement 30-second main-thread timeout guards. | - [ ] Add parameter-level self-correction heuristics (e.g. automatically decrementing fillet radius on error). | - [ ] Build test suite for deliberate error injection (oversized fillets, out-of-bounds hole coordinates). | - [ ] Fault recovery verified |
| **Nov 17** | **Abhijit** | - [ ] Test bridge robustness against repeated intentionally malformed calls and sudden resets. | - [ ] Verify LangGraph autonomous recovery (agent corrects bad fillet on 2nd attempt without user input). | - [ ] Integrate reflection logs and live retry status into the Streamlit UI dashboard. | - [ ] 🎯 **Self-Correction Working** |

---

### Phase 4: Live Bridge Integration & Primary Prompt Test (Nov 18 – Nov 20)

| Date | Lead | Jaidev Basandrai (Bridge) | Abhijit Saha (Agent Core) | Bibhukesh Medhi (Validation & UI) | Milestone |
|---|---|---|---|---|---|
| **Nov 18** | **Jaidev + Abhijit** | - [ ] Install live Add-In into Autodesk Fusion 360; connect Abhijit's agent to the live Fusion session. | - [ ] Swap mock bridge endpoint for live Fusion bridge; identify and resolve parameter/schema mismatches. | - [ ] Validate live `inspect_brep` outputs against ground-truth mechanical drawings. | - [ ] Live bridge connected |
| **Nov 19** | **All** | - [ ] Fix live Fusion sketch plane orientation and face token mapping during consecutive operations. | - [ ] Refine system prompts and planner templates based on live Fusion modeling behaviors. | - [ ] Run and log first live autonomous execution of the NEMA 17 plate (42.3mm, 22mm pilot, 4x M3). | - [ ] Live NEMA 17 plate built |
| **Nov 20** | **All** | - [ ] Stabilize add-in lifecycle (clean start, stop, reconnection after agent network disconnects). | - [ ] Freeze LangGraph agent workflow v1.0; document state transitions and decision logic. | - [ ] Inspect exported STEP and STL files of NEMA 17 plate in FreeCAD/PrusaSlicer for geometric integrity. | - [ ] 🎯 **Live End-to-End Success** |

---

### Phase 5: Part Family Expansion (Nov 21 – Nov 22)

| Date | Lead | Jaidev Basandrai (Bridge) | Abhijit Saha (Agent Core) | Bibhukesh Medhi (Validation & UI) | Milestone |
|---|---|---|---|---|---|
| **Nov 21** | **Jaidev + Abhijit** | - [ ] Add bridge support for 90-degree L-bracket operations (multi-face sketches, gusset features). | - [ ] Build agent planning recipes for L-brackets with corner fillets and mounting slots. | - [ ] Execute evaluation batch on Part Family 1 (10 Mounting Plate prompts); log retry counts. | - [ ] Part Family 1 benchmarked |
| **Nov 22** | **Bibhukesh + Abhijit** | - [ ] Add bridge support for cylindrical standoffs / spacers (revolve/circular extrusion and tapped bores). | - [ ] Build agent planning recipes for cylindrical spacers; handle parameter edge cases. | - [ ] Execute evaluation batch on Part Family 2 (10 L-Bracket prompts); log retry counts. | - [ ] Part Family 2 benchmarked |

---

### Phase 6: 30-Prompt Evaluation & Baseline Comparison (Nov 23 – Nov 24)

| Date | Lead | Jaidev Basandrai (Bridge) | Abhijit Saha (Agent Core) | Bibhukesh Medhi (Validation & UI) | Milestone |
|---|---|---|---|---|---|
| **Nov 23** | **Bibhukesh** | - [ ] Monitor live bridge during batch runs; hotfix geometric edge cases or timing delays. | - [ ] Implement and execute the One-Shot LLM Baseline (generating raw Python scripts in one shot). | - [ ] Run the full 30-prompt evaluation suite on CADPilot (recording success rate, retries, time). | - [ ] 30 prompts executed |
| **Nov 24** | **Bibhukesh** | - [ ] Extract bridge log statistics (average tool execution time, error frequency by tool type). | - [ ] Compile baseline vs agent comparison metrics (success rate, fatal error rate, human interventions). | - [ ] Generate final evaluation graphs, comparison charts, and statistical summary tables for report. | - [ ] 🎯 **Evaluation Completed** |

---

### Phase 7: Code Freeze, Final Report & Submission (Nov 25 – Nov 27)

| Date | Lead | Jaidev Basandrai (Bridge) | Abhijit Saha (Agent Core) | Bibhukesh Medhi (Validation & UI) | Milestone |
|---|---|---|---|---|---|
| **Nov 25** | **All** | - [ ] **Code Freeze**: Clean up add-in code, verify installer scripts on macOS & Windows, write bridge setup guide. | - [ ] **Code Freeze**: Package agent core repository, clean up config files and dependencies, lock prompt templates. | - [ ] **Code Freeze**: Finalize Streamlit app, package benchmark evaluation data and metrics. | - [ ] 🔒 **Code Frozen** |
| **Nov 26** | **All** | - [ ] Draft report sections: Architecture, Main-thread `CustomEvent` synchronization, Unit conversion, Error hints. | - [ ] Draft report sections: Agentic workflow, LangGraph state machine, Feasibility checks, Planning algorithms. | - [ ] Draft report sections: Evaluation results, B-Rep reflection metrics, Baseline comparison, Front-end UI. | - [ ] Report draft complete |
| **Nov 27** | **All** | - [ ] Record 3-minute video demo of live Fusion modeling; review final report; assemble submission archive. | - [ ] Review and proofread report; verify agent reproducibility; finalize repo README. | - [ ] Compile final report PDF with tables and diagrams; submit project deliverables. | - [ ] 🚀 **Final Submission** |

---

### Post-Submission: Viva Preparation (Nov 28 – Early Dec)

* [ ] **Jaidev Basandrai:** Prepare to defend the 3 bridge architectural decisions:
  1. *Why the main-thread event pattern is mandatory* (ASM single-threaded kernel vs worker thread crash prevention).
  2. *Why step-by-step structured observations are superior to one-shot scripts* (closed-loop inspection vs blind hallucination).
  3. *How errors become actionable feedback for retries* (translating C++ exceptions into structured `hint`s for LLM recovery).
* [ ] **Abhijit Saha:** Prepare to defend the agentic loop, LangGraph state machine transitions, and self-correction autonomy.
* [ ] **Bibhukesh Medhi:** Prepare to defend the evaluation methodology, B-Rep reflection rigor, and metric comparisons against one-shot LLMs.

---

## 🏗️ Architecture & Core Innovations

1. **Main-Thread Event Loop Bridge**: Fusion's C++ core forbids calling `adsk.fusion` APIs from worker threads. We host a standard-library `http.server` in a daemon thread. When a request arrives, it fires a Fusion `CustomEvent`. Fusion processes the tool call on its **main UI thread**, stores the result, and wakes the waiting HTTP thread.
2. **Zero-Dependency Transport**: Uses only Python standard library (`http.server`, `json`, `threading`). No fragile `pip install fastapi` into Fusion's bundled Python runtime.
3. **Strict mm Units**: Fusion internally operates in **centimetres (cm)**. All agent inputs and outputs are strictly in **millimeters (mm)**. Unit conversions are isolated to `addin/core/units.py`.
4. **Structured Error Feedback for LLMs**: Instead of unhelpful C++ stack traces (`RuntimeError: 2 : InternalValidationError`), exceptions are mapped into JSON-RPC errors with a structured `hint` field so LangGraph can self-correct on the next iteration.
5. **Standalone Mock Bridge**: Allows agent teammates (Abhijit & Bibhukesh) to develop and benchmark without needing Fusion 360 open.

---

## 🤖 Agent Core Architecture (LangGraph State Machine)

The **Agent Core** (implemented by Abhijit Saha, merged in `agent/`) executes the closed-loop agentic cycle: **Perceive $\rightarrow$ Reason $\rightarrow$ Plan $\rightarrow$ Act $\rightarrow$ Reflect**.

```
  [START]
     │
     ▼
  [spec_extractor]       Node 1: Parses natural-language prompt into structured TaskSpec
     │
     ▼
  [feasibility_checker]  Node 2: Pre-flight checks (boundary containment, hole clearance, fillet limits)
     │
     ├──(infeasible)────────────────────────┐
     │                                      ▼
     ▼ (feasible)                      [reflector] (Node 5: Error diagnosis & parameter self-correction)
  [planner]              Node 3: CAD plan   ▲      │
     │                   (ordered tools)    │      ├──(retries left <= 3)──┐
     ▼                                      │      │                       │
  [tool_executor]        Node 4: Dispatches ┘      ▼ (retries exhausted)   │
     │                   calls via client         [END (failed)]           │
     ├──(bridge error: -32002)─────────────────────────────────────────────┘
     │
     ▼ (success & export)
  [END (completed)]
```

### Core Nodes:
1. **`spec_extractor` (`agent/nodes/spec_extractor.py`)**: Normalizes raw user prompts into a standardized `TaskSpec` (part type, outer dimensions, hole positions/diameters, fillet radii, export format/path).
2. **`feasibility_checker` (`agent/nodes/feasibility_checker.py`)**: Performs physical sanity checks before calling Fusion (e.g., verifying holes are entirely inside the plate, checking for hole-to-hole collisions, and ensuring fillet radius $\le$ wall thickness).
3. **`planner` (`agent/nodes/planner.py`)**: Synthesizes the validated spec into an ordered sequence of JSON-RPC tool calls matching [`docs/JSON_RPC_CONTRACT.md`](file:///Users/jaidevbasandrai/Desktop/ALL/AI%20project/docs/JSON_RPC_CONTRACT.md).
4. **`tool_executor` (`agent/nodes/executor.py`)**: Sequentially executes calls against the bridge via `CADPilotClient`, capturing intermediate bounding boxes, body IDs, and profile tokens into state observations.
5. **`reflection` (`agent/nodes/reflection.py`)**: Diagnoses errors returned by the bridge (`-32002`), reads `error.data.hint`, decrements the retry budget ($\le 3$ retries), adjusts invalid parameters, and triggers replanning.

### Dual Engine Support:
* **Native LangGraph**: Compiles `langgraph.graph.StateGraph` if `langgraph` is installed in the Python environment.
* **Zero-Dependency Fallback**: Transparently runs `StandaloneCADStateMachine` using Python standard library if LangGraph is not installed. Both execute the exact same node transitions.

---

## 📁 Repository Structure

```
.
├── README.md                      # This file
├── docs/
│   ├── JSON_RPC_CONTRACT.md       # Complete JSON-RPC 2.0 API specification
│   └── ARCHITECTURE.md            # Threading model, unit system & error design
├── agent/                         # LangGraph Agent Core (Abhijit Saha)
│   ├── state.py                  # Agent State Schema (CADState, TaskSpec, CADPlan)
│   ├── prompts.py                # System prompts and extraction templates
│   ├── graph.py                  # LangGraph StateGraph & Standalone state machine
│   ├── agent.py                  # High-level CADPilotAgent class & CLI runner
│   └── nodes/
│       ├── spec_extractor.py     # Node 1: Natural Language Spec Extractor
│       ├── feasibility_checker.py# Node 2: Feasibility Pre-Flight Checker
│       ├── planner.py            # Node 3: CAD Sequence Planner
│       ├── executor.py           # Node 4: Tool Execution Node
│       └── reflection.py         # Node 5: Closed-Loop Self-Correction
├── addin/                         # The Fusion 360 Add-In
│   ├── CADPilotBridge.manifest   # Fusion Add-In manifest file
│   ├── CADPilotBridge.py         # Entrypoint (run, stop, CustomEventHandler)
│   └── core/
│       ├── units.py              # Centralized unit conversion (cm <-> mm)
│       ├── errors.py             # Structured error definitions and hints
│       ├── server.py             # stdlib HTTP JSON-RPC 2.0 server
│       ├── dispatcher.py         # Main-thread tool registry & execution
│       └── tools/
│           ├── system.py         # ping, reset_design
│           ├── sketch.py         # create_sketch
│           ├── features.py       # extrude_profile, cut_hole, apply_fillet
│           ├── export.py         # export_cad (STEP, STL, F3D)
│           └── inspect.py        # inspect_brep (for Bibhukesh's checks)
├── mock/
│   ├── mock_bridge.py            # Standalone mock server (implements full contract)
│   └── canned_responses.py       # Realistic CAD bounding boxes, profiles, bodies
├── client/
│   └── test_client.py            # Standalone client & CLI for end-to-end testing
├── tests/
│   └── test_mock_bridge.py       # Test suite verifying contract compliance
└── scripts/
    └── install_addin.py          # Helper to link/install Add-In into Fusion 360
```

---

## 🚀 Quickstart

### 1. Run the Mock Bridge (For Agent / Evaluator development)
No Fusion 360 required! Teammates can start immediately:
```bash
python3 mock/mock_bridge.py --port 9090
```

### 2. Test with the Standalone Client
In another terminal, test the endpoints and run the **NEMA 17 plate** sequence:
```bash
# Ping the bridge
python3 client/test_client.py ping

# Reset the design workspace
python3 client/test_client.py reset

# Run the complete NEMA 17 plate integration scenario
python3 client/test_client.py nema17

# Run all test assertions
python3 -m unittest discover -s tests
```

### 3. Run the Autonomous Agent (Abhijit Saha)
Execute the closed-loop LangGraph agent loop against Mock Bridge or live Fusion 360:
```bash
# Run agent with default NEMA 17 prompt on Mock Bridge
python3 -m agent.agent --url mock

# Run agent with custom prompt
python3 -m agent.agent "Create a 42.3mm NEMA 17 mount plate with 4mm thickness, 22mm center hole, and 4x M3 holes spaced 31mm apart with 2mm fillets, export to /tmp/nema17_plate.step" --url mock
```

### 4. Install the Real Add-In into Fusion 360
When ready to run in Fusion 360:
```bash
# Auto-detects macOS or Windows Fusion AddIns directory and creates a symlink:
python3 scripts/install_addin.py
```
Then in Fusion 360:
1. Open **Utilities > Add-Ins > Scripts and Add-Ins** (`Shift + S`).
2. Select the **Add-Ins** tab.
3. Locate **CADPilotBridge** and click **Run**.
4. Check the **Text Palette** (`Cmd + Alt + C` / `Ctrl + Alt + C`) to see the server startup log:
   `[CADPilotBridge] JSON-RPC server listening on http://127.0.0.1:9090`

