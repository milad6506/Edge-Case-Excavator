"""Flat nuScenes tree adapter (no VQA json needed).

Scans <root>/samples/<CAM_*>/*.jpg, groups frames by the scene-tag prefix of
the filename (n008-2018-08-30-... style), one Scene per prefix. Text evidence
is absent at this level, which drives L1 verdicts to 'absent' and pushes
discovery to L2/L3 - the mode users run when they only have raw sensor data.
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from .base import BaseAdapter, Frame, Scene


class NuscenesFlatAdapter(BaseAdapter):
    name = "nuscenes_flat"

    _SCENE_RX = re.compile(r"^(n\d{3}-[\w-]+)__")

    def load(self, limit: int | None = None) -> list[Scene]:
        samples = self.root / "samples"
        if not samples.is_dir():
            samples = self.root  # allow passing .../nuscenes/samples directly
        buckets: dict[str, dict[str, dict[str, Path]]] = defaultdict(lambda: defaultdict(dict))
        for cam_dir in sorted(samples.glob("CAM_*")):
            for img in sorted(cam_dir.glob("*.jpg")):
                m = self._SCENE_RX.match(img.name)
                tag = m.group(1) if m else cam_dir.name
                buckets[tag][img.name[: len(img.stem)]][cam_dir.name] = img
        scenes: list[Scene] = []
        for tag in sorted(buckets):
            sc = Scene(token=tag, name=tag)
            for i, (stamp, cams) in enumerate(sorted(buckets[tag].items())):
                sc.frames.append(Frame(token=stamp, scene_token=tag, index=i, images=cams))
            scenes.append(sc)
            if limit and len(scenes) >= limit:
                break
        return scenes


def register(registry: dict) -> None:
    registry["nuscenes_flat"] = NuscenesFlatAdapter
