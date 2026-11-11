# CADPilot: Fusion 360 Bridge

The **Fusion Bridge** is the execution engine for CADPilot. It connects an AI agent (e.g. LangGraph loop) to Autodesk Fusion 360 via a lightweight, zero-dependency JSON-RPC 2.0 interface.

---

## 📅 Roadmap & Milestones (Nov 3 – Nov 27)

| Status | Phase | Dates | Milestone / Focus |
|---|---|---|---|
| [x] | **Phase 0** | Nov 3–5 | Environment setup, Add-In skeleton, stdlib HTTP transport |
| [x] | **Phase 1** | Nov 4–8 | Main-thread `CustomEvent` dispatch, JSON-RPC contract, mock bridge |
| [ ] | **Phase 2** | Nov 8–15 | Tools (`sketch`, `extrude`, `cut_hole`, `fillet`, `export`, `inspect_brep`) |
| [ ] | **Phase 3** | Nov 13–17 | Structured errors, self-correction hints, timeout guards |
| [ ] | **Phase 4** | Nov 15–20 | LangGraph integration (with Abhijit), NEMA 17 test prompt |
| [ ] | **Phase 5** | Nov 18–24 | Part families (Mounting plate, L-bracket, Standoff) |
| [ ] | **Phase 6** | Nov 20–25 | 30-prompt evaluation & one-shot baseline (with Bibhukesh) |
| [ ] | **Phase 7** | Nov 25–27 | Code freeze, report, viva prep |

---

## 🗓️ Distributed Day-Wise Schedule (Nov 3 – Nov 27)

### 👥 Team Ownership Breakdown
* **Jaidev Basandrai (Fusion Bridge):** Fusion Add-in, stdlib HTTP JSON-RPC server, main-thread synchronization (`CustomEvent`), unit isolation (`units.py`), structured error wrapping (`errors.py`), mock bridge server, live Fusion tool implementations, CAD export.
* **Abhijit Saha (Agent Core):** LangGraph state machine, Natural Language Spec Extractor, Feasibility Checker, CAD Sequence Planner, tool execution dispatch, closed-loop self-correction reasoning.
* **Bibhukesh Medhi (Validation, Reflection & UI):** B-Rep validation metrics (`inspect_brep`), geometric checking algorithms (bounding box, volume, hole count, edge clearance), 30-prompt evaluation suite, one-shot LLM baseline comparison, Streamlit front-end.

---

### Phase 0 & Phase 1: Foundations & Mock Bridge (Nov 3 – Nov 8)

| Date | Jaidev Basandrai (Bridge) | Abhijit Saha (Agent Core) | Bibhukesh Medhi (Validation & UI) | Milestone |
|---|---|---|---|---|
| **Nov 3** | - [x] Verify Fusion environment, create Add-in skeleton, test palette logging, select stdlib HTTP transport. | - [x] Set up LangGraph environment, define initial Agent State schema (`CADState`, `TaskSpec`). | - [x] Survey mechanical spec formats, define B-Rep verification criteria and tolerance thresholds. | - [x] Add-in skeleton boots cleanly |
| **Nov 4** | - [x] Design daemon HTTP server thread and `CustomEvent` main-thread synchronization model. | - [x] Draft prompt templates for Natural Language Spec Extractor (dimensions, hole patterns, fillets). | - [x] Specify `inspect_brep` schema with Jaidev (volume, bounding boxes, cylindrical hole features). | - [x] Architecture agreement |
| **Nov 5** | - [x] Define shared JSON-RPC 2.0 contract (`docs/JSON_RPC_CONTRACT.md`); implement `ping` and `reset_design`. | - [x] Implement LangGraph Node 1: Spec Extractor (parsing natural language into structured geometric constraints). | - [x] Build ground-truth validation criteria (volume tolerance %, hole center coordinates). | - [x] Contract published |
| **Nov 6** | - [x] Implement centralized `units.py` (cm $\leftrightarrow$ mm) and `errors.py` structured error hierarchy. | - [x] Implement LangGraph Node 2: Feasibility Pre-Flight Checker (detecting geometric contradictions). | - [ ] Draft first 10 prompts of the benchmark dataset (flat mounting plates: NEMA 17, Raspberry Pi, etc.). | - [ ] Feasibility checks active |
| **Nov 7** | - [x] Build stateful `mock_bridge.py` (simulating sketches, bodies, holes, fillets, and bounding boxes). | - [x] Implement LangGraph Node 3: CAD Sequence Planner (generating ordered tool calls). | - [ ] Build standalone verification rule engine for bounding box and hole count assertions. | - [ ] Mock engine functional |
| **Nov 8** | - [x] Release & validate Mock Bridge and test client CLI (`client/test_client.py`). Deliver to team. | - [x] Wire LangGraph Tool Execution Node to call `CADPilotClient` pointing to Mock Bridge. | - [ ] Connect validation harness to Mock Bridge's `inspect_brep` output; verify metric calculations. | - [ ] 🎯 **Mock Bridge Released** |

