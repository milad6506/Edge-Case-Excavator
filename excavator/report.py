"""Reporting: machine-readable excavation report + self-contained HTML matrix
+ human-readable findings. All outputs are scrubbed of local filesystem
identifiers (home directory paths) before being written."""
from __future__ import annotations

import json
import os
from pathlib import Path

_HOME = os.path.expanduser("~")


def _scrub(obj):
    """Recursively replace local home-dir prefixes with '~' in strings."""
    if isinstance(obj, str):
        return obj.replace(_HOME + "/", "~/").replace(_HOME, "~")
    if isinstance(obj, dict):
        return {k: _scrub(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_scrub(x) for x in obj]
    return obj

_VERDICT_STYLE = {
    "COVERED": ("#1a7f37", "#e6ffec"),
    "COVERED_WEAK": ("#9a6700", "#fff8c5"),
    "DETECTOR_PRESENT": ("#1a7f37", "#e6ffec"),
    "VLM_PRESENT": ("#0550ae", "#ddf4ff"),
    "FALSE_POSITIVE": ("#6e7781", "#f6f8fa"),
    "MISSING_CANDIDATE": ("#cf222e", "#ffebe9"),
    "UNVERIFIED": ("#57606a", "#f6f8fa"),
}


def write_findings(out_dir: Path, *, dataset_label: str, config_summary: dict,
                   reference_stats: dict, fused: dict[str, dict], corners: list[dict],
                   summary: dict, scene_count: int, unit: str) -> Path:
    """Human-readable audit findings (the deliverable users read)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "findings.txt"
    W = 78
    lines: list[str] = []

    def rule(ch: str = "=") -> None:
        lines.append(ch * W)

    def head(title: str) -> None:
        lines.append("")
        rule()
        lines.append(title)
        rule()

    def wrap(text: str, indent: str = "   ") -> list[str]:
        import textwrap
        return textwrap.wrap(text, W, initial_indent=indent, subsequent_indent=indent) or [indent]

    rule("=")
    lines.append("EDGE-CASE EXCAVATOR — AUDIT FINDINGS")
    lines.append("=" * W)
    lines.append(f"Dataset            : {_scrub(dataset_label)}")
    lines.append(f"Assessment unit    : {unit}")
    lines.append(f"Sequences audited  : {scene_count}")
    lines.append(f"Reference model    : taxonomy v{reference_stats.get('taxonomy_version')} + "
                 f"{reference_stats.get('expectations')} behavioral expectations "
                 f"({summary['total_cases']} audited cases)")
    lines.append(f"Levels executed    : {', '.join(config_summary.get('levels', [])) or 'none'}")
    cfg_line = (f"adapter={config_summary.get('adapter')} "
                f"scope={config_summary.get('scope')} limit={config_summary.get('limit')}")
    lines.append(f"Config             : {_scrub(cfg_line)}")

    head("1. HEADLINE")
    bv = summary["by_verdict"]
    total = summary["total_cases"] or 1
    for k in ("COVERED", "COVERED_WEAK", "DETECTOR_PRESENT", "VLM_PRESENT",
              "FALSE_POSITIVE", "TEXT_ABSENT", "MISSING_CANDIDATE", "UNVERIFIED"):
        if k in bv:
            lines.append(f"  {k:<20}{bv[k]:>5}   ({100 * bv[k] / total:.1f}%)")
    lines.append(f"  {'corner candidates':<20}{summary['corner_candidates']:>5}")
    if "MISSING_CANDIDATE" not in bv and "TEXT_ABSENT" in bv:
        lines.append("")
        lines.extend(wrap(
            "NOTE: absence is not yet verified — TEXT_ABSENT cases are queued for "
            "the sensory (L2 VLM) and detector (L3) levels. Only cases confirmed "
            "absent by all executed levels are MISSING_CANDIDATE."))

    head("2. COVERAGE BY CASE KIND")
    kinds = sorted(summary["by_kind"])
    verdicts_order = ["COVERED", "COVERED_WEAK", "DETECTOR_PRESENT", "VLM_PRESENT",
                      "FALSE_POSITIVE", "TEXT_ABSENT", "MISSING_CANDIDATE", "UNVERIFIED"]
    lines.append("  " + f"{'kind':<13}" + "".join(f"{v[:9]:>10}" for v in verdicts_order))
    for k in kinds:
        row = summary["by_kind"][k]
        lines.append("  " + f"{k:<13}" + "".join(f"{row.get(v, 0):>10}" for v in verdicts_order))

    head("3. THE GAP LIST (sequences show no evidence for these cases)")
    for kind in ("actor", "misbehavior", "state", "factor", "band", "buffer"):
        gaps = sorted(f["case_id"] for f in fused.values()
                      if f["kind"] == kind and f["verdict"] in ("TEXT_ABSENT", "MISSING_CANDIDATE"))
        if not gaps:
            continue
        label = {"actor": "Actor sub-classes", "misbehavior": "Misbehavior regime tokens",
                 "state": "Signaling states", "factor": "ODD factor enums",
                 "band": "ODD numeric bands", "buffer": "Statutory buffers"}[kind]
        lines.append(f"\n  3.{('actor', 'misbehavior', 'state', 'factor', 'band', 'buffer').index(kind) + 1} "
                     f"{label} — {len(gaps)} absent")
        for gid in gaps:
            lines.append(f"      - {gid}")

    exp_gaps = [f for f in sorted(fused.values(), key=lambda x: x["case_id"])
                if f["kind"] == "expectation" and f["verdict"] in ("TEXT_ABSENT", "MISSING_CANDIDATE")]
    n_exp = sum(summary["by_kind"].get("expectation", {}).values())
    lines.append(f"\n  3.7 Behavioral expectations — {len(exp_gaps)} of {n_exp} absent "
                 f"(full list in excavation_report.json)")
    by_src: dict[str, int] = {}
    for f in exp_gaps:
        src = f.get("source") or "unknown"
        by_src[src] = by_src.get(src, 0) + 1
    lines.append("      gap distribution by source framework:")
    for src, n in sorted(by_src.items(), key=lambda kv: -kv[1]):
        lines.append(f"        - {src}: {n}")

    head("4. CORNER-CASE CANDIDATES (co-occurrence mining)")
    if not corners:
        lines.append("  none found (needs >=2 leaf cases with per-sequence evidence)")
    else:
        lines.append(f"  {len(corners)} candidate pairs; top items:")
        for c in corners[:25]:
            lines.append(f"    - {c['pair'][0]}  ×  {c['pair'][1]}")
            lines.append(f"        {c['class']}: co-occurrence {c['co_occurrence']} "
                         f"(individually {c['scenes_a']} / {c['scenes_b']} sequences)")

    covered_exp = [f for f in fused.values()
                   if f["kind"] == "expectation" and f["verdict"].startswith("COVERED")]
    if covered_exp:
        head("5. EXPECTATION COVERAGE HIGHLIGHTS")
        lines.append(f"  {len(covered_exp)} of {reference_stats.get('expectations')} "
                     f"behavioral expectations have sequences in the corpus; sample:")
        for f in sorted(covered_exp, key=lambda x: x["case_id"])[:15]:
            seq = " -> ".join(f.get("sequence") or []) or "n/a"
            lines.append(f"    + {f['case_id']}  {f['name'][:52]}")
            lines.append(f"        sequence: {seq}")

    head("6. METHOD & CAVEATS")
    caveats = [
        f"Unit of assessment is the {unit}; frames and cameras never produce verdicts alone.",
        "L1 keywords are recall-first (plural-tolerant phrases + distinctive tokens);",
        "L1c LLM close-reading filters incidental word overlaps.",
        "TEXT_ABSENT != MISSING: sensory (VLM) and detector levels must confirm",
        "absence before a case is a missing-case candidate.",
        "Keyword coverage cannot see compliance states annotated only visually;",
        "the L2/L3 levels exist precisely for those.",
    ]
    for c in caveats:
        lines.extend(wrap(c, "  "))

    path.write_text("\n".join(lines) + "\n")
    return path


def write_report(out_dir: Path, *, config_summary: dict, reference_stats: dict,
                 fused: dict[str, dict], corners: list[dict], summary: dict,
                 scene_count: int) -> tuple[Path, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "excavation_report.json"
    report_path.write_text(json.dumps(_scrub({
        "tool": "edge-case-excavator", "version": "0.1.0",
        "config": config_summary,
        "reference": reference_stats,
        "scenes_audited": scene_count,
        "summary": summary,
        "corner_candidates": corners,
        "cases": sorted(fused.values(), key=lambda f: (f["kind"], f["case_id"])),
    }), indent=1, ensure_ascii=False) + "\n")
    html_path = out_dir / "coverage_matrix.html"
    html_path.write_text(_html(config_summary, reference_stats, summary, fused,
                               corners, scene_count))
    return report_path, html_path


def _html(config_summary, reference_stats, summary, fused, corners, scene_count) -> str:
    rows = []
    for f in sorted(fused.values(), key=lambda x: (x["kind"], x["case_id"])):
        color, bg = _VERDICT_STYLE.get(f["verdict"], ("#57606a", "#f6f8fa"))
        levels = " · ".join(f"{lvl}:{r['verdict']}" for lvl, r in f["levels"].items()) or "—"
        rows.append(
            f"<tr><td class='kind'>{f['kind']}</td><td><code>{f['case_id']}</code><br>"
            f"<span class='dim'>{f['name'][:90]}</span></td>"
            f"<td><span class='pill' style='color:{color};background:{bg}'>{f['verdict']}</span></td>"
            f"<td class='dim'>{levels}</td></tr>")
    cards = " ".join(
        f"<div class='card'><div class='num'>{n}</div><div class='lbl'>{k}</div></div>"
        for k, n in sorted(summary["by_verdict"].items()))
    corner_rows = "".join(
        f"<tr><td><code>{c['pair'][0]}</code> × <code>{c['pair'][1]}</code></td>"
        f"<td>{c['co_occurrence']}</td><td>{c['scenes_a']} / {c['scenes_b']}</td>"
        f"<td><span class='pill' style='color:#9a6700;background:#fff8c5'>{c['class']}</span></td></tr>"
        for c in corners[:80])
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Edge-Case Excavator — coverage matrix</title>
<style>
 body{{font:14px/1.45 -apple-system,Segoe UI,sans-serif;margin:24px;color:#1f2328}}
 h1{{font-size:20px}} h2{{font-size:16px;margin-top:28px}}
 .cards{{display:flex;gap:12px;flex-wrap:wrap;margin:16px 0}}
 .card{{border:1px solid #d0d7de;border-radius:8px;padding:10px 16px;text-align:center}}
 .num{{font-size:22px;font-weight:600}} .lbl{{font-size:11px;color:#57606a}}
 table{{border-collapse:collapse;width:100%;margin-top:8px}}
 td,th{{border-bottom:1px solid #d8dee4;padding:6px 10px;text-align:left;vertical-align:top}}
 th{{background:#f6f8fa;font-size:12px;text-transform:uppercase;letter-spacing:.04em}}
 .kind{{font-size:11px;color:#57606a;text-transform:uppercase}}
 .pill{{padding:2px 8px;border-radius:10px;font-size:12px;font-weight:600;white-space:nowrap}}
 .dim{{color:#57606a;font-size:12px}}
 code{{font-size:12px}}
 .meta{{color:#57606a;font-size:12px}}
</style></head><body>
<h1>Edge-Case Excavator — coverage matrix</h1>
<div class="meta">scenes audited: {scene_count} · taxonomy: {reference_stats.get('taxonomy_version')} ·
cases: {summary['total_cases']} · config: <code>{_scrub(config_summary)}</code></div>
<div class="cards">{cards}</div>
<h2>Corner-case candidates (co-occurrence mining)</h2>
<table><tr><th>pair</th><th>co-occurrence</th><th>scenes a / b</th><th>class</th></tr>
{corner_rows or '<tr><td colspan=4 class="dim">no corner candidates (need ≥2 leaf cases with evidence)</td></tr>'}</table>
<h2>Case verdicts</h2>
<table><tr><th>kind</th><th>case</th><th>verdict</th><th>levels</th></tr>{''.join(rows)}</table>
</body></html>"""
