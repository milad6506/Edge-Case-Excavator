"""Edge-Case Excavator engine.

Audits an ADS scenario database (nuScenes / DriveLM-like) against the
Excavator reference model (taxonomy v6, 221 behavioral expectations, 16
meta-actions) to mine EDGE, CORNER and MISSING cases.

Evidence levels:
  L1 text       - deterministic keyword sweep over descriptions/QA/annotations
  L2 vlm        - VLM judgment over per-scene multi-camera strips
  L3 detector   - open-vocabulary detector sweep (YOLO-World)
Fusion combines levels into per-case verdicts; co-occurrence mining yields
corner-case candidates; zero-evidence cases yield missing-case candidates.
"""

__version__ = "0.1.0"

from .config import ExcavatorConfig  # noqa: F401
from .reference import Reference, Case  # noqa: F401
