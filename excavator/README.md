# Edge-Case Excavator — engine

Audits an ADS scenario database against the Excavator reference model
(`../reference/taxonomy_v6.json` + `../reference/expectations_v2.json`) and
mines **EDGE / CORNER / MISSING** cases per `../iso_edge_corner_missing_cases.md`.

You bring two things:

1. **Dataset access** — a nuScenes-like tree or a DriveLM-style VQA export.
2. **A strong LLM API** — any OpenAI-compatible endpoint (OpenRouter, OpenAI,
   vLLM, llama.cpp server). The key stays in your environment or a local
   `--env-file`; it is never written to the repo.

## Install

No third-party deps are required for the text level (pure stdlib + Pillow for
strips). Optional:

```bash
pip install pillow            # L2 strips (already needed for VLM level)
pip install ultralytics       # L3 YOLO-World detector sweep
```

## Quick start (offline, text level only)

```bash
python3 -m excavator.cli excavate \
  --dataset-root ~/Documents/DriveLM \
  --adapter drivelm --limit 25 \
  --levels text --out runs/excavate-smoke
```

Outputs `runs/excavate-smoke/excavation_report.json` and a self-contained
`coverage_matrix.html`.

## Full audit (all levels)

```bash
python3 -m excavator.cli excavate \
  --dataset-root ~/Documents/DriveLM \
  --adapter drivelm \
  --levels text,vlm,detector \
  --detector-model yolov8s-worldv2.pt \
  --env-file ~/secrets/openrouter.env \
  --vlm-model qwen/qwen3-vl-8b-instruct \
  --judge-model z-ai/glm-5.3-flash \
  --limit 50 --out runs/excavate-full
```

Useful filters:

```bash
--scope leaves                      # taxonomy leaves only (skip the 221 expectations)
--scope expectations                # behavioral-expectation coverage only
--families 'MISBEHAVIOR:.*'         # regex on case ids
list-cases                          # dump the registry + counts
```

## Case registry (what gets audited)

| Kind | id pattern | count (v6 reference) |
|---|---|---|
| actor sub-classes | `ACTOR:<cat>:<name>` | 42 |
| misbehavior tokens | `MISBEHAVIOR:<TOKEN>` | 49 |
| signaling states | `STATE:<cat>:<machine>` | per state machine |
| ODD factor enums | `FACTOR:<layer>.<sec>.<name>` | per enum |
| ODD numeric bands | `BAND:<layer>.<sec>.<name>` | per band (edge mining) |
| statutory buffers | `BUFFER:<loc>` | 7 |
| behavioral expectations | `EXP:<id>` | 221 |

## Audit levels

- **L1 text** — deterministic keyword sweep over descriptions, QA pairs,
  annotation objects and scene descriptions, then optional **L1c close-reading**
  by your judge model to kill keyword false positives.
- **L2 VLM (sequence)** — for cases without text evidence: per scene a
  time×camera contact sheet is judged by your VLM with a constrained JSON
  verdict; majority vote; per-claim provenance (strip + scene token) in the
  report; results cached per (case, scene) under `out/vlm_cache/`.
- **L3 detector** — open-vocab YOLO-World sweep with a vocabulary derived from
  the 42 actor sub-classes. Detectors are the authority on **absence**: a
  `MISSING_CANDIDATE` verdict requires every executed level to be negative.

## Verdict semantics

`COVERED`, `COVERED_WEAK` (close-read unclear), `FALSE_POSITIVE`,
`DETECTOR_PRESENT`, `VLM_PRESENT`, `MISSING_CANDIDATE`, `UNVERIFIED`.
Corner mining additionally emits `unrealized_confluence` pairs (both leaves
individually present, never together) and `rare_confluence` pairs.

## Adding a dataset adapter

Subclass `excavator.adapters.base.BaseAdapter`, implement
`load(limit) -> list[Scene]` (frames carry camera image paths + text records),
and register in `excavator/adapters/__init__.py`. Anything nuScenes-shaped
(scenes → keyframes → cameras) maps directly.

## Worked example — DriveLM-nuScenes (committed)

`../examples/` contains committed audit results on real datasets (dataset
files themselves are never pushed — only scrubbed results). The DriveLM
example is a full L1 text audit (696 scenario sequences, keyword sweep +
glm-5.3-flash close-reading):

- `examples/drivelm-full/findings.txt` — readable audit findings (headline,
  gap list, corner candidates, method & caveats)
- `examples/drivelm-full/excavation_report_slim.json` — per-case verdicts +
  close-read reasons (evidence bulk stripped)
- `examples/drivelm-full/coverage_matrix.html` — the interactive matrix

The raw report with full evidence (~4.3 MB) stays local in gitignored `runs/`.
