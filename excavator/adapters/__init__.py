from .base import BaseAdapter, Frame, Scene, TextRecord  # noqa: F401
from .drivelm import DriveLmAdapter  # noqa: F401
from .nuscenes_flat import NuscenesFlatAdapter  # noqa: F401

_REGISTRY: dict = {}


def get_adapter(name: str, dataset_root, data_file=None) -> BaseAdapter:
    import importlib
    for mod_name in ("drivelm", "nuscenes_flat"):
        mod = importlib.import_module(f".{mod_name}", __package__)
        mod.register(_REGISTRY)
    if name not in _REGISTRY:
        raise KeyError(f"unknown adapter {name!r}; known: {sorted(_REGISTRY)}")
    return _REGISTRY[name](dataset_root, data_file)
