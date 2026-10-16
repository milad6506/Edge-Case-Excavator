"""Dataset adapter interface.

A Scene is the unit of audit: ordered frames, each with camera images and
textual records (descriptions, QA pairs, annotation objects). Adapters
translate concrete datasets (nuScenes/DriveLM exports, flat nuScenes trees)
into this shape.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


@dataclass
class TextRecord:
    kind: str          # description | qa | annotation | scene_description
    text: str


@dataclass
class Frame:
    token: str
    scene_token: str
    index: int
    images: dict[str, Path] = field(default_factory=dict)   # camera -> path
    texts: list[TextRecord] = field(default_factory=list)


@dataclass
class Scene:
    token: str
    name: str
    frames: list[Frame] = field(default_factory=list)
    texts: list[TextRecord] = field(default_factory=list)   # scene-level

    def corpus(self) -> list[tuple[str, str]]:
        """All textual evidence of the scene as (kind, text) pairs."""
        out = [(t.kind, t.text) for t in self.texts]
        for f in self.frames:
            out += [(t.kind, t.text) for t in f.texts]
        return out


Registry = dict[str, Callable[[], "BaseAdapter"]]


class BaseAdapter:
    name = "base"

    def __init__(self, dataset_root: Path, data_file: str | None = None):
        self.root = Path(dataset_root).expanduser()
        self.data_file = data_file

    def load(self, limit: int | None = None) -> list[Scene]:
        raise NotImplementedError
