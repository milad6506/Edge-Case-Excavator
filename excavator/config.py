"""Engine configuration and environment handling."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def load_env_file(path: str | Path) -> dict[str, str]:
    """Parse a .env-style file (KEY=VALUE lines, # comments) without exporting."""
    env: dict[str, str] = {}
    p = Path(path).expanduser()
    if not p.exists():
        raise FileNotFoundError(f"env file not found: {p}")
    for raw in p.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        env[key.strip()] = val.strip().strip("'\"")
    return env


@dataclass
class ApiConfig:
    """OpenAI-compatible endpoint (OpenRouter by default)."""

    base_url: str = "https://openrouter.ai/api/v1"
    api_key_env: str = "OPENROUTER_API_KEY"
    api_key: str | None = None
    vlm_model: str = "qwen/qwen3-vl-8b-instruct"
    judge_model: str = "z-ai/glm-5.3-flash"
    temperature: float = 0.2
    max_tokens: int = 512
    retries: int = 4
    timeout_s: int = 180

    def resolved_key(self) -> str | None:
        return self.api_key or os.environ.get(self.api_key_env)


@dataclass
class ExcavatorConfig:
    dataset_root: Path
    data_file: str | None = None          # DriveLM-style json; adapter may auto-detect
    adapter: str = "drivelm"
    reference_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent / "reference")
    out_dir: Path = field(default_factory=lambda: Path("runs/excavate"))
    levels: tuple[str, ...] = ("text",)   # subset of: text, vlm, detector
    scope: str = "all"                    # all | leaves | expectations
    families: str = ".*"                  # regex filter on case ids
    limit: int | None = None              # max scenes
    vlm_scenes_per_case: int = 6
    strip_frames: int = 6
    detector_model: str | None = None
    detector_conf: float = 0.25
    api: ApiConfig = field(default_factory=ApiConfig)
    close_read: bool = True               # L1c LLM close-reading of keyword hits
    unit_label: str | None = None         # assessment-unit description for findings

    def validate(self) -> None:
        if self.adapter not in ("drivelm", "nuscenes_flat"):
            raise ValueError(f"unknown adapter: {self.adapter}")
        unknown = set(self.levels) - {"text", "vlm", "detector"}
        if unknown:
            raise ValueError(f"unknown levels: {sorted(unknown)}")
        if self.scope not in ("all", "leaves", "expectations"):
            raise ValueError(f"unknown scope: {self.scope}")
        if not Path(self.reference_dir).is_dir():
            raise FileNotFoundError(f"reference dir not found: {self.reference_dir}")

    def needs_api(self) -> bool:
        return "vlm" in self.levels or (self.close_read and "text" in self.levels)