---

### Phase 2: Native Tool Implementation & Initial Agent Loop (Nov 9 – Nov 14)

| Date | Jaidev Basandrai (Bridge) | Abhijit Saha (Agent Core) | Bibhukesh Medhi (Validation & UI) | Milestone |
|---|---|---|---|---|
| **Nov 9** | - [ ] Implement native `create_sketch` in Fusion (rectangles, circles, plane selection) and verify profile output. | - [ ] Implement agent observation parser (storing sketch IDs and profile tokens into LangGraph state). | - [ ] Build Streamlit UI wireframe (prompt input, step-by-step progress monitor, 3D placeholder). | - [ ] `create_sketch` tested |
| **Nov 10** | - [ ] Implement native `extrude_profile` (distance, new_body vs cut vs join) and bounding box updates. | - [ ] Wire basic end-to-end loop (Prompt $\rightarrow$ Spec $\rightarrow$ Plan $\rightarrow$ Sketch $\rightarrow$ Extrude) on Mock Bridge. | - [ ] Draft benchmark prompts 11–20 (90-degree L-brackets with gussets & fillets). | - [ ] Base solid generation works |
| **Nov 11** | - [ ] Implement native `cut_hole` (planar face selection, circular cut extrusions, through/blind depths). | - [ ] Add multi-hole pattern planner (linear arrays, pitch-circle diameters, symmetric bolt patterns). | - [ ] Implement `inspect_brep` cylindrical feature analyzer (extracting hole radii, origins, and axes). | - [ ] Hole patterns functional |
| **Nov 12** | - [ ] Implement native `apply_fillet` (edge detection, constant radius, handling maximum radius limits). | - [ ] Update state schema to maintain entity token lineage across intermediate modeling operations. | - [ ] Build volume and surface area validator inside the reflection pipeline. | - [ ] Fillet tool verified |
| **Nov 13** | - [ ] Implement native `export_cad` (STEP, STL, F3D file writing, directory creation, size check). | - [ ] Add Export Node to LangGraph state machine; configure termination and artifact delivery. | - [ ] Implement automated export file validation checks in the evaluation test runner. | - [ ] Export formats functional |
| **Nov 14** | - [ ] Implement native `inspect_brep` querying `adsk.fusion.BRepBody` properties directly in Fusion. | - [ ] Execute full Happy Path loop on Mock Bridge for the NEMA 17 plate sequence end-to-end. | - [ ] Complete benchmark prompts 21–30 (cylindrical standoffs & complex bracket variations). | - [ ] 🎯 **Full Tool Suite Scaffolded** |

---

### Phase 3: Error Handling & Closed-Loop Self-Correction (Nov 15 – Nov 17)

