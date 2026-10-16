"""CLI: python -m excavator.cli {excavate,list-cases}"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import ExcavatorConfig, load_env_file
from .reference import Reference
from .run import run


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--dataset-root", type=Path, required=True,
                   help="dataset root (e.g. ~/Documents/DriveLM or .../nuscenes)")
    p.add_argument("--data-file", default=None,
                   help="DriveLM VQA json (adapter auto-detects if omitted)")
    p.add_argument("--adapter", default="drivelm",
                   choices=("drivelm", "nuscenes_flat"))
    p.add_argument("--reference-dir", type=Path, default=None)
    p.add_argument("--out", type=Path, default=Path("runs/excavate"))
    p.add_argument("--levels", default="text",
                   help="comma list: text,vlm,detector")
    p.add_argument("--scope", default="all",
                   choices=("all", "leaves", "expectations"))
    p.add_argument("--families", default=".*", help="regex filter on case ids")
    p.add_argument("--limit", type=int, default=None, help="max scenes")
    p.add_argument("--env-file", type=Path, default=None,
                   help=".env file with the API key (never committed)")
    p.add_argument("--api-base", default="https://openrouter.ai/api/v1")
    p.add_argument("--api-key-env", default="OPENROUTER_API_KEY")
    p.add_argument("--vlm-model", default="qwen/qwen3-vl-8b-instruct")
    p.add_argument("--judge-model", default="z-ai/glm-5.3-flash")
    p.add_argument("--no-close-read", action="store_true",
                   help="disable L1c LLM close-reading")
    p.add_argument("--detector-model", default=None,
                   help="YOLO-World weights (enables the detector level only with --levels detector)")
    p.add_argument("--detector-conf", type=float, default=0.25)
    p.add_argument("--vlm-scenes-per-case", type=int, default=6)
    p.add_argument("--strip-frames", type=int, default=6)


def _config(args: argparse.Namespace) -> ExcavatorConfig:
    api_key = None
    if args.env_file:
        env = load_env_file(args.env_file)
        api_key = env.get(args.api_key_env)
        if not api_key:
            raise SystemExit(f"{args.api_key_env} not found in {args.env_file}")
    cfg = ExcavatorConfig(
        dataset_root=args.dataset_root.expanduser(),
        data_file=args.data_file,
        adapter=args.adapter,
        reference_dir=args.reference_dir
        or Path(__file__).resolve().parent.parent / "reference",
        out_dir=args.out,
        levels=tuple(x.strip() for x in args.levels.split(",") if x.strip()),
        scope=args.scope,
        families=args.families,
        limit=args.limit,
        detector_model=args.detector_model,
        detector_conf=args.detector_conf,
        vlm_scenes_per_case=args.vlm_scenes_per_case,
        strip_frames=args.strip_frames,
        close_read=not args.no_close_read,
    )
    cfg.api.base_url = args.api_base
    cfg.api.api_key_env = args.api_key_env
    cfg.api.api_key = api_key
    cfg.api.vlm_model = args.vlm_model
    cfg.api.judge_model = args.judge_model
    return cfg


def main(argv: list[str] | None = None) -> int:
    top = argparse.ArgumentParser(prog="excavator",
                                  description="Edge-Case Excavator engine")
    sub = top.add_subparsers(dest="cmd", required=True)

    p_ex = sub.add_parser("excavate", help="run the multi-level audit")
    _add_common(p_ex)

    p_ls = sub.add_parser("list-cases", help="dump the case registry")
    _add_common(p_ls)

    args = top.parse_args(argv)
    if args.cmd == "list-cases":
        cfg = _config(args)
        ref = Reference(cfg.reference_dir)
        cases = ref.filter(cfg.scope, cfg.families)
        print(f"reference: taxonomy v{ref.version}, "
              f"{len(ref.expectations)} expectations")
        stats = ref.stats()
        print(f"registry: {sum(stats['cases'].values())} cases by kind: {stats['cases']}")
        print(f"after filter (scope={cfg.scope}, families={cfg.families!r}): {len(cases)}")
        for c in cases[:20]:
            print(f"  {c.case_id}  [{c.kind}]  {c.name[:60]}")
        if len(cases) > 20:
            print(f"  ... and {len(cases) - 20} more")
        return 0

    result = run(_config(args))
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())
