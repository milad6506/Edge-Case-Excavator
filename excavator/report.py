"""Reporting: machine-readable excavation report + self-contained HTML matrix."""
from __future__ import annotations

import json
from pathlib import Path

_VERDICT_STYLE = {
    "COVERED": ("#1a7f37", "#e6ffec"),
    "COVERED_WEAK": ("#9a6700", "#fff8c5"),
    "DETECTOR_PRESENT": ("#1a7f37", "#e6ffec"),
    "VLM_PRESENT": ("#0550ae", "#ddf4ff"),
    "FALSE_POSITIVE": ("#6e7781", "#f6f8fa"),
    "MISSING_CANDIDATE": ("#cf222e", "#ffebe9"),
    "UNVERIFIED": ("#57606a", "#f6f8fa"),
}


def write_report(out_dir: Path, *, config_summary: dict, reference_stats: dict,
                 fused: dict[str, dict], corners: list[dict], summary: dict,
                 scene_count: int) -> tuple[Path, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "excavation_report.json"
    report_path.write_text(json.dumps({
        "tool": "edge-case-excavator", "version": "0.1.0",
        "config": config_summary,
        "reference": reference_stats,
        "scenes_audited": scene_count,
        "summary": summary,
        "corner_candidates": corners,
        "cases": sorted(fused.values(), key=lambda f: (f["kind"], f["case_id"])),
    }, indent=1, ensure_ascii=False) + "\n")
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
cases: {summary['total_cases']} · config: <code>{config_summary}</code></div>
<div class="cards">{cards}</div>
<h2>Corner-case candidates (co-occurrence mining)</h2>
<table><tr><th>pair</th><th>co-occurrence</th><th>scenes a / b</th><th>class</th></tr>
{corner_rows or '<tr><td colspan=4 class="dim">no corner candidates (need ≥2 leaf cases with evidence)</td></tr>'}</table>
<h2>Case verdicts</h2>
<table><tr><th>kind</th><th>case</th><th>verdict</th><th>levels</th></tr>{''.join(rows)}</table>
</body></html>"""