| Date | Jaidev Basandrai (Bridge) | Abhijit Saha (Agent Core) | Bibhukesh Medhi (Validation & UI) | Milestone |
|---|---|---|---|---|
| **Nov 15** | - [ ] Wrap native `adsk` exceptions into structured JSON-RPC errors with actionable `data.hint` fields. | - [ ] Implement LangGraph Reflection Node (extracting `error.data.hint` and injecting into replanning prompt). | - [ ] Implement retry counter tracking ($\le 3$ attempts) and error taxonomy categorization. | - [ ] Structured hints active |
| **Nov 16** | - [ ] Harden `reset_design` for clean post-failure recovery; implement 30-second main-thread timeout guards. | - [ ] Add parameter-level self-correction heuristics (e.g. automatically decrementing fillet radius on error). | - [ ] Build test suite for deliberate error injection (oversized fillets, out-of-bounds hole coordinates). | - [ ] Fault recovery verified |
| **Nov 17** | - [ ] Test bridge robustness against repeated intentionally malformed calls and sudden resets. | - [ ] Verify LangGraph autonomous recovery (agent corrects bad fillet on 2nd attempt without user input). | - [ ] Integrate reflection logs and live retry status into the Streamlit UI dashboard. | - [ ] 🎯 **Self-Correction Working** |

---

### Phase 4: Live Bridge Integration & Primary Prompt Test (Nov 18 – Nov 20)

| Date | Jaidev Basandrai (Bridge) | Abhijit Saha (Agent Core) | Bibhukesh Medhi (Validation & UI) | Milestone |
|---|---|---|---|---|
| **Nov 18** | - [ ] Install live Add-In into Autodesk Fusion 360; connect Abhijit's agent to the live Fusion session. | - [ ] Swap mock bridge endpoint for live Fusion bridge; identify and resolve parameter/schema mismatches. | - [ ] Validate live `inspect_brep` outputs against ground-truth mechanical drawings. | - [ ] Live bridge connected |
| **Nov 19** | - [ ] Fix live Fusion sketch plane orientation and face token mapping during consecutive operations. | - [ ] Refine system prompts and planner templates based on live Fusion modeling behaviors. | - [ ] Run and log first live autonomous execution of the NEMA 17 plate (42.3mm, 22mm pilot, 4x M3). | - [ ] Live NEMA 17 plate built |
| **Nov 20** | - [ ] Stabilize add-in lifecycle (clean start, stop, reconnection after agent network disconnects). | - [ ] Freeze LangGraph agent workflow v1.0; document state transitions and decision logic. | - [ ] Inspect exported STEP and STL files of NEMA 17 plate in FreeCAD/PrusaSlicer for geometric integrity. | - [ ] 🎯 **Live End-to-End Success** |

---

### Phase 5: Part Family Expansion (Nov 21 – Nov 22)

| Date | Jaidev Basandrai (Bridge) | Abhijit Saha (Agent Core) | Bibhukesh Medhi (Validation & UI) | Milestone |
|---|---|---|---|---|
| **Nov 21** | - [ ] Add bridge support for 90-degree L-bracket operations (multi-face sketches, gusset features). | - [ ] Build agent planning recipes for L-brackets with corner fillets and mounting slots. | - [ ] Execute evaluation batch on Part Family 1 (10 Mounting Plate prompts); log retry counts. | - [ ] Part Family 1 benchmarked |
| **Nov 22** | - [ ] Add bridge support for cylindrical standoffs / spacers (revolve/circular extrusion and tapped bores). | - [ ] Build agent planning recipes for cylindrical spacers; handle parameter edge cases. | - [ ] Execute evaluation batch on Part Family 2 (10 L-Bracket prompts); log retry counts. | - [ ] Part Family 2 benchmarked |

---

### Phase 6: 30-Prompt Evaluation & Baseline Comparison (Nov 23 – Nov 24)

