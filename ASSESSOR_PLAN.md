# Scenario Assessor — Multi-Level Audit Architecture

Status: agreed design (2026-10-16). Implementation phases at the bottom.
Goal: audit an ADS scenario database ( DriveLM / CARLA / Waymo ) against the
Excavator reference model (taxonomy v6 + 221 expectations + 16 meta-actions) to
mine **EDGE / CORNER / MISSING** cases per `iso_edge_corner_missing_cases.md`.

## Principle

The reference model says what *should* be expressible; the scenario DB says what
*is* expressed. The assessor computes the delta with a tiered evidence hierarchy:

```
L0 reference ──► case registry (EDGE/CORNER/MISSING predicates)
                       ▲
   L1 text  ───────────┤
   L2 VLM  ────────────┤── fusion (L4) ──► verdicts + provenance ──► reports (L5)
   L3 detectors ───────┘
```

## Audit levels

**L0 — Reference layer** (`reference/`): machine-readable `taxonomy_v6.json`
(actor sub-classes + SI bounds, movement regimes, misbehavior tokens, factor
bands/enums/buffers) and `expectations_v2.json` (221 entries: trigger conditions,
meta-action sequences, statutory refs). ISO classes as computable predicates:
EDGE = parameter at band extreme; CORNER = multi-actor/factor confluence;
MISSING = zero evidence across all levels / expectation triggers never occur.

**Level 1 — Textual audit** (descriptions, QA pairs, JSON objects, scenario types):
- 1a deterministic keyword/gazetteer + structured-field sweep (port of the
  DriveLM `taxonomy_coverage/` pipeline; regression gate: must reproduce its
  FINDINGS.md verdicts on DriveLM)
- 1b embedding retrieval vs leaf descriptions + expectation triggers (paraphrase)
- 1c LLM close-reading (glm-5.3-flash): adjudicate hits with quoted-span citations

**Level 2 — Sensory audit (VLM, sequence-level)** — targeted at cases unresolved
at L1: per scene a time-ordered multi-camera strip; VLM judges *does this
sequence exercise case X* with forced-enum JSON outputs from v6 bands, frame
provenance, multi-frame voting; dual-model verification for positives.

**Level 3 — Detector sweep** — scene-wide, not case-targeted:
- YOLO-World v2 open-vocab (vocab derived from v6 actor classes: pedestrians,
  children, wheelchairs, strollers, cyclists, animals, cones/barricades, …)
- multi-object tracking → kinematic proxies (speed, TTC, headway, clearance)
  → parametric distributions for EDGE detection
- detectors ground VLM claims; **absence claims come from L3, never from the
  VLM** (prior ped_arms/edge_case_research data: VLM free-text pedestrian recall
  ~34%, cycles 4.5% — detectors are the authority on absence)

**L4 — Fusion verdicts**: evidence matrix {L1, L2, L3} × {present, partial,
absent, unobservable}. MISSING requires negative across all applicable levels;
single-source findings are flagged "verify". Expectation-level verdicts:
covered / trigger-present-response-unknown / trigger-absent.

**L5 — Outputs**: HTML coverage matrix + per-case dossiers (full provenance),
`excavation_report.json` usable as noise-injector preset input.

## Reuse inventory

| Asset | Reuse |
|---|---|
| `ped_arms/` (yolo_runner, openrouter_client, judge, html_report, run caching) | L2/L3 execution skeleton |
| `yolov8s-worldv2.pt` + judge_agent2 venv (ultralytics) | L3 core |
| `edge_case_research/` (GT index, claim extraction) | L4 fusion patterns |
| `taxonomy_coverage/` scripts | L1a baseline + regression gate |
| noise-injector exp infra (retries, env-file, pricing) | API clients |
| nuScenes 6-cam samples, DriveLM VQAs, CARLA vqa dirs | DB adapters |

## Phases (each with an exit gate)

- **P1** L0 parsing → `reference/*.json` + stats validation — *gate: all counts
  reconciled against the source files*
- **P2** L1a on DriveLM — *gate: reproduces FINDINGS.md verdicts*
- **P3** L3 detector sweep over DriveLM scenes + kinematic extraction (local, free)
- **P4** L2 VLM pass on unresolved cases (OpenRouter, cost-capped)
- **P5** L4 fusion + corner mining + reports
- **P6** Waymo / CARLA adapters

## Known limitations carried into the assessor

Resolution status after taxonomy v5→v6 (tracked in the git history of the
superseded gap-analysis document): still open — `curve_radius_m` absent from
v6 Layer 1.4; RAMP_METERING_SIGNAL & BUS_LANE_PRIORITY_SIGNAL signal types
dropped vs v4; SCHOOL_ZONE_FLASHING & NO_PASSING_ZONE sign categories not
restored; lane-width lower bound raised 2.5→2.75 m; superelevation changed
from ±6° to 1–6% (negative bank angles unrepresentable);
NARROW_MOUNTAIN_SINGLE_LANE_PASS network type removed. Expectation-layer
items (AVSC metadata restore, sequence-template audit, TX/Texas IDs) and the
v2.1 synthesis-layer import (130 combined cases + 259 gap candidates) remain
open work items.
