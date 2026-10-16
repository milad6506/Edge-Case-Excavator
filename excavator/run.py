"""Orchestrator: reference -> scenes -> levels -> fusion -> report."""
from __future__ import annotations

import json
from pathlib import Path

from .adapters import get_adapter
from .audit.detector import DetectorAuditor
from .audit.text import TextAuditor
from .audit.vlm import VlmAuditor
from .config import ExcavatorConfig
from .fuse import fuse_case, mine_corners, summarize
from .llm import LlmClient
from .reference import Reference
from .report import write_findings, write_report

_UNIT_BY_ADAPTER = {
    "drivelm": "scenario sequence (scene: multi-keyframe ego trajectory, 6 surround cameras)",
    "nuscenes_flat": "scenario sequence (scene-tag frame grouping across cameras)",
}


def run(config: ExcavatorConfig) -> dict:
    config.validate()
    out_dir = Path(config.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    reference = Reference(config.reference_dir)
    cases = reference.filter(config.scope, config.families)
    if not cases:
        raise SystemExit("no cases after filtering — check --scope/--families")

    adapter = get_adapter(config.adapter, config.dataset_root, config.data_file)
    scenes = adapter.load(config.limit)
    if not scenes:
        raise SystemExit(f"adapter {config.adapter} returned no scenes from {config.dataset_root}")

    llm: LlmClient | None = None
    key = config.api.resolved_key()
    if key:
        llm = LlmClient(config.api.base_url, key, config.api.judge_model,
                        temperature=0.0, max_tokens=config.api.max_tokens,
                        retries=config.api.retries, timeout_s=config.api.timeout_s)
    elif config.needs_api():
        print(f"[warn] no API key ({config.api.api_key_env}) — L1c close-reading "
              "and L2 VLM levels will be skipped")

    executed: set[str] = set()
    results: dict[str, dict[str, dict]] = {}
    cache_dir = out_dir / "level_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    def load_cached(level: str) -> dict | None:
        p = cache_dir / f"{level}_results.json"
        if p.exists():
            print(f"[cache] reusing {level} results from {p}")
            return json.loads(p.read_text())
        return None

    def store_cached(level: str, res: dict) -> None:
        (cache_dir / f"{level}_results.json").write_text(json.dumps(res))

    if "text" in config.levels:
        cached = load_cached("text")
        if cached is not None:
            results["text"] = cached
        else:
            auditor = TextAuditor(cases, llm=llm)
            results["text"] = auditor.run(scenes, close_read=config.close_read and llm is not None)
            store_cached("text", results["text"])
        executed.add("text")

    if "detector" in config.levels:
        cached = load_cached("detector")
        if cached is not None:
            results["detector"] = cached
        else:
            model = config.detector_model or "yolov8s-worldv2.pt"
            auditor = DetectorAuditor(model, conf=config.detector_conf,
                                      cameras=config.detector_cameras)
            results["detector"] = auditor.run(cases, scenes)
            store_cached("detector", results["detector"])
        executed.add("detector")

    if "vlm" in config.levels:
        if llm is None:
            results["vlm"] = {c.case_id: {"level": "vlm", "verdict": "not_run",
                                          "reason": "no api key", "evidence": []}
                              for c in cases}
        else:
            vlm_llm = LlmClient(config.api.base_url, key, config.api.vlm_model,
                                temperature=0.0, max_tokens=config.api.max_tokens,
                                retries=config.api.retries, timeout_s=config.api.timeout_s)
            auditor = VlmAuditor(vlm_llm, out_dir,
                                 scenes_per_case=config.vlm_scenes_per_case,
                                 strip_frames=config.strip_frames)
            # target only cases the cheaper levels left unresolved: no confirmed
            # text evidence (absent / unclear / rejected). COVERED cases skip L2.
            unresolved = set()
            if "text" in results:
                for cid, r in results["text"].items():
                    if r.get("verdict") in ("absent", "unclear", "false_positive"):
                        unresolved.add(cid)
            targets = [c for c in cases if c.case_id in unresolved] or list(cases)
            leaf_cases = [c for c in targets if c.kind != "expectation"]
            exp_cases = [c for c in targets if c.kind == "expectation"]
            res = {}
            cached_vlm = load_cached("vlm")
            if cached_vlm is not None:
                res = cached_vlm
            else:
                if leaf_cases:
                    res.update(auditor.run(leaf_cases, scenes))
                if exp_cases:
                    res.update(auditor.run(exp_cases, scenes))
                store_cached("vlm", res)
            results["vlm"] = res
            executed.add("vlm")

    case_map = {c.case_id: c for c in cases}
    fused = fuse_case(case_map, results, executed)

    # corner mining uses leaf-level keyword hits across scenes
    scene_hits: dict[str, set[str]] = {}
    for cid, r in results.get("text", {}).items():
        toks = r.get("scene_tokens") or []
        if toks and not cid.startswith("EXP:"):
            scene_hits[cid] = set(toks)
    corners = mine_corners(scene_hits)
    summary = summarize(fused, corners)

    cfg_summary = {"adapter": config.adapter, "levels": list(executed),
                   "scope": config.scope, "limit": config.limit,
                   "dataset_root": str(config.dataset_root)}
    report_path, html_path = write_report(
        out_dir, config_summary=cfg_summary, reference_stats=reference.stats(),
        fused=fused, corners=corners, summary=summary, scene_count=len(scenes))
    unit = config.unit_label or _UNIT_BY_ADAPTER.get(config.adapter, "scenario sequence (Scene)")
    findings_path = write_findings(
        out_dir, dataset_label=f"{config.adapter} @ {config.dataset_root}",
        config_summary=cfg_summary, reference_stats=reference.stats(),
        fused=fused, corners=corners, summary=summary, scene_count=len(scenes),
        unit=unit)
    print(f"[done] {summary['total_cases']} cases · sequences: {len(scenes)} · "
          f"verdicts: {summary['by_verdict']}")
    print(f"[done] findings: {findings_path}")
    print(f"[done] report:   {report_path}")
    print(f"[done] html:     {html_path}")
    return {"summary": summary, "report": str(report_path), "html": str(html_path),
            "findings": str(findings_path)}