| Date | Jaidev Basandrai (Bridge) | Abhijit Saha (Agent Core) | Bibhukesh Medhi (Validation & UI) | Milestone |
|---|---|---|---|---|
| **Nov 23** | - [ ] Monitor live bridge during batch runs; hotfix geometric edge cases or timing delays. | - [ ] Implement and execute the One-Shot LLM Baseline (generating raw Python scripts in one shot). | - [ ] Run the full 30-prompt evaluation suite on CADPilot (recording success rate, retries, time). | - [ ] 30 prompts executed |
| **Nov 24** | - [ ] Extract bridge log statistics (average tool execution time, error frequency by tool type). | - [ ] Compile baseline vs agent comparison metrics (success rate, fatal error rate, human interventions). | - [ ] Generate final evaluation graphs, comparison charts, and statistical summary tables for report. | - [ ] 🎯 **Evaluation Completed** |

---

### Phase 7: Code Freeze, Final Report & Submission (Nov 25 – Nov 27)

| Date | Jaidev Basandrai (Bridge) | Abhijit Saha (Agent Core) | Bibhukesh Medhi (Validation & UI) | Milestone |
|---|---|---|---|---|
| **Nov 25** | - [ ] **Code Freeze**: Clean up add-in code, verify installer scripts on macOS & Windows, write bridge setup guide. | - [ ] **Code Freeze**: Package agent core repository, clean up config files and dependencies, lock prompt templates. | - [ ] **Code Freeze**: Finalize Streamlit app, package benchmark evaluation data and metrics. | - [ ] 🔒 **Code Frozen** |
| **Nov 26** | - [ ] Draft report sections: Architecture, Main-thread `CustomEvent` synchronization, Unit conversion, Error hints. | - [ ] Draft report sections: Agentic workflow, LangGraph state machine, Feasibility checks, Planning algorithms. | - [ ] Draft report sections: Evaluation results, B-Rep reflection metrics, Baseline comparison, Front-end UI. | - [ ] Report draft complete |
| **Nov 27** | - [ ] Record 3-minute video demo of live Fusion modeling; review final report; assemble submission archive. | - [ ] Review and proofread report; verify agent reproducibility; finalize repo README. | - [ ] Compile final report PDF with tables and diagrams; submit project deliverables. | - [ ] 🚀 **Final Submission** |

---

### Post-Submission: Viva Preparation (Nov 28 – Early Dec)

* [ ] **Jaidev Basandrai:** Prepare to defend the 3 bridge architectural decisions:
  1. *Why the main-thread event pattern is mandatory* (ASM single-threaded kernel vs worker thread crash prevention).
  2. *Why step-by-step structured observations are superior to one-shot scripts* (closed-loop inspection vs blind hallucination).
  3. *How errors become actionable feedback for retries* (translating C++ exceptions into structured `hint`s for LLM recovery).
* [ ] **Abhijit Saha:** Prepare to defend the agentic loop, LangGraph state machine transitions, and self-correction autonomy.
* [ ] **Bibhukesh Medhi:** Prepare to defend the evaluation methodology, B-Rep reflection rigor, and metric comparisons against one-shot LLMs.

---

## 🗓️ Distributed Day-Wise Schedule (Nov 3 – Nov 27)

### 👥 Team Ownership Breakdown
* **Jaidev Basandrai (Fusion Bridge):** Fusion Add-in, stdlib HTTP JSON-RPC server, main-thread synchronization (`CustomEvent`), unit isolation (`units.py`), structured error wrapping (`errors.py`), mock bridge server, live Fusion tool implementations, CAD export.
* **Abhijit Saha (Agent Core):** LangGraph state machine, Natural Language Spec Extractor, Feasibility Checker, CAD Sequence Planner, tool execution dispatch, closed-loop self-correction reasoning.
* **Bibhukesh Medhi (Validation, Reflection & UI):** B-Rep validation metrics (`inspect_brep`), geometric checking algorithms (bounding box, volume, hole count, edge clearance), 30-prompt evaluation suite, one-shot LLM baseline comparison, Streamlit front-end.

---

### Phase 0 & Phase 1: Foundations & Mock Bridge (Nov 3 – Nov 8)

| Date | Jaidev Basandrai (Bridge) | Abhijit Saha (Agent Core) | Bibhukesh Medhi (Validation & UI) | Milestone |
|---|---|---|---|---|
| **Nov 3** | - [x] Verify Fusion environment, create Add-in skeleton, test palette logging, select stdlib HTTP transport. | - [x] Set up LangGraph environment, define initial Agent State schema (`CADState`, `TaskSpec`). | - [x] Survey mechanical spec formats, define B-Rep verification criteria and tolerance thresholds. | - [x] Add-in skeleton boots cleanly |
| **Nov 4** | - [x] Design daemon HTTP server thread and `CustomEvent` main-thread synchronization model. | - [x] Draft prompt templates for Natural Language Spec Extractor (dimensions, hole patterns, fillets). | - [x] Specify `inspect_brep` schema with Jaidev (volume, bounding boxes, cylindrical hole features). | - [x] Architecture agreement |
| **Nov 5** | - [x] Define shared JSON-RPC 2.0 contract (`docs/JSON_RPC_CONTRACT.md`); implement `ping` and `reset_design`. | - [x] Implement LangGraph Node 1: Spec Extractor (parsing natural language into structured geometric constraints). | - [x] Build ground-truth validation criteria (volume tolerance %, hole center coordinates). | - [x] Contract published |
| **Nov 6** | - [x] Implement centralized `units.py` (cm $\leftrightarrow$ mm) and `errors.py` structured error hierarchy. | - [x] Implement LangGraph Node 2: Feasibility Pre-Flight Checker (detecting geometric contradictions). | - [ ] Draft first 10 prompts of the benchmark dataset (flat mounting plates: NEMA 17, Raspberry Pi, etc.). | - [ ] Feasibility checks active |
| **Nov 7** | - [x] Build stateful `mock_bridge.py` (simulating sketches, bodies, holes, fillets, and bounding boxes). | - [x] Implement LangGraph Node 3: CAD Sequence Planner (generating ordered tool calls). | - [ ] Build standalone verification rule engine for bounding box and hole count assertions. | - [ ] Mock engine functional |
| **Nov 8** | - [x] Release & validate Mock Bridge and test client CLI (`client/test_client.py`). Deliver to team. | - [x] Wire LangGraph Tool Execution Node to call `CADPilotClient` pointing to Mock Bridge. | - [ ] Connect validation harness to Mock Bridge's `inspect_brep` output; verify metric calculations. | - [ ] 🎯 **Mock Bridge Released** |

---

### Phase 2: Native Tool Implementation & Initial Agent Loop (Nov 9 – Nov 14)

| Date | Jaidev Basandrai (Bridge) | Abhijit Saha (Agent Core) | Bibhukesh Medhi (Validation & UI) | Milestone |
|---|---|---|---|---|
| **Nov 9** | - [ ] Implement native `create_sketch` in Fusion (rectangles, circles, plane selection) and verify profile output. | - [ ] Implement agent observation parser (storing sketch IDs and profile tokens into LangGraph state). | - [ ] Build Streamlit UI wireframe (prompt input, step-by-step progress monitor, 3D placeholder). | - [ ] `create_sketch` tested |
| **Nov 10** | - [ ] Implement native `extrude_profile` (distance, new_body vs cut vs join) and bounding box updates. | - [ ] Wire basic end-to-end loop (Prompt $\rightarrow$ Spec $\rightarrow$ Plan $\rightarrow$ Sketch $\rightarrow$ Extrude) on Mock Bridge. | - [ ] Draft benchmark prompts 11–20 (90-degree L-brackets with gussets & fillets). | - [ ] Base solid generation works |
| **Nov 11** | - [ ] Implement native `cut_hole` (planar face selection, circular cut extrusions, through/blind depths). | - [ ] Add multi-hole pattern planner (linear arrays, pitch-circle diameters, symmetric bolt patterns). | - [ ] Implement `inspect_brep` cylindrical feature analyzer (extracting hole radii, origins, and axes). | - [ ] Hole patterns functional |
| **Nov 12** | - [ ] Implement native `apply_fillet` (edge detection, constant radius, handling maximum radius limits). | - [ ] Update state schema to maintain entity token lineage across intermediate modeling operations. | - [ ] Build volume and surface area validator inside the reflection pipeline. | - [ ] Fillet tool verified |
| **Nov 13** | - [ ] Implement native `export_cad` (STEP, STL, F3D file writing, directory creation, size check). | - [ ] Add Export Node to LangGraph state machine; configure termination and artifact delivery. | - [ ] Implement automated export file validation checks in the evaluation test runner. | - [ ] Export formats functional |
| **Nov 14** | - [ ] Implement native `inspect_brep` querying `adsk.fusion.BRepBody` properties directly in Fusion. | - [ ] Execute full Happy Path loop on Mock Bridge for the NEMA 17 plate sequence end-to-end. | - [ ] Complete benchmark prompts 21–30 (cylindrical standoffs & complex bracket variations). | - [ ] 🎯 **Full Tool Suite Scaffolded** |

---

### Phase 3: Error Handling & Closed-Loop Self-Correction (Nov 15 – Nov 17)

| Date | Jaidev Basandrai (Bridge) | Abhijit Saha (Agent Core) | Bibhukesh Medhi (Validation & UI) | Milestone |
|---|---|---|---|---|
| **Nov 15** | - [ ] Wrap native `adsk` exceptions into structured JSON-RPC errors with actionable `data.hint` fields. | - [ ] Implement LangGraph Reflection Node (extracting `error.data.hint` and injecting into replanning prompt). | - [ ] Implement retry counter tracking ($\le 3$ attempts) and error taxonomy categorization. | - [ ] Structured hints active |
| **Nov 16** | - [ ] Harden `reset_design` for clean post-failure recovery; implement 30-second main-thread timeout guards. | - [ ] Add parameter-level self-correction heuristics (e.g. automatically decrementing fillet radius on error). | - [ ] Build test suite for deliberate error injection (oversized fillets, out-of-bounds hole coordinates). | - [ ] Fault recovery verified |
| **Nov 17** | - [ ] Test bridge robustness against repeated intentionally malformed calls and sudden resets. | - [ ] Verify LangGraph autonomous recovery (agent corrects bad fillet on 2nd attempt without user input). | - [ ] Integrate reflection logs and live retry status into the Streamlit UI dashboard. | - [ ] 🎯 **Self-Correction Working** |

---

### Phase 4: Live Bridge Integration & Primary Prompt Test (Nov 18 – Nov 20)

| Date | Jaidev Basandrai (Bridge) | Abhijit Saha (Agent Core) | Bibhukesh Medhi (Validation & UI) | Milestone |
|---|---|---|---|---|
| **Nov 18** | - [ ] Install live Add-In into Autodesk Fusion 360; connect Abhijit's agent to the live Fusion session. | - [ ] Swap mock bridge endpoint for live Fusion bridge; identify and resolve parameter/schema mismatches. | - [ ] Validate live `inspect_brep` outputs against ground-truth mechanical drawings. | - [ ] Live bridge connected |
| **Nov 19** | - [ ] Fix live Fusion sketch plane orientation and face token mapping during consecutive operations. | - [ ] Refine system prompts and planner templates based on live Fusion modeling behaviors. | - [ ] Run and log first live autonomous execution of the NEMA 17 plate (42.3mm, 22mm pilot, 4x M3). | - [ ] Live NEMA 17 plate built |
| **Nov 20** | - [ ] Stabilize add-in lifecycle (clean start, stop, reconnection after agent network disconnects). | - [ ] Freeze LangGraph agent workflow v1.0; document state transitions and decision logic. | - [ ] Inspect exported STEP and STL files of NEMA 17 plate in FreeCAD/PrusaSlicer for geometric integrity. | - [ ] 🎯 **Live End-to-End Success** |

---

### Phase 5: Part Family Expansion (Nov 21 – Nov 22)

| Date | Jaidev Basandrai (Bridge) | Abhijit Saha (Agent Core) | Bibhukesh Medhi (Validation & UI) | Milestone |
|---|---|---|---|---|
| **Nov 21** | - [ ] Add bridge support for 90-degree L-bracket operations (multi-face sketches, gusset features). | - [ ] Build agent planning recipes for L-brackets with corner fillets and mounting slots. | - [ ] Execute evaluation batch on Part Family 1 (10 Mounting Plate prompts); log retry counts. | - [ ] Part Family 1 benchmarked |
| **Nov 22** | - [ ] Add bridge support for cylindrical standoffs / spacers (revolve/circular extrusion and tapped bores). | - [ ] Build agent planning recipes for cylindrical spacers; handle parameter edge cases. | - [ ] Execute evaluation batch on Part Family 2 (10 L-Bracket prompts); log retry counts. | - [ ] Part Family 2 benchmarked |

---

### Phase 6: 30-Prompt Evaluation & Baseline Comparison (Nov 23 – Nov 24)

| Date | Jaidev Basandrai (Bridge) | Abhijit Saha (Agent Core) | Bibhukesh Medhi (Validation & UI) | Milestone |
|---|---|---|---|---|
| **Nov 23** | - [ ] Monitor live bridge during batch runs; hotfix geometric edge cases or timing delays. | - [ ] Implement and execute the One-Shot LLM Baseline (generating raw Python scripts in one shot). | - [ ] Run the full 30-prompt evaluation suite on CADPilot (recording success rate, retries, time). | - [ ] 30 prompts executed |
| **Nov 24** | - [ ] Extract bridge log statistics (average tool execution time, error frequency by tool type). | - [ ] Compile baseline vs agent comparison metrics (success rate, fatal error rate, human interventions). | - [ ] Generate final evaluation graphs, comparison charts, and statistical summary tables for report. | - [ ] 🎯 **Evaluation Completed** |

---

### Phase 7: Code Freeze, Final Report & Submission (Nov 25 – Nov 27)

| Date | Jaidev Basandrai (Bridge) | Abhijit Saha (Agent Core) | Bibhukesh Medhi (Validation & UI) | Milestone |
|---|---|---|---|---|
| **Nov 25** | - [ ] **Code Freeze**: Clean up add-in code, verify installer scripts on macOS & Windows, write bridge setup guide. | - [ ] **Code Freeze**: Package agent core repository, clean up config files and dependencies, lock prompt templates. | - [ ] **Code Freeze**: Finalize Streamlit app, package benchmark evaluation data and metrics. | - [ ] 🔒 **Code Frozen** |
| **Nov 26** | - [ ] Draft report sections: Architecture, Main-thread `CustomEvent` synchronization, Unit conversion, Error hints. | - [ ] Draft report sections: Agentic workflow, LangGraph state machine, Feasibility checks, Planning algorithms. | - [ ] Draft report sections: Evaluation results, B-Rep reflection metrics, Baseline comparison, Front-end UI. | - [ ] Report draft complete |
| **Nov 27** | - [ ] Record 3-minute video demo of live Fusion modeling; review final report; assemble submission archive. | - [ ] Review and proofread report; verify agent reproducibility; finalize repo README. | - [ ] Compile final report PDF with tables and diagrams; submit project deliverables. | - [ ] 🚀 **Final Submission** |

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

